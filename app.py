import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule, reset_db
from processor import run_agent_workflow

st.set_page_config(page_title="AI Recruiter", layout="wide")

# --- INITIALIZE AUTH ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None

def login_ui():
    st.title("🛡️ Secure Login")
    with st.form("login"):
        u = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Sign In"):
            if u == "admin@hr.com" and p == "admin789":
                st.session_state.update({"authenticated": True, "user_role": "Admin", "email": u})
                st.rerun()
            elif u == "manager@hr.com" and p == "manager423":
                st.session_state.update({"authenticated": True, "user_role": "Manager", "email": u})
                st.rerun()
            else: st.error("Try admin@hr.com / admin789")

def main():
    if not st.session_state.authenticated:
        login_ui()
        return

    conn = init_db()
    role = st.session_state.user_role
    
    st.sidebar.subheader(f"Role: {role}")
    if st.sidebar.button("Logout"):
        st.session_state.authenticated = False
        st.rerun()

    tabs = st.tabs(["Agent", "Dashboard", "Admin"])

    with tabs[0]:
        st.header("Recruiter Agent")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        
        if st.button("Run Agent"):
            res_list = run_agent_workflow(key, jd, files, st.session_state.email, conn, save_candidate)
            for res in res_list:
                with st.container(border=True):
                    st.write(f"**{res['name']}** (Score: {res['score']})")
                    st.write(res['summary'])

    with tabs[1]:
        st.header("Manager View")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        st.dataframe(df)

    with tabs[2]:
        if role == "Admin":
            if st.button("🚨 Reset Database"):
                reset_db(conn)
                st.success("Cleared!")
        else: st.error("Admin Only")

if __name__ == "__main__":
    main()
