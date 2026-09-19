import streamlit as st
import pandas as pd
import graphviz
import json
import time
import io
import fitz  # PyMuPDF
import docx
from google import genai
from google.genai import types
from database import init_db, get_audit_logs, log_audit

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Candidate AI Skill-Gap Agent",
    page_icon="🎯",
    layout="wide"
)

# --- 2. INLINE AGENTS & DATABASES ---
JOB_DATABASE = [
    {
        "job_id": "job_101",
        "title": "Junior AI Engineer",
        "company": "Tech Corp",
        "location": "Ahmedabad",
        "required_skills": ["Python", "LangChain", "Vector Databases", "Docker", "REST APIs"],
        "salary_range": "₹6,000,000 - ₹8,000,000 LPA"
    },
    {
        "job_id": "job_102",
        "title": "Data Scientist",
        "company": "Analytics Inc",
        "location": "Remote",
        "required_skills": ["Python", "SQL", "Pandas", "Scikit-Learn", "Data Analysis"],
        "salary_range": "₹5,000,000 - ₹7,500,000 LPA"
    },
    {
        "job_id": "job_103",
        "title": "LLM Application Developer",
        "company": "AI Innovations",
        "location": "Bengaluru",
        "required_skills": ["Python", "LangChain", "LangGraph", "Docker", "FastAPI"],
        "salary_range": "₹8,000,000 - ₹12,000,000 LPA"
    }
]

COURSE_DATABASE = [
    {
        "course_id": "crs_201",
        "platform": "NPTEL",
        "title": "Building Applications with LangChain & Vector DBs",
        "teaches_skills": ["LangChain", "Vector Databases"],
        "duration_weeks": 4,
        "cost": 0,
        "is_free": True,
        "link": "https://nptel.ac.in/"
    },
    {
        "course_id": "crs_202",
        "platform": "Skill India",
        "title": "Docker Containerization Essentials",
        "teaches_skills": ["Docker"],
        "duration_weeks": 2,
        "cost": 0,
        "is_free": True,
        "link": "https://www.skillindia.gov.in/"
    },
    {
        "course_id": "crs_203",
        "platform": "Coursera",
        "title": "REST APIs & FastAPI Mastery",
        "teaches_skills": ["REST APIs", "FastAPI"],
        "duration_weeks": 3,
        "cost": 1500,
        "is_free": False,
        "link": "https://www.coursera.org/"
    },
    {
        "course_id": "crs_204",
        "platform": "YouTube Freecodecamp",
        "title": "REST APIs & Microservices Crash Course",
        "teaches_skills": ["REST APIs"],
        "duration_weeks": 1,
        "cost": 0,
        "is_free": True,
        "link": "https://youtube.com"
    }
]

def parse_profile_agent(api_key, file_obj, filename):
    try:
        file_obj.seek(0)
        file_bytes = file_obj.read()
        if not file_bytes: return None
        ext = filename.split('.')[-1].lower()
        text = ""
        if ext == 'pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            text = chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs]).strip()

        client = genai.Client(api_key=api_key)
        schema = {
            "type": "OBJECT",
            "properties": {
                "candidate_id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "location": {"type": "STRING"},
                "education": {"type": "STRING"},
                "current_skills": {"type": "ARRAY", "items": {"type": "STRING"}},
                "interests": {"type": "ARRAY", "items": {"type": "STRING"}}
            },
            "required": ["name", "location", "education", "current_skills", "interests"]
        }
        prompt = f"Parse the following resume into a structured candidate profile:\n\n{text}"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema, temperature=0.0)
        )
        data = json.loads(response.text)
        data["candidate_id"] = f"cand_{int(time.time())}"
        return data
    except Exception as e:
        st.error(f"Parsing failed: {e}")
        return None

