import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_full_lifecycle
from processor import run_agent_workflow

# 1. SETUP
st.set_page_config(page_title="Goldwin AI Recruiter", layout="wide")

# 2. AUTHENTICATION
def get_auth_status():
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    if st.session_state.get("manager_login"):
        return {"ok": True, "user": st.session_state.manager_email, "role": "Manager"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("Enterprise Recruitment Gateway")
    u = st.text_input("Corporate Email")
    p = st.text_input("Password", type="password")
    if st.button("Sign In"):
        if u == "admin@hr.com" and p == "admin789":
            st.session_state.update({"admin_login": True, "admin_email": u})
            st.rerun()
        else:
            st.error("Invalid Credentials")
    st.stop()

# 3. MAIN APP
conn = init_db()
if "is_processing" not in st.session_state:
    st.session_state.is_processing = False

tab_run, tab_pipe, tab_stats = st.tabs(["🚀 Sourcing", "📋 Pipeline", "📊 Analytics"])

with tab_run:
    st.header("Sourcing Engine")
    jd = st.text_area("Job Description")
    files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
    
    if st.button("Launch Agent") or st.session_state.is_processing:
        if jd and files:
            st.session_state.is_processing = True
            try:
                run_agent_workflow(
                    st.secrets["GEMINI_API_KEY"], 
                    jd, files, auth["user"], 
                    conn, save_full_lifecycle
                )
            finally:
                st.session_state.is_processing = False
            st.success("Done!")
            st.rerun()

with tab_pipe:
    st.header("Pipeline")
    try:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        st.dataframe(df)
    except:
        st.info("No data yet.")

with tab_stats:
    st.header("Analytics")
    try:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.plotly_chart(px.pie(df, names='education_tier', hole=0.5))
    except:
        st.info("Run the agent first.")
