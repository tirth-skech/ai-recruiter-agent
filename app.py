import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_agent_workflow

# ... (Auth logic remains the same) ...

def recruiter_ui(conn):
    st.subheader("🚀 Candidate Screening Agent")
    k = st.text_input("Gemini API Key", type="password")
    jd = st.text_area("Step 1: Paste Job Description")
    files = st.file_uploader("Step 2: Upload Resumes", accept_multiple_files=True)
    
    if st.button("Run AI Agent"):
        if k and jd and files:
            # The summaries will now appear here
            results = run_agent_workflow(k, jd, files, st.session_state.user_email, conn, save_candidate)
            
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
            st.warning("Please upload files and enter your API key.")

def admin_ui(conn):
    st.subheader("⚙️ System Admin Controls")
    st.warning("Critical Actions: These cannot be undone.")
    
    if st.button("🚨 Factory Reset Database"):
        try:
            conn.execute("DELETE FROM recruitment_pipeline")
            conn.commit()
            st.success("Database cleared successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Error resetting database: {e}")

def main():
    if not st.session_state.authenticated:
        login_ui()
    else:
        conn = init_db()
        role = st.session_state.user_role
        
        # Navigation
        if role == "Recruiter":
            recruiter_ui(conn)
        elif role == "Hiring Manager":
            t1, t2 = st.tabs(["Agent", "Dashboard"])
            with t1: recruiter_ui(conn)
            with t2: # Add your dashboard logic here
                pass
        elif role == "Admin":
            t1, t2, t3 = st.tabs(["Agent", "Dashboard", "Admin Control"])
            with t1: recruiter_ui(conn)
            with t2: # Add your dashboard logic here
                pass
            with t3: admin_ui(conn)

if __name__ == "__main__":
    main()
