import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, save_candidate
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin AI Recruiter | Week 5",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (Track A/B Requirement) ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Recruiter"}
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("🛡️ Enterprise Recruitment Gateway")
    st.info("Week 5: External API Integration & Indian Market Context")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Partner Login")
            if st.button("Login with Auth0", type="primary", use_container_width=True):
                try: st.login("auth0")
                except: st.error("Check Streamlit Secrets for [auth] block.")
                
    with col2:
        with st.form("admin_form"):
            st.subheader("Internal Staff")
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"admin_login": True, "admin_email": u})
                    st.rerun()
                else: st.error("Invalid Credentials")
else:
    # --- 3. MAIN DASHBOARD ---
    conn = init_db()
    
    st.sidebar.title(f"👤 {auth['role']}")
    st.sidebar.caption(f"Active: {auth['user']}")
    
    if st.sidebar.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

    st.sidebar.divider()
    st.sidebar.success("✅ HackerEarth Connected")
    st.sidebar.success("✅ Gemini 2.5 Flash Active")

    # --- 4. TABS ---
    tab_run, tab_pipe, tab_stats = st.tabs([
        "🚀 Run 2.5 Flash Agent", 
        "📋 Pipeline Management", 
        "📊 Market Analytics"
    ])

    # TAB 1: Processing
    with tab_run:
        st.header("Agentic Sourcing Engine")
        if "GEMINI_API_KEY" in st.secrets:
            col_a, col_b = st.columns([1, 2])
            with col_a:
                st.subheader("Step 1: Context")
                jd = st.text_area("Job Description", height=200, placeholder="Paste JD (e.g., Python Developer at Tier-1 firm)")
                test_id = st.text_input("HackerEarth Test ID", value="python_dev_01")
            
            with col_b:
                st.subheader("Step 2: Resumes")
                files = st.file_uploader("Upload Resumes (PDF/DOCX)", accept_multiple_files=True)
                
                if st.button("▶️ Start Week 5 Pipeline", type="primary"):
                    if jd and files:
                        run_agent_workflow(
                            st.secrets["GEMINI_API_KEY"], 
                            jd, files, auth["user"], 
                            conn, save_candidate
                        )
                    else:
                        st.warning("Please provide both JD and Resumes.")
        else:
            st.error("Missing GEMINI_API_KEY in Secrets.")

    # TAB 2: Pipeline Management (WEEK 5 REQUIREMENT)
    with tab_pipe:
        st.header("Candidate Tracking System")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        
        if not df.empty:
            # Filters for Indian Market Context
            f1, f2, f3 = st.columns(3)
            with f1:
                tier_sel = st.multiselect("Education Tier", options=["Tier-1", "Tier-2", "Tier-3"], default=["Tier-1", "Tier-2"])
            with f2:
                status_sel = st.multiselect("Status", options=df['status'].unique(), default=df['status'].unique())
            with f3:
                reloc_sel = st.radio("Relocation Willingness", ["All", "Yes", "No"], horizontal=True)

            # Apply Filters
            filtered_df = df[df['education_tier'].isin(tier_sel) & df['status'].isin(status_sel)]
            if reloc_sel != "All":
                filtered_df = filtered_df[filtered_df['relocation_willing'] == reloc_sel]

            st.dataframe(
                filtered_df.sort_values(by="score", ascending=False), 
                use_container_width=True,
                column_config={
                    "expected_salary": st.column_config.NumberColumn("Expected Salary (LPA)", format="₹%d"),
                    "score": st.column_config.ProgressColumn("Match Score", min_value=0, max_value=100)
                }
            )
        else:
            st.info("No candidates processed yet.")

    # TAB 3: Indian Market Analytics
    with tab_stats:
        st.header("Hiring Insights")
        if not df.empty:
            c1, c2 = st.columns(2)
            with c1:
                fig_tier = px.pie(df, names='education_tier', title="Tier-1 vs Others (Indian System)")
                st.plotly_chart(fig_tier, use_container_width=True)
            with c2:
                fig_salary = px.box(df, x='education_tier', y='expected_salary', title="Salary Expectations by Tier")
                st.plotly_chart(fig_salary, use_container_width=True)
            
            st.subheader("Notice Period Breakdown")
            fig_notice = px.histogram(df, x='notice_period', color='status')
            st.plotly_chart(fig_notice, use_container_width=True)

# --- 5. FOOTER ---
st.divider()
st.caption("Gujarat Technological University | Agentic AI Internship | Week 5")
