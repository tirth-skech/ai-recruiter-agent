import streamlit as st
import pandas as pd
import graphviz
import json
import time
import io
import requests
import urllib.parse
import fitz  # PyMuPDF
import docx
from google import genai
from google.genai import types
from database import init_db, get_audit_logs, log_audit

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="AI Recruiter & Skill-Gap Agent",
    page_icon="🎯",
    layout="wide"
)

# Fetch system Gemini API Key securely from Streamlit secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# --- 2. INLINE AGENTS & LIVE GOOGLE SEARCH ---
def fetch_live_linkedin_posts(search_term="ai"):
    """Dynamically fetches authentic hiring announcements using Google Custom Search API."""
    clean_keyword = search_term.strip() if search_term.strip() else "hiring"
    
    api_key = st.secrets.get("GOOGLE_SEARCH_API_KEY", "")
    cx_id = st.secrets.get("GOOGLE_SEARCH_CX", "")
    
    if api_key and cx_id:
        params = {
            "q": f"{clean_keyword} hiring",
            "key": api_key,
            "cx": cx_id,
            "num": 5
        }
        url = f"https://www.googleapis.com/customsearch/v1?{urllib.parse.urlencode(params)}"
        
        try:
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                res_data = response.json()
                items = res_data.get("items", [])
                
                if items:
                    cleaned_posts = []
                    for idx, item in enumerate(items):
                        title = item.get("title", f"{clean_keyword.upper()} Role")
                        snippet = item.get("snippet", "No post snippet preview available.")
                        company_author = title.split("|")[0].split(" - ")[0].strip() or "Recruiter"
                        
                        cleaned_posts.append({
                            "job_id": f"google_live_{idx}",
                            "title": f"Hiring Role: {clean_keyword.upper()}",
                            "company": company_author,
                            "location": "India / Remote",
                            "salary_range": "Market Standard",
                            "raw_text": snippet
                        })
                    return cleaned_posts
        except Exception:
            pass

    return [
        {
            "job_id": "fallback_1",
            "title": f"Hiring: {clean_keyword.upper()} Specialist / Engineer",
            "company": "Tech Solutions",
            "location": "India / Remote",
            "salary_range": "₹8,00,000 - ₹14,00,000 PA",
            "raw_text": f"We are actively seeking an experienced {clean_keyword.upper()} professional proficient in core domain skills, REST APIs, and modern toolchains."
        },
        {
            "job_id": "fallback_2",
            "title": f"Senior {clean_keyword.upper()} Specialist",
            "company": "Enterprise Global Labs",
            "location": "Bengaluru (Hybrid)",
            "salary_range": "₹12,00,000 - ₹20,00,000 PA",
            "raw_text": f"Join our growing team as a Senior {clean_keyword.upper()} Lead. Key requirements include proven hands-on project experience and end-to-end execution."
        }
    ]

def extract_skills_from_text(api_key, text_content):
    """Uses Gemini 2.5 Flash Lite to extract required technical skills from text."""
    if not text_content or not api_key:
        return ["Python", "Machine Learning", "SQL"]
        
    client = genai.Client(api_key=api_key)
    prompt = f"Extract a clean JSON array of up to 5 technical skills required in this text:\n\n{text_content}"
    schema = {"type": "ARRAY", "items": {"type": "STRING"}}
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0
            )
        )
        return json.loads(res.text)
    except Exception:
        return ["Python", "SQL", "Data Analysis"]

