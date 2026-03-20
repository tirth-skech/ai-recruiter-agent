import fitz  # PyMuPDF
import docx
import json
import time
import streamlit as st
import io
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

def get_document_text(file_bytes, filename):
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes))
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except: return None

# --- AGENT NODES ---
def screening_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    prompt = f"Analyze Resume: {state['resume_text']} against JD: {state['jd']}. Return ONLY JSON: {{'name': 'str', 'score': int, 'is_qualified': bool, 'diversity_index': int, 'skills': []}}"
    response = llm.invoke(prompt)
    data = json.loads(response.content.replace('```json', '').replace('```', '').strip())
    return {"candidate_data": data, "steps": state['steps'] + ["AI Screening Complete"]}

def assessment_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    skills = state['candidate_data'].get('skills', [])
    res = llm.invoke(f"Generate 3 tech questions for skills: {skills}")
    state['candidate_data']['tech_questions'] = res.content
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Technical Assessment Generated"]}

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    workflow.set_entry_point("screen")
    workflow.add_conditional_edges("screen", lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "end", {"qualified": "assess", "end": END})
    workflow.add_edge("assess", END)
    
    app = workflow.compile()
    for f in resume_files:
        text = get_document_text(f.read(), f.name)
        if text:
            result = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
            save_func(db_conn, result['candidate_data'], email, 0.5, result['steps'])
            st.success(f"Processed: {result['candidate_data']['name']}")['steps'])
