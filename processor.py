import fitz, docx, io, json, time, requests, streamlit as st
from google import genai
from google.genai import types
from langgraph.graph import StateGraph, END
from typing import TypedDict, List
from database import log_api_status

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    api_key: str

# --- 5+ API INTEGRATIONS HUB ---
def call_social_enrichment(name):
    # Simulated Proxycurl/GitHub Enrichment
    return {"linkedin_url": f"linkedin.com/in/{name.replace(' ', '')}", "github_url": "github.com/dev-profile"}

# --- NODES ---
def screening_node(state: AgentState):
    client = genai.Client(api_key=state['api_key'])
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"}, "email": {"type": "STRING"},
            "edu_tier": {"type": "STRING"}, "score": {"type": "INTEGER"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"}, "relocation": {"type": "STRING"},
            "notice_period": {"type": "STRING"}
        },
        "required": ["name", "email", "edu_tier", "score"]
    }
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=f"JD: {state['jd']}\n\nResume: {state['resume_text']}",
        config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema)
    )
    return {"candidate_data": json.loads(response.text), "steps": state['steps'] + ["AI Screening"]}

def enrichment_node(state: AgentState):
    socials = call_social_enrichment(state['candidate_data']['name'])
    state['candidate_data'].update(socials)
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Social Enrichment"]}

# --- ORCHESTRATOR ---
def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    workflow = StateGraph(AgentState)
    workflow.add_node("screen", screening_node)
    workflow.add_node("enrich", enrichment_node)
    workflow.set_entry_point("screen")
    workflow.add_edge("screen", "enrich")
    workflow.add_edge("enrich", END)
    app = workflow.compile()

    for f in resume_files:
        bytes_data = f.read()
        text = ""
        if f.name.endswith('.pdf'):
            doc = fitz.open(stream=io.BytesIO(bytes_data), filetype="pdf")
            text = "\n".join([p.get_text() for p in doc])
            
        if text:
            with st.spinner(f"Agent Lifecycle: {f.name}..."):
                try:
                    time.sleep(5) # Pacing to avoid 429 error
                    result = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
                    candidate = result['candidate_data']
                    
                    if candidate['edu_tier'] == "Tier-1":
                        result['steps'].append("Assessment Triggered")
                    
                    save_func(db_conn, candidate, user_email, 0, result['steps'], overrides)
                    st.success(f"Processed {candidate['name']}")
                except Exception as e:
                    if "429" in str(e):
                        st.error("Quota Exceeded. Pausing...")
                        log_api_status(db_conn, "Gemini", 429, "Rate Limit")
                        break
