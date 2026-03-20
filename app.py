import streamlit as st
from database import init_db, save_candidate
from processor import run_agent_workflow
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="Goldwin AI Recruiter", layout="wide")

# --- AUTHENTICATION ---
if "auth" not in st.session_state:
    st.session_state.auth = False

def login():
    st.title("🛡️ Enterprise Login")
    with st.form("login"):
        user = st.text_input("Email")
        pw = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if user == "admin@goldwin.com" and pw == "cse2026":
                st.session_state.auth = True
                st.session_state.user = user
                st.rerun()
            else: st.error("Invalid Credentials")

# --- MAIN APP ---
if not st.session_state.auth:
    login()
else:
    conn = init_db()
    st.sidebar.title(f"User: {st.session_state.user}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    tab1, tab2 = st.tabs(["🚀 Recruitment Agent", "📊 Analytics Dashboard"])

    with tab1:
        st.header("Agentic Pipeline")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        if st.button("Start Agent"):
            run_agent_workflow(key, jd, files, st.session_state.user, conn, save_candidate)

    with tab2:
        st.header("Candidate Leaderboard")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df[['candidate_name', 'score', 'diversity_index', 'status']])
            fig = px.bar(df, x="candidate_name", y="score", color="diversity_index", title="Matching vs Diversity")
            st.plotly_chart(fig)
