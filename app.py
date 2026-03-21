import streamlit as st
import pandas as pd
import plotly.express as px
from database import init_db, save_candidate
from processor import run_agent_workflow

st.set_page_config(page_title="AI Recruiter Agent", layout="wide")

def get_user():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "email": st.user.get("email"), "role": "Recruiter"}
    if st.session_state.get("admin_auth"):
        return {"ok": True, "email": st.session_state.admin_email, "role": "Admin"}
    return {"ok": False}

user = get_user()

if not user["ok"]:
    st.title("🛡️ Goldwin Secure Portal")
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Auth0 Login", type="primary"):
            st.login("auth0")
    with c2:
        with st.form("admin"):
            u = st.text_input("Admin Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Login"):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"admin_auth": True, "admin_email": u})
                    st.rerun()
else:
    conn = init_db()
    st.sidebar.write(f"Logged as: {user['role']}")
    if st.sidebar.button("Logout"):
        if hasattr(st, "user") and st.user.get("is_logged_in"): st.logout()
        st.session_state.clear()
        st.rerun()

    t1, t2 = st.tabs(["🚀 2.5 Flash Agent", "📊 Analytics"])
    
    with t1:
        if "GEMINI_API_KEY" in st.secrets:
            jd = st.text_area("Job Description", height=150)
            files = st.file_uploader("Candidate Resumes", accept_multiple_files=True)
            if st.button("Start 2.5 Flash Agent"):
                run_agent_workflow(st.secrets["GEMINI_API_KEY"], jd, files, user["email"], conn, save_candidate)
        else: st.error("GEMINI_API_KEY missing in Secrets.")

    with t2:
        df = pd.read_sql("SELECT * FROM recruitment_pipeline", conn)
        if not df.empty:
            st.plotly_chart(px.scatter(df, x="score", y="api_latency", color="status"))
            st.dataframe(df)
