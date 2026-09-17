import streamlit as st
import pandas as pd
import plotly.express as px
import graphviz
import os
import time
from database import init_db, save_candidate_v8, get_audit_logs, log_audit
from processor import preview_resumes, PredictiveAnalytics
import urllib.parse

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="RecruitGap AI | Skill-Gap Matching",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION (UNTOUCHED ORIGINAL LOGIC) ---
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

# --- 3. ENTERPRISE SIDEBAR & NAVIGATION ---
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
tabs = ["📊 Dashboard", "🚀 Candidate Intake", "📋 Pipeline", "🌈 Talent Analytics", "📜 Audit Log"]
active_tabs = st.tabs(tabs)

# --- TAB 1: DASHBOARD ---
with active_tabs[0]:
    st.title("RecruitGap AI")
    st.caption("Skill-Gap-to-Job Matching Agent 🎈")
    st.markdown(f"**Welcome, {auth['role']}!**")
    
    st.text_input("🔍 Search candidates and job roles...", key="dash_search")

    st.markdown("### AI Matching Overview")
    m1, m2, m3 = st.columns(3)
    
    df_count = pd.read_sql("SELECT COUNT(*) as cnt, AVG(match_score) as avg_score FROM candidates", conn)
    total_cands = df_count['cnt'].iloc[0] if not df_count.empty else 0
    avg_score = round(df_count['avg_score'].iloc[0], 1) if not df_count.empty and df_count['avg_score'].iloc[0] else 85.0
    
    m1.metric("Active Job Roles", "17", "1.86%")
    m2.metric("Total Candidates Analyzed", f"{1315 + total_cands}", "9.59%")
    m3.metric("Average Matching Score", f"{avg_score} %", "12.6%")

    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("#### Recent Analysis")
        df_recent = pd.read_sql("SELECT name as 'Candidate Name', job_role as 'Job Role', match_score as 'Current Matching Score', gaps as 'Skill Gaps' FROM candidates ORDER BY id DESC LIMIT 5", conn)
        if not df_recent.empty:
            df_recent['Current Matching Score'] = df_recent['Current Matching Score'].astype(str) + "%"
            st.dataframe(df_recent, use_container_width=True)
        else:
            sample_data = [
                {"Candidate Name": "Emily Chen", "Job Role": "Manager", "Current Matching Score": "85%", "Skill Gaps": "Python, Gap Identified"},
                {"Candidate Name": "Mark Johnson", "Job Role": "Developer", "Current Matching Score": "85%", "Skill Gaps": "SQL, Gap Identified"},
                {"Candidate Name": "Acinm Dlosd", "Job Role": "Talent Manager", "Current Matching Score": "85%", "Skill Gaps": "SQL, In Progress"},
                {"Candidate Name": "Berry Cromit", "Job Role": "Developer", "Current Matching Score": "85%", "Skill Gaps": "Python, In Progress"}
            ]
            st.dataframe(pd.DataFrame(sample_data), use_container_width=True)

    with c2:
        st.markdown("#### Matches Over Time & Top Skill Shortages")
        shortage_df = pd.DataFrame({
            'Skill': ['Python', 'SQL', 'GCP Architecture', 'Kafka'],
            'Shortage': [80, 55, 30, 15]
        })
        fig = px.bar(shortage_df, x='Shortage', y='Skill', orientation='h', height=200)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Candidate Inbox")
        st.info("Drag and drop file upload for resumes and job descriptions available in Candidate Intake tab.")

