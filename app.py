import streamlit as st
import pandas as pd
from database import init_db, save_candidate, reset_pipeline
from processor import run_agent_workflow

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- 1. FORCE INITIALIZE SESSION STATE ---
if "auth" not in st.session_state:
    st.session_state.auth = False
if "role" not in st.session_state:
    st.session_state.role = None
if "email" not in st.session_state:
    st.session_state.email = None

# --- 2. LOGIN PAGE UI ---
def show_login_page():
    st.title("🛡️ AI Recruitment Gateway")
    st.info("Please log in to access the agent workspace.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Staff Login")
        with st.form("login_form"):
            user_val = st.text_input("Email")
            pass_val = st.text_input("Password", type="password")
            submit = st.form_submit_button("Sign In")
            
            if submit:
                if user_val == "admin@hr.com" and pass_val == "admin789":
                    st.session_state.auth = True
                    st.session_state.role = "Admin"
                    st.session_state.email = user_val
                    st.rerun()
                elif user_val == "manager@hr.com" and pass_val == "manager423":
                    st.session_state.auth = True
                    st.session_state.role = "Manager"
                    st.session_state.email = user_val
                    st.rerun()
                else:
                    st.error("Invalid credentials. Try admin@hr.com / admin789")

    with col2:
        st.subheader("Recruiter Social")
        st.write("Use corporate SSO")
        if st.button("Login with Auth0 / Google"):
            # This triggers Streamlit's internal Auth0 if configured
            st.login("auth0")

# --- 3. MAIN APPLICATION ---
def main():
    # Handle Auth0 callback automatically
    if hasattr(st, "user") and st.user.is_logged_in:
        st.session_state.auth = True
        st.session_state.role = "Recruiter"
        st.session_state.email = st.user.email

    # GATEKEEPER: If not authenticated, show login and STOP
    if not st.session_state.auth:
        show_login_page()
        return

    # --- IF LOGGED IN, SHOW THIS ---
    conn = init_db()
    
    # Sidebar
    st.sidebar.success(f"Logged in as: {st.session_state.role}")
    st.sidebar.write(f"📧 {st.session_state.email}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.session_state.role = None
        st.rerun()

    tabs = st.tabs(["Agent Workspace", "Pipeline Analytics", "Admin Controls"])

    # --- TAB 1: WORKSPACE ---
    with tabs[0]:
        st.header("Recruitment Agent")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Run Agent"):
            if key and jd and files:
                results = run_agent_workflow(key, jd, files, st.session_state.email, conn, save_candidate)
                
                st.divider()
                st.subheader("Results Summary")
                for res in results:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        c1.metric("Match", f"{res['score']}%")
                        c2.write(f"**Candidate:** {res['name']}")
                        c2.info(f"**AI Analysis:** {res['summary']}")
                        
                        # Only Manager/Admin see the invite tool
                        if st.session_state.role in ["Manager", "Admin"]:
                            with c2.expander("📩 View/Send Invite"):
                                st.text_area("Draft", res['invite'], height=100, key=f"txt_{res['name']}")
                                if st.button(f"Confirm Send to {res['name']}", key=f"btn_{res['name']}"):
                                    st.toast("Email sent successfully!")
            else:
                st.warning("Please check API Key and Uploads.")

    # --- TAB 2: ANALYTICS ---
    with tabs[1]:
        st.header("Candidate Pipeline")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
        else:
            st.info("No data in pipeline.")

    # --- TAB 3: ADMIN ---
    with tabs[2]:
        if st.session_state.role == "Admin":
            st.header("System Admin")
            if st.button("🚨 Factory Reset Pipeline"):
                reset_pipeline(conn)
                st.success("Database Wiped!")
                st.rerun()
        else:
            st.error("Access Denied: Admin Only.")

if __name__ == "__main__":
    main()
