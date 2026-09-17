import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import graphviz
from database import init_db, save_candidate_intake, log_audit, get_candidates, get_audit_logs
from processor import analyze_skill_gap

# --- 1. PAGE SETUP ---
st.set_page_config(
    page_title="RecruitGap AI | Skill-Gap-to-Job Matching Agent",
    page_icon="🎈",
    layout="wide"
)

conn = init_db()

# --- 2. AUTHENTICATION (Recruiter OR ADMIN) ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
    st.session_state.role = None
    st.session_state.username = ""

if not st.session_state.authenticated:
    st.title("RecruitGap AI Login")
    st.caption("Skill-Gap-to-Job Matching Agent — Track C4 Project")
    
    col1, col2 = st.columns(2)
    
    with col1:
        with st.container(border=True):
            st.subheader("👤 Recruiter Login")
            r_user = st.text_input("Recruiter Email", key="r_user")
            r_pass = st.text_input("Password", type="password", key="r_pass")
            if st.button("Login as Recruiter", type="primary", use_container_width=True):
                if r_user and r_pass == "recruit123":
                    st.session_state.authenticated = True
                    st.session_state.role = "Recruiter"
                    st.session_state.username = r_user
                    log_audit(conn, "Auth System", "Login", f"Recruiter {r_user} logged in.")
                    st.rerun()
                else:
                    st.error("Invalid Recruiter Credentials")

    with col2:
        with st.container(border=True):
            st.subheader("🛡️ ADMIN Login")
            a_user = st.text_input("Admin Email", key="a_user")
            a_pass = st.text_input("Password", type="password", key="a_pass")
            if st.button("Login as Admin", type="secondary", use_container_width=True):
                if a_user == "admin@hr.com" and a_pass == "admin789":
                    st.session_state.authenticated = True
                    st.session_state.role = "Admin"
                    st.session_state.username = a_user
                    log_audit(conn, "Auth System", "Login", f"Admin {a_user} logged in.")
                    st.rerun()
                else:
                    st.error("Invalid Admin Credentials")
    st.stop()

# --- 3. SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("Navigation")
    menu = st.radio("", ["Dashboard", "Candidate Intake", "Talent Analytics", "Audit Log"])
    
    st.divider()
    st.caption(f"Account: **{st.session_state.role}** ({st.session_state.username})")
    
    user_api_key = st.text_input(
        "Gemini API Key", 
        type="password", 
        value=st.secrets.get("GEMINI_API_KEY", ""),
        help="API Key for Agentic Reasoning"
    )
    
    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.role = None
        st.rerun()

# --- 4. NAVIGATION MODULES ---

# --- DASHBOARD ---
if menu == "Dashboard":
    st.title("RecruitGap AI")
    st.subheader("Skill-Gap-to-Job Matching Agent 🎈")
    st.markdown(f"**Welcome, {st.session_state.role}!**")
    
    st.text_input("🔍 Search candidates and job roles...", "")

    st.markdown("### AI Matching Overview")
    m1, m2, m3 = st.columns(3)
    m1.metric("Active Job Roles", "17", "1.86%")
    m2.metric("Total Candidates Analyzed", "1,315", "9.59%")
    m3.metric("Average Matching Score", "85 %", "12.6%")

    c1, c2 = st.columns([2, 1])

    with c1:
        st.markdown("#### Recent Analysis")
        data = [
            {"Candidate Name": "Emily Chen", "Job Role": "Manager", "Current Matching Score": "85%", "Skill Gaps": "Python, Gap Identified", "Action": "View Profile"},
            {"Candidate Name": "Mark Johnson", "Job Role": "Developer", "Current Matching Score": "85%", "Skill Gaps": "SQL, Gap Identified", "Action": "View Profile"},
            {"Candidate Name": "Acinm Dlosd", "Job Role": "Talent Manager", "Current Matching Score": "85%", "Skill Gaps": "SQL, In Progress", "Action": "View Profile"},
            {"Candidate Name": "Mark Johnson", "Job Role": "Manager", "Current Matching Score": "70%", "Skill Gaps": "SQL, Gap Identified", "Action": "View Profile"},
            {"Candidate Name": "Berry Cromit", "Job Role": "Developer", "Current Matching Score": "85%", "Skill Gaps": "Python, In Progress", "Action": "View Profile"}
        ]
        st.dataframe(pd.DataFrame(data), use_container_width=True)

    with c2:
        st.markdown("#### Matches Over Time & Shortages")
        
        # Skill shortage bar chart
        shortage_df = pd.DataFrame({
            'Skill': ['Python', 'SQL', 'GCP', 'Kafka'],
            'Shortage': [80, 55, 30, 15]
        })
        fig = px.bar(shortage_df, x='Shortage', y='Skill', orientation='h', height=200)
        st.plotly_chart(fig, use_container_width=True)

        st.markdown("#### Candidate Inbox")
        st.info("Drag and drop file upload for resumes and job descriptions")