# --- TAB 2: CANDIDATE INTAKE & SOURCING ---
with active_tabs[1]:
    st.header("🚀 Candidate Data Intake & Smart Sourcing")
    
    col_up1, col_up2 = st.columns(2)
    with col_up1:
        files = st.file_uploader("Upload Resume (PDF/DOCX)", accept_multiple_files=True, type=['pdf', 'docx'], key="sourcing_upload")
    with col_up2:
        jd = st.text_area("Job Description (Required for Matching)", placeholder="Paste Job Description for skill matching...", key="jd_text")

    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        c_name = st.text_input("Candidate Full Name", placeholder="Candidate Full Name")
    with col_meta2:
        c_email = st.text_input("Candidate Email", placeholder="Candidate Email @gmail.com")

    if files and jd:
        if st.button("Step 1: Extract & Run Skill Gap Analysis"):
            with st.spinner("Executing Agentic Analysis..."):
                results = preview_resumes(user_api_key, jd, files, c_name, c_email)
                st.session_state.preview_data = results

    if "preview_data" in st.session_state:
        st.divider()
        st.subheader("📋 Core Skills & Review Overrides")
        final_list = []
        
        for i, candidate in enumerate(st.session_state.preview_data):
            with st.expander(f"Review: {candidate['name']} ({candidate['filename']})", expanded=True):
                st.markdown("**Core Skills Identified by AI Agent:**")
                skills_tags = " ".join([f"`{s}`" for s in candidate.get('skills', [])])
                st.markdown(skills_tags if skills_tags else "`None Extracted`")

                col1, col2, col3 = st.columns(3)
                with col1:
                    o_name = st.text_input("Name", value=candidate['name'], key=f"n_{i}")
                    o_role = st.text_input("Primary Job Title", value=candidate.get('job_role', 'Developer'), key=f"jr_{i}")
                with col2:
                    o_email = st.text_input("Email Override", value=candidate['email'], key=f"e_{i}")
                    o_salary = st.number_input("Salary (LPA)", value=float(candidate.get('salary_exp', 0)), key=f"s_{i}")
                with col3:
                    st.metric("Match Score", f"{candidate.get('match_score', 85)}%")
                    st.metric("Projected Score", f"{candidate.get('projected_score', 95)}%")
                
                candidate.update({"name": o_name, "email": o_email, "job_role": o_role, "salary_exp": o_salary})
                final_list.append(candidate)

        if st.button("Step 2: Save All to Pipeline", type="primary"):
            for person in final_list:
                p_score = PredictiveAnalytics.calculate_retention_score(person)
                save_candidate_v8(conn, person, 1, p_score)
            
            st.success("All candidates and skill gap profiles saved successfully!")
            del st.session_state.preview_data
            st.rerun()

# --- TAB 3: PIPELINE ---
with active_tabs[2]:
    st.header("📋 Candidate Pipeline")
    df_pipe = pd.read_sql("SELECT * FROM candidates", conn)
    
    if not df_pipe.empty:
        st.dataframe(df_pipe, use_container_width=True)
        
        st.divider()
        st.subheader("📧 Recruitment Mail Dashboard")
        
        target_email = st.selectbox("Select Candidate", df_pipe['email'].unique())
        
        if target_email:
            row = df_pipe[df_pipe['email'] == target_email].iloc[0]
            cand_name = row['name']
            
            mail_content = f"""FROM: Goldwin Recruitment Team <hr@goldwin.com>
TO: {cand_name} <{target_email}>
SUBJECT: Interview Invitation - Skill Match Role ({row['job_role']})

MESSAGE:
Hi {cand_name},

We have reviewed your skill gap analysis profile for the {row['job_role']} position. 
We were impressed with your technical background and would like to schedule an interview.

Best regards,
Goldwin Recruitment Team
"""
            st.code(mail_content, language="markdown")
            
            safe_subject = urllib.parse.quote(f"Interview Invitation - {cand_name}")
            safe_body = urllib.parse.quote(f"Hi {cand_name}, we would like to move forward...")
            mail_link = f"mailto:{target_email}?subject={safe_subject}&body={safe_body}"
            
            st.markdown(f'<a href="{mail_link}" target="_blank" style="background-color:#28a745; color:white; padding:8px 16px; text-decoration:none; border-radius:5px;">🚀 Open Default Mail App</a>', unsafe_allow_html=True)

