import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="AI Recruiter Agent | Week 5",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION ---
def get_auth_status():
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    # Defaulting to demo session for your testing
    return {"ok": True, "user": "admin@goldwin.com", "role": "Admin"}

auth = get_auth_status()
conn = init_db()

# --- 3. SIDEBAR: BYOK (Bring Your Own Key) ---
with st.sidebar:
    st.title("⚙️ Configuration")
    
    # Input for API Key
    user_api_key = st.text_input(
        "Enter Gemini API Key", 
        type="password", 
        help="Get your key from https://aistudio.google.com/",
        value=st.secrets.get("GEMINI_API_KEY", "") 
    )
    
    if not user_api_key:
        st.warning("⚠️ Please enter your API Key to proceed")
    else:
        st.success("✅ API Key Loaded")

    st.divider()
    st.info(f"Logged in as: {auth['user']}")

# --- 4. MAIN INTERFACE ---
st.header("🎯 AI Recruiter Agent (Gemini 2.0 Flash)")

tab1, tab2 = st.tabs(["📥 Bulk Screening", "📊 Analytics"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Screening Setup")
        jd = st.text_area("Job Description", placeholder="Paste JD here...", height=200)
        files = st.file_uploader("Upload Resumes", type=['pdf', 'docx'], accept_multiple_files=True)
        
        with st.expander("Manual Overrides"):
            salary_ov = st.number_input("Override Salary (LPA)", min_value=0.0)
            reloc_ov = st.selectbox("Override Relocation", ["Use AI", "Yes", "No"])
            overrides = {"salary": salary_ov, "relocation": reloc_ov}

        if st.button("🚀 Run 2.0 Flash Agent", type="primary"):
            if not user_api_key:
                st.error("Missing API Key! Please enter it in the sidebar.")
            elif not jd or not files:
                st.warning("Please provide a JD and at least one Resume.")
            else:
                run_agent_workflow(
                    user_api_key, 
                    jd, 
                    files, 
                    auth["user"], 
                    conn, 
                    save_candidate, 
                    overrides=overrides
                )

with tab2:
    # Basic Analytics View
    try:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            fig = px.histogram(df, x="education_tier", title="Candidates by Tier")
            st.plotly_chart(fig)
        else:
            st.info("No data processed yet.")
    except Exception as e:
        st.error("Database not initialized or empty.")
