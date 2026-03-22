import streamlit as st
import pandas as pd
from database import init_db, save_candidate, reset_database
from processor import run_agent_workflow

# 1. Page Config
st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# 2. Strict Session Initialization
if "auth" not in st.session_state:
    st.session_state.auth = False
if "role" not in st.session_state:
    st.session_state.role = None
if "email" not in st.session_state:
    st.session_state.email = None

def show_login_screen():
    st.title("🛡️ AI Recruitment Portal")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Staff Login")
        with st.form("login_form"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth": True, "role": "Admin", "email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"auth": True, "role": "Manager", "email": u})
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    with col2:
        st.subheader("External Access")
        if st.button("Login with Auth0"):
            st.login("auth0")

def main():
    # Handle Auth0 callback
    if hasattr(st, "user") and st.user.is_logged_in:
        st.session_state.update({"auth": True, "role": "Recruiter", "email": st.user.email})

    # GATEKEEPER
    if not st.session_state.auth:
        show_login_screen()
        return

    # --- LOGGED IN AREA ---
    conn = init_db()
    role = st.session_state.role

    # SIDEBAR & LOGOUT
    with st.sidebar:
        st.title(f"🤖 {role}")
        st.write(f"User: {st.session_state.email}")
        if st.button("Logout", width='stretch'): # UPDATED PARAMETER
            # Nuke the session
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.auth = False
            st.rerun()

    # TABS
    tab_list = ["Agent", "Pipeline"]
    if role == "Admin": tab_list.append("Admin Controls")
    tabs = st.tabs(tab_list)

    with tabs[0]:
        st.header("Recruiter Workflow")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Paste JD Here")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Process Resumes"):
            if key and jd and files:
                results = run_agent_workflow(key, jd, files, st.session_state.email, conn, save_candidate)
                for res in results:
                    with st.container(border=True):
                        st.write(f"**{res['name']}** (Score: {res['score']})")
                        st.info(res['summary'])
            else:
                st.warning("Please fill all fields.")

    with tabs[1]:
        st.header("Analytics")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        # UPDATED PARAMETER HERE
        st.dataframe(df, width='stretch') 

    if role == "Admin":
        with tabs[2]:
            if st.button("🚨 Reset Database", width='stretch'): # UPDATED PARAMETER
                reset_database(conn)
                st.success("Wiped!")
                st.rerun()

if __name__ == "__main__":
    main()
