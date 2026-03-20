import fitz  # PyMuPDF
import docx
import json
import time
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

def screening_node(state: AgentState):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=state['api_key'])
    prompt = f"Analyze Resume: {state['resume_text']} against JD: {state['jd']}. Return ONLY JSON: {{'name': 'str', 'score': int, 'is_qualified': bool, 'diversity_index': int, 'skills': []}}"
    response = llm.invoke(prompt)
    data = json.loads(response.content.replace('```json', '').replace('```', ''))
    return {"candidate_data": data, "steps": state['steps'] + ["AI Screening Complete"]}

def assessment_node(state: AgentState):
    # Tool: Generate Tech Questions
    return {"steps": state['steps'] + ["Technical Assessment Generated"]}

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    workflow.set_entry_point("screen")
    workflow.add_conditional_edges("screen", lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject", {"qualified": "assess", "reject": END})
    workflow.add_edge("assess", END)
    
    app = workflow.compile()
    # Processing logic for each file...