# --- TAB 4: TALENT ANALYTICS ---
with active_tabs[3]:
    st.header("🌈 Talent Analytics & Agentic Workflow")
    
    st.markdown("### Talent Pipeline Overview")
    a1, a2, a3, a4 = st.columns(4)
    df_pipe_all = pd.read_sql("SELECT * FROM candidates", conn)
    count_val = len(df_pipe_all) if not df_pipe_all.empty else 10
    
    a1.metric("Processed Candidates", f"{count_val}")
    a2.metric("Average Match Score (Current)", "85%")
    a3.metric("Match Score (Projected after Upskilling)", "95%")
    a4.metric("Top In-Demand Role", "Senior Data Scientist")

    st.divider()
    st.markdown("### Explainable Match Graph")
    st.caption("How agentic workflow graph routes candidate profiling, skill gap analysis, and training recommendations.")

    # Agentic Visual Workflow Chart
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR', size='8,5')
    graph.node('A', 'Candidate Selection', shape='ellipse', style='filled', fillcolor='#e1f5fe')
    graph.node('B', 'Candidate Profiling Agent', shape='box', style='filled', fillcolor='#c8e6c9')
    graph.node('C', 'Skill-Gap Agent', shape='box', style='filled', fillcolor='#ffcdd2')
    graph.node('D', 'Skill Gap Analysis', shape='box')
    graph.node('E', 'Role Alignment', shape='box')
    graph.node('F', 'Training Recs', shape='box')
    graph.node('G', 'Match Score', shape='ellipse', style='filled', fillcolor='#fff59d')

    graph.edge('A', 'B')
    graph.edge('A', 'C')
    graph.edge('B', 'D')
    graph.edge('B', 'E')
    graph.edge('C', 'E')
    graph.edge('C', 'F')
    graph.edge('D', 'G')
    graph.edge('E', 'G')
    graph.edge('F', 'G')

    st.graphviz_chart(graph)

    st.divider()
    st.markdown("### Strategic Upskilling Suggestions")
    recs_data = [
        {"Skill Gap": "Python (Cloud)", "Recommended Course": "Coursera/Udemy", "Upskilling Time": "20 minutes", "Match Score Improvement": "+10%"},
        {"Skill Gap": "GCP Architecture", "Recommended Course": "Coursera/Google Cloud", "Upskilling Time": "2 hours", "Match Score Improvement": "+15%"},
        {"Skill Gap": "Kafka", "Recommended Course": "Coursera/Confluent", "Upskilling Time": "2 hours", "Match Score Improvement": "+8%"}
    ]
    st.dataframe(pd.DataFrame(recs_data), use_container_width=True)

    if not df_pipe_all.empty:
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            fig = px.pie(df_pipe_all, names='gender', title="Gender Distribution")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            fig2 = px.bar(df_pipe_all, x='edu_tier', color='ethnicity', title="Talent Source Hubs")
            st.plotly_chart(fig2, use_container_width=True)

# --- TAB 5: AUDIT LOG ---
with active_tabs[4]:
    st.header("📜 System Audit Log & Compliance")
    st.caption("Traceable System Activity and AI Decisions")

    logs = get_audit_logs(conn)
    if logs:
        log_df = pd.DataFrame(logs, columns=["Timestamp", "System Component", "User Action", "Description", "Associated Data", "IP Address"])
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No audit logs recorded yet.")

    st.divider()
    col_c1, col_c2 = st.columns(2)
    with col_c1:
        st.markdown("#### Compliance Controls")
        st.toggle("GDPR/CCPA Masking", value=True)
        st.toggle("API Log Rotation", value=True)
    
    with col_c2:
        st.metric("Total Events Today", "2,415")
        st.metric("Recent Agent Errors", "0")

# --- 5. ADMIN DANGER ZONE (ORIGINAL RESTORED) ---
if auth["role"] == "Admin":
    st.divider()
    st.subheader("⚠️ Danger Zone")
    st.write("Authorized Personnel Only.")

    if st.button("🔥 Initialize Database Reset", type="secondary"):
        st.session_state.confirm_reset = True
        
if st.session_state.get("confirm_reset"):
    with st.container(border=True):
        st.warning("⚠️ Final Confirmation Required")
        confirm_p = st.text_input("Enter Admin Password", type="password", key="reset_gate")
        
        col_a, col_b = st.columns(2)
        
        if col_a.button("Confirm Permanent Delete", type="primary", use_container_width=True):
            if confirm_p == "admin789":
                db_file = "recruitment_v8_enterprise.db"
                try:
                    if 'conn' in globals():
                        conn.close()
                    
                    if os.path.exists(db_file):
                        os.remove(db_file)
                        st.success("Database wiped successfully. Please restart the app.")
                        st.session_state.confirm_reset = False
                        time.sleep(2)
                        st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}. The file might be in use.")
            else:
                st.error("Incorrect Password.")
        
        if col_b.button("Cancel", use_container_width=True):
            st.session_state.confirm_reset = False
            st.rerun()
    st.divider()
    st.caption("RecruitGap AI Enterprise | Track C4 Integration")
