import streamlit as st
from database import init_db, save_candidate
from processor import run_agent_workflow
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AI Recruiter Agent Pro", layout="wide", page_icon="🛡️")

# --- LOGIN SYSTEM ---
if "auth" not in st.session_state:
    st.session_state.auth = False
    st.session_state.role = None

def login_ui():
    st.title("🔐 Enterprise Recruitment Portal")
    col1, col2 = st.columns(2)
    
    with col1:
        st.info("Staff Login")
        with st.form("staff_form"):
            user = st.text_input("Corporate Email")
            pw = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if user == "admin@hr.com" and pw == "admin789":
                    st.session_state.auth, st.session_state.role, st.session_state.user = True, "Admin", user
                    st.rerun()
                elif user == "manager@hr.com" and pw == "manager423":
                    st.session_state.auth, st.session_state.role, st.session_state.user = True, "Manager", user
                    st.rerun()
                else: st.error("Invalid credentials")

    with col2:
        st.info("Recruiter Access")
        if st.button("Login with Auth0"):
            st.login("auth0") # Native Auth0 integration

# --- MAIN APPLICATION ---
if not st.session_state.auth:
    login_ui()
else:
    conn = init_db()
    st.sidebar.title(f"Role: {st.session_state.role}")
    st.sidebar.write(f"Logged: {st.session_state.user}")
    
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    # Navigation Tabs based on Role
    tabs = ["🚀 Agent Pipeline", "📊 Analytics"]
    if st.session_state.role == "Admin": tabs.append("⚙️ System")
    
    active_tabs = st.tabs(tabs)

    with active_tabs[0]:
        st.header("Agentic AI Workflow")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description", height=150)
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        if st.button("Run Pipeline"):
            run_agent_workflow(key, jd, files, st.session_state.user, conn, save_candidate)

    with active_tabs[1]:
        st.header("Candidate Insights")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df[['candidate_name', 'score', 'status', 'timestamp']])
            # Track B Analytics
            fig = px.scatter(df, x="score", y="diversity_index", color="status", size="api_latency", title="Match Score vs Diversity Index")
            st.plotly_chart(fig)
        else: st.write("No candidates processed yet.")
