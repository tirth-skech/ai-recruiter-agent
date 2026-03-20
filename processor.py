import fitz  # PyMuPDF
import docx
import json
import time
import streamlit as st
import io
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# --- 1. AGENT STATE DEFINITION ---
class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

# --- 2. DOCUMENT EXTRACTION ENGINE ---
def get_document_text(file_bytes, filename):
    """Extracts text from PDF and DOCX files safely."""
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            # Open PDF from bytes stream
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            # Open DOCX from bytes stream
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error parsing {filename}: {e}")
        return None
    return None

# --- 3. AGENT NODES (RECRUITMENT TOOLS) ---

def screening_node(state: AgentState):
    """Node 1: Screen resume against JD and check for D&I metrics."""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    
    prompt = f"""
    Task: Act as an expert HR Screening Agent.
    JD: {state['jd']}
    Resume: {state['resume_text']}
    
    Requirement: Return ONLY a valid JSON object with these keys:
    {{
        "name": "Full Name",
        "score": 0-100,
        "is_qualified": true/false,
        "diversity_index": 1-10,
        "skills": ["skill1", "skill2"]
    }}
    """
    
    response = llm.invoke(prompt)
    # Clean potential markdown formatting from LLM
    clean_json = response.content.replace('```json', '').replace('```', '').strip()
    data = json.loads(clean_json)
    
    return {
        "candidate_data": data, 
        "steps": state['steps'] + ["AI Screening & D&I Check Complete"]
    }

def assessment_node(state: AgentState):
    """Node 2: Generate technical questions based on identified skills."""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    skills = state['candidate_data'].get('skills', [])
    
    res = llm.invoke(f"Generate 3 highly technical interview questions for these skills: {skills}")
    
    # Update candidate data with generated questions
    updated_data = state['candidate_data']
    updated_data['tech_questions'] = res.content
    
    return {
        "candidate_data": updated_data, 
        "steps": state['steps'] + ["Technical Assessment Generated"]
    }

# --- 4. WORKFLOW ORCHESTRATION ---

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    """Compiles and executes the LangGraph recruitment pipeline."""
    
    # Initialize StateGraph
    workflow = StateGraph(AgentState)
    
    # Define Nodes
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    
    # Define Logic Flow
    workflow.set_entry_point("screen")
    
    # Conditional Edge: Only assess if qualified
    workflow.add_conditional_edges(
        "screen",
        lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject",
        {
            "qualified": "assess",
            "reject": END
        }
    )
    
    # Assessment always leads to end
    workflow.add_edge("assess", END)
    
    # Compile
    app = workflow.compile()
    
    # Process each uploaded file
    for f in resume_files:
        raw_bytes = f.read()
        text = get_document_text(raw_bytes, f.name)
        
        if text:
            with st.spinner(f"Agentic Pipeline: Processing {f.name}..."):
                start_time = time.time()
                
                # Execute Graph
                initial_state = {
                    "jd": jd_text, 
                    "resume_text": text, 
                    "steps": [], 
                    "api_key": api_key
                }
                result = app.invoke(initial_state)
                
                latency = time.time() - start_time
                
                # Persistence (Database)
                save_func(
                    db_conn, 
                    result['candidate_data'], 
                    email, 
                    latency, 
                    result['steps']
                )
                
                st.success(f"✅ Finished: {result['candidate_data'].get('name', f.name)}")
