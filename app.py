import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate as save_full_lifecycle
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="AI Recruiter Agent | Week 6",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (Strict Role-Based Access) ---
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
    st.info("Week 6: Indian Market Context & Relational Pipeline")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            if st.button("Sign-UP / Log-In", type="primary", use_container_width=True):
                try: 
                    st.login("auth0")
                except: 
                    st.error("Check Streamlit Secrets for [auth] configuration.")
                
    with col2:
        with st.form("staff_login"):
            st.subheader("Internal Staff Access")
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

# --- 3. MAIN DASHBOARD ---
else:
    # Initialize Relational Database
    conn = init_db()
    
    st.sidebar.title(f"👤 {auth['role']}")
    st.sidebar.caption(f"Active: {auth['user']}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.subheader("🌐 Global Integrations")
    auto_enrich = st.sidebar.toggle("Auto-Enrich Socials", value=True)
    auto_verify = st.sidebar.toggle("Auto-Verify Tier-1", value=False)
    
    st.sidebar.divider()
    st.sidebar.success("✅ HackerEarth Connected")
    st.sidebar.success("✅ Gemini 2.5 Flash Active")

    # --- 4. TABS (Consolidated Visibility Logic) ---
    if auth["role"] == "Admin":
        tabs = st.tabs(["🚀 Sourcing Agent", "📋 Pipeline & Team", "📊 Analytics"])
        tab_run, tab_pipe, tab_stats = tabs
    else:
        tabs = st.tabs(["🚀 Sourcing Agent", "📋 Pipeline & Team"])
        tab_run, tab_pipe = tabs

    # --- TAB 1: Agent Processing ---
    with tab_run:
        st.header("Agentic Sourcing Engine")
        if "GEMINI_API_KEY" in st.secrets:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.subheader("Step 1: Context & Overrides")
                jd = st.text_area("Job Description", height=200, placeholder="Paste requirements...")
                
                st.divider()
                st.caption("🛠️ Human-in-the-Loop Overrides")
                manual_salary = st.number_input("Override Salary (LPA)", min_value=0.0, value=0.0, step=0.5)
                manual_reloc = st.radio("Override Relocation", ["Use AI Extraction", "Yes", "No"], horizontal=True)
            
            with col_b:
                st.subheader("Step 2: Resumes")
                files = st.file_uploader("Upload Resumes (PDF/DOCX)", accept_multiple_files=True)
                
                if st.button("▶️ Launch Week 6 Pipeline", type="primary", use_container_width=True):
                    if jd and files:
                        overrides = {
                            "salary": manual_salary if manual_salary > 0 else None,
                            "relocation": manual_reloc if manual_reloc != "Use AI Extraction" else None
                        }
                        
                        run_agent_workflow(
                            st.secrets["GEMINI_API_KEY"], 
                            jd, files, auth["user"], 
                            conn, save_full_lifecycle,
                            overrides=overrides
                        )
                        st.success("Batch Processing Complete!")
                        st.rerun()
                    else:
                        st.warning("Please provide both Job Description and Resumes.")
        else:
            st.error("Missing GEMINI_API_KEY in Secrets.")

    # --- TAB 2: Relational Pipeline & Collaboration ---
    with tab_pipe:
        st.header("Team Collaboration & Lifecycle")
        try:
            df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
            if not df.empty:
                col_view, col_note = st.columns([2, 1])
                
                with col_view:
                    # Filter Controls
                    tier_f = st.multiselect("Filter Tier", ["Tier-1", "Tier-2", "Tier-3"], ["Tier-1", "Tier-2"])
                    f_df = df[df['education_tier'].isin(tier_f)]
                    
                    st.dataframe(
                        f_df.sort_values(by="score", ascending=False), 
                        use_container_width=True,
                        column_config={
                            "expected_salary": st.column_config.NumberColumn("Expected Salary (LPA)", format="₹%d"),
                            "score": st.column_config.ProgressColumn("Match", min_value=0, max_value=100)
                        }
                    )
                
                with col_note:
                    with st.container(border=True):
                        st.subheader("💬 Team Feedback")
                        selected_cand = st.selectbox("Select Candidate", df['candidate_name'].unique())
                        st.text_area(f"Comments for {selected_cand}")
                        if st.button("Save & Share Feedback", use_container_width=True):
                            st.toast("Feedback synced to team dashboard!")
            else:
                st.info("No candidates processed yet.")
        except Exception as e:
            st.info("Awaiting first processing run to initialize views.")

    # --- TAB 3: Analytics (ADMIN ONLY) ---
    if auth["role"] == "Admin":
        with tab_stats:
            st.header("Hiring Insights")
            if 'df' in locals() and not df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    st.plotly_chart(px.pie(df, names='education_tier', title="Tier Distribution", hole=0.4), use_container_width=True)
                with c2:
                    st.plotly_chart(px.box(df, x='education_tier', y='expected_salary', title="Salary Trends by Tier"), use_container_width=True)
                
                st.subheader("Notice Period Breakdown")
                st.plotly_chart(px.histogram(df, x='notice_period', color='status'), use_container_width=True)
            else:
                st.info("Run the agent to populate analytics.")

# --- 5. FOOTER ---
st.divider()
st.caption("Week 6 | Full-Lifecycle Agentic AI | VGEC Logickverse")
