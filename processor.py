import fitz  # PyMuPDF
import docx
import json
import time
import streamlit as st
import io
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# --- 1. AGENT STATE ---
class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

# --- 2. DOCUMENT PARSER ---
def get_document_text(file_bytes, filename):
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            # Use io.BytesIO for Streamlit file buffers
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error parsing {filename}: {e}")
        return None
    return None

# --- 3. AGENT NODES ---
def screening_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    prompt = f"""
    Analyze Resume: {state['resume_text']} 
    against JD: {state['jd']}. 
    Return ONLY valid JSON: 
    {{
        "name": "str", 
        "score": int, 
        "is_qualified": bool, 
        "diversity_index": int, 
        "skills": []
    }}
    """
    response = llm.invoke(prompt)
    # Clean the LLM output to ensure it's pure JSON
    res_text = response.content.replace('```json', '').replace('```', '').strip()
    data = json.loads(res_text)
    return {"candidate_data": data, "steps": state['steps'] + ["AI Screening Complete"]}

def assessment_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    skills = state['candidate_data'].get('skills', [])
    res = llm.invoke(f"Generate 3 technical interview questions based on these skills: {skills}")
    state['candidate_data']['tech_questions'] = res.content
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Assessment Generated"]}

# --- 4. WORKFLOW ORCHESTRATOR ---
def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    # Initialize the Graph
    workflow = StateGraph(AgentState)
    
    # Add Nodes
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    
    # Set entry point
    workflow.set_entry_point("screen")
    
    # Logic: If qualified -> assess; else -> end
    workflow.add_conditional_edges(
        "screen", 
        lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "end",
        {"qualified": "assess", "end": END}
    )
    
    workflow.add_edge("assess", END)
    
    # Compile the graph
    app = workflow.compile()
    
    for f in resume_files:
        raw_bytes = f.read()
        text = get_document_text(raw_bytes, f.name)
        
        if text:
            with st.spinner(f"Agent processing {f.name}..."):
                start_time = time.time()
                # Run the Agentic Chain
                inputs = {"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key}
                result = app.invoke(inputs)
                
                latency = time.time() - start_time
                
                # Save to Database (using your save_candidate function)
                save_func(db_conn, result['candidate_data'], email, latency, result['steps'])
                st.success(f"Successfully processed: {result['candidate_data']['name']}")
