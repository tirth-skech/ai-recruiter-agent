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
    """Extracts text from PDF or DOCX files."""
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

# --- REST OF YOUR EXISTING CODE ---
# class AgentState(TypedDict): ...
# --- STATE DEFINITION ---
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

# --- NODES ---
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
    
    # Using 2.0-flash for stability on Free Tier
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema)
    )
    return {"candidate_data": json.loads(response.text), "steps": state['steps'] + ["AI Screened"]}

# --- THE MISSING FUNCTION ---
"""
API DOCUMENTATION - WEEK 8 RECRUITMENT SERVICE
Endpoint: /api/v1/screen
Method: POST
Description: Triggers LangGraph Agentic Workflow for resume extraction.
"""

# ... (Previous imports and AgentState remain exactly the same)

def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    # Performance Optimization: Batch Processing Simulation
    for f in resume_files:
        # Existing logic maintained...
        text = get_document_text(f.read(), f.name)
        if text:
            # Simulated Microservice Call for Analytics
            result = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
            pred_score = PredictiveAnalytics.calculate_retention_score(result['candidate_data'])
            
            # GDPR Compliance: Anonymize data if privacy flag is set (handled in UI)
            save_func(db_conn, result['candidate_data'], 1, pred_score)
                
                # Save using Week 7 Schema
                save_func(db_conn, result['candidate_data'], 1, pred_score) # Assuming job_id 1 for demo
                st.success(f"✅ {result['candidate_data']['name']} Processed")
