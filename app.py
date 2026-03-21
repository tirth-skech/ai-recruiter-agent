import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_complex_agent

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- AUTHENTICATION GATE ---
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.update({"auth": True, "role": "Recruiter", "email": st.user.email})
elif "auth" not in st.session_state:
    st.session_state.auth = False

def login_ui():
    st.title("🛡️ AI Recruitment Portal")
    choice = st.radio("Select Login Method", ["Recruiter (Auth0)", "Staff Login"], horizontal=True)
    
    if choice == "Recruiter (Auth0)":
        if st.button("Login with Auth0"):
            st.login("auth0") 
    else:
        with st.form("staff_login"):
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth": True, "role": "Admin", "email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"auth": True, "role": "Hiring Manager", "email": u})
                    st.rerun()
                else:
                    st.error("Invalid Credentials")

# --- MAIN APP ---
def main():
    if not st.session_state.auth:
        login_ui()
        return

    conn = init_db()
    role = st.session_state.role
    
    st.sidebar.title(f"Logged as: {role}")
    if st.sidebar.button("Logout"):
        is_auth0 = hasattr(st, "user") and st.user.is_logged_in
        st.session_state.auth = False
        if is_auth0: st.logout()
        else: st.rerun()

    tabs = st.tabs(["Agent Workspace", "Analytics Dashboard"])

    with tabs[0]:
        st.header("LangGraph Recruitment Agent")
        key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        resumes = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Process Candidates"):
            if key and jd and resumes:
                results = run_complex_agent(key, jd, resumes)
                for res in results:
                    save_candidate(conn, res)
                    # SUMMARY UI
                    with st.container(border=True):
                        c1, c2 = st.columns([1, 4])
                        c1.metric("Score", f"{res['score']}%")
                        c2.subheader(res['name'])
                        c2.write(f"**AI Analysis:** {res['summary']}")
                        with c2.expander("📩 Invitation Draft (ai26agent@gmail.com)"):
                            st.text_area("Email Body", res['invite_text'], height=150)
            else:
                st.warning("Please provide all inputs.")

    with tabs[1]:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            col1, col2 = st.columns(2)
            col1.subheader("Match Scores")
            col1.bar_chart(df.set_index('candidate_name')['score'])
            
            pass_rate = (df['diversity_flag'].sum() / len(df)) * 100
            col2.metric("Diversity Pass Rate", f"{pass_rate:.1f}%")
            st.dataframe(df)

if __name__ == "__main__":
    main()
