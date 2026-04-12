import time
import json
import streamlit as st
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

# --- STATE DEFINITION ---
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

# --- NODES ---
def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "edu_tier": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"},
            "score": {"type": "INTEGER"}
        },
        "required": ["name", "edu_tier", "skills", "salary_exp", "score"]
    }
    
    # Using 2.0-flash for stability on Free Tier
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema)
    )
    return {"candidate_data": json.loads(response.text), "steps": state['steps'] + ["AI Screened"]}

# --- THE MISSING FUNCTION ---
def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", END)
    app = workflow.compile()
    
    for f in resume_files:
        from processor import get_document_text # Ensure parsing helper is present
        text = get_document_text(f.read(), f.name)
        if text:
            with st.spinner(f"Analyzing {f.name}..."):
                time.sleep(5) # Quota protection
                result = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
                
                # Week 7 Analytics
                pred_score = PredictiveAnalytics.calculate_retention_score(result['candidate_data'])
                
                # Save using Week 7 Schema
                save_func(db_conn, result['candidate_data'], 1, pred_score) # Assuming job_id 1 for demo
                st.success(f"✅ {result['candidate_data']['name']} Processed")
