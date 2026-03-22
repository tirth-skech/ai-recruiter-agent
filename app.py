import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_agent_workflow

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- AUTH LOGIC ---
def login_ui():
    st.title("🛡️ AI Recruitment Portal")
    choice = st.radio("Access Method", ["Recruiter (Auth0)", "Staff Login"], horizontal=True)
    
    if choice == "Recruiter (Auth0)":
        if st.button("Login with Auth0"):
            st.login("auth0") 
    else:
        with st.form("staff_login"):
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.authenticated = True
                    st.session_state.user_role = "Admin"
                    st.session_state.user_email = u
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

# --- UI COMPONENTS ---
def recruiter_ui(conn):
    st.subheader("🚀 Candidate Screening")
    k = st.text_input("Gemini API Key", type="password")
    jd = st.text_area("Step 1: Paste Job Description")
    files = st.file_uploader("Step 2: Upload Resumes", accept_multiple_files=True)
    
    if st.button("Run AI Agent"):
        if k and jd and files:
            # This triggers the "Name scanned successfully" messages inside the processor
            results = run_agent_workflow(k, jd, files, st.session_state.user_email, conn, save_candidate)
            
            if results:
                st.divider()
                st.subheader("📋 Screening Summaries")
                for res in results:
                    with st.container(border=True):
                        col1, col2 = st.columns([1, 4])
                        col1.metric("Score", f"{res['score']}%")
                        col2.markdown(f"**Candidate:** {res['name']}")
                        col2.info(f"**AI Summary:** {res['summary']}")
                        with col2.expander("📩 View Drafted Invite"):
                            st.caption("From: ai26agent@gmail.com")
                            st.code(res['invite'], language="markdown")
        else:
            st.warning("Please provide API Key, JD, and Files.")

def admin_ui(conn):
    st.subheader("⚙️ System Admin Controls")
    if st.button("🚨 Factory Reset Database"):
        conn.execute("DELETE FROM recruitment_pipeline")
        conn.commit()
        st.success("Database cleared.")
        st.rerun()

# --- MAIN ROUTER ---
def main():
    # CRITICAL FIX: Initialize session state keys if they don't exist
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user_role" not in st.session_state:
        st.session_state.user_role = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None

    # Check for Auth0 login (Streamlit built-in)
    if hasattr(st, "user") and st.user.is_logged_in:
        st.session_state.authenticated = True
        st.session_state.user_role = "Recruiter"
        st.session_state.user_email = st.user.email

    if not st.session_state.authenticated:
        login_ui()
    else:
        conn = init_db()
        role = st.session_state.user_role
        
        st.sidebar.title(f"🤖 {role}")
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            # If Auth0 was used
            if hasattr(st, "user") and st.user.is_logged_in:
                st.logout()
            else:
                st.rerun()

        if role == "Admin":
            t1, t2 = st.tabs(["Agent Workspace", "Admin Control"])
            with t1: recruiter_ui(conn)
            with t2: admin_ui(conn)
        else:
            recruiter_ui(conn)

if __name__ == "__main__":
    main()
