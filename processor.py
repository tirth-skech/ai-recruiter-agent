import time
import json
import streamlit as st
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
import fitz  # PyMuPDF
import docx
import io

def get_document_text(file_bytes, filename):
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

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

class PredictiveAnalytics:
    @staticmethod
    def calculate_retention_score(data):
        base = data.get('score', 0)
        tier_bonus = 15 if data.get('edu_tier') == "Tier-1" else 5
        return round(min((base * 0.7) + tier_bonus, 100), 2)

def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "email": {"type": "STRING"},
            "edu_tier": {"type": "STRING"},
            "gender": {"type": "STRING", "enum": ["Male", "Female", "Other"]},
            "ethnicity": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"},
            "score": {"type": "INTEGER"}
        },
        "required": ["name", "email", "edu_tier", "gender", "ethnicity", "skills", "salary_exp", "score"]
    }
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(
            response_mime_type="application/json", 
            response_schema=schema,
            temperature=0.0
        )
    )
    return {"candidate_data": json.loads(response.text), "steps": state['steps'] + ["AI Screened"]}

def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", END)
    app = workflow.compile()
    
    count = 0
    for f in resume_files:
        content = f.read() # Read once
        text = get_document_text(content, f.name)
        if text:
            try:
                result = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
                data = result['candidate_data']
                
                # Apply Salary Overrides
                if overrides and overrides.get("salary"):
                    data['salary_exp'] = overrides["salary"]
                
                pred_score = PredictiveAnalytics.calculate_retention_score(data)
                
                # SAVE INSIDE LOOP
                save_func(db_conn, data, 1, pred_score)
                count += 1
                st.write(f"✅ Processed: {data['name']}")
            except Exception as e:
                st.error(f"Failed to process {f.name}: {e}")
        time.sleep(1) # Rate limit protection

    st.success(f"Pipeline finished! {count} candidates added.")
    time.sleep(2)
    st.rerun()
