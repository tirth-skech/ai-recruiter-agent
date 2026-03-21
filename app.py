import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_complex_agent

st.set_page_config(page_title="Agentic AI Recruiter", layout="wide")

# --- AUTH0 & SESSION INITIALIZATION ---
# Streamlit detects if a user is logged in via Auth0 automatically
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.authenticated = True
    st.session_state.user_role = "Recruiter"
    st.session_state.user_email = st.user.email
elif "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_ui():
    st.title("🛡️ AI Recruitment Portal")
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("Recruiter Access")
        st.info("Log in with your corporate Google account.")
        if st.button("Login with Auth0"):
            st.login("auth0") # Triggers the Auth0 handshake
            
    with col2:
        st.subheader("Staff Login")
        with st.form("staff_login"):
            e = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if e == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                    st.rerun()
                elif e == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"authenticated": True, "user_role": "Hiring Manager", "user_email": e})
                    st.rerun()
                else:
                    st.error("Invalid credentials")

# --- MAIN APP LOGIC ---
def main():
    if not st.session_state.authenticated:
        login_ui()
        return

    conn = init_db()
    role = st.session_state.user_role
    email = st.session_state.user_email

    # Sidebar Logout
    st.sidebar.title(f"🤖 {role}")
    st.sidebar.write(f"User: {email}")
    if st.sidebar.button("Logout"):
        is_auth0 = hasattr(st, "user") and st.user.is_logged_in
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.session_state.authenticated = False
        if is_auth0:
            st.logout() 
        else:
            st.rerun()

    # Role-Based Tabs
    tab_list = ["Agent Workspace", "Pipeline Analytics"]
    if role in ["Admin", "Hiring Manager"]:
        tab_list.append("Admin Controls")
        
    tabs = st.tabs(tab_list)

    with tabs[0]:
        st.header("LangGraph Multi-Stage Agent")
        k = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        
        if st.button("🚀 Run Workflow"):
            if k and jd and files:
                results = run_complex_agent(k, jd, files)
                for res in results:
                    save_candidate(conn, res, email)
                    # Real-time Summary Card
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        c1.metric("Match", f"{res['score']}%")
                        c2.write(f"**Candidate:** {res['name']}")
                        c2.write(f"**AI Analysis:** {res['summary']}")
                        with c2.expander("📩 View Drafted Invite (ai26agent@gmail.com)"):
                            st.code(res['invite_text'], language="markdown")
                st.success("Workflow Complete!")

    with tabs[1]:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.subheader("Candidate Dashboard")
            st.dataframe(df, use_container_width=True)
            st.bar_chart(df.set_index('candidate_name')['score'])

if __name__ == "__main__":
    main()