def job_matching_and_gap_agent(candidate_profile):
    user_skills = set([s.lower() for s in candidate_profile.get("current_skills", [])])
    matched_jobs = []
    for job in JOB_DATABASE:
        req_skills = set([s.lower() for s in job["required_skills"]])
        matched_set = user_skills.intersection(req_skills)
        missing_set = set(job["required_skills"]) - set([s for s in job["required_skills"] if s.lower() in user_skills])
        match_pct = round((len(matched_set) / len(req_skills)) * 100, 1) if req_skills else 0
        matched_jobs.append({
            "job": job, "match_pct": match_pct, "missing_skills": list(missing_set),
            "matched_skills": [s for s in job["required_skills"] if s.lower() in user_skills]
        })
    matched_jobs.sort(key=lambda x: x["match_pct"], reverse=True)
    return matched_jobs

def training_recommendation_agent(missing_skills, free_only=False):
    recommended_courses = []
    for skill in missing_skills:
        for course in COURSE_DATABASE:
            if free_only and not course["is_free"]: continue
            if any(skill.lower() in s.lower() for s in course["teaches_skills"]):
                if course["course_id"] not in [c["course_id"] for c in recommended_courses]:
                    recommended_courses.append(course)
    total_weeks = sum(c["duration_weeks"] for c in recommended_courses)
    total_cost = sum(c["cost"] for c in recommended_courses)
    return {"courses": recommended_courses, "total_weeks": total_weeks, "total_cost": total_cost}

def generate_reasoning_transparency(api_key, profile, selected_job, gap_data, train_data):
    client = genai.Client(api_key=api_key)
    prompt = f"Explain reasoning step-by-step for Candidate: {profile.get('current_skills')} vs Job: {selected_job['required_skills']} with Gaps: {gap_data}"
    try:
        res = client.models.generate_content(model="gemini-2.5-flash", contents=prompt)
        return res.text
    except Exception as e:
        return f"Parsed profile skills against required sets. Identified gaps: {gap_data}."

# --- 3. DATABASE INITIALIZATION ---
conn = init_db()

# --- 4. AUTHENTICATION ENGINE ---
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
                    log_audit(conn, "AUTH", "STAFF_LOGIN", f"Admin logged in: {u}", json.dumps({"user": u}))
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update({"manager_login": True, "manager_email": u})
                    log_audit(conn, "AUTH", "STAFF_LOGIN", f"Manager logged in: {u}", json.dumps({"user": u}))
                    st.rerun()
                else: 
                    st.error("Invalid Credentials")
    st.stop()

# --- 5. SIDEBAR & NAVIGATION ---
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
        log_audit(conn, "AUTH", "LOGOUT", f"User logged out: {auth['user']}", json.dumps({"user": auth['user']}))
        if hasattr(st, "user"): st.logout()
        st.session_state.clear()
        st.rerun()

# --- 6. CANDIDATE DASHBOARD INTERFACE ---
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
                    log_audit(
                        conn, 
                        "AGENT_1_PARSER", 
                        "PARSE_RESUME", 
                        f"Parsed resume for candidate: {profile.get('name')}", 
                        json.dumps({"candidate_id": profile.get("candidate_id"), "filename": uploaded_file.name})
                    )
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
    st.header("Step 2 & 3: Job Matching, Skill-Gap Analysis & Training Pathways")

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
                log_audit(
                    conn,
                    "AGENT_REASONING",
                    "GENERATE_EXPLANATION",
                    f"Generated LLM transparency report for {profile.get('name')}",
                    json.dumps({"job_id": top_match["job"]["job_id"]})
                )
                st.info(reasoning)
    else:
        st.info("Parse a resume in Step 1 to generate live reasoning logs.")

# --- TAB 4: AUDIT LOG ---
with active_tabs[3]:
    st.header("📜 System Audit Log & Compliance")
    st.caption("Tracks all system events, login attempts, resume parsing, and agent executions for governance.")

    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Refresh Logs", type="secondary"):
            st.rerun()

    logs = get_audit_logs(conn)
    if logs:
        # Exactly 6 columns matching: timestamp, component, action, description, data, ip_address
        log_df = pd.DataFrame(
            logs, 
            columns=["Timestamp", "Component", "Action", "Description", "Data Payload", "IP Address"]
        )
        st.dataframe(log_df, use_container_width=True)
    else:
        st.info("No audit logs recorded yet. Perform actions like uploading a resume or logging in to see recorded logs.")
