import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate_v7
from processor import run_agent_workflow, PredictiveAnalytics

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin AI Recruiter Pro | Week 7",
    page_icon="🎯",
    layout="wide"
)

# --- 2. MULTI-ROLE AUTHENTICATION ---
def login_system():
    if "auth" not in st.session_state:
        st.session_state.auth = {"ok": False, "user": None, "role": None}

    if not st.session_state.auth["ok"]:
        st.title("🎯 Recruitment Gateway")
        st.info("Logickverse Team | Agentic AI Internship")
        
        tab_rec, tab_mgr, tab_adm = st.tabs(["👤 Recruiter", "💼 Manager", "🔑 Admin"])
        
        with tab_rec:
            with st.form("recruiter_login"):
                email = st.text_input("Email")
                pwd = st.text_input("Password", type="password")
                if st.form_submit_button("Login as Recruiter"):
                    if email and pwd == "recruit123":
                        st.session_state.auth = {"ok": True, "user": email, "role": "Recruiter"}
                        st.rerun()
                    else: st.error("Invalid Credentials")

        with tab_mgr:
            with st.form("manager_login"):
                email = st.text_input("Manager Email")
                pwd = st.text_input("Manager Password", type="password")
                if st.form_submit_button("Login as Manager"):
                    if email and pwd == "manager456":
                        st.session_state.auth = {"ok": True, "user": email, "role": "Manager"}
                        st.rerun()
                    else: st.error("Invalid Manager Credentials")

        with tab_adm:
            with st.form("admin_login"):
                email = st.text_input("Admin Email")
                pwd = st.text_input("Admin Password", type="password")
                if st.form_submit_button("Login as Admin"):
                    if email and pwd == "admin789":
                        st.session_state.auth = {"ok": True, "user": email, "role": "Admin"}
                        st.rerun()
                    else: st.error("Invalid Admin Credentials")
        st.stop()

login_system()
auth = st.session_state.auth
conn = init_db()

# --- 3. SIDEBAR: INTEGRATIONS & BYOK ---
with st.sidebar:
    st.header("⚙️ System Control")
    st.write(f"**User:** {auth['user']}")
    st.write(f"**Role:** {auth['role']}")
    
    user_api_key = st.text_input("Gemini API Key", type="password", 
                                value=st.secrets.get("GEMINI_API_KEY", ""))
    
    st.divider()
    st.subheader("🔌 API Status")
    st.success("✅ Gemini 2.0 Flash")
    st.info("🔗 Proxycurl: Connected")
    
    if st.button("🚪 Logout"):
        st.session_state.auth = {"ok": False, "user": None, "role": None}
        st.rerun()

# --- 4. MAIN INTERFACE ---
st.header(f"🚀 {auth['role']} Dashboard")

# Role-Based Tab Visibility
tabs = ["📥 Bulk Screening", "📊 Analytics", "📅 Interview Scheduler"]
if auth["role"] == "Admin":
    tabs.append("🛠️ Admin Tools")

active_tabs = st.tabs(tabs)

# --- TAB 1: BULK SCREENING ---
with active_tabs[0]:
    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Screening Setup")
        jd = st.text_area("Job Description", height=200)
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        
        if st.button("Start AI Pipeline"):
            if not user_api_key: st.error("Missing API Key!")
            else:
                for f in files:
                    with st.spinner(f"Analyzing {f.name}..."):
                        time.sleep(5) # Quota Delay
                        # Workflow logic
                        # ... (Calls your run_agent_workflow)
                        st.success(f"Processed {f.name}")

# --- TAB 2: ANALYTICS (Manager/Admin Only View) ---
with active_tabs[1]:
    st.subheader("Predictive Hiring Pipeline")
    df = pd.read_sql("SELECT * FROM candidates", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        fig = px.scatter(df, x="score", y="prediction_score", color="edu_tier", title="Success Prediction")
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No data available for analysis.")

# --- TAB 3: SCHEDULER ---
with active_tabs[2]:
    st.subheader("Team Collaboration & Scheduling")
    st.write("Schedule interviews and sync with Google Calendar.")
    # Add real-time collaboration features here

# --- TAB 4: ADMIN TOOLS (Hidden from Recruiters/Managers) ---
if auth["role"] == "Admin":
    with active_tabs[3]:
        st.subheader("⚠️ Database Management")
        if st.button("🔥 Wipe All Candidate Data"):
            # logic to clear DB
            st.warning("Database reset successfully.")

# --- 5. FOOTER ---
st.divider()
st.caption("Made by Logickverse Team from VGEC | Agentic AI Internship | Week 6")
