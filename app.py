import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin AI Recruiter | Week 5",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION LOGIC ---
def get_auth_status():
    if st.session_state.get("is_logged_in"):
        return {
            "ok": True, 
            "user": st.session_state.user_email, 
            "role": st.session_state.user_role
        }
    return {"ok": False}

# Login Gate
if not st.session_state.get("is_logged_in"):
    st.title("🛡️ Enterprise Recruitment Portal")
    st.info("GTU Internship Week 5: Role-Based Access Control")
    
    with st.form("login_gate"):
        u = st.text_input("Corporate Email ")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In", use_container_width=True):
            if u == "admin@hr.com" and p == "admin789":
                st.session_state.update({"is_logged_in": True, "user_email": u, "user_role": "Admin"})
                st.rerun()
            elif u == "manager@hr.com" and p == "manager423":
                st.session_state.update({"is_logged_in": True, "user_email": u, "user_role": "Manager"})
                st.rerun()
            else:
                st.error("Invalid Credentials. Please check your email/password.")
    st.stop()

auth = get_auth_status()

# --- 3. MAIN DASHBOARD ---
conn = init_db()

# Sidebar Info
st.sidebar.title(f"👤 {auth['role']}")
st.sidebar.caption(f"Logged in as: {auth['user']}")

if st.sidebar.button("🚪 Logout", use_container_width=True):
    st.session_state.clear()
    st.rerun()

st.sidebar.divider()
st.sidebar.success("✅ Gemini 2.5 Flash Connected")
st.sidebar.success("✅ HackerEarth API Active")

# --- 4. DYNAMIC TAB DEFINITION ---
# Admin sees 3 tabs, Manager sees 2.
if auth["role"] == "Admin":
    tab_run, tab_pipe, tab_stats = st.tabs(["🚀 Run Pipeline", "📋 Pipeline Management", "📊 Market Analytics"])
else:
    tab_run, tab_pipe = st.tabs(["🚀 Run Pipeline", "📋 Pipeline Management"])

# --- TAB 1: RUN PIPELINE (Shared) ---
with tab_run:
    st.header("Agentic Sourcing Engine")
    if "GEMINI_API_KEY" in st.secrets:
        col_a, col_b = st.columns([1, 2])
        with col_a:
            st.subheader("Configuration")
            jd = st.text_area("Job Description", height=250, placeholder="Paste requirements here...")
            st.caption("Auto-trigger: Score > 80 + Tier-1 College")
        
        with col_b:
            st.subheader("Upload Resumes")
            files = st.file_uploader("Upload PDF or DOCX", accept_multiple_files=True)
            
            if st.button("▶️ Start Week 5 Pipeline", type="primary"):
                if jd and files:
                    run_agent_workflow(
                        st.secrets["GEMINI_API_KEY"], 
                        jd, files, auth["user"], 
                        conn, save_candidate
                    )
                else:
                    st.warning("Please provide both a Job Description and at least one Resume.")
    else:
        st.error("GEMINI_API_KEY missing in Streamlit Secrets.")

# --- TAB 2: PIPELINE MANAGEMENT (Shared) ---
with tab_pipe:
    st.header("Candidate Tracking System")
    df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
    
    if not df.empty:
        # Week 5 Market Filters
        f1, f2 = st.columns(2)
        with f1:
            tier_filter = st.multiselect("Filter by Tier", options=["Tier-1", "Tier-2", "Tier-3"], default=["Tier-1", "Tier-2"])
        with f2:
            search = st.text_input("Search Candidate Name")
            
        filtered_df = df[df['education_tier'].isin(tier_filter)]
        if search:
            filtered_df = filtered_df[filtered_df['candidate_name'].str.contains(search, case=False)]
            
        st.dataframe(
            filtered_df.sort_values(by="score", ascending=False),
            use_container_width=True,
            column_config={
                "expected_salary": st.column_config.NumberColumn("Salary (LPA)", format="₹%d"),
                "score": st.column_config.ProgressColumn("Match Score", min_value=0, max_value=100)
            }
        )
    else:
        st.info("No candidates processed yet.")

# --- TAB 3: MARKET ANALYTICS (Admin Only) ---
if auth["role"] == "Admin":
    with tab_stats:
        st.header("📈 Enterprise Hiring Analytics")
        df_stats = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        
        if not df_stats.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig_tier = px.pie(df_stats, names='education_tier', title="Tier Distribution (Indian System)")
                st.plotly_chart(fig_tier, use_container_width=True)
            with c2:
                fig_sal = px.histogram(df_stats, x="expected_salary", color="education_tier", title="Salary Expectations by Tier")
                st.plotly_chart(fig_sal, use_container_width=True)
        else:
            st.warning("Insufficient data for analytics.")
            
        st.divider()
        
        # --- RESET DATABASE SECURITY FEATURE ---
        st.subheader("⚠️ Danger Zone")
        st.write("Resetting the database will permanently delete all candidate records.")
        
        if st.button("🔥 Reset Database", type="secondary"):
            st.session_state.confirm_reset = True
            
        if st.session_state.get("confirm_reset"):
            confirm_p = st.text_input("Enter Admin Password to Wipe Database", type="password", key="reset_pass_input")
            if st.button("Confirm Permanent Delete", type="primary"):
                if confirm_p == "admin789":
                    if os.path.exists("recruiter_v5.db"):
                        os.remove("recruiter_v5.db")
                        st.success("Database wiped successfully. Refreshing...")
                        st.session_state.confirm_reset = False
                        time.sleep(2)
                        st.rerun()
                else:
                    st.error("Incorrect Password. Action Aborted.")

# --- FOOTER ---
st.divider()
st.caption("Gujarat Technological University | Agentic AI Internship | Track B - Week 5 Final")
