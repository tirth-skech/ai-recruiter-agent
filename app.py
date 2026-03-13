import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_ai_workflow

# Page Config
st.set_page_config(page_title="Enterprise HR Portal", layout="wide")

# --- AUTH0 INTEGRATION ---
# Check if the user is logged in via Auth0
if st.user.is_logged_in:
    # If logged in via Auth0, we treat them as a Recruiter
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email
elif "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_ui():
    st.title("🛡️ Enterprise HR Portal")
    method = st.radio("Method", ["Recruiter (Google Auth0)", "Staff (Password)"], horizontal=True)
    
    if method == "Recruiter (Google Auth0)":
        st.info("You will be redirected to the secure Auth0 portal.")
        if st.button("Login with Auth0"):
            st.login("auth0") # Triggers the OIDC flow
            
    else:
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.button("Staff Login"):
            # Existing Staff Logic
            if e == "admin@hr.com" and p == "admin789":
                st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                st.rerun()
            elif e == "manager@hr.com" and p == "manager123":
                st.session_state.update({"authenticated": True, "user_role": "Hiring Manager", "user_email": e})
                st.rerun()
            else:
                st.error("Invalid credentials")

# --- UI VIEWS (Kept same as your original) ---

def recruiter_ui(conn):
    st.header("🎯 Recruiter Workspace")
    k = st.text_input("API Key", type="password")
    c = st.text_area("Hiring Criteria")
    u = st.file_uploader("Upload Resumes", type="pdf", accept_multiple_files=True)
    if st.button("Start AI Screening"):
        run_ai_workflow(k, c, u, st.session_state.user_email, conn, save_candidate)

def manager_ui(conn):
    st.header("📊 Manager Dashboard")
    # Wrap in try/except in case table is empty initially
    try:
        df = pd.read_sql_query("SELECT candidate_name, score, summary, status FROM recruitment_pipeline", conn)
        st.dataframe(df, use_container_width=True)
    except:
        st.info("No candidates screened yet.")

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
        login_ui()
    else:
        conn = init_db()
        role = st.session_state.user_role
        st.sidebar.title(f"👤 {role}")
        
        # LOGOUT LOGIC
        if st.sidebar.button("Logout"):
            if st.user.is_logged_in:
                st.logout() # Clears Auth0 session
            else:
                st.session_state.authenticated = False
                st.rerun()

        # Role-based View Routing
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
