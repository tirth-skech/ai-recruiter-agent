import fitz
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
    # Clean JSON
    res_text = response.content.replace('```json', '').replace('```', '').strip()
    data = json.loads(res_text)
    return {"candidate_data": data, "steps": state['steps'] + ["AI Screening Complete"]}

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", END)
    
    chain = workflow.compile()
    
    for f in resume_files:
        # (Include your get_document_text logic here)
        # ...
        inputs = {"jd": jd_text, "resume_text": "extracted_text", "steps": [], "api_key": api_key}
        result = chain.invoke(inputs)
        save_func(db_conn, result['candidate_data'], email, 0.5, result['steps'])
