import streamlit as st
from database import init_db, save_candidate
from processor import run_agent_workflow
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Goldwin AI Recruiter Pro", layout="wide")

# --- AUTHENTICATION LOGIC ---
if "auth_status" not in st.session_state:
    st.session_state.auth_status = False

def login_gateway():
    st.title("🛡️ Enterprise HR Portal")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recruiter Access")
        if st.button("Login with Auth0"):
            st.login("auth0") # Uses your secrets.toml config

    with col2:
        st.subheader("Internal Staff")
        with st.form("staff_login"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth_status": True, "role": "Admin", "user": u})
                    st.rerun()
                else: st.error("Access Denied")

# --- APP ROUTING ---
if not st.session_state.auth_status and not (hasattr(st, "user") and st.user.is_logged_in):
    login_gateway()
else:
    # Set session data from Auth0 if applicable
    if hasattr(st, "user") and st.user.is_logged_in:
        st.session_state.update({"auth_status": True, "role": "Recruiter", "user": st.user.email})

    conn = init_db()
    st.sidebar.title(f"User: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.logout() if hasattr(st, "user") else st.session_state.update({"auth_status": False})
        st.rerun()

    tab1, tab2 = st.tabs(["🚀 Agent Pipeline", "📊 Analytics"])

    with tab1:
        st.header("Agentic AI Workflow")
        # Automatically pull Gemini key from secrets
        gemini_key = st.secrets["GEMINI_API_KEY"]
        jd = st.text_area("Job Description", height=200)
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True, type=['pdf', 'docx'])
        
        if st.button("Run Pipeline"):
            if jd and files:
                run_agent_workflow(gemini_key, jd, files, st.session_state.user, conn, save_candidate)
            else: st.warning("Please provide both JD and Resumes.")

    with tab2:
        st.header("Candidate Leaderboard")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df[['candidate_name', 'score', 'status', 'timestamp']])
            fig = px.scatter(df, x="score", y="diversity_index", color="status", title="Matching vs D&I Analytics")
            st.plotly_chart(fig)
