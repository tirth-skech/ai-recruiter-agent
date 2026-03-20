import streamlit as st
from database import init_db, save_candidate
from processor import run_agent_workflow
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- AUTH LOGIC (THE FIX) ---
if "auth_status" not in st.session_state:
    st.session_state.auth_status = False
    st.session_state.user_email = ""
    st.session_state.user_role = ""

def check_auth():
    # 1. Check for Auth0 Login (Safe check)
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        st.session_state.auth_status = True
        st.session_state.user_email = st.user.get("email")
        st.session_state.user_role = "Recruiter"
        return True
    
    # 2. Check for Manual Session Auth
    if st.session_state.auth_status:
        return True
        
    return False

def login_screen():
    st.title("🛡️ Enterprise Recruitment Portal")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("External Recruiter")
        if st.button("Login with Auth0"):
            st.login("auth0")
    with c2:
        st.subheader("Internal Staff")
        with st.form("internal"):
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth_status": True, "user_role": "Admin", "user_email": u})
                    st.rerun()
                else: st.error("Invalid Credentials")

# --- MAIN APP ROUTING ---
if not check_auth():
    login_screen()
else:
    conn = init_db()
    st.sidebar.title(f"Role: {st.session_state.user_role}")
    st.sidebar.write(f"User: {st.session_state.user_email}")
    
    if st.sidebar.button("Logout"):
        if hasattr(st, "user") and st.user.get("is_logged_in"):
            st.logout()
        st.session_state.clear()
        st.rerun()

    t1, t2 = st.tabs(["🚀 Agent Pipeline", "📊 Analytics"])
    
    with t1:
        st.header("Agentic AI Workflow")
        # Automatically pulls from secrets.toml
        api_key = st.secrets["GEMINI_API_KEY"] 
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        if st.button("Run Agent Pipeline"):
            run_agent_workflow(api_key, jd, files, st.session_state.user_email, conn, save_candidate)

    with t2:
        st.header("Candidate Analytics")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df)
            fig = px.bar(df, x="candidate_name", y="score", color="status")
            st.plotly_chart(fig)