# --- CANDIDATE INTAKE ---
elif menu == "Candidate Intake":
    st.title("Candidate Data Intake")
    st.caption("Skill-Gap-to-Job Matching Agent — Multi-agent Analysis")

    col_up1, col_up2 = st.columns(2)
    with col_up1:
        resume_file = st.file_uploader("Upload Resume (PDF/DOCX)", type=['pdf', 'docx'])
    with col_up2:
        jd_input = st.text_area("Job Description (Required for Matching)", placeholder="Paste Job Description matching...")

    c_name = st.text_input("Candidate Full Name", placeholder="Candidate Full Name")
    c_email = st.text_input("Candidate Email", placeholder="Candidate Email @gmail.com")

    if resume_file and jd_input:
        if st.button("Extract & Run Skill Gap Analysis", type="primary"):
            with st.spinner("Executing Agentic Analysis..."):
                res = analyze_skill_gap(user_api_key, jd_input, c_name, c_email, resume_file)
                if res:
                    st.session_state.processed_candidate = res
                    save_candidate_intake(conn, res)
                    st.success("Candidate Processed and Saved to Pipeline!")

    if "processed_candidate" in st.session_state:
        cand = st.session_state.processed_candidate
        st.divider()
        st.markdown("### Core Skills Extraction")
        st.write("Key Skills identified by AI agent:")
        
        # Tags display
        skills_html = " ".join([f"<span style='background-color:#e1f5fe; color:#0288d1; padding:4px 8px; border-radius:4px; margin-right:4px;'>{s}</span>" for s in cand.get('skills', [])])
        st.markdown(skills_html, unsafe_allow_html=True)

        st.markdown(f"**Primary Job Title:** `{cand.get('job_role', 'N/A')}`")
        st.button("Validate and add more")

        st.markdown("### Intake Queue")
        queue_df = pd.DataFrame([
            {"File Name": resume_file.name if resume_file else "RecruitGap.PDF", "Candidate": cand['name'], "Status": "Processing", "Actions": "Match Now"},
            {"File Name": "RecruitGap.PDF", "Candidate": "Mark Johnson", "Status": "Reviewing", "Actions": "View Details"},
            {"File Name": "RecruitGap.DOCX", "Candidate": "Arim Blood", "Status": "Complete", "Actions": "View Details"}
        ])
        st.dataframe(queue_df, use_container_width=True)

# --- TALENT ANALYTICS ---
elif menu == "Talent Analytics":
    st.title("Talent Analysis")
    st.caption("Agentic Workflow & Pipeline Analytics")

    st.markdown("### Talent Pipeline Overview")
    a1, a2, a3, a4 = st.columns(4)
    a1.metric("Processed Candidates", "10")
    a2.metric("Average Match Score (Current)", "85%")
    a3.metric("Match Score (Projected after Upskilling)", "95%")
    a4.metric("Top In-Demand Role", "Senior Data Scientist")

    st.divider()
    st.markdown("### Explainable Match Graph")
    st.caption("How agentic workflow graph routes candidate profiling, skill gap analysis, and training recommendations.")

    # Agentic Visual Workflow
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

# --- AUDIT LOG ---
elif menu == "Audit Log":
    st.title("SYSTEM AUDIT LOG & COMPLIANCE")
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
