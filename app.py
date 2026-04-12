import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin AI Recruiter Pro | Week 7",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (Your Specified Login System) ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Recruiter"}
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    if st.session_state.get("manager_login"):
        return {"ok": True, "user": st.session_state.manager_email, "role": "Manager"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("Recruitment Gateway")
    st.info("Indian Market Context | Week 7 Production")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            # Using your 'stretch' and 'Sign-UP' logic
            if st.button("Sign-UP", type="primary", use_container_width=True):
                try: 
                    st.login("auth0")
                except: 
                    st.error("Check Streamlit Secrets for [auth] block.")
                
    with col2:
        with st.form("staff_login"):
            st.subheader("Internal Staff")
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"admin_login": True, "admin_email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"manager_login": True, "manager_email": u})
                    st.rerun()
                else: 
                    st.error("Invalid Credentials")
    st.stop()

# --- 3. MAIN INTERFACE ---
conn = init_db()

with st.sidebar:
    st.title(f"👤 {auth['role']}")
    st.caption(f"Active: {auth['user']}")
    
    # BYOK: Sidebar API Key Input
    user_api_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=st.secrets.get("GEMINI_API_KEY", ""),
        help="Paste your API key here. It will override secrets."
    )

    if st.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

    st.divider()
    st.success("✅ Gemini 2.0 Flash Active")
    st.info("🌐 Week 7 Production Mode")

# --- 4. TABS (Production Lifecycle) ---
tabs = ["🚀 Sourcing Engine", "📋 Pipeline & Collaboration", "📊 Market Analytics"]
if auth["role"] != "Admin":
    tabs.remove("📊 Market Analytics")

active_tabs = st.tabs(tabs)

with active_tabs[0]:
    st.header("Agentic Sourcing Engine")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        jd = st.text_area("Job Description", height=200, placeholder="Paste JD...")
        with st.expander("Manual Overrides"):
            m_salary = st.number_input("Override Salary (LPA)", min_value=0.0)
            m_reloc = st.radio("Override Relocation", ["Use AI", "Yes", "No"])
            overrides = {"salary": m_salary if m_salary > 0 else None, 
                         "relocation": m_reloc if m_reloc != "Use AI" else None}
    
    with col_b:
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        if st.button("▶️ Start Production Pipeline", type="primary"):
            if user_api_key and jd and files:
                run_agent_workflow(user_api_key, jd, files, auth["user"], conn, save_candidate, overrides)
            else:
                st.warning("Ensure API Key, JD, and Files are present.")

with active_tabs[1]:
    st.header("Candidate Tracking & Team Notes")
    df = pd.read_sql("SELECT * FROM candidates", conn)
    if not df.empty:
        st.dataframe(df, use_container_width=True)
        with st.expander("💬 Add Team Feedback"):
            c_id = st.selectbox("Select Candidate ID", df['id'])
            note = st.text_area("Manager Comments")
            if st.button("Save Feedback"):
                st.success(f"Feedback saved for Candidate #{c_id}")
    else:
        st.info("No candidates processed yet.")

if auth["role"] == "Admin" and len(active_tabs) > 2:
    with active_tabs[2]:
        st.header("Predictive Hiring Insights")
        df = pd.read_sql("SELECT * FROM candidates", conn)
        if not df.empty:
            fig = px.scatter(df, x="score", y="prediction_score", color="edu_tier", size="salary_exp")
            st.plotly_chart(fig, use_container_width=True)
