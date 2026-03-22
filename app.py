import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule
from processor import run_agent_workflow

# 1. Page Config MUST be first
st.set_page_config(page_title="AI Recruitment Agent", layout="wide")

# 2. Force Initialize Session State
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# 3. Check for Auth0 Social Login
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email

# --- LOGIN UI ---
def login_ui():
    st.title("🛡️ AI Recruitment Agent")
    st.info("Please authenticate to continue.")
    
    method = st.radio("Access Method", ["Staff Login", "Recruiter (Auth0)"], horizontal=True)
    
    if method == "Recruiter (Auth0)":
        if st.button("Login with Google"):
            st.login("auth0") 
    else:
        with st.form("staff_login"):
            e = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if e == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                    st.rerun()
                elif e == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"authenticated": True, "user_role": "Manager", "user_email": e})
                    st.rerun()
                else:
                    st.error("Invalid Credentials. (admin@hr.com / admin789)")

# --- APP ROUTER ---
def main():
    # GATEKEEPER: If not logged in, show login and STOP everything else
    if not st.session_state.authenticated:
        login_ui()
        return # This prevents the rest of the app from loading

    # --- IF WE ARE HERE, THE USER IS LOGGED IN ---
    conn = init_db()
    role = st.session_state.user_role
    
    # Sidebar Info & LOGOUT
    st.sidebar.title(f"🤖 {role}")
    st.sidebar.write(f"User: {st.session_state.user_email}")
    
    if st.sidebar.button("Logout 🚪"):
        # Explicitly clear everything
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        
        st.session_state.authenticated = False
        
        if hasattr(st, "user") and st.user.is_logged_in:
            st.logout() # Auth0 Logout
        else:
            st.rerun() # Staff Logout

    # Role-Based UI
    if role == "Admin":
        t1, t2, t3, t4 = st.tabs(["Agent", "Dashboard", "Scheduling", "Admin Control"])
        with t1: recruiter_ui(conn)
        with t2: dashboard_ui(conn) # You'll need to define these UI functions
        with t3: scheduler_ui(conn)
        with t4: admin_control_ui(conn)
    elif role == "Manager":
        t1, t2 = st.tabs(["Agent", "Dashboard"])
        with t1: recruiter_ui(conn)
        with t2: dashboard_ui(conn)
    else:
        recruiter_ui(conn)

def recruiter_ui(conn):
    st.header("Recruiter Workspace")
    # Add your key, JD, and file uploader logic here...

def admin_control_ui(conn):
    st.header("Admin Settings")
    if st.button("🚨 Reset Database Pipeline"):
        conn.execute("DELETE FROM recruitment_pipeline")
        conn.commit()
        st.success("Pipeline reset successfully!")

if __name__ == "__main__":
    main()
