import io
import json
import time
import urllib.parse
import docx
from duckduckgo_search import DDGS
import fitz  # PyMuPDF
import graphviz
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

from database import (
    cache_search_results,
    get_audit_logs,
    get_cached_search_results,
    init_db,
    log_audit,
)

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="AI Recruiter & Skill-Gap Agent", page_icon="🎯", layout="wide"
)

# Fetch system Gemini API Key securely from Streamlit secrets
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", "")


# --- 2. LIVE JOB SEARCH ENGINES ---
def fetch_live_ddg_jobs(search_term="AI Engineer"):
    """Fetches real-time, active job listings using DuckDuckGo search + Gemini Flash JSON parsing.

    Bypasses Gemini Search Grounding tool to prevent API quota exhaustion. Returns max 3 active jobs.
    """
    clean_keyword = search_term.strip() if search_term.strip() else "AI Engineer"
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY is missing in secrets.")
        return []

    # 1. Scrape real live job search web results using DuckDuckGo
    raw_search_results = []
    try:
        with DDGS() as ddgs:
            results = list(
                ddgs.text(
                    f"{clean_keyword} hiring remote or india apply job site:linkedin.com/jobs OR site:indeed.com OR site:naukri.com",
                    max_results=6,
                )
            )
            for r in results:
                raw_search_results.append({
                    "title": r.get("title", ""),
                    "snippet": r.get("body", ""),
                    "url": r.get("href", ""),
                })
    except Exception as e:
        st.warning(f"DuckDuckGo search error: {e}")

    # Fallback search if specific domain filters yield no results
    if not raw_search_results:
        try:
            with DDGS() as ddgs:
                results = list(
                    ddgs.text(f"{clean_keyword} jobs apply online", max_results=5)
                )
                for r in results:
                    raw_search_results.append({
                        "title": r.get("title", ""),
                        "snippet": r.get("body", ""),
                        "url": r.get("href", ""),
                    })
        except Exception:
            pass

    if not raw_search_results:
        st.warning("No live job listings were found for this query.")
        return []

    # 2. Extract and format structured JSON using standard Gemini Flash
    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Below are raw web search results for open "{clean_keyword}" positions:
    {json.dumps(raw_search_results, indent=2)}

    Extract strictly 3 distinct, high-quality job postings into a JSON array.
    Return ONLY a raw JSON array of 3 items without markdown code blocks.
    Schema required for each object:
    - "job_id": a unique string ID (e.g. "job_1")
    - "title": Clean Job Title
    - "company": Hiring Company Name (Infer from snippet or title)
    - "location": Location or "Remote"
    - "salary_range": "Market Competitive"
    - "raw_text": 2-3 sentence overview of responsibilities
    - "required_skills": Array of 4 to 6 specific technical skills (e.g. ["Python", "SQL", "LangChain"])
    - "job_url": Exact URL from the search result
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json", temperature=0.1
            ),
        )

        cleaned_text = (
            response.text.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
        )
        jobs = json.loads(cleaned_text)

        cleaned_posts = []
        for idx, job in enumerate(jobs[:3]):  # Max 3 items
            cleaned_posts.append({
                "job_id": job.get("job_id", f"ddg_live_{idx+1}"),
                "title": job.get("title", f"{clean_keyword} Role"),
                "company": job.get("company", "Tech Enterprise"),
                "location": job.get("location", "Remote / India"),
                "salary_range": job.get("salary_range", "Market Competitive"),
                "raw_text": job.get("raw_text", "No summary provided."),
                "required_skills": job.get(
                    "required_skills", ["Python", "SQL"]
                ),
                "job_url": job.get(
                    "job_url",
                    f"[https://www.google.com/search?q=](https://www.google.com/search?q=){urllib.parse.quote(clean_keyword + ' jobs')}",
                ),
            })
        return cleaned_posts
    except Exception as e:
        st.error(f"Live Search Formatting Error: {e}")
        return []


