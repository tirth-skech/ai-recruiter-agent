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

# --- 1. STATE DEFINITION ---
class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

# --- 2. DOCUMENT PARSING ---
def get_document_text(file_bytes, filename):
    """Extracts text from uploaded PDF or DOCX files."""
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
    return None

# --- 3. HACKEREARTH API ---
def trigger_hackerearth_invite(candidate_email):
    """Sends automated test invitation via HackerEarth API."""
    if "hackerearth" not in st.secrets:
        return False
    url = "https://api.hackerearth.com/v4/partner/tests/invite/"
    headers = {
        "client-secret": st.secrets["hackerearth"]["client_secret"],
        "Content-Type": "application/json"
    }
    payload = {"test_id": "standard_tech_01", "emails": [candidate_email]}
    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except:
        return False

# --- 4. GRAPH NODES (Gemini 2.5 Flash) ---# --- 4. GRAPH NODES (Strictly 2.5 Flash) ---
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

    system_instr = "Extract resume data into JSON. Identify Tier-1 vs Tier-2/3 schools."

    # UPDATE THIS LINE
    response = client.models.generate_content(
        model="gemini-2.5-flash", 
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(
            system_instruction=system_instr,
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    
    data = json.loads(response.text)
    return {"candidate_data": data, "steps": state['steps'] + ["AI Extraction Complete"]}

# --- 5. WORKFLOW ORCHESTRATION ---
def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    """
    Main entry point for the Agentic Workflow.
    overrides: dict containing manual 'salary' and 'relocation' values.
    """
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", END)
    app = workflow.compile()
    
    for f in resume_files:
        file_bytes = f.read()
        text = get_document_text(file_bytes, f.name)
        
        if text:
            with st.spinner(f"Agent analyzing {f.name}..."):
                start_time = time.time()
                
                # Invoke the LangGraph
                result = app.invoke({
                    "jd": jd_text, 
                    "resume_text": text, 
                    "steps": [], 
                    "api_key": api_key
                })
                
                candidate = result['candidate_data']
                latency = time.time() - start_time
                
                # --- APPLY MANUAL OVERRIDES FROM UI ---
                if overrides:
                    if overrides.get("salary") is not None:
                        candidate['salary_exp'] = overrides['salary']
                    if overrides.get("relocation") is not None:
                        candidate['relocation'] = overrides['relocation']
                
                # --- AUTOMATION LOGIC ---
                # Trigger HackerEarth only for Tier-1 with high score
                if candidate.get('edu_tier') == "Tier-1" and candidate.get('score', 0) > 80:
                    if trigger_hackerearth_invite(user_email):
                        result['steps'].append("HackerEarth Assessment Sent")
                
                # Save to SQLite
                save_func(db_conn, candidate, user_email, latency, result['steps'])
                st.success(f"✅ Processed: {candidate.get('name')}")
        else:
            st.error(f"Failed to read {f.name}")
