import streamlit as st
import pandas as pd
from database import init_db, save_full_lifecycle
from processor import run_agent_workflow

st.set_page_config(page_title="Goldwin AI Recruiter v6", layout="wide")

# Persistent Database Connection
if 'conn' not in st.session_state:
    st.session_state.conn = init_db()

# 1. Sourcing Tab with HITL Overrides
tab_run, tab_pipe, tab_stats = st.tabs(["🚀 Agent Sourcing", "📋 Pipeline", "📊 Analytics"])

with tab_run:
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.subheader("Configuration")
        jd = st.text_area("Job Description")
        st.divider()
        st.caption("Human-in-the-Loop Overrides")
        m_salary = st.number_input("Force Salary (LPA)", value=0.0)
        m_reloc = st.radio("Force Relocation", ["Use AI Extraction", "Yes", "No"])
        
    with col_b:
        st.subheader("Upload Resumes")
        files = st.file_uploader("Upload", accept_multiple_files=True)
        if st.button("Launch Agent", type="primary"):
            if jd and files:
                overrides = {"salary": m_salary, "relocation": m_reloc}
                run_agent_workflow(st.secrets["GEMINI_API_KEY"], jd, files, 
                                 "admin@goldwin.com", st.session_state.conn, 
                                 save_full_lifecycle, overrides=overrides)
                st.rerun()

with tab_pipe:
    st.header("Candidate Tracking")
    df = pd.read_sql("SELECT * FROM recruitment_pipeline", st.session_state.conn)
    if not df.empty:
        st.dataframe(df.sort_values(by="score", ascending=False), use_container_width=True)
    else:
        st.info("No candidates processed yet.")

with tab_stats:
    st.header("Market Analytics")
    # ... (Plotly pie and box charts as per your previous version)
