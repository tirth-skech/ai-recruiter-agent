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
    # Placeholder for actual HackerEarth API implementation
    return True

# --- 4. AGENT NODES (Your Original Logic) ---
def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    
    prompt = f"""
    You are an expert Indian Technical Recruiter. Analyze the JD and Resume.
    JD: {state['jd']}
    Resume: {state['resume_text']}
    
    Extract the following JSON:
    {{
        "name": "Full Name",
        "email": "Email Address",
        "edu_tier": "Tier-1 or Tier-2 or Tier-3",
        "skills": ["skill1", "skill2"],
        "notice_period": "Immediate/15 days/30 days/90 days",
        "salary_exp": 0.0,
        "relocation": "Yes/No",
        "score": 0-100
    }}
    Tier-1: IIT, NIT, BITS, IIIT, DTU.
    Tier-2: VIT, SRM, Thapar, Manipal, VGEC, LD.
    """
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
        config=types.GenerateContentConfig(response_mime_type="application/json")
    )
    
    state['candidate_data'] = json.loads(response.text)
    state['steps'].append("AI Extraction Complete")
    return state

# --- 5. WORKFLOW ENGINE ---
def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    # Initialize Graph
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
                # --- RATE LIMIT FIX ---
                # Pause for 5 seconds to prevent 429 RESOURCE_EXHAUSTED
                time.sleep(5) 
                
                start_time = time.time()
                
                try:
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
                        if overrides.get("salary") is not None and overrides.get("salary") > 0:
                            candidate['salary_exp'] = overrides['salary']
                        if overrides.get("relocation") is not None and overrides.get("relocation") != "Use AI Extraction":
                            candidate['relocation'] = overrides['relocation']
                    
                    # --- AUTOMATION LOGIC ---
                    if candidate.get('edu_tier') == "Tier-1" and candidate.get('score', 0) > 80:
                        if trigger_hackerearth_invite(candidate.get('email')):
                            result['steps'].append("HackerEarth Assessment Sent")
                    
                    # Save to Database
                    save_func(db_conn, candidate, user_email, latency, result['steps'])
                    st.success(f"✅ Processed: {candidate.get('name')}")
                
                except Exception as e:
                    if "429" in str(e):
                        st.error(f"Rate limit exceeded. Waiting longer for {f.name}...")
                        time.sleep(10)
                    else:
                        st.error(f"Failed on {f.name}: {e}")
        else:
            st.error(f"Failed to read {f.name}")
