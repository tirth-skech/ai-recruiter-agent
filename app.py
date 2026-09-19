import streamlit as st
import pandas as pd
import graphviz
import json
import time
from database import init_db, save_candidate_v8, get_audit_logs, log_audit
from processor import (
    parse_profile_agent,
    job_matching_and_gap_agent,
    training_recommendation_agent,
    generate_reasoning_transparency,
    JOB_DATABASE,
    COURSE_DATABASE
)

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Candidate AI Skill-Gap Agent",
    page_icon="🎯",
    layout="wide"
)

# --- 2. AUTHENTICATION ENGINE (PRESERVED EXACTLY) ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Candidate"}
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    if st.session_state.get("manager_login"):
        return {"ok": True, "user": st.session_state.manager_email, "role": "Manager"}
    return {"ok": False}

auth = get_auth_status()

if not auth["ok"]:
    st.title("Recruitment Gateway")
    st.info("Indian Market Context | Enterprise Recruitment Agent")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Candidate Login")
            if st.button("Sign-UP / Log-In", type="primary", use_container_width=True):
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

# --- 3. SIDEBAR & NAVIGATION ---
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
    st.subheader("⚙️ Agentic Filters")
    free_only = st.toggle("🆓 Free-Only Courses Toggle", value=False, help="Filter out paid courses and recalculate metrics using 0-cost pathways.")

    if st.button("🚪 Logout", use_container_width=True):
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

# --- 4. CANDIDATE DASHBOARD INTERFACE ---
st.title("🎯 Skill-Gap-to-Job Matching Agent")
st.caption("Sequential Multi-Agent Pathway & Upskilling Intelligence (Problem Statement C4)")

tabs = ["📄 Profile Upload & Parsing", "📊 Target Job Pathways", "🤖 Reasoning Transparency", "📜 Audit Log"]
active_tabs = st.tabs(tabs)

# --- TAB 1: PARSING AGENT ---
with active_tabs[0]:
    st.header("Step 1: Candidate Profile Intake")
    uploaded_file = st.file_uploader("Upload Your Resume (PDF / DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        if st.button("Run Profile Parsing Agent", type="primary"):
            with st.spinner("Extracting candidate profile schema via Agent 1..."):
                profile = parse_profile_agent(user_api_key, uploaded_file, uploaded_file.name)
                if profile:
                    st.session_state.candidate_profile = profile
                    st.success("Profile parsed successfully!")

    if "candidate_profile" in st.session_state:
        p = st.session_state.candidate_profile
        st.divider()
        st.subheader("Parsed Candidate Schema")
        
        c1, c2 = st.columns(2)
        with c1:
            st.json(p)
        with c2:
            st.markdown(f"**Name:** {p.get('name')}")
            st.markdown(f"**Location:** {p.get('location')}")
            st.markdown(f"**Education:** {p.get('education')}")
            st.markdown("**Current Skills:**")
            st.write(", ".join([f"`{s}`" for s in p.get("current_skills", [])]))

# --- TAB 2: JOB MATCHING & GAP ANALYSIS ---
with active_tabs[1]:
    st.header("Step 2 & 3: Job Matching, Skill-Gap Analysis & Training pathways")

    if "candidate_profile" not in st.session_state:
        st.info("Please upload and parse your resume in Step 1 first.")
    else:
        profile = st.session_state.candidate_profile
        matches = job_matching_and_gap_agent(profile)

        st.subheader("Top Target Job Matches")
        
        for idx, match in enumerate(matches):
            job = match["job"]
            with st.expander(f"💼 {job['title']} @ {job['company']} — Match: {match['match_pct']}%", expanded=(idx == 0)):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown(f"**Location:** {job['location']}")
                    st.markdown(f"**Salary Range:** {job['salary_range']}")
                    st.markdown("**Required Skills:** " + ", ".join([f"`{s}`" for s in job["required_skills"]]))
                    st.markdown("**Matched Skills:** " + ", ".join([f"✅ `{s}`" for s in match["matched_skills"]]))
                    st.markdown("**Missing Skills (Gaps):** " + ", ".join([f"❌ `{s}`" for s in match["missing_skills"]]))

                with col_b:
                    # Calculate Recommendations for this job
                    recs = training_recommendation_agent(match["missing_skills"], free_only=free_only)
                    
                    st.markdown("### 🔑 Key Metrics (Compulsory Feature 7)")
                    m1, m2 = st.columns(2)
                    m1.metric("⏱️ Time-to-Ready", f"{recs['total_weeks']} Weeks")
                    m2.metric("💰 Financial Estimate", f"₹{recs['total_cost']}")

                st.divider()
                st.markdown("#### 🎓 Recommended Training Pathway")
                if recs["courses"]:
                    df_c = pd.DataFrame(recs["courses"])[["platform", "title", "teaches_skills", "duration_weeks", "cost", "is_free", "link"]]
                    st.dataframe(df_c, use_container_width=True)
                else:
                    st.success("No course training needed or no courses match the free-only filter!")

# --- TAB 3: REASONING TRANSPARENCY ---
with active_tabs[2]:
    st.header("Step 4: Reasoning Transparency & Multi-Agent Architecture")
    st.caption("Demonstrating Agent Step Handoffs & Decision Pathways")

    st.markdown("### Agentic Sequential Architecture Flow")
    graph = graphviz.Digraph()
    graph.attr(rankdir='LR', size='8,5')
    graph.node('1', '1. Profile Parsing Agent', shape='box', style='filled', fillcolor='#e1f5fe')
    graph.node('2', '2. Job Matching Agent', shape='box', style='filled', fillcolor='#c8e6c9')
    graph.node('3', '3. Gap Analysis Agent', shape='box', style='filled', fillcolor='#ffcdd2')
    graph.node('4', '4. Training Recommendation Agent', shape='box', style='filled', fillcolor='#fff59d')
    graph.node('5', 'User Dashboard Output', shape='ellipse', style='filled', fillcolor='#d1c4e9')

    graph.edge('1', '2', label='Structured JSON')
    graph.edge('2', '3', label='Target Jobs & Similarity')
    graph.edge('3', '4', label='Missing Skills')
    graph.edge('4', '5', label='Pathways + Metrics')

    st.graphviz_chart(graph)

    st.divider()
    st.markdown("### Agent Reasoning Log")
    if "candidate_profile" in st.session_state:
        profile = st.session_state.candidate_profile
        matches = job_matching_and_gap_agent(profile)
        top_match = matches[0]
        recs = training_recommendation_agent(top_match["missing_skills"], free_only=free_only)

        if st.button("Generate LLM Reasoning Trail"):
            with st.spinner("Generating Agentic Transparency Report..."):
                reasoning = generate_reasoning_transparency(
                    user_api_key,
                    profile,
                    top_match["job"],
                    top_match["missing_skills"],
                    recs
                )
                st.info(reasoning)
    else:
        st.info("Parse a resume in Step 1 to generate live reasoning logs.")

# --- TAB 4: AUDIT LOG ---
with active_tabs[3]:
    st.header("📜 System Audit Log & Compliance")
    logs = get_audit_logs(conn)
    if logs:
        log_df = pd.DataFrame(logs, columns=["Timestamp", "Component", "Action", "Description", "Data", "IP Address"])
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No audit logs recorded yet.")
