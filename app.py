import streamlit as st
import pandas as pd
from database import init_db, save_candidate, update_schedule, reset_database
from processor import run_agent_workflow

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- 1. SESSION INITIALIZATION ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_role" not in st.session_state:
    st.session_state.user_role = None

# Check for Social Login (Auth0)
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.update({"authenticated": True, "user_role": "Recruiter", "user_email": st.user.email})

# --- 2. LOGIN UI ---
def login_ui():
    st.title("🛡️ Secure HR Portal")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Staff Login")
        with st.form("staff"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"authenticated": True, "user_role": "Manager", "user_email": u})
                    st.rerun()
                else: st.error("Invalid Credentials")
                
    with col2:
        st.subheader("Social Login")
        if st.button("Login with Auth0 / Google"):
            st.login("auth0")

# --- 3. MAIN APP ROUTER ---
def main():
    if not st.session_state.authenticated:
        login_ui()
        return  # STOP HERE if not logged in

    conn = init_db()
    role = st.session_state.user_role
    email = st.session_state.user_email

    st.sidebar.title(f"🤖 {role}")
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()): del st.session_state[key]
        st.rerun()

    # Tabs based on Role
    tab_list = ["Agent Workspace", "Dashboard"]
    if role == "Admin": tab_list.append("Admin Controls")
    tabs = st.tabs(tab_list)

    with tabs[0]:
        st.header("Recruiter Agent")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Run AI Agent"):
            if key and jd and files:
                results = run_agent_workflow(key, jd, files, email, conn, save_candidate)
                
                # SHOW SUMMARIES BELOW BUTTON
                st.divider()
                for res in results:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        c1.metric("Match", f"{res['score']}%")
                        c2.subheader(res['name'])
                        c2.write(f"**AI Fit Summary:** {res['summary']}")
                        
                        # Manager/Admin can see the invite
                        if role in ["Admin", "Manager"]:
                            with c2.expander("📩 Send Interview Invite"):
                                st.text_area("Draft", res['invite'], height=100)
                                if st.button(f"Confirm Email to {res['name']}", key=res['name']):
                                    st.toast(f"Invite sent to {res['name']}!")
            else: st.warning("Missing Info.")

    with tabs[1]:
        st.header("Pipeline Analytics")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        st.dataframe(df, use_container_width=True)

    if role == "Admin":
        with tabs[2]:
            st.header("System Admin")
            if st.button("🚨 Reset Database"):
                reset_database(conn)
                st.success("Cleared!")
                st.rerun()

if __name__ == "__main__":
    main()
