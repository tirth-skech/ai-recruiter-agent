import fitz
import docx
import json
import time
import streamlit as st
import io
from google import genai
from google.genai import types
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
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except: return None

def screening_node(state: AgentState):
    # Initialize the 2.5-era Native Client
    client = genai.Client(api_key=state['api_key'])
    
    # Define the Strict Schema for 2.5 Flash
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "score": {"type": "INTEGER"},
            "is_qualified": {"type": "BOOLEAN"},
            "diversity_index": {"type": "INTEGER"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}}
        },
        "required": ["name", "score", "is_qualified", "diversity_index", "skills"]
    }

    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(
            system_instruction="You are a 2.5 Flash Screening Agent. Extract data into the requested JSON schema.",
            response_mime_type="application/json",
            response_schema=schema,
        ),
    )
    
    data = json.loads(response.text)
    return {"candidate_data": data, "steps": state['steps'] + ["2.5 Flash Screening Complete"]}

def assessment_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    skills = state['candidate_data'].get('skills', [])
    
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"Generate 3 expert technical interview questions for a candidate with these skills: {skills}",
    )
    
    state['candidate_data']['tech_questions'] = response.text
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["2.5 Flash Assessment Generated"]}

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("assess", assessment_node)
    workflow.set_entry_point("screen")
    
    workflow.add_conditional_edges(
        "screen", 
        lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject", 
        {"qualified": "assess", "reject": END}
    )
    workflow.add_edge("assess", END)
    
    app = workflow.compile()
    
    for f in resume_files:
        text = get_document_text(f.read(), f.name)
        if text:
            with st.spinner(f"2.5 Flash Pipeline: {f.name}"):
                start = time.time()
                res = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
                save_func(db_conn, res['candidate_data'], email, time.time()-start, res['steps'])
                st.success(f"✅ Processed: {res['candidate_data'].get('name', f.name)}")
