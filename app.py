import streamlit as st
import pandas as pd
from database import init_db, save_candidate, reset_pipeline
from processor import run_agent_workflow

st.set_page_config(page_title="Enterprise AI Recruiter", layout="wide")

# --- INITIALIZE SESSION STATE ---
if "auth" not in st.session_state:
    st.session_state.update({"auth": False, "role": None, "email": None})

def login_page():
    st.title("🛡️ Secure HR Portal")
    tab1, tab2 = st.tabs(["Staff Login", "Recruiter (Auth0)"])
    
    with tab1:
        with st.form("login"):
            u = st.text_input("Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth": True, "role": "Admin", "email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"auth": True, "role": "Manager", "email": u})
                    st.rerun()
                else: st.error("Invalid Credentials")
    with tab2:
        if st.button("Login with Auth0"):
            st.login("auth0")

def main():
    # Handle Auth0 callback if applicable
    if hasattr(st, "user") and st.user.is_logged_in:
        st.session_state.update({"auth": True, "role": "Recruiter", "email": st.user.email})

    if not st.session_state.auth:
        login_page()
        return

    conn = init_db()
    role = st.session_state.role
    
    st.sidebar.title(f"Role: {role}")
    if st.sidebar.button("Logout"):
        st.session_state.update({"auth": False, "role": None, "email": None})
        st.rerun()

    # --- UI LAYOUT ---
    tabs = st.tabs(["Agent Workspace", "Pipeline Analytics", "Admin Controls"])

    # TAB 1: RECRUITER WORKSPACE
    with tabs[0]:
        st.header("Recruitment Agent")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        uploaded_files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Run Agent"):
            if key and jd and uploaded_files:
                results = run_agent_workflow(key, jd, uploaded_files, st.session_state.email, conn, save_candidate)
                
                st.divider()
                st.subheader("Results Summary")
                for res in results:
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        c1.metric("Score", f"{res['score']}%")
                        c2.write(f"**Candidate:** {res['name']}")
                        c2.info(f"**AI Summary:** {res['summary']}")
                        if role in ["Manager", "Admin"]:
                            with c2.expander("📩 Send Invitation"):
                                st.text_area("Email Draft", res['invite'], height=150)
                                if st.button(f"Send to {res['name']}", key=res['name']):
                                    st.toast(f"Email sent to {res['name']}!")
            else:
                st.warning("Please fill in all fields.")

    # TAB 2: PIPELINE (MANAGER VIEW)
    with tabs[1]:
        st.header("Candidate Pipeline")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            st.bar_chart(df.set_index('candidate_name')['score'])
        else:
            st.info("No candidates processed yet.")

    # TAB 3: ADMIN
    with tabs[2]:
        if role == "Admin":
            st.header("System Settings")
            if st.button("🚨 Reset Recruitment Pipeline"):
                reset_pipeline(conn)
                st.success("Pipeline Cleared!")
                st.rerun()
        else:
            st.error("Admin access required for this section.")

if __name__ == "__main__":
    main()
