import streamlit as st
import pandas as pd
import plotly.express as px
import os
import time
from database import init_db, save_candidate_v8
from processor import run_agent_workflow

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Goldwin Enterprise AI | Week 8",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (Logic Maintained) ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Recruiter"}
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    if st.session_state.get("manager_login"):
        return {"ok": True, "user": st.session_state.manager_email, "role": "Manager"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("Recruitment Gateway")
    st.info("Indian Market Context | Week 8 Enterprise")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Recruiter Login")
            if st.button("Sign-UP", type="primary", use_container_width=True):
                try: 
                    st.login("auth0")
                except: 
                    st.error("Auth0 Configuration Missing in Secrets.")
                
    with col2:
        with st.form("staff_login"):
            st.subheader("Internal Staff")
            u = st.text_input("Corporate Email")
            p = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                if u == "admin@hr.com" and p == "admin789":
                    st.session_state.update({"admin_login": True, "admin_email": u})
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"manager_login": True, "manager_email": u})
                    st.rerun()
                else: 
                    st.error("Invalid Credentials")
    st.stop()

# --- 3. ENTERPRISE SIDEBAR (Week 8 Security) ---
conn = init_db()

with st.sidebar:
    st.title(f"👤 {auth['role']}")
    st.caption(f"Active: {auth['user']}")
    
    user_api_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=st.secrets.get("GEMINI_API_KEY", ""),
        help="Paste key to override default."
    )

    st.divider()
    st.subheader("🛡️ Governance & GDPR")
    gdpr_privacy = st.toggle("GDPR Data Masking", value=True)
    st.caption("Performance: SQL Indexing Active")

    if st.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

# --- 4. ENTERPRISE TABS ---
tabs = ["🚀 Sourcing", "📋 Pipeline", "🌈 Diversity & Analytics", "📜 API Docs"]
active_tabs = st.tabs(tabs)

with active_tabs[0]:
    st.header("Agentic Sourcing Engine")
    col_a, col_b = st.columns([1, 2])
    with col_a:
        jd = st.text_area("Job Description", height=200, placeholder="Paste JD...")
        with st.expander("Manual Overrides"):
            m_salary = st.number_input("Override Salary (LPA)", min_value=0.0)
            m_reloc = st.radio("Override Relocation", ["Use AI", "Yes", "No"])
            overrides = {"salary": m_salary if m_salary > 0 else None, 
                         "relocation": m_reloc if m_reloc != "Use AI" else None}
    
    with col_b:
        files = st.file_uploader("Upload Resumes", accept_multiple_files=True)
        if st.button("▶️ Start Production Pipeline", type="primary"):
            if user_api_key and jd and files:
                run_agent_workflow(user_api_key, jd, files, auth["user"], conn, save_candidate_v8 ,overrides=overrides)
            else:
                st.warning("Ensure API Key, JD, and Files are present.")

with active_tabs[1]:
    st.header("📋 Candidate Pipeline")
    df_pipe = pd.read_sql("SELECT * FROM candidates", conn)
    if not df_pipe.empty:
        st.dataframe(df_pipe, use_container_width=True)
        
        st.divider()
        st.subheader("📧 Professional Outreach")
        target = st.selectbox("Select Candidate to Contact", df_pipe['email'].unique())
        if target:
            name = df_pipe[df_pipe['email'] == target]['name'].values[0]
            # Mailto link for quick recruiter action
            mail_link = f"mailto:{target}?subject=Interview Invitation&body=Hi {name}, we loved your profile..."
            st.markdown(f'<a href="{mail_link}" style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">✉️ Email {name}</a>', unsafe_allow_html=True)

with active_tabs[2]:
    st.header("🌈 Diversity & Market Analytics")
    df_fresh = pd.read_sql("SELECT * FROM candidates", conn)
    if not df_fresh.empty:
        c1, c2 = st.columns(2)
        with c1:
            # This will now work because gender is extracted in processor.py
            fig = px.pie(df_fresh, names='gender', title="Gender Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(df_fresh, x='edu_tier', color='ethnicity', title="Talent Source Hubs")
            st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Analytics will populate after processing resumes.")

with active_tabs[3]:
    st.header("Technical Documentation")
    st.markdown("""
    ### Microservices Architecture
    - **Auth Service**: Role-based access (Recruiter, Manager, Admin).
    - **Candidate Service**: SQL Backend with Performance Indexing.
    - **AI Engine**: Gemini 2.0 Flash Agentic Workflow via LangGraph.
    - **Privacy**: GDPR-compliant masking toggles enabled.
    """)

# --- 5. ADMIN DANGER ZONE (Fixed Indentation) ---
if auth["role"] == "Admin":
    st.divider()
    st.subheader("⚠️ Danger Zone")
    st.write("Authorized Personnel Only.")

    # Start of Reset Logic
    if st.button("🔥 Initialize Database Reset", type="secondary"):
        st.session_state.confirm_reset = True
        
    if st.session_state.get("confirm_reset"):
        with st.container(border=True):
            st.warning("Final Confirmation Required")
            confirm_p = st.text_input("Enter Admin Password", type="password", key="reset_gate")
            
            col_reset_a, col_reset_b = st.columns(2)
            if col_reset_a.button("Confirm Permanent Delete", type="primary", use_container_width=True):
                if confirm_p == "admin789":
                    db_file = "recruitment_v8_enterprise.db"
                    if os.path.exists(db_file):
                        os.remove(db_file)
                        st.success("Database wiped successfully. Restarting...")
                        st.session_state.confirm_reset = False
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error("Database file not found.")
                else:
                    st.error("Incorrect Password.")
            
            if col_reset_b.button("Cancel", use_container_width=True):
                st.session_state.confirm_reset = False
                st.rerun()

st.divider()
st.caption("Logickverse Enterprise v8.0 | Agentic AI Internship")
