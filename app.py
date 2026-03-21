import streamlit as st
import pandas as pd
from database import init_db, save_candidate
from processor import run_complex_agent

st.set_page_config(page_title="Agentic AI Recruiter", layout="wide")

# --- Auth Logic (Existing) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def login_ui():
    st.title("🛡️ Staff Portal")
    with st.form("login"):
        e = st.text_input("Email")
        p = st.text_input("Password", type="password")
        if st.form_submit_button("Login"):
            if e == "admin@hr.com" and p == "admin789":
                st.session_state.update({"authenticated": True, "user_role": "Admin", "user_email": e})
                st.rerun()
            else: st.error("Invalid Credentials")

def main():
    if not st.session_state.authenticated:
        login_ui()
        return

    conn = init_db()
    st.sidebar.title(f"👤 {st.session_state.user_role}")
    
    t1, t2 = st.tabs(["Agent Workspace", "Analytics Dashboard"])

    with t1:
        st.header("LangGraph Recruitment Pipeline")
        api_key = st.text_input("Gemini API Key", type="password")
        jd = st.text_area("Job Description")
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)

        if st.button("🚀 Run Complex Agent"):
            results = run_complex_agent(api_key, jd, files, st.session_state.user_email)
            
            for res in results:
                # Save to DB
                save_candidate(conn, res, st.session_state.user_email)
                
                # --- RECRUITER SUMMARY UI ---
                with st.container(border=True):
                    col1, col2 = st.columns([1, 4])
                    col1.metric("Score", f"{res['score']}%")
                    col2.subheader(f"Candidate: {res['name']}")
                    col2.write(f"**AI Summary:** {res['summary']}")
                    
                    with col2.expander("📩 View Drafted Invitation"):
                        st.caption("Sender: ai26agent@gmail.com")
                        st.text_area("Email Draft", res['invite_text'], height=200)
                        st.button(f"Send Invite to {res['name']}", key=res['name'])

    with t2:
        st.header("Diversity & Pipeline Analytics")
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            c1, c2 = st.columns(2)
            # ML Matching Analytics
            c1.line_chart(df['score'])
            # Diversity Analytics
            div_count = df['diversity_flag'].sum()
            c2.pie_chart(pd.DataFrame({'status': ['Diversity Pass', 'Standard'], 'count': [div_count, len(df)-div_count]}))
            st.dataframe(df)

if __name__ == "__main__":
    main()
