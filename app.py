import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule, reset_database
from processor import run_agent_workflow

# 1. Page Config MUST be the very first Streamlit command
st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# 2. Initialize Session State so it's NEVER 'AttributeError'
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# 3. Handle Social Login (Auth0)
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email

# --- LOGIN UI ---
def login_ui():
    st.title("🛡️ AI Recruitment Gateway")
    method = st.radio("Access Method", ["Staff Login", "Recruiter (Social)"], horizontal=True)
    
    if method == "Recruiter (Social)":
        if st.button("Login with Google"):
            st.login("auth0") 
    else:
        with st.form("staff_login"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"authenticated": True, "user_role": "Manager", "user_email": u})
                    st.rerun()
                else:
                    st.error("Access Denied. Try admin@hr.com / admin789")

# --- MAIN APP ---
def main():
    # GATEKEEPER: If not authenticated, show login and STOP.
    if not st.session_state.authenticated:
        login_ui()
        return 

    # --- EVERYTHING BELOW ONLY RUNS AFTER LOGIN ---
    conn = init_db()
    role = st.session_state.user_role
    
    # Logout in Sidebar
    st.sidebar.title(f"🤖 {role}")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

    # Role-Based Tabs
    if role == "Admin":
        t1, t2, t3 = st.tabs(["Agent", "Dashboard", "Admin Controls"])
    elif role == "Manager":
        t1, t2 = st.tabs(["Agent", "Dashboard"])
    else:
        t1 = st.container() # Recruiter only sees the Agent

    with t1:
        st.header("Agent Workspace")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        
        if st.button("🚀 Run AI Agent"):
            if key and jd and files:
                # The 'processor.py' we built shows the "Successfully scanned" messages
                results = run_agent_workflow(key, jd, files, st.session_state.user_email, conn, save_candidate)
                
                # Show summaries below the button
                st.divider()
                for res in results:
                    with st.container(border=True):
                        st.write(f"**Candidate:** {res['name']} (Score: {res['score']}%)")
                        st.info(f"**Fit:** {res['summary']}")
            else:
                st.warning("Please fill all fields.")

    if role in ["Admin", "Manager"]:
        with t2:
            st.header("Manager Dashboard")
            df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
            st.dataframe(df, use_container_width=True)

    if role == "Admin":
        with t3:
            st.header("System Settings")
            if st.button("🚨 Reset Database"):
                reset_database(conn)
                st.success("Database cleared!")
                st.rerun()

if __name__ == "__main__":
    main()
