import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_ai_workflow

# Page Config
st.set_page_config(page_title="Enterprise HR Portal", layout="wide")

# Auth State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login():
    st.title("🛡️ Enterprise HR Portal")
    method = st.radio("Method", ["Recruiter (Google Auth)", "Staff (Password)"], horizontal=True)
    
    if method == "Recruiter (Google Auth)":
        email = st.text_input("Google Email")
        if st.button("Login"):
            st.session_state.update({"authenticated": True, "user_role": "Recruiter", "user_email": email})
            st.rerun()
    else:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Staff Login"):
            if e == "admin@hr.com" and p == "admin789":
                st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                st.rerun()
            elif e == "manager@hr.com" and p == "manager123":
                st.session_state.update({"authenticated": True, "user_role": "Hiring Manager", "user_email": e})
                st.rerun()

# Views
def recruiter_ui(conn):
    st.header("🎯 Recruiter Workspace")
    k = st.text_input("API Key", type="password")
    c = st.text_area("Hiring Criteria")
    u = st.file_uploader("Upload Resumes", type="pdf", accept_multiple_files=True)
    if st.button("Start AI Screening"):
        run_ai_workflow(k, c, u, st.session_state.user_email, conn, save_candidate)

def manager_ui(conn):
    st.header("📊 Manager Dashboard")
    df = pd.read_sql_query("SELECT candidate_name, score, summary, status FROM recruitment_pipeline", conn)
    st.dataframe(df, use_container_width=True)

def admin_ui(conn):
    st.header("⚙️ Admin Controls")
    df = pd.read_sql_query("SELECT * FROM recruitment_pipeline", conn)
    st.write(df)
    if st.button("Reset DB"):
        conn.execute("DELETE FROM recruitment_pipeline")
        conn.commit()
        st.rerun()

def main():
    if not st.session_state.authenticated:
        login()
    else:
        conn = init_db()
        role = st.session_state.user_role
        st.sidebar.title(f"👤 {role}")
        if st.sidebar.button("Logout"):
            st.session_state.authenticated = False
            st.rerun()

        if role == "Recruiter":
            recruiter_ui(conn)
        elif role == "Hiring Manager":
            t1, t2 = st.tabs(["Recruiter", "Manager"])
            with t1: recruiter_ui(conn)
            with t2: manager_ui(conn)
        elif role == "Admin":
            t1, t2, t3 = st.tabs(["Recruiter", "Manager", "Admin"])
            with t1: recruiter_ui(conn)
            with t2: manager_ui(conn)
            with t3: admin_ui(conn)

if __name__ == "__main__":
    main()
