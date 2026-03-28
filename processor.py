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

# --- 2. DOCUMENT PARSING (The "Eyes" of the Agent) ---
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

# --- 3. HACKEREARTH API INTEGRATION ---
def trigger_hackerearth_invite(candidate_email):
    """Sends automated test invitation via HackerEarth API V4."""
    url = "https://api.hackerearth.com/v4/partner/tests/invite/"
    
    # Validation: Ensure secrets exist
    if "hackerearth" not in st.secrets:
        st.error("HackerEarth secrets missing in Streamlit Cloud.")
        return False

    headers = {
        "client-secret": st.secrets["hackerearth"]["client_secret"],
        "Content-Type": "application/json"
    }
    
    # Using a generic test ID - replace with your actual ID from HE dashboard
    payload = {
        "test_id": "standard_tech_assessment_01", 
        "emails": [candidate_email]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        return response.status_code == 200
    except:
        return False

# --- 4. GRAPH NODES (Gemini 2.5 Flash Logic) ---
def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    
    # Week 5 Strict Schema for Indian Market
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "edu_tier": {"type": "STRING"}, # Tier-1, Tier-2, Tier-3
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "notice_period": {"type": "STRING"},
            "salary_exp": {"type": "NUMBER"},
            "relocation": {"type": "STRING"},
            "score": {"type": "INTEGER"},
            "is_qualified": {"type": "BOOLEAN"}
        },
        "required": ["name", "edu_tier", "skills", "notice_period", "score", "is_qualified"]
    }

    system_instr = """
    Act as a Senior Indian Technical Recruiter.
    1. Tiering: Label IIT, NIT, BITS, IIIT as 'Tier-1'. Label established state colleges as 'Tier-2'.
    2. Skills: Focus on Java, Python, React, and Data Science.
    3. Context: Extract Notice Period (e.g., 30 days) and Salary in LPA.
    4. Relocation: Identify if the candidate is willing to move.
    """

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
    return {"candidate_data": data, "steps": state['steps'] + ["2.5 Flash Screening Complete"]}

def assessment_node(state: AgentState):
    # This node could generate custom interview questions (Track B requirement)
    state['steps'].append("Technical Assessment Generated")
    return {"steps": state['steps']}

# --- 5. WORKFLOW ORCHESTRATION ---
def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func):
    # Build LangGraph
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    workflow.set_entry_point("screen")
    
    # Logic: Only assess if qualified
    workflow.add_conditional_edges(
        "screen", 
        lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject", 
        {"qualified": "assess", "reject": END}
    )
    workflow.add_edge("assess", END)
    app = workflow.compile()
    
    for f in resume_files:
        file_bytes = f.read()
        text = get_document_text(file_bytes, f.name)
        
        if text:
            with st.spinner(f"Processing {f.name}..."):
                start_time = time.time()
                # Run the Agentic Graph
                result = app.invoke({
                    "jd": jd_text, 
                    "resume_text": text, 
                    "steps": [], 
                    "api_key": api_key
                })
                
                candidate = result['candidate_data']
                latency = time.time() - start_time
                
                # --- WEEK 5: AUTO-INVITE TRIGGER ---
                if candidate.get('edu_tier') == "Tier-1" and candidate.get('score', 0) > 80:
                    if trigger_hackerearth_invite(user_email):
                        result['steps'].append("HackerEarth Assessment Sent")
                
                # Save to SQLite
                save_func(db_conn, candidate, user_email, latency, result['steps'])
                st.success(f"✅ Finished: {candidate.get('name')}")
        else:
            st.error(f"Could not parse text from {f.name}")
