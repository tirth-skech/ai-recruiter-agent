import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_complex_agent

st.set_page_config(page_title="AI Recruiter Pro", layout="wide")

# --- AUTH0 & STAFF LOGIN LOGIC ---
if hasattr(st, "user") and st.user.is_logged_in:
    st.session_state.update({"auth": True, "role": "Recruiter", "email": st.user.email})
elif "auth" not in st.session_state:
    st.session_state.auth = False

def login_ui():
    st.title("🛡️ Secure Recruitment Portal")
    choice = st.radio("Access Method", ["Recruiter (Auth0)", "Staff Login"], horizontal=True)
    
    if choice == "Recruiter (Auth0)":
        if st.button("Login with Google"): st.login("auth0")
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
                else: st.error("Invalid credentials")

# --- MAIN APP ROUTER ---
def main():
    if not st.session_state.auth:
        login_ui()
        return

    conn = init_db()
    role = st.session_state.role
    
    st.sidebar.title(f"Role: {role}")
    if st.sidebar.button("Logout"):
        st.session_state.auth = False
        st.rerun()

    # Role-based Tab View
    tab_titles = ["Agent Workspace", "Dashboard"]
    if role == "Admin": tab_titles.append("System Admin")
    tabs = st.tabs(tab_titles)

    with tabs[0]:
        st.header("LangGraph Pipeline")
        key = st.text_input("API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Execute Agent"):
            results = run_complex_agent(key, jd, files)
            for res in results:
                save_candidate(conn, res)
                
                # RECRUITER SUMMARY CARD
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    c1.metric("Score", f"{res['score']}%")
                    c2.subheader(res['name'])
                    c2.markdown(f"**AI Summary:** {res['summary']}")
                    with c2.expander("📩 Invitation Draft (from: ai26agent@gmail.com)"):
                        st.text_area("Draft Body", res['invite_text'], height=150)
                        st.button(f"Send to {res['name']}", key=res['name'])

    with tabs[1]:
        st.header("Analytics & Diversity")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            col1, col2 = st.columns(2)
            col1.subheader("Match Scores")
            col1.bar_chart(df.set_index('candidate_name')['score'])
            
            # Diversity Analytics
            col2.subheader("D&I Metrics")
            pass_rate = (df['diversity_flag'].sum() / len(df)) * 100
            col2.metric("Diversity Pass Rate", f"{pass_rate:.1f}%")
            st.dataframe(df)

if __name__ == "__main__":
    main()
