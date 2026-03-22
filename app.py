import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule, reset_database
from processor import run_agent_workflow

# 1. Page Config MUST be at the very top
st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# 2. Initialize Session State
if "auth" not in st.session_state:
    st.session_state.auth = False
if "role" not in st.session_state:
    st.session_state.role = None

# 3. Handle Social Login (Auth0)
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.auth = True
    st.session_state.role = "Recruiter"
    st.session_state.email = st.user.email

# --- LOGIN UI ---
def login_ui():
    st.title("🛡️ AI Recruitment Gateway")
    tab1, tab2 = st.tabs(["Staff Login", "Recruiter (Social)"])
    
    with tab1:
        with st.form("staff_login"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth": True, "role": "Admin", "email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"auth": True, "role": "Manager", "email": u})
                    st.rerun()
                else: st.error("Access Denied.")
    with tab2:
        if st.button("Login with Auth0"):
            st.login("auth0")

# --- MAIN APP ---
def main():
    if not st.session_state.auth:
        login_ui()
        return

    conn = init_db()
    role = st.session_state.role
    
    # Sidebar Logout
    st.sidebar.title(f"🤖 {role}")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Define Tabs based on Role
    if role == "Admin":
        t1, t2, t3 = st.tabs(["Agent", "Dashboard", "Admin Controls"])
    elif role == "Manager":
        t1, t2 = st.tabs(["Agent", "Dashboard"])
    else:
        t1 = st.container() # Recruiter only sees Agent

    with t1:
        st.header("Recruiter Workspace")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        
        if st.button("🚀 Run Agent"):
            if key and jd and files:
                # This function in processor.py should handle the st.success messages
                results = run_agent_workflow(key, jd, files, st.session_state.email, conn, save_candidate)
                for res in results:
                    with st.container(border=True):
                        st.write(f"**{res['name']}** - Match: {res['score']}%")
                        st.info(res['summary'])
            else: st.warning("Missing Inputs.")

    if role in ["Admin", "Manager"]:
        with t2:
            st.header("Manager Dashboard")
            df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
            st.dataframe(df)

    if role == "Admin":
        with t3:
            st.header("System Reset")
            if st.button("🚨 Reset Pipeline"):
                reset_database(conn)
                st.success("Database Wiped.")
                st.rerun()

if __name__ == "__main__":
    main()
