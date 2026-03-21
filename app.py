import streamlit as st
import pandas as pd
from processor import run_complex_agent
from database import init_db, save_full_journey

st.set_page_config(page_title="LangGraph AI Recruiter", layout="wide")
conn = init_db()

# --- Tool 5: Analytics Dashboard ---
def show_analytics(df):
    st.subheader("📊 Pipeline Analytics")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Sourced", len(df))
    col2.metric("Avg Match Score", f"{round(df['score'].mean(), 1)}%")
    col3.metric("Diversity Pass Rate", f"{round((df['diversity_flag'].sum()/len(df))*100, 1)}%")
    
    st.line_chart(df.set_index('timestamp')['score'])

# --- Main UI ---
tabs = st.tabs(["Sourcing & AI Agent", "Candidate Journey", "Analytics"])

with tabs[0]:
    st.header("Complex LangGraph Workflow")
    api_key = st.text_input("Gemini API Key", type="password")
    jd = st.text_area("Job Description")
    files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
    
    if st.button("Run Multi-Stage Agent"):
        results = run_complex_agent(api_key, jd, files)
        for res in results:
            save_full_journey(conn, res)
            st.success(f"Processed {res['name']} through LangGraph")

with tabs[1]:
    st.header("Candidate Journey Tracking")
    df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
    st.dataframe(df[['candidate_name', 'score', 'status', 'timestamp']])
    
    # Tool 6: Automated Scheduling
    st.divider()
    st.subheader("📅 Smart Scheduler")
    top_candidates = df[df['score'] > 70]['candidate_name'].tolist()
    selected = st.selectbox("Schedule Top Talent", top_candidates)
    if st.button("Sync to Google Calendar (Simulated)"):
        st.toast(f"Invite sent to {selected} for tomorrow at 10:00 AM!")

with tabs[2]:
    if not df.empty:
        show_analytics(df)