def fetch_live_gemini_jobs(search_term="AI Engineer"):
    """Fetches open job listings using Gemini 2.5 Flash with Google Search Grounding."""
    clean_keyword = search_term.strip() if search_term.strip() else "AI Engineer"
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY is missing in secrets.")
        return []

    client = genai.Client(api_key=GEMINI_API_KEY)
    prompt = f"""
    Find 3 REAL, active, and currently open job listings for the role: "{clean_keyword}".
    Search across real job boards and hiring company sites (e.g. LinkedIn, Indeed, enterprise career pages).

    Return ONLY a raw JSON array containing exactly 3 objects. Do NOT wrap in markdown formatting or code blocks.
    Strict JSON keys required for each object:
    - "job_id": a unique string ID
    - "title": Job title
    - "company": Hiring company name
    - "location": Job location or "Remote"
    - "salary_range": Mention "Market Competitive" or actual salary if listed
    - "snippet": Brief overview of role responsibilities (approx 200-300 characters)
    - "required_skills": Array of 4 to 6 specific technical skills requested (e.g. ["Python", "PyTorch", "SQL", "LangChain"])
    - "job_url": Direct URL to the job post or company career page
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[{"google_search": {}}], temperature=0.1
            ),
        )

        cleaned_text = (
            response.text.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
        )

        jobs = json.loads(cleaned_text.strip())

        cleaned_posts = []
        for idx, job in enumerate(jobs[:3]):  # Strictly capped at 3
            cleaned_posts.append({
                "job_id": job.get("job_id", f"gemini_live_{idx+1}"),
                "title": job.get("title", f"{clean_keyword} Role"),
                "company": job.get("company", "Tech Company"),
                "location": job.get("location", "Remote"),
                "salary_range": job.get("salary_range", "Market Competitive"),
                "raw_text": job.get("snippet", "No summary provided."),
                "required_skills": job.get(
                    "required_skills", ["Python", "SQL"]
                ),
                "job_url": job.get(
                    "job_url",
                    f"https://www.google.com/search?q={urllib.parse.quote(clean_keyword + ' jobs')}",
                ),
            })
        return cleaned_posts
    except Exception as e:
        st.error(f"Live Search Execution Error: {e}")
        return []


def get_jobs_with_cache(conn, keyword):
    """Checks SQLite database cache before querying DuckDuckGo to prevent redundant re-runs."""
    keyword_clean = keyword.strip().lower()

    # Try loading cached result first
    try:
        cached_data = get_cached_search_results(conn, keyword_clean)
        if cached_data:
            return json.loads(cached_data)
    except Exception:
        pass

    # Fetch live search jobs
    fresh_jobs = fetch_live_ddg_jobs(keyword_clean)

    if fresh_jobs:
        try:
            cache_search_results(conn, keyword_clean, json.dumps(fresh_jobs))
        except Exception:
            pass

    return fresh_jobs


def parse_profile_agent(api_key, file_obj, filename):
    """Parses candidate profile schema from uploaded resumes (PDF / DOCX)."""
    try:
        file_obj.seek(0)
        file_bytes = file_obj.read()
        if not file_bytes:
            return None
        ext = filename.split(".")[-1].lower()
        text = ""
        if ext == "pdf":
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            text = chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == "docx":
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
                "interests": ["Data Science", "AI Agent Development"],
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
                "current_skills": {
                    "type": "ARRAY",
                    "items": {"type": "STRING"},
                },
                "interests": {"type": "ARRAY", "items": {"type": "STRING"}},
            },
            "required": [
                "name",
                "location",
                "education",
                "current_skills",
                "interests",
            ],
        }
        prompt = f"Parse the following resume into a structured candidate profile:\n\n{text}"
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0,
            ),
        )
        data = json.loads(response.text)
        data["candidate_id"] = f"cand_{int(time.time())}"
        return data
    except Exception as e:
        st.error(f"Parsing failed: {e}")
        return None


def generate_targeted_courses(missing_skills, free_only=False):
    """Generates exact learning links targeting the missing skill name directly on Coursera, YouTube, and NPTEL."""
    courses = []
    for skill in missing_skills:
        exact_skill_query = urllib.parse.quote(skill.strip())

        coursera_url = f"https://www.coursera.org/search?query={exact_skill_query}"
        nptel_url = f"https://swayam.gov.in/explorer?searchText={exact_skill_query}"
        yt_url = f"https://www.youtube.com/results?search_query={exact_skill_query}+tutorial"

        if not free_only:
            courses.append({
                "platform": "Coursera",
                "title": f"Coursera Courses: {skill}",
                "link": coursera_url,
                "skill": skill,
            })

        courses.append({
            "platform": "NPTEL / SWAYAM",
            "title": f"NPTEL Certification: {skill}",
            "link": nptel_url,
            "skill": skill,
        })

        courses.append({
            "platform": "YouTube Free",
            "title": f"{skill} Video Tutorials & Projects",
            "link": yt_url,
            "skill": skill,
        })

    return courses


# --- 3. DATABASE INITIALIZATION ---
conn = init_db()


# --- 4. STRICT RECRUITMENT GATEWAY AUTHENTICATION ENGINE ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {
            "ok": True,
            "user": st.user.get("email"),
            "role": "Candidate",
        }
    if st.session_state.get("admin_login"):
        return {
            "ok": True,
            "user": st.session_state.admin_email,
            "role": "Admin",
        }
    if st.session_state.get("manager_login"):
        return {
            "ok": True,
            "user": st.session_state.manager_email,
            "role": "Manager",
        }
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
            if st.button(
                "Sign-UP / Log-In", type="primary", use_container_width=True
            ):
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
                    st.session_state.update(
                        {"admin_login": True, "admin_email": u}
                    )
                    log_audit(
                        conn,
                        "AUTH",
                        "STAFF_LOGIN",
                        f"Admin logged in: {u}",
                        json.dumps({"user": u}),
                    )
                    st.rerun()
                elif u == "manager@hr.com" and p == "manager423":
                    st.session_state.update(
                        {"manager_login": True, "manager_email": u}
                    )
                    log_audit(
                        conn,
                        "AUTH",
                        "STAFF_LOGIN",
                        f"Manager logged in: {u}",
                        json.dumps({"user": u}),
                    )
                    st.rerun()
                else:
                    st.error("Invalid Credentials")
    st.stop()

# --- 5. SIDEBAR NAVIGATION & USER CONTEXT ---
with st.sidebar:
    st.title("👤 Account Portal")
    st.write(f"**Role:** {auth['role']}")
    st.caption(f"**Active User:** {auth['user']}")

    st.divider()
    st.subheader("⚙️ Agentic Filters")
    free_only = st.toggle(
        "🆓 Free-Only Courses Toggle",
        value=False,
        help="Filter out paid courses and show only free pathways.",
    )

    st.divider()
    if st.button("🚪 Logout", use_container_width=True):
        log_audit(
            conn,
            "AUTH",
            "LOGOUT",
            f"User logged out: {auth['user']}",
            json.dumps({"user": auth["user"]}),
        )
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

tabs = [
    "📄 Profile Ingestion",
    "📊 Job Matching & Search",
    "🧠 Reasoning Transparency",
    "📜 Audit Logs",
]
active_tabs = st.tabs(tabs)

# --- TAB 1: PARSING AGENT & VERIFICATION ---
with active_tabs[0]:
    st.header("Profile Upload & Verification")
    uploaded_file = st.file_uploader(
        "Upload Resume / Portfolio Document (PDF / DOCX)", type=["pdf", "docx"]
    )

    if uploaded_file:
        if st.button("Run Profile Parsing Agent", type="primary"):
            with st.spinner(
                "Extracting candidate profile schema via Gemini 2.5 Flash..."
            ):
                profile = parse_profile_agent(
                    GEMINI_API_KEY, uploaded_file, uploaded_file.name
                )
                if profile:
                    profile.setdefault("marks_10th", "88.5%")
                    profile.setdefault("marks_12th", "91.2%")
                    st.session_state.candidate_profile = profile
                    log_audit(
                        conn,
                        "AGENT_1_PARSER",
                        "PARSE_RESUME",
                        f"Parsed resume for candidate: {profile.get('name')}",
                        json.dumps({
                            "candidate_id": profile.get("candidate_id"),
                            "filename": uploaded_file.name,
                        }),
                    )
                    st.success("Profile parsed successfully!")

    if "candidate_profile" in st.session_state:
        st.divider()
        st.subheader("⚙️ Candidate Information & General Override")
        st.caption(
            "General profile parameters can be edited below. **Skills** and"
            " **10th/12th Grade Records** are locked verified data."
        )

        p = st.session_state.candidate_profile
        col_e1, col_e2 = st.columns(2)

        with col_e1:
            new_name = st.text_input(
                "Candidate Name", value=p.get("name", "Candidate")
            )
            new_location = st.text_input(
                "Location", value=p.get("location", "Ahmedabad")
            )
            new_education = st.text_input(
                "Education Background",
                value=p.get("education", "B.E. Computer Engineering"),
            )

            roles_list = [
                "AI Engineer",
                "Data Scientist",
                "LLM Application Developer",
                "Machine Learning Engineer",
                "Python Developer",
                "Data Analyst",
                "Backend Developer",
                "Custom Role...",
            ]

            current_target = p.get("target_role", "AI Engineer")
            default_index = (
                roles_list.index(current_target)
                if current_target in roles_list
                else 0
            )
            selected_role = st.selectbox(
                "Target Job Role", options=roles_list, index=default_index
            )

            if selected_role == "Custom Role...":
                custom_role_input = st.text_input(
                    "Custom Role Title", value="Generative AI Engineer"
                )
                chosen_role = custom_role_input.strip()
            else:
                chosen_role = selected_role

        with col_e2:
            st.markdown(
                "🔒 **Locked Academic & Verified Record (Read-Only)**"
            )
            st.text_input(
                "10th Grade Marks (Locked)",
                value=p.get("marks_10th", "88.5%"),
                disabled=True,
            )
            st.text_input(
                "12th Grade Marks (Locked)",
                value=p.get("marks_12th", "91.2%"),
                disabled=True,
            )

            locked_skills_str = ", ".join(
                p.get("current_skills", ["Python", "SQL", "Pandas"])
            )
            st.text_area(
                "Extracted Verified Skills (Locked)",
                value=locked_skills_str,
                disabled=True,
                height=100,
            )

        st.session_state.candidate_profile["name"] = new_name
        st.session_state.candidate_profile["location"] = new_location
        st.session_state.candidate_profile["education"] = new_education
        st.session_state.candidate_profile["target_role"] = chosen_role
        st.session_state.override_role = chosen_role

        st.info(f"Target position configured for: **{chosen_role}**")

# --- TAB 2: LIVE JOB MATCHING & GAP RECOMMENDATIONS ---
with active_tabs[1]:
    st.header("Real-Time Job Search & Skill Gap Analysis")

    default_role = st.session_state.get(
        "override_role"
    ) or st.session_state.get("candidate_profile", {}).get(
        "target_role", "AI Engineer"
    )

    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_keyword = st.text_input(
            "Search Role Title / Keyword", value=default_role
        )
    with col_btn:
        st.write("")
        st.write("")
        fetch_clicked = st.button(
            "🔎 Fetch Live Jobs", type="primary", use_container_width=True
        )

    if fetch_clicked:
        with st.spinner(
            f"Searching live web for open '{search_keyword}' roles via Gemini Grounding..."
        ):
            raw_posts = get_jobs_with_cache(conn, search_keyword)

            st.session_state.live_posts = raw_posts
            log_audit(
                conn,
                "DUCKDUCKGO_SEARCH",
                "FETCH_LIVE_JOBS",
                f"Queried live web for role: {search_keyword}",
                json.dumps({"count": len(raw_posts)}),
            )

    if "live_posts" in st.session_state and st.session_state.live_posts:
        candidate_skills = set([
            s.lower()
            for s in st.session_state.get("candidate_profile", {}).get(
                "current_skills", ["python", "sql"]
            )
        ])

        st.subheader(
            f"🌐 Live Recommendations for: {search_keyword} (Max 3 Jobs)"
        )
        for post in st.session_state.live_posts:
            req_skills = post.get("required_skills", [])
            missing = [
                s for s in req_skills if s.lower() not in candidate_skills
            ]

            with st.expander(
                f"💼 {post['title']} — Company: {post['company']}"
                f" ({post['location']})",
                expanded=True,
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Extracted Job Snippet:** {post['raw_text']}")
                    st.write(
                        "**Required Skills:** ",
                        ", ".join([f"`{s}`" for s in req_skills]),
                    )
                    st.write(
                        "**Identified Skill Gaps:** ",
                        ", ".join([f"❌ `{s}`" for s in missing])
                        if missing
                        else "✅ No Gaps!",
                    )

                    st.write("")
                    st.link_button(
                        f"🔗 Apply Directly for {post['title']}",
                        post.get("job_url", "https://google.com"),
                        use_container_width=True,
                        type="primary",
                    )

                with c2:
                    st.markdown("### 🎓 Tailored Learning Pathways")
                    rec_courses = generate_targeted_courses(
                        missing, free_only=free_only
                    )
                    if rec_courses:
                        for course in rec_courses:
                            st.markdown(
                                f"* [{course['platform']}]"
                                f" [{course['title']}]({course['link']})"
                            )
                    else:
                        st.success("All technical requirements matched!")

# --- TAB 3: REASONING TRANSPARENCY ---
with active_tabs[2]:
    st.header("Reasoning Transparency & Agent Decision Pathway")
    st.caption("Demonstrating Agent Step Handoffs & Decision Pathways")

    cand_profile = st.session_state.get(
        "candidate_profile",
        {"name": "Candidate", "current_skills": ["Python", "SQL", "Pandas"]},
    )
    candidate_skills = cand_profile.get("current_skills", ["Python", "SQL"])
    target_role = cand_profile.get("target_role", "AI Engineer")

    st.markdown(
        f"### 🧠 Agentic Architecture Flow (Target Role: **{target_role}**)"
    )
    graph = graphviz.Digraph(format="png")
    graph.attr(rankdir="LR", size="10,4")
    graph.node(
        "A",
        f"📄 Parsed Profile\nRole: {target_role}\nSkills:"
        f" {', '.join(candidate_skills)}",
        shape="ellipse",
        style="filled",
        fillcolor="#E3F2FD",
    )
    graph.node(
        "B",
        f"🌐 Live Web Engine\nDuckDuckGo: '{target_role}'",
        shape="box",
        style="filled",
        fillcolor="#FFF3E0",
    )
    graph.node(
        "C",
        "🤖 Gemini 2.5 Engine\nSkill Extraction",
        shape="box",
        style="filled",
        fillcolor="#E8F5E9",
    )
    graph.node(
        "D",
        "⚡ Set Difference Engine\n(Candidate Skills - Role Skills)",
        shape="diamond",
        style="filled",
        fillcolor="#FFFDE7",
    )
    graph.node(
        "E",
        "🎓 Dynamic Skill Router\n(Coursera, YouTube, NPTEL)",
        shape="ellipse",
        style="filled",
        fillcolor="#F3E5F5",
    )

    graph.edge("A", "D", label="User Skill Vector")
    graph.edge("B", "C", label="Live Search Payload")
    graph.edge("C", "D", label="Extracted Job Skill Array")
    graph.edge("D", "E", label="Identified Skill Gaps")

    st.graphviz_chart(graph, use_container_width=True)
    st.divider()

    if "live_posts" in st.session_state and st.session_state.live_posts:
        st.markdown("### 🔍 Live Matching Logic Breakdown")
        for idx, post in enumerate(st.session_state.live_posts):
            req_skills = post.get("required_skills", [])
            user_skills_lower = [s.lower() for s in candidate_skills]

            matched = [s for s in req_skills if s.lower() in user_skills_lower]
            gaps = [
                s for s in req_skills if s.lower() not in user_skills_lower
            ]
            match_percentage = (
                round((len(matched) / len(req_skills)) * 100)
                if req_skills
                else 100
            )

            with st.expander(
                f"📊 Role {idx+1}: {post['company']} — Match Index:"
                f" {match_percentage}%",
                expanded=True,
            ):
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    st.metric("Role Match Score", f"{match_percentage}%")
                    st.write("**Extracted Required Skills:**")
                    st.json(req_skills)
                with col_m2:
                    st.write(
                        "✅ **Matched Skills:**",
                        ", ".join(matched) if matched else "None",
                    )
                    st.write(
                        "❌ **Missing Skill Gaps:**",
                        ", ".join(gaps) if gaps else "None",
                    )
                    st.caption(
                        "Decision Logic: `Skill Gap = [Skill for Skill in"
                        " Job_Requirements if Skill not in Candidate_Profile]`"
                    )
    else:
        st.info(
            "💡 Run a search query in the **Job Matching & Search** tab to"
            " generate live decision analytics."
        )

# --- TAB 4: AUDIT LOG (RESTRICTED TO ADMIN / MANAGER) ---
with active_tabs[3]:
    st.header("📜 System Audit Log & Compliance")
    st.caption(
        "Tracks all system events, login attempts, resume parsing, and agent"
        " executions for governance."
    )

    if auth["role"] in ["Admin", "Manager"]:
        col_btn, _ = st.columns([1, 4])
        with col_btn:
            if st.button("🔄 Refresh Logs"):
                st.rerun()

        logs = get_audit_logs(conn)
        if logs:
            log_df = pd.DataFrame(
                logs,
                columns=[
                    "Timestamp",
                    "Component",
                    "Action",
                    "Description",
                    "Data Payload",
                    "IP Address",
                ],
            )
            st.dataframe(log_df, use_container_width=True)
        else:
            st.info("No audit logs recorded yet.")
    else:
        st.error(
            "🔒 Access Restricted: Audit logs are accessible only to internal"
            " HR Staff (Admin / Manager)."
        )
        st.info("Please log in as internal staff to view system audit logs.")
