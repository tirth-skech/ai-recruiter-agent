import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_agent_workflow

st.set_page_config(page_title="Goldwin AI Recruiter", layout="wide")

# --- AUTHENTICATION CHECK ---
def is_authenticated():
    # Priority 1: Auth0 (Google/Social)
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        st.session_state.auth_status = True
        st.session_state.user_email = st.user.get("email")
        st.session_state.role = "Recruiter"
        return True
    # Priority 2: Manual Staff Login
    return st.session_state.get("auth_status", False)

if "auth_status" not in st.session_state:
    st.session_state.update({"auth_status": False, "user_email": None, "role": None})

# --- UI LOGIC ---
if not is_authenticated():
    st.title("🛡️ Recruitment Portal")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("External Access")
        if st.button("Login with Auth0", type="primary"):
            try:
                st.login("auth0")
            except Exception as e:
                st.error("Secrets Configuration Missing in Cloud Settings.")
                
    with col2:
        st.subheader("Internal Staff")
        with st.form("staff"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth_status": True, "role": "Admin", "user_email": u})
                    st.rerun()
                else: st.error("Invalid Credentials")
else:
    conn = init_db()
    st.sidebar.title(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.logout() if hasattr(st, "user") else None
        st.session_state.clear()
        st.rerun()

    t1, t2 = st.tabs(["🚀 Agent", "📊 Analytics"])
    with t1:
        # Check for Gemini Key in Secrets
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
            jd = st.text_area("Job Description")
            files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
            if st.button("Run Pipeline"):
                run_agent_workflow(api_key, jd, files, st.session_state.user_email, conn, save_candidate)
        else:
            st.error("GEMINI_API_KEY missing in Streamlit Cloud Secrets.")
