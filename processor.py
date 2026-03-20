import fitz
import docx
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import json
import streamlit as st
import io
import time

# --- 1. AGENT STATE DEFINITION ---
class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

# --- 2. THE 4+ RECRUITMENT TOOLS (Nodes) ---

def screening_node(state: AgentState):
    """Tool 1 & 2: Sourcing + AI Screening with ML Matching"""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    
    prompt = f"""
    Analyze Resume: {state['resume_text']} against JD: {state['jd']}.
    Perform a Diversity & Inclusion (D&I) check for bias-free language.
    Return ONLY JSON: 
    {{
        "name": "str", "score": int, "summary": "str", 
        "is_qualified": bool, "diversity_index": int, "skills": []
    }}
    """
    response = llm.invoke(prompt)
    data = json.loads(response.content.replace('```json', '').replace('```', ''))
    return {"candidate_data": data, "steps": state['steps'] + ["Screened & D&I Analyzed"]}

def assessment_node(state: AgentState):
    """Tool 3: Technical Assessment Generation"""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    skills = state['candidate_data'].get('skills', [])
    res = llm.invoke(f"Generate 3 technical questions for a candidate with skills: {skills}")
    state['candidate_data']['assessment_questions'] = res.content
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Assessment Generated"]}

def scheduling_node(state: AgentState):
    """Tool 4: Automated Scheduling logic"""
    # Mocking a calendar integration
    state['candidate_data']['scheduled_slot'] = "Next Monday at 10:00 AM"
    state['candidate_data']['invite'] = f"Hi {state['candidate_data']['name']}, your interview is scheduled."
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Interview Scheduled"]}

# --- 3. WORKFLOW CONSTRUCTION ---
def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    workflow.add_node("schedule", scheduling_node)
    
    workflow.set_entry_point("screen")
    
    # Track B requirement: Complex workflow logic
    workflow.add_conditional_edges(
        "screen",
        lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject",
        {"qualified": "assess", "reject": END}
    )
    workflow.add_edge("assess", "schedule")
    workflow.add_edge("schedule", END)
    
    app = workflow.compile()

    for f in resume_files:
        with st.spinner(f"Agent Navigating Pipeline: {f.name}..."):
            resume_text = get_document_text(f.read(), f.name)
            if not resume_text: continue
            
            start = time.time()
            inputs = {"jd": jd_text, "resume_text": resume_text, "steps": [], "api_key": api_key}
            result = app.invoke(inputs)
            
            # Save all data including Track B Journey Steps
            latency = time.time() - start
            save_func(db_conn, result['candidate_data'], email, latency, result['steps'])
            
            # UI Feedback
            st.success(f"Pipeline Complete: {result['candidate_data']['name']}")
