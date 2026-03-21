import streamlit as st
import pandas as pd
from database import init_db, save_full_journey
from processor import run_complex_agent

# Page Config
st.set_page_config(page_title="AI Recruitment Agent Pro", layout="wide")

# --- AUTH0 / SESSION CHECK (Restored from your original code) ---
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email
elif "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_ui():
    st.title("🛡️ AI Recruitment Agent")
    method = st.radio("Access Method", ["Recruiter (Auth0)", "Staff Login"], horizontal=True)
    
    if method == "Recruiter (Auth0)":
        if st.button("Login with Google"):
            st.login("auth0") 
    else:
        with st.form("staff_login"):
            e = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                # Restoring your specific credentials
                if e == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                    st.rerun()
                elif e == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"authenticated": True, "user_role": "Hiring Manager", "user_email": e})
                    st.rerun()
                else:
                    st.error("Invalid credentials")

# --- MAIN ROUTER ---
def main():
    if not st.session_state.authenticated:
        login_ui()
    else:
        conn = init_db()
        role = st.session_state.user_role
        
        st.sidebar.title(f"🤖 {role}")
        st.sidebar.write(f"Logged as: {st.session_state.user_email}")
        
        if st.sidebar.button("Logout"):
            is_auth0 = hasattr(st, "user") and st.user.is_logged_in
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.authenticated = False
            if is_auth0:
                st.logout() 
            else:
                st.rerun()

        # Define Role-Based Tabs
        if role == "Recruiter":
            tabs = st.tabs(["Agent Workspace"])
        elif role == "Hiring Manager":
            tabs = st.tabs(["Agent Workspace", "Dashboard", "Scheduling"])
        else: # Admin
            tabs = st.tabs(["Agent", "Dashboard", "Scheduling", "Admin Control"])

        # --- TAB: Agent Workspace (LangGraph Implementation) ---
        with tabs[0]:
            st.header("Complex Recruitment Pipeline")
            k = st.text_input("Gemini API Key", type="password")
            col1, col2 = st.columns(2)
            jd = col1.text_area("Step 1: Job Description", height=200)
            files = col2.file_uploader("Step 2: Upload Resumes", type=["pdf", "docx"], accept_multiple_files=True)
            
            if st.button("🚀 Execute LangGraph Agent"):
                if k and jd and files:
                    with st.spinner("Running Multi-Stage LangGraph Workflow..."):
                        # Triggers Sourcing -> Screening -> Assessment
                        results = run_complex_agent(k, jd, files)
                        for res in results:
                            save_full_journey(conn, res)
                        st.success("Successfully processed candidates through the pipeline.")
                        st.rerun()
                else:
                    st.warning("Please provide API Key, JD, and Resumes.")

        # --- TAB: Dashboard & Diversity Analytics ---
        if len(tabs) > 1:
            with tabs[1]:
                st.header("📊 Candidate Leaderboard & Analytics")
                df = pd.read_sql_query("SELECT * FROM recruitment_pipeline", conn)
                if not df.empty:
                    # Diversity and Inclusion Analytics
                    d_col1, d_col2 = st.columns(2)
                    pass_rate = (df['diversity_flag'].sum() / len(df)) * 100
                    d_col1.metric("Diversity Pass Rate", f"{pass_rate:.1f}%")
                    d_col2.metric("Avg Match Score", f"{df['score'].mean():.1f}%")
                    st.dataframe(df, use_container_width=True)
                else:
                    st.info("No candidates processed yet.")

        # --- TAB: Scheduler ---
        if len(tabs) > 2:
            with tabs[2]:
                st.header("📅 Interview Scheduler")
                # Scheduling logic would go here, utilizing 'technical_questions' from the DB
                st.write("Top candidates available for scheduling.")

        # --- TAB: Admin Control ---
        if role == "Admin" and len(tabs) > 3:
            with tabs[3]:
                if st.button("🚨 Factory Reset Database"):
                    conn.execute("DELETE FROM recruitment_pipeline")
                    conn.commit()
                    st.success("Database cleared.")
                    st.rerun()

if __name__ == "__main__":
    main()
