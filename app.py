import streamlit as st
import pandas as pd
# Import only what we need to avoid startup crashes
from database import init_db, save_candidate, reset_database
from processor import run_agent_workflow

# 1. MUST BE FIRST
st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# 2. INITIALIZE SESSION STATE (The Fix)
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# 3. CHECK AUTH0 (Google/Social)
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.role = "Recruiter"
    st.session_state.email = st.user.email

# --- LOGIN UI FUNCTION ---
def show_login_screen():
    st.title("🛡️ AI Recruitment Portal")
    st.warning("Authentication Required")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Corporate Login")
        with st.form("login_form"):
            email_input = st.text_input("Email")
            pass_input = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if email_input == "admin@hr.com" and pass_input == "admin789":
                    st.session_state.authenticated = True
                    st.session_state.user_role = "Admin"
                    st.session_state.user_email = email_input
                    st.rerun()
                elif email_input == "manager@hr.com" and pass_input == "manager423":
                    st.session_state.authenticated = True
                    st.session_state.user_role = "Manager"
                    st.session_state.user_email = email_input
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    with col2:
        st.subheader("External Access")
        if st.button("Sign in with Auth0 / Google"):
            st.login("auth0")

# --- MAIN APP LOGIC ---
def main():
    # THE GATEKEEPER: If not logged in, show login and STOP.
    if not st.session_state.authenticated:
        show_login_screen()
        return 

    # --- EVERYTHING BELOW ONLY RUNS AFTER SUCCESSFUL LOGIN ---
    conn = init_db()
    role = st.session_state.user_role
    email = st.session_state.user_email

    st.sidebar.success(f"Logged in: {role}")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    tabs = st.tabs(["Agent Workspace", "Analytics", "Admin"])

    with tabs[0]:
        st.header("Recruiter Workflow")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Paste JD Here")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Process Resumes"):
            if key and jd and files:
                # This shows the "Successfully Scanned" messages per resume
                results = run_agent_workflow(key, jd, files, email, conn, save_candidate)
                
                st.divider()
                st.subheader("AI Summaries")
                for res in results:
                    with st.container(border=True):
                        st.write(f"**{res['name']}** (Score: {res['score']})")
                        st.write(f"**Fit:** {res['summary']}")
                        if role in ["Admin", "Manager"]:
                            with st.expander("📩 View Drafted Invite"):
                                st.code(res['invite'], language="markdown")
            else:
                st.warning("Please provide API Key, JD, and Files.")

    with tabs[1]:
        st.header("Pipeline Status")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        st.dataframe(df, use_container_width=True)

    with tabs[2]:
        if role == "Admin":
            st.header("System Admin")
            if st.button("🚨 Factory Reset Database"):
                reset_database(conn)
                st.success("Database Wiped!")
                st.rerun()
        else:
            st.error("Access Restricted to Admin")

if __name__ == "__main__":
    main()
