import fitz  # PyMuPDF
import docx
import io
import json
import time
import requests
import streamlit as st
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# --- STATE DEFINITION ---
class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

# --- DOCUMENT PARSING ---
def get_document_text(file_bytes, filename):
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None

# --- NODES ---
def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "edu_tier": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "notice_period": {"type": "STRING"},
            "salary_exp": {"type": "NUMBER"},
            "relocation": {"type": "STRING"},
            "score": {"type": "INTEGER"},
            "is_qualified": {"type": "BOOLEAN"}
        },
        "required": ["name", "edu_tier", "skills", "notice_period", "salary_exp", "relocation", "score", "is_qualified"]
    }

    # CRITICAL: Using gemini-2.0-flash to avoid ClientError
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    
    data = json.loads(response.text)
    return {"candidate_data": data, "steps": state['steps'] + ["AI Extraction Complete"]}

# --- WORKFLOW ---
def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", END)
    app = workflow.compile()
    
    for f in resume_files:
        file_bytes = f.read()
        text = get_document_text(file_bytes, f.name)
        
        if text:
            with st.spinner(f"Analyzing {f.name}..."):
                # --- MANDATORY DELAY FOR FREE TIER ---
                time.sleep(5) 
                
                try:
                    start_time = time.time()
                    result = app.invoke({
                        "jd": jd_text, 
                        "resume_text": text, 
                        "steps": [], 
                        "api_key": api_key
                    })
                    
                    candidate = result['candidate_data']
                    latency = time.time() - start_time
                    
                    # Apply Overrides
                    if overrides:
                        if overrides.get("salary") > 0:
                            candidate['salary_exp'] = overrides['salary']
                        if overrides.get("relocation") != "Use AI":
                            candidate['relocation'] = overrides['relocation']
                    
                    # Save to DB
                    save_func(db_conn, candidate, user_email, latency, result['steps'])
                    st.success(f"✅ Processed: {candidate.get('name')}")
                except Exception as e:
                    st.error(f"Error processing {f.name}: {e}")
