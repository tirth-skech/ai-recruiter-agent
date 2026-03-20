import streamlit as st
import pandas as pd
import plotly.express as px
from typing import TypedDict, List, Annotated
from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from pydantic import BaseModel, Field
import json
from pypdf import PdfReader
import datetime

# --- 1. DATA MODELS ---
class CandidateSchema(BaseModel):
    name: str = Field(description="Full name of the candidate")
    score: int = Field(description="Match score from 0 to 100")
    skills: List[str] = Field(description="List of technical skills found")
    experience_years: int = Field(description="Estimated years of experience")
    diversity_score: int = Field(description="Score for inclusivity and bias-free language 0-100")
    is_qualified: bool = Field(description="True if candidate matches > 75% of JD")

class AgentState(TypedDict):
    jd: str
    resume_text: str
    candidate_data: dict
    steps: List[str]
    next_node: str

# --- 2. AGENT NODES (RECRUITMENT TOOLS) ---

def screening_tool(state: AgentState):
    """Tool 1: AI Screening & ML Matching"""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=st.session_state.api_key)
    structured_llm = llm.with_structured_output(CandidateSchema)
    
    prompt = f"""
    Act as a Senior Technical Recruiter. Analyze this Resume against the Job Description.
    JD: {state['jd']}
    Resume: {state['resume_text']}
    Perform a bias-free assessment and calculate a diversity inclusion score.
    """
    result = structured_llm.invoke(prompt)
    return {"candidate_data": result.dict(), "steps": state['steps'] + ["Screening & Diversity Check Complete"]}

def assessment_tool(state: AgentState):
    """Tool 2: Technical Assessment Generation"""
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=st.session_state.api_key)
    skills = state['candidate_data']['skills']
    questions = llm.invoke(f"Generate 3 advanced technical interview questions for a candidate with these skills: {skills}")
    
    state['candidate_data']['tech_assessment'] = questions.content
    return {"candidate_data": state['candidate_data'], "steps": state['steps'] + ["Technical Assessment Generated"]}

def scheduling_tool(state: AgentState):
    """Tool 3: Automated Scheduling Logic"""
    # Simulated Calendar Integration
    next_monday = (datetime.date.today() + datetime.timedelta(days=(7 - datetime.date.today().weekday()))).strftime("%A, %b %d")
    state['candidate_data']['calendar_event'] = f"Interview confirmed for {next_monday} at 11:00 AM IST"
    return {"steps": state['steps'] + ["Calendar Integration: Interview Scheduled"]}

# --- 3. LANGGRAPH WORKFLOW ---
def build_recruitment_graph():
    workflow = StateGraph(AgentState)
    
    workflow.add_node("screen", screening_tool)
    workflow.add_node("assess", assessment_tool)
    workflow.add_node("schedule", scheduling_tool)
    
    workflow.set_entry_point("screen")
    
    # Track B: Complex Workflow Logic
    workflow.add_conditional_edges(
        "screen",
        lambda x: "qualified" if x["candidate_data"]["is_qualified"] else "reject",
        {"qualified": "assess", "reject": END}
    )
    
    workflow.add_edge("assess", "schedule")
    workflow.add_edge("schedule", END)
    
    return workflow.compile()

# --- 4. STREAMLIT INTERFACE ---
st.set_page_config(page_title="AI Recruiter Agent Pro", layout="wide")

if "api_key" not in st.session_state:
    st.session_state.api_key = ""

with st.sidebar:
    st.title("🛡️ Recruiter Dashboard")
    st.session_state.api_key = st.text_input("Gemini API Key", type="password")
    st.info("Track B: Agentic Workflow Active")

st.title("🤖 Agentic AI Recruiter (Week 4)")

c1, c2 = st.columns(2)
with c1:
    jd_input = st.text_area("Job Description", placeholder="Paste JD here...", height=200)
with c2:
    resume_file = st.file_uploader("Upload Candidate Resume", type="pdf")

if st.button("🚀 Start Agent Pipeline"):
    if not st.session_state.api_key or not resume_file:
        st.error("Missing API Key or Resume!")
    else:
        with st.spinner("Agent is navigating the pipeline..."):
            # 1. Parse PDF
            reader = PdfReader(resume_file)
            resume_text = "".join([p.extract_text() for p in reader.pages])
            
            # 2. Run LangGraph
            app = build_recruitment_graph()
            final_state = app.invoke({
                "jd": jd_input, 
                "resume_text": resume_text, 
                "steps": [], 
                "candidate_data": {}
            })
            
            data = final_state['candidate_data']
            
            # --- 5. ANALYTICS & RESULTS ---
            st.success(f"Pipeline Finished for {data.get('name', 'Candidate')}")
            
            col_a, col_b, col_c = st.columns(3)
            col_a.metric("Match Score", f"{data['score']}%")
            col_b.metric("Exp. Level", f"{data['experience_years']} Years")
            col_c.metric("Diversity Index", f"{data['diversity_score']}%")

            # Journey Tracking
            with st.expander("🛤️ Candidate Journey Log", expanded=True):
                for step in final_state['steps']:
                    st.write(f"✅ {step}")

            # Tools Outputs
            st.divider()
            t1, t2 = st.columns(2)
            with t1:
                st.subheader("📊 Diversity & Match Analytics")
                chart_data = pd.DataFrame({
                    "Category": ["Technical Match", "Experience", "D&I Compliance"],
                    "Value": [data['score'], data['experience_years'] * 10, data['diversity_score']]
                })
                fig = px.line_polar(chart_data, r='Value', theta='Category', line_close=True)
                st.plotly_chart(fig, use_container_width=True)
            
            with t2:
                st.subheader("📅 Scheduling & Assessment")
                if data['is_qualified']:
                    st.info(data.get('calendar_event', "Scheduling pending..."))
                    st.text_area("Generated Technical Questions", data.get('tech_assessment', ""), height=150)
                else:
                    st.warning("Candidate did not meet the qualification threshold for scheduling.")