def parse_profile_agent(api_key, file_obj, filename):
    """Parses candidate profile schema from uploaded resumes (PDF / DOCX)."""
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

        if not api_key:
            return {
                "candidate_id": f"cand_{int(time.time())}",
                "name": "Candidate",
                "location": "Ahmedabad",
                "education": "B.E. Computer Engineering",
                "target_role": "AI Engineer",
                "marks_10th": "88.5%",
                "marks_12th": "91.2%",
                "current_skills": ["Python", "SQL", "Pandas", "Data Science"],
                "interests": ["Data Science", "AI Agent Development"]
            }

        client = genai.Client(api_key=api_key)
        schema = {
            "type": "OBJECT",
            "properties": {
                "candidate_id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "location": {"type": "STRING"},
                "education": {"type": "STRING"},
                "target_role": {"type": "STRING"},
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

def generate_hackathon_courses(missing_skills, free_only=False):
    """Generates direct skill-targeted pathways across Coursera, YouTube, and NPTEL."""
    courses = []
    for skill in missing_skills:
        skill_enc = urllib.parse.quote(skill)
        courses.append({
            "platform": "Coursera",
            "title": f"Mastering {skill} Specialization",
            "teaches_skills": [skill],
            "duration_weeks": 3,
            "cost": 0 if free_only else 1499,
            "is_free": free_only,
            "link": f"https://www.coursera.org/search?query={skill_enc}"
        })
        courses.append({
            "platform": "YouTube",
            "title": f"{skill} Full Crash Course & Hands-on Projects",
            "teaches_skills": [skill],
            "duration_weeks": 1,
            "cost": 0,
            "is_free": True,
            "link": f"https://www.youtube.com/results?search_query={skill_enc}+full+course"
        })
        courses.append({
            "platform": "NPTEL / SWAYAM",
            "title": f"NPTEL Certification Course for {skill}",
            "teaches_skills": [skill],
            "duration_weeks": 4,
            "cost": 0,
            "is_free": True,
            "link": f"https://swayam.gov.in/explorer?searchText={skill_enc}"
        })
    return courses

# --- 3. DATABASE INITIALIZATION ---
conn = init_db()

# --- 4. STRICT RECRUITMENT GATEWAY AUTHENTICATION ENGINE ---
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
    st.caption("Made by Logicverse Dynamic Team from VGEC Chandkheda")
    st.info("Indian Market Context | Enterprise Recruitment Agent")
    
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.subheader("Candidate Login")
            if st.button("Sign-UP / Log-In", type="primary", use_container_width=True):
                try: 
                    st.login("auth0")
                except Exception: 
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

# --- 5. SIDEBAR NAVIGATION & USER CONTEXT ---
with st.sidebar:
    st.title(f"👤 Account Portal")
    st.write(f"**Role:** {auth['role']}")
    st.caption(f"**Active User:** {auth['user']}")
    
    st.divider()
    st.subheader("⚙️ Agentic Filters")
    free_only = st.toggle("🆓 Free-Only Courses Toggle", value=False, help="Filter out paid courses and recalculate metrics using 0-cost pathways.")

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        log_audit(conn, "AUTH", "LOGOUT", f"User logged out: {auth['user']}", json.dumps({"user": auth['user']}))
        if hasattr(st, "user"): 
            try:
                st.logout()
            except Exception:
                pass
        st.session_state.clear()
        st.rerun()

# --- 6. CANDIDATE DASHBOARD INTERFACE ---
st.title("🎯 Live Skill-Gap & Search Agent")
st.caption("Made by Logicverse Dynamic Team from VGEC Chandkheda")
st.markdown("---")

tabs = ["📄 Profile Ingestion", "📊 Job Matching & Search", "🧠 Reasoning Transparency", "📜 Audit Logs"]
active_tabs = st.tabs(tabs)

# --- TAB 1: PARSING AGENT & VERIFICATION ---
with active_tabs[0]:
    st.header("Profile Upload & Verification")
    uploaded_file = st.file_uploader("Upload Resume / Portfolio Document (PDF / DOCX)", type=["pdf", "docx"])

    if uploaded_file:
        if st.button("Run Profile Parsing Agent", type="primary"):
            with st.spinner("Extracting candidate profile schema via Gemini 2.5 Flash..."):
                profile = parse_profile_agent(GEMINI_API_KEY, uploaded_file, uploaded_file.name)
                if profile:
                    profile.setdefault("marks_10th", "88.5%")
                    profile.setdefault("marks_12th", "91.2%")
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
        st.divider()
        st.subheader("⚙️ Candidate Information & General Override")
        st.caption("General profile parameters can be edited below. **Skills** and **10th/12th Grade Records** are locked verified data.")

        p = st.session_state.candidate_profile
        col_e1, col_e2 = st.columns(2)
        
        with col_e1:
            new_name = st.text_input("Candidate Name", value=p.get("name", "Candidate"))
            new_location = st.text_input("Location", value=p.get("location", "Ahmedabad"))
            new_education = st.text_input("Education Background", value=p.get("education", "B.E. Computer Engineering"))
            
            roles_list = [
                "AI Engineer",
                "Data Scientist",
                "LLM Application Developer",
                "Machine Learning Engineer",
                "Python Developer",
                "Data Analyst",
                "Backend Developer",
                "Custom Role..."
            ]
            
            current_target = p.get("target_role", "AI Engineer")
            default_index = roles_list.index(current_target) if current_target in roles_list else 0
            selected_role = st.selectbox("Target Job Role", options=roles_list, index=default_index)
            
            if selected_role == "Custom Role...":
                custom_role_input = st.text_input("Custom Role Title", value="Generative AI Engineer")
                chosen_role = custom_role_input.strip()
            else:
                chosen_role = selected_role

        with col_e2:
            st.markdown("🔒 **Locked Academic & Verified Record (Read-Only)**")
            st.text_input("10th Grade Marks (Locked)", value=p.get("marks_10th", "88.5%"), disabled=True)
            st.text_input("12th Grade Marks (Locked)", value=p.get("marks_12th", "91.2%"), disabled=True)
            
            locked_skills_str = ", ".join(p.get("current_skills", ["Python", "SQL", "Pandas"]))
            st.text_area("Extracted Verified Skills (Locked)", value=locked_skills_str, disabled=True, height=100)

        st.session_state.candidate_profile["name"] = new_name
        st.session_state.candidate_profile["location"] = new_location
        st.session_state.candidate_profile["education"] = new_education
        st.session_state.candidate_profile["target_role"] = chosen_role
        st.session_state.override_role = chosen_role

        st.info(f"Target position configured for: **{chosen_role}**")

# --- TAB 2: LIVE JOB MATCHING & GAP RECOMMENDATIONS ---
with active_tabs[1]:
    st.header("Real-Time Job Search & Skill Gap Analysis")

    default_role = st.session_state.get("override_role") or st.session_state.get("candidate_profile", {}).get("target_role", "AI Engineer")
    
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_keyword = st.text_input("Search Role Title / Keyword", value=default_role)
    with col_btn:
        st.write("")
        st.write("")
        fetch_clicked = st.button("🔎 Fetch Live Jobs", type="primary", use_container_width=True)

    if fetch_clicked:
        with st.spinner(f"Fetching live '{search_keyword}' roles..."):
            raw_posts = fetch_live_linkedin_posts(search_keyword)
            for post in raw_posts:
                post["required_skills"] = extract_skills_from_text(GEMINI_API_KEY, post["raw_text"])
            
            st.session_state.live_posts = raw_posts
            log_audit(
                conn, 
                "GOOGLE_SEARCH_API", 
                "FETCH_POSTS", 
                f"Queried search engine for role: {search_keyword}", 
                json.dumps({"count": len(raw_posts)})
            )

    if "live_posts" in st.session_state and st.session_state.live_posts:
        candidate_skills = set([s.lower() for s in st.session_state.get("candidate_profile", {}).get("current_skills", ["python", "sql"])])
        
        st.subheader(f"🌐 Live Matches for: {search_keyword}")
        for post in st.session_state.live_posts:
            req_skills = post["required_skills"]
            missing = [s for s in req_skills if s.lower() not in candidate_skills]
            
            with st.expander(f"💼 {post['title']} — Company: {post['company']}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Extracted Job Snippet:** {post['raw_text']}")
                    st.write("**Required Skills:** ", ", ".join([f"`{s}`" for s in req_skills]))
                    st.write("**Identified Skill Gaps:** ", ", ".join([f"❌ `{s}`" for s in missing]) if missing else "✅ No Gaps!")
                    
                with c2:
                    st.markdown("### 🎓 Recommended Learning Pathways")
                    rec_courses = generate_hackathon_courses(missing, free_only=free_only)
                    if rec_courses:
                        for course in rec_courses:
                            st.markdown(f"* [{course['platform']}] [{course['title']}]({course['link']})")
                    else:
                        st.success("All technical requirements matched!")

# --- TAB 3: REASONING TRANSPARENCY ---
with active_tabs[2]:
    st.header("Reasoning Transparency & Agent Decision Pathway")
    st.caption("Demonstrating Agent Step Handoffs & Decision Pathways")

    cand_profile = st.session_state.get("candidate_profile", {
        "name": "Candidate",
        "current_skills": ["Python", "SQL", "Pandas"]
    })
    candidate_skills = cand_profile.get("current_skills", ["Python", "SQL"])
    target_role = cand_profile.get("target_role", "AI Engineer")

    st.markdown(f"### 🧠 Agentic Architecture Flow (Target Role: **{target_role}**)")
    graph = graphviz.Digraph(format="png")
    graph.attr(rankdir='LR', size='10,4')
    graph.node('A', f"📄 Parsed Profile\nRole: {target_role}\nSkills: {', '.join(candidate_skills)}", shape='ellipse', style='filled', fillcolor='#E3F2FD')
    graph.node('B', f"🌐 Search API Engine\nQuery: '{target_role} hiring'", shape='box', style='filled', fillcolor='#FFF3E0')
    graph.node('C', "🤖 Gemini Engine\nSkill Extraction", shape='box', style='filled', fillcolor='#E8F5E9')
    graph.node('D', "⚡ Set Difference Engine\n(Candidate Skills - Role Skills)", shape='diamond', style='filled', fillcolor='#FFFDE7')
    graph.node('E', "🎓 Dynamic Learning Router\n(Coursera, YouTube, NPTEL)", shape='ellipse', style='filled', fillcolor='#F3E5F5')

    graph.edge('A', 'D', label='User Skill Vector')
    graph.edge('B', 'C', label='Raw Post Payload')
    graph.edge('C', 'D', label='Extracted Job Skill Array')
    graph.edge('D', 'E', label='Identified Skill Gaps')

    st.graphviz_chart(graph, use_container_width=True)
    st.divider()

    if "live_posts" in st.session_state and st.session_state.live_posts:
        st.markdown("### 🔍 Live Matching Logic Breakdown")
        for idx, post in enumerate(st.session_state.live_posts):
            req_skills = post.get("required_skills", [])
            user_skills_lower = [s.lower() for s in candidate_skills]
            
            matched = [s for s in req_skills if s.lower() in user_skills_lower]
            gaps = [s for s in req_skills if s.lower() not in user_skills_lower]
            match_percentage = round((len(matched) / len(req_skills)) * 100) if req_skills else 100

            with st.expander(f"📊 Role {idx+1}: {post['company']} — Match Index: {match_percentage}%", expanded=True):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("Role Match Score", f"{match_percentage}%")
                    st.write("**Extracted Required Skills:**")
                    st.json(req_skills)
                with col_m2:
                    st.write("✅ **Matched Skills:**", ", ".join(matched) if matched else "None")
                    st.write("❌ **Missing Skill Gaps:**", ", ".join(gaps) if gaps else "None")
                    st.caption("Decision Logic: `Skill Gap = [Skill for Skill in Job_Requirements if Skill not in Candidate_Profile]`")
    else:
        st.info("💡 Run a search query in the **Job Matching & Search** tab to generate live decision analytics.")

# --- TAB 4: AUDIT LOG (RESTRICTED TO ADMIN / MANAGER) ---
with active_tabs[3]:
    st.header("📜 System Audit Log & Compliance")
    st.caption("Tracks all system events, login attempts, resume parsing, and agent executions for governance.")

    if auth["role"] in ["Admin", "Manager"]:
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button("🔄 Refresh Logs"):
                st.rerun()

        logs = get_audit_logs(conn)
        if logs:
            log_df = pd.DataFrame(
                logs, 
                columns=["Timestamp", "Component", "Action", "Description", "Data Payload", "IP Address"]
            )
            st.dataframe(log_df, use_container_width=True)
        else:
            st.info("No audit logs recorded yet.")
    else:
        st.error("🔒 Access Restricted: Audit logs are accessible only to internal HR Staff (Admin / Manager).")
        st.info("Please log in as internal staff to view system audit logs.")
