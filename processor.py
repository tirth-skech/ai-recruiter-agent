import time
import json
import streamlit as st
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import fitz  # PyMuPDF
import docx
import io

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

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

class PredictiveAnalytics:
    @staticmethod
    def calculate_retention_score(data):
        base = data.get('score', 0)
        tier_bonus = 15 if data.get('edu_tier') == "Tier-1" else 5
        return round(min((base * 0.7) + tier_bonus, 100), 2)

def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "edu_tier": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"},
            "score": {"type": "INTEGER"}
        },
        "required": ["name", "edu_tier", "skills", "salary_exp", "score"]
    }
    
    # Correct way to pass temperature to Gemini 2.0/2.5 Flash
    response = client.models.generate_content(
        model="gemini-2.5-flash", # Or gemini-2.5-flash
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=schema,
            temperature=0.0  # Pass directly inside GenerateContentConfig
        )
    )
    return {"candidate_data": json.loads(response.text), "steps": state['steps'] + ["AI Screened"]}
  

def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", END)
    app = workflow.compile()
    
    for f in resume_files:
        text = get_document_text(f.read(), f.name)
        if text:
            with st.spinner(f"Analyzing {f.name}..."):
                time.sleep(2) 
                result = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
                
                # --- APPLY OVERRIDES HERE ---
                if overrides:
                    if overrides.get("salary") is not None:
                        result['candidate_data']['salary_exp'] = overrides["salary"]
                    # If you have other overrides like 'relocation', apply them here
                
                # Calculate score based on the updated data
                pred_score = PredictiveAnalytics.calculate_retention_score(result['candidate_data'])
                
                # Save the updated data to the database
                save_func(db_conn, result['candidate_data'], 1, pred_score)
    st.success("Batch Processing Complete!")
