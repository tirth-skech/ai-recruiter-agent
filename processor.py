import fitz  # PyMuPDF
import docx
import google.generativeai as genai
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import json
import streamlit as st
import io
import time

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

def get_document_text(file_bytes, filename):
    ext = filename.split('.')[-1].lower()
    if ext == 'pdf':
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        return chr(12).join([page.get_text() for page in doc]).strip()
    elif ext == 'docx':
        doc = docx.Document(io.BytesIO(file_bytes))
        return "\n".join([para.text for para in doc.paragraphs]).strip()
    return None

# --- AGENT TOOLS (NODES) ---
def screening_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    prompt = f"Analyze Resume: {state['resume_text']} against JD: {state['jd']}. Check for D&I bias. Return ONLY JSON: {{'name': 'str', 'score': int, 'is_qualified': bool, 'diversity_index': int, 'skills': []}}"
    response = llm.invoke(prompt)
    data = json.loads(response.content.replace('```json', '').replace('```', ''))
    return {"candidate_data": data, "steps": state['steps'] + ["Screened & D&I Analyzed"]}

def assessment_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    res = llm.invoke(f"Generate 3 tech questions for: {state['candidate_data'].get('skills', [])}")
    state['candidate_data']['assessment_questions'] = res.content
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Assessment Generated"]}

def scheduling_node(state: AgentState):
    state['candidate_data']['status'] = "Scheduled for Monday 10AM"
    return {"steps": state['steps'] + ["Interview Automatically Scheduled"]}

# --- WORKFLOW ---
def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    workflow.add_node("schedule", scheduling_node)
    workflow.set_entry_point("screen")
    
    workflow.add_conditional_edges("screen", lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject", {"qualified": "assess", "reject": END})
    workflow.add_edge("assess", "schedule")
    workflow.add_edge("schedule", END)
    
    chain = workflow.compile()

    for f in resume_files:
        text = get_document_text(f.read(), f.name)
        if text:
            start = time.time()
            result = chain.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
            save_func(db_conn, result['candidate_data'], email, time.time()-start, result['steps'])
            st.toast(f"Processed: {result['candidate_data']['name']}")
