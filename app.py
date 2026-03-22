import streamlit as st
import pandas as pd
from database import init_db, save_candidate, reset_database
from processor import run_agent_workflow

# --- 1. CONFIG & INITIALIZATION ---
st.set_page_config(page_title="AI Recruiter Pro", layout="wide", initial_sidebar_state="collapsed")

# Initialize session state keys if they don't exist
if "auth" not in st.session_state:
    st.session_state.auth = False
if "role" not in st.session_state:
    st.session_state.role = None
if "email" not in st.session_state:
    st.session_state.email = None

# --- 2. LOGIN UI ---
def login_ui():
    st.title("🛡️ Secure HR Portal")
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Staff Authentication")
        with st.form("staff_login"):
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
            
            if submitted:
                # Replace these with your actual credentials
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth": True, "role": "Admin", "email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"auth": True, "role": "Manager", "email": u})
                    st.rerun()
                else:
                    st.error("Invalid credentials.")

    with col2:
        st.subheader("External Access")
        st.write("Sign in using your Google or Corporate SSO.")
        if st.button("Login with Auth0"):
            st.login("auth0") # Built-in Streamlit Auth0

# --- 3. MAIN APPLICATION (THE WORKSPACE) ---
def workspace():
    conn = init_db()
    role = st.session_state.role
    email = st.session_state.email

    # Sidebar for logout and info
    with st.sidebar:
        st.title(f"🤖 {role}")
        st.write(f"Logged in as: **{email}**")
        st.divider()
        if st.button("Logout", use_container_width=True):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()

    # Dynamic Tabs based on Role
    tab_titles = ["Agent Workspace", "Analytics"]
    if role == "Admin":
        tab_titles.append("Admin Controls")
    
    tabs = st.tabs(tab_titles)

    # TAB 1: WORKFLOW
    with tabs[0]:
        st.header("Recruiter Workflow")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Paste JD Here")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Process Resumes"):
            if key and jd and files:
                results = run_agent_workflow(key, jd, files, email, conn, save_candidate)
                st.divider()
                st.subheader("AI Summaries")
                for res in results:
                    with st.container(border=True):
                        st.write(f"**{res['name']}** (Score: {res['score']})")
                        st.info(f"**Summary:** {res['summary']}")
            else:
                st.warning("Please fill all fields.")

    # TAB 2: ANALYTICS
    with tabs[1]:
        st.header("Pipeline Status")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No candidates processed yet.")

    # TAB 3: ADMIN
    if role == "Admin":
        with tabs[2]:
            st.header("System Settings")
            if st.button("🚨 Reset Database"):
                reset_database(conn)
                st.success("Database Wiped!")
                st.rerun()

# --- 4. EXECUTION FLOW ---
def main():
    # Handle Auth0 callback if it happened
    if hasattr(st, "user") and st.user.is_logged_in:
        st.session_state.update({"auth": True, "role": "Recruiter", "email": st.user.email})

    # The GATEKEEPER logic
    if not st.session_state.auth:
        login_ui()
    else:
        workspace()

if __name__ == "__main__":
    main()
