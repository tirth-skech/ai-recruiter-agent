import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_complex_agent

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- AUTH LOGIC ---
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.update({"auth": True, "role": "Recruiter", "email": st.user.email})
elif "auth" not in st.session_state:
    st.session_state.auth = False

def login_page():
    st.title("🛡️ AI Recruitment Portal")
    choice = st.radio("Login via", ["Recruiter (Auth0)", "Staff Login"])
    if choice == "Recruiter (Auth0)":
        if st.button("Sign in with Google"): st.login("auth0")
    else:
        with st.form("staff"):
            u, p = st.text_input("Email"), st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"auth": True, "role": "Admin", "email": u})
                    st.rerun()
                else: st.error("Access Denied")

def main():
    if not st.session_state.auth:
        login_page()
        return

    conn = init_db()
    st.sidebar.title(f"Role: {st.session_state.role}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    t1, t2 = st.tabs(["Agent Workspace", "Analytics"])

    with t1:
        st.header("LangGraph Recruitment Agent")
        key = st.text_input("API Key", type="password")
        jd = st.text_area("Job Description")
        resumes = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Process Candidates"):
            results = run_complex_agent(key, jd, resumes)
            for res in results:
                save_candidate(conn, res)
                # SUMMARY UI
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    c1.metric("Score", f"{res['score']}%")
                    c2.subheader(res['name'])
                    c2.write(f"**Analysis:** {res['summary']}")
                    with c2.expander("📩 Generated Invitation (ai26agent@gmail.com)"):
                        st.text_area("Draft", res['invite_text'], height=150)

    with t2:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.subheader("Diversity & Performance Analytics")
            col1, col2 = st.columns(2)
            col1.bar_chart(df.set_index('candidate_name')['score'])
            div_rate = (df['diversity_flag'].sum() / len(df)) * 100
            col2.metric("Diversity Pass Rate", f"{div_rate:.1f}%")
            st.dataframe(df)

if __name__ == "__main__":
    main()
