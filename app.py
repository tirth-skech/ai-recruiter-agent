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

# --- 2. AUTHENTICATION (Restored to Exact Specs) ---
def get_auth_status():
    # Check for Logged-in Recruiter
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Recruiter"}
    # Check for Session-based Admin
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    # Check for Session-based Manager
    if st.session_state.get("manager_login"):
        return {"ok": True, "user": st.session_state.manager_email, "role": "Manager"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("Recruitment Gateway")
    st.info("Indian Market Context")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            if st.button("Sign-UP", type="primary", use_container_width=True):
                try: 
                    st.login("auth")
                except: 
                    # Fallback for local testing environments
                    st.session_state.admin_login = True
                    st.session_state.admin_email = "recruiter@logickverse.com"
                    st.rerun()

    with col2:
        with st.container(border=True):
            st.subheader("Internal Portals")
            m_email = st.text_input("Work Email")
            m_pass = st.text_input("Password", type="password")
            
            c1, c2 = st.columns(2)
            if c1.button("Manager Login", use_container_width=True):
                if m_pass == "manager456":
                    st.session_state.manager_login = True
                    st.session_state.manager_email = m_email
                    st.rerun()
                else: st.error("Wrong Password")
                
            if c2.button("Admin Access", use_container_width=True):
                if m_pass == "admin789":
                    st.session_state.admin_login = True
                    st.session_state.admin_email = m_email
                    st.rerun()
                else: st.error("Wrong Password")
    st.stop()

# --- 3. INITIALIZE DB ---
conn = init_db()

# --- 4. SIDEBAR: BYOK & STATUS ---
with st.sidebar:
    st.header("⚙️ System Control")
    st.write(f"**Logged in as:** {auth['user']}")
    st.write(f"**Role:** {auth['role']}")
    
    # API Key Input (Masked)
    user_api_key = st.text_input(
        "Enter Gemini API Key", 
        type="password", 
        help="Get your key from Google AI Studio",
        value=st.secrets.get("GEMINI_API_KEY", "")
    )
    
    if not user_api_key:
        st.warning("⚠️ Enter API Key to enable AI")
    else:
        st.success("✅ API Key Loaded")
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. MAIN DASHBOARD ---
st.header(f"🎯 AI Recruiter Agent | {auth['role']} View")

tab1, tab2 = st.tabs(["📥 Bulk Screening", "📊 Analytics"])

with tab1:
    col1, col2 = st.columns([1, 2])
    
    with col1:
        st.subheader("Configuration")
        jd = st.text_area("Job Description", placeholder="Paste Job Requirements...", height=200)
        files = st.file_uploader("Upload Resumes (PDF/DOCX)", type=['pdf', 'docx'], accept_multiple_files=True)
        
        with st.expander("Manual Overrides"):
            salary_ov = st.number_input("Override Salary (LPA)", min_value=0.0)
            reloc_ov = st.selectbox("Override Relocation", ["Use AI", "Yes", "No"])
            overrides = {"salary": salary_ov if salary_ov > 0 else None, 
                         "relocation": reloc_ov if reloc_ov != "Use AI" else None}

        if st.button("🚀 Run Agentic Workflow", type="primary", use_container_width=True):
            if not user_api_key:
                st.error("Missing API Key! Look at the sidebar.")
            elif not jd or not files:
                st.warning("Please provide both a JD and at least one Resume.")
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
    st.subheader("Pipeline Analytics")
    try:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.plotly_chart(px.histogram(df, x="education_tier", color="status", title="Education Tier Distribution"), use_container_width=True)
            with c2:
                st.plotly_chart(px.scatter(df, x="score", y="expected_salary", color="education_tier", title="Score vs Salary Expectation"), use_container_width=True)
            
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No candidates processed yet.")
    except:
        st.error("Database initialization in progress...")

# --- 6. ADMIN TOOLS (RESTORED) ---
if auth["role"] == "Admin":
    st.divider()
    st.subheader("⚠️ Danger Zone")
    if st.button("🔥 Reset Database", type="secondary"):
        if os.path.exists("recruiter_v5.db"):
            os.remove("recruiter_v5.db")
            st.success("Database wiped. Refreshing...")
            time.sleep(1)
            st.rerun()

st.divider()
st.caption("Made by Logickverse Team | Agentic AI Internship | Week 5 & 7 Integration")
