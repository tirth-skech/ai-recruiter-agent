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
    st.info("Indian Market Context")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            # 2026 Fix: width='stretch'
            if st.button("Sign-UP", type="primary", width="stretch"):
                try: st.login("auth0")
                except: st.error("Check Streamlit Secrets for [auth] block.")
                
    with col2:
        with st.form("staff_login"):
            st.subheader("Internal Staff")
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            # 2026 Fix: width='stretch'
            if st.form_submit_button("Sign In", width="stretch"):
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
    conn = init_db()
    
    st.sidebar.title(f"👤 {auth['role']}")
    st.sidebar.caption(f"Active: {auth['user']}")
    
    # 2026 Fix: width='stretch'
    if st.sidebar.button("🚪 Logout", width="stretch"):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.success("✅ HackerEarth Connected")
    st.sidebar.success("✅ Gemini 2.5 Flash Active")

    # --- 4. TABS (Strict Visibility Logic) ---
    if auth["role"] == "Admin":
        tab_run, tab_pipe, tab_stats = st.tabs([
            "🚀 Run 2.5 Flash Agent", 
            "📋 Pipeline Management", 
            "📊 Market Analytics"
        ])
    else:
        # Managers & External Recruiters cannot see Analytics
        tab_run, tab_pipe = st.tabs([
            "🚀 Run 2.5 Flash Agent", 
            "📋 Pipeline Management"
        ])

    # TAB 1: Processing
    # TAB 1: Processing
    with tab_run:
        st.header("Agentic Sourcing Engine")
        if "GEMINI_API_KEY" in st.secrets:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.subheader("Step 1: Context & Overrides")
                jd = st.text_area("Job Description", height=150, placeholder="Paste JD...")
                
                # --- NEW MANUAL OVERRIDE FIELDS ---
                st.write("---")
                st.caption("🛠️ Manual Overrides (Optional)")
                manual_salary = st.number_input("Override Salary (LPA)", min_value=0.0, value=0.0, step=0.5, help="Set a specific salary if known.")
                manual_reloc = st.radio("Override Relocation", ["Use AI Extraction", "Yes", "No"], horizontal=True)
                # ----------------------------------
                
                test_id = st.text_input("HackerEarth Test ID", value="python_dev_01")
            
            with col_b:
                st.subheader("Step 2: Resumes")
                files = st.file_uploader("Upload Resumes (PDF/DOCX)", accept_multiple_files=True)
                
                if st.button("▶️ Start Week 5 Pipeline", type="primary"):
                    if jd and files:
                        # Prepare override dictionary to pass to the workflow
                        overrides = {
                            "salary": manual_salary if manual_salary > 0 else None,
                            "relocation": manual_reloc if manual_reloc != "Use AI Extraction" else None
                        }
                        
                        run_agent_workflow(
                            st.secrets["GEMINI_API_KEY"], 
                            jd, files, auth["user"], 
                            conn, save_candidate,
                            overrides=overrides # Passing the new overrides
                        )
                    else:
                        st.warning("Please provide both JD and Resumes.")
        else:
            st.error("Missing GEMINI_API_KEY in Secrets.")
    # ... (Auth logic same as Week 5) ...

# NEW FOR WEEK 6: COLLABORATION TAB
with tab_pipe:
    st.header("Team Collaboration & Lifecycle")
    # Display candidates with a "View Details" button
    # When clicked, open a sidebar to add notes
    with st.expander("💬 Add Team Feedback"):
        note = st.text_area("Hiring Manager Comments")
        if st.button("Save Feedback"):
            # Logic to save to team_notes table
            st.success("Note shared with the team!")

# NEW FOR WEEK 6: SOURCE SETTINGS
with st.sidebar:
    st.divider()
    st.subheader("🌐 Global Integrations")
    st.toggle("Auto-Enrich Socials", value=True)
    st.toggle("Auto-Verify Tier-1", value=False)
  

    # TAB 2: Pipeline Management
    with tab_pipe:
        st.header("Candidate Tracking System")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        
        if not df.empty:
            f1, f2, f3 = st.columns(3)
            with f1:
                tier_sel = st.multiselect("Education Tier", options=["Tier-1", "Tier-2", "Tier-3"], default=["Tier-1", "Tier-2"])
            with f2:
                status_sel = st.multiselect("Status", options=df['status'].unique(), default=df['status'].unique())
            with f3:
                reloc_sel = st.radio("Relocation Willingness", ["All", "Yes", "No"], horizontal=True)

            filtered_df = df[df['education_tier'].isin(tier_sel) & df['status'].isin(status_sel)]
            if reloc_sel != "All":
                filtered_df = filtered_df[filtered_df['relocation_willing'] == reloc_sel]

            st.dataframe(
                filtered_df.sort_values(by="score", ascending=False), 
                width="stretch", # 2026 Update
                column_config={
                    "expected_salary": st.column_config.NumberColumn("Expected Salary (LPA)", format="₹%d"),
                    "score": st.column_config.ProgressColumn("Match Score", min_value=0, max_value=100)
                }
            )
        else:
            st.info("No candidates processed yet.")

    # TAB 3: Market Analytics (ADMIN ONLY)
    if auth["role"] == "Admin":
        with tab_stats:
            st.header("Hiring Insights")
            if not df.empty:
                c1, c2 = st.columns(2)
                with c1:
                    fig_tier = px.pie(df, names='education_tier', title="Tier-1 vs Others")
                    st.plotly_chart(fig_tier, width="stretch")
                with c2:
                    fig_salary = px.box(df, x='education_tier', y='expected_salary', title="Salary Expectations by Tier")
                    st.plotly_chart(fig_salary, width="stretch")
                
                st.subheader("Notice Period Breakdown")
                fig_notice = px.histogram(df, x='notice_period', color='status')
                st.plotly_chart(fig_notice, width="stretch")
            
            st.divider()
            
            # --- PROTECTED RESET FEATURE ---
            st.subheader("⚠️ Danger Zone")
            if st.button("🔥 Reset Database", type="secondary"):
                st.session_state.confirm_reset = True
                
            if st.session_state.get("confirm_reset"):
                # Use a unique key for the input to avoid state collision
                confirm_p = st.text_input("Enter Admin Password to confirm wipe", type="password", key="reset_gate")
                if st.button("Confirm Permanent Delete", type="primary"):
                    if confirm_p == "admin789":
                        if os.path.exists("recruiter_v5.db"):
                            os.remove("recruiter_v5.db")
                            st.success("Database wiped. Refreshing...")
                            st.session_state.confirm_reset = False
                            time.sleep(2)
                            st.rerun()
                    else:
                        st.error("Incorrect Password. Action Aborted.")

# --- 5. FOOTER ---
st.divider()
st.caption("Made by Logickverse Team from VGEC | Agentic AI Internship | Week 5")
