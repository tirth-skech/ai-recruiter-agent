import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule
from processor import run_agent_workflow

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="AI Recruitment Agent - Enterprise", layout="wide", page_icon="🛡️")

# --- SESSION STATE INITIALIZATION ---
# Using streamlit.user for Auth0 and manual state for corporate login
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email
elif "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_ui():
    """Renders the centralized login gateway."""
    st.title("🛡️ AI Recruitment Agent")
    st.subheader("Secure Gateway")
    
    # Choose between Auth0 and Staff credentials
    method = st.radio("Access Method", ["Recruiter (Social Login)", "Corporate Staff"], horizontal=True)
    
    if method == "Recruiter (Social Login)":
        st.info("Authorized access for external recruiters via Google/Auth0.")
        if st.button("Login with Auth0"):
            st.login("auth0") # Triggers the Auth0 redirect[cite: 3]
    else:
        with st.form("staff_login"):
            st.markdown("### Internal Staff Portal")
            email = st.text_input("Corporate Email")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                # Role-Based Authentication Logic[cite: 3]
                if email == "admin@hr.com" and password == "admin789":
                    st.session_state.update({
                        "authenticated": True, 
                        "user_role": "Admin", 
                        "user_email": email
                    })
                    st.success("Admin Access Granted")
                    st.rerun()
                elif email == "manager@hr.com" and password == "manager423":
                    st.session_state.update({
                        "authenticated": True, 
                        "user_role": "Hiring Manager", 
                        "user_email": email
                    })
                    st.success("Manager Access Granted")
                    st.rerun()
                else:
                    st.error("Invalid corporate credentials.")

# --- UI WORKSPACES ---

def recruiter_workspace(conn):
    """Core Agent Interface for processing resumes[cite: 3]."""
    st.header("🤖 Agentic Workspace")
    api_key = st.text_input("Gemini API Key", type="password", help="Required for LangGraph Agent")
    
    col1, col2 = st.columns(2)
    with col1:
        jd = st.text_area("Step 1: Job Description", placeholder="Paste JD requirements here...", height=200)
    with col2:
        files = st.file_uploader("Step 2: Upload Candidates", type=["pdf", "docx"], accept_multiple_files=True)
    
    if st.button("🚀 Run Agentic Pipeline"):
        if api_key and jd and files:
            # Executes the LangGraph workflow and saves to DB[cite: 3]
            run_agent_workflow(api_key, jd, files, st.session_state.user_email, conn, save_candidate)
        else:
            st.warning("All inputs (API Key, JD, Files) are mandatory.")

# --- NAVIGATION ROUTER ---

def main():
    if not st.session_state.authenticated:
        login_ui()
    else:
        conn = init_db() #
        role = st.session_state.user_role
        
        # Sidebar Profile & Logout[cite: 3]
        st.sidebar.title(f"Logged as: {role}")
        st.sidebar.write(f"📧 {st.session_state.user_email}")
        
        if st.sidebar.button("🚪 Logout"):
            is_auth0 = hasattr(st, "user") and st.user.is_logged_in
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.authenticated = False
            
            if is_auth0:
                st.logout() # Native Auth0 logout[cite: 3]
            else:
                st.rerun()

        # RBAC Navigation: Managers and Admins get more tabs[cite: 3]
        if role == "Recruiter":
            recruiter_workspace(conn)
        elif role == "Hiring Manager":
            t1, t2 = st.tabs(["Agent Workspace", "Leaderboard"])
            with t1: recruiter_workspace(conn)
            with t2: dashboard_ui(conn) # Assumes dashboard_ui exists in your script[cite: 3]
        elif role == "Admin":
            t1, t2, t3 = st.tabs(["Agent", "Dashboard", "System Admin"])
            with t1: recruiter_workspace(conn)
            with t2: dashboard_ui(conn)
            with t3: admin_ui(conn) # Assumes admin_ui exists in your script[cite: 3]

if __name__ == "__main__":
    main()
