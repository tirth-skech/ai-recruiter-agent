import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule
from processor import run_agent_workflow

# Page Config
st.set_page_config(page_title="AI Recruitment Agent", layout="wide")

# --- AUTH0 / SESSION CHECK ---
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email
elif "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_ui():
    st.title("🛡️ Enterprise AI Recruitment Agent")
    method = st.radio("Access Method", ["Recruiter (Auth0)", "Staff Login"], horizontal=True)
    
    if method == "Recruiter (Auth0)":
        st.info("Secure OIDC redirect via Auth0.")
        if st.button("Login with Auth0"):
            st.login("auth0") 
    else:
        with st.form("staff_login"):
            e = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if e == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                    st.rerun()
                elif e == "manager@hr.com" and p == "manager123":
                    st.session_state.update({"authenticated": True, "user_role": "Hiring Manager", "user_email": e})
                    st.rerun()
                else:
                    st.error("Invalid credentials")

# --- UI COMPONENTS ---

def recruiter_ui(conn):
    st.header("🎯 Agent Workspace")
    
    col1, col2 = st.columns(2)
    with col1:
        jd = st.text_area("Step 1: Job Description (JD)", placeholder="Paste requirements here...", height=200)
    with col2:
        files = st.file_uploader("Step 2: Upload Resumes", type=["pdf", "docx"], accept_multiple_files=True)
    
    if st.button("🚀 Execute Agent Screening"):
        if jd and files:
            # API Key is now handled internally via st.secrets
            run_agent_workflow(jd, files, st.session_state.user_email, conn, save_candidate)
        else:
            st.warning("Please provide both Job Description and Resumes.")

def dashboard_ui(conn):
    st.header("📊 Candidate Leaderboard")
    try:
        df = pd.read_sql_query("SELECT * FROM recruitment_pipeline", conn)
        if df.empty:
            st.info("No candidates processed yet.")
            return

        for _, row in df.iterrows():
            with st.container(border=True):
                c1, c2, c3 = st.columns([1, 4, 1.5])
                c1.metric("Score", f"{row['score']}%")
                c2.subheader(row['candidate_name'])
                c2.write(f"**AI Match Summary:** {row['summary']}")
                c2.caption(f"Suggested Email: {row['invite_text']}")
                
                if row['status'] == 'Scheduled':
                    c3.success(f"✅ Scheduled: {row['interview_date']}")
                else:
                    if c3.button("✉️ Invite", key=f"btn_{row['id']}"):
                        st.toast(f"Invite template generated for {row['candidate_name']}!")
    except Exception as e:
        st.error(f"Database error: {e}")

def scheduler_ui(conn):
    st.header("📅 Interview Scheduler")
    df = pd.read_sql_query("SELECT candidate_name FROM recruitment_pipeline WHERE status != 'Scheduled'", conn)
    
    if not df.empty:
        with st.form("schedule_form"):
            target = st.selectbox("Select Candidate", df['candidate_name'])
            d = st.date_input("Date")
            t = st.time_input("Time")
            if st.form_submit_button("Confirm Schedule"):
                update_schedule(conn, target, f"{d} {t}")
                st.success(f"Interview set for {target}")
                st.rerun()
    else:
        st.info("No pending candidates to schedule.")

def admin_ui(conn):
    st.header("⚙️ System Administration")
    df = pd.read_sql_query("SELECT * FROM recruitment_pipeline", conn)
    st.dataframe(df)
    if st.button("🚨 Factory Reset Database"):
        conn.execute("DELETE FROM recruitment_pipeline")
        conn.commit()
        st.success("Database cleared.")
        st.rerun()

# --- MAIN ROUTER ---

def main():
    if not st.session_state.authenticated:
        login_ui()
    else:
        conn = init_db()
        role = st.session_state.user_role
        
        st.sidebar.title(f"🤖 {role}")
        st.sidebar.write(f"Logged as: {st.session_state.user_email}")
        
        # UNIFIED LOGOUT LOGIC
        if st.sidebar.button("Logout"):
            is_auth0 = hasattr(st, "user") and st.user.is_logged_in
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.session_state.authenticated = False
            
            if is_auth0:
                st.logout() 
            else:
                st.rerun()

        # Tab Navigation
        if role == "Recruiter":
            recruiter_ui(conn)
        elif role == "Hiring Manager":
            t1, t2, t3 = st.tabs(["Agent Workspace", "Dashboard", "Scheduling"])
            with t1: recruiter_ui(conn)
            with t2: dashboard_ui(conn)
            with t3: scheduler_ui(conn)
        elif role == "Admin":
            t1, t2, t3, t4 = st.tabs(["Agent", "Dashboard", "Scheduling", "Admin"])
            with t1: recruiter_ui(conn)
            with t2: dashboard_ui(conn)
            with t3: scheduler_ui(conn)
            with t4: admin_ui(conn)

if __name__ == "__main__":
    main()
