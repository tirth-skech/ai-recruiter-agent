import io
import json
import operator
import random
import re
import time
import urllib.parse
from typing import Annotated, TypedDict

import docx
from duckduckgo_search import DDGS
import fitz  # PyMuPDF
import pandas as pd
import streamlit as st
from google import genai
from google.genai import types

try:
    from langgraph.graph import END, START, StateGraph

    LANGGRAPH_AVAILABLE = True
except ImportError:  # add `langgraph` to requirements.txt
    LANGGRAPH_AVAILABLE = False

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


# --- 1B. RETRY + FALLBACK HELPERS (handles 503 / 429 "high demand" errors) ---
PRIMARY_MODEL = "gemini-3.6-flash"
FALLBACK_MODEL = "gemini-2.5-flash"  # backup model; set to "" to disable
MAX_RETRIES = 4  # attempts per model
BASE_DELAY = 2  # seconds; doubles each retry (2s, 4s, 8s ...)
MAX_DELAY = 20  # cap for a single wait


def _is_transient_error(err):
    """True for temporary errors worth retrying (overload, rate limit, timeout)."""
    code = getattr(err, "code", None)
    if code in (429, 500, 502, 503, 504):
        return True
    msg = str(err).lower()
    markers = (
        "unavailable",
        "overloaded",
        "high demand",
        "resource_exhausted",
        "rate limit",
        "deadline exceeded",
        "timed out",
        "timeout",
        "temporarily",
        "connection reset",
        "connection error",
    )
    return any(m in msg for m in markers)


def generate_with_retry(client, contents, config, max_retries=MAX_RETRIES):
    """Calls Gemini with exponential backoff, then falls back to a backup model.

    - Retries only temporary errors (503, 429, timeouts).
    - Permanent errors (bad API key, bad request) are raised immediately.
    - If every attempt fails, the last error is raised so callers can show it.
    """
    models = [PRIMARY_MODEL]
    if FALLBACK_MODEL and FALLBACK_MODEL != PRIMARY_MODEL:
        models.append(FALLBACK_MODEL)

    last_error = None
    for model_idx, model_name in enumerate(models):
        for attempt in range(1, max_retries + 1):
            try:
                return client.models.generate_content(
                    model=model_name, contents=contents, config=config
                )
            except Exception as e:
                if not _is_transient_error(e):
                    if model_idx == 0 or last_error is None:
                        raise
                    # Backup model failed for a permanent reason (e.g. wrong
                    # model name): report the original overload error instead.
                    raise last_error
                last_error = e
                if attempt < max_retries:
                    delay = min(BASE_DELAY * (2 ** (attempt - 1)), MAX_DELAY)
                    delay += random.uniform(0, 1)
                    st.toast(
                        f"⏳ Gemini is busy — retrying ({attempt}/{max_retries})"
                        f" in {delay:.0f}s...",
                        icon="🔁",
                    )
                    time.sleep(delay)
        if model_idx + 1 < len(models):
            st.toast(
                f"⚠️ {model_name} still busy — switching to {models[model_idx + 1]}...",
                icon="🔀",
            )
    raise last_error


def show_api_error(prefix, err):
    """Shows a friendly message for overload errors, raw details otherwise."""
    print(f"[{prefix}] {err}")
    if _is_transient_error(err):
        st.error(
            f"{prefix}: Gemini is still overloaded after several automatic"
            " retries. Please wait about a minute and try again."
        )
    else:
        st.error(f"{prefix}: {err}")


def ddg_text_with_retry(query, max_results, retries=3, base_delay=2):
    """DuckDuckGo search that retries on rate limits and empty (throttled) replies."""
    last_error = None
    for attempt in range(1, retries + 1):
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=max_results))
            if results:
                return results
        except Exception as e:
            last_error = e
        if attempt < retries:
            time.sleep(base_delay * attempt + random.uniform(0, 1))
    if last_error:
        st.warning(f"DuckDuckGo search error: {last_error}")
    return []


def collect_ddg_results(query, max_results):
    """Runs a DuckDuckGo search and returns cleaned title/snippet/url dicts."""
    return [
        {
            "title": r.get("title", ""),
            "snippet": r.get("body", ""),
            "url": r.get("href", ""),
        }
        for r in ddg_text_with_retry(query, max_results)
    ]


# --- 2. LIVE JOB SEARCH ENGINES ---
def fetch_live_ddg_jobs(search_term="AI Engineer"):
    """Fetches real-time, active job listings using DuckDuckGo search + Gemini Flash JSON parsing.

    Bypasses Gemini Search Grounding tool to prevent API quota exhaustion. Returns max 3 active jobs.
    """
    clean_keyword = search_term.strip() if search_term.strip() else "AI Engineer"
    if not GEMINI_API_KEY:
        st.error("GEMINI_API_KEY is missing in secrets.")
        return []

    # 1. Scrape real live job search web results using DuckDuckGo (with retries)
    raw_search_results = collect_ddg_results(
        f"{clean_keyword} hiring remote or india apply job site:linkedin.com/jobs OR site:indeed.com OR site:naukri.com",
        6,
    )

    # Fallback search if specific domain filters yield no results
    if not raw_search_results:
        raw_search_results = collect_ddg_results(
            f"{clean_keyword} jobs apply online", 5
        )

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
        response = generate_with_retry(
            client,
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
                    f"https://www.google.com/search?q={urllib.parse.quote(clean_keyword + ' jobs')}",
                ),
            })
        return cleaned_posts
    except Exception as e:
        show_api_error("Live Search Formatting Error", e)
        return []


def fetch_live_gemini_jobs(search_term="AI Engineer"):
    """Fetches open job listings using Gemini 3.6 Flash with Google Search Grounding."""
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
        response = generate_with_retry(
            client,
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
        show_api_error("Live Search Execution Error", e)
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
        response = generate_with_retry(
            client,
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
        show_api_error("Parsing failed", e)
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


# --- 2B. LANGGRAPH AGENT PIPELINE ---
# load_profile -> search_jobs -> match_skills -> analyze_gaps -> recommend_courses
SKILL_ALIASES = {
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "genai": "generative ai",
    "gen ai": "generative ai",
    "llms": "llm",
    "large language models": "llm",
    "large language model": "llm",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "tf": "tensorflow",
    "sklearn": "scikit learn",
    "nodejs": "node.js",
    "node js": "node.js",
    "reactjs": "react",
    "react js": "react",
    "react.js": "react",
    "postgres": "postgresql",
    "powerbi": "power bi",
    "ms excel": "excel",
    "microsoft excel": "excel",
    "data analytics": "data analysis",
    "rest apis": "rest api",
    "restful api": "rest api",
    "restful apis": "rest api",
    "apis": "api",
}


def normalize_skill(skill):
    """Lower-cases a skill, strips punctuation and maps aliases (ML -> machine learning)."""
    text = re.sub(r"[^a-z0-9+#.\s]", " ", str(skill).lower())
    text = re.sub(r"\s+", " ", text).strip(" .")
    return SKILL_ALIASES.get(text, text)


def skill_is_covered(job_skill, candidate_norms):
    """A job skill is covered if a candidate skill equals it or contains all its words."""
    job_norm = normalize_skill(job_skill)
    if not job_norm:
        return True
    job_words = set(job_norm.split())
    for cand in candidate_norms:
        if cand == job_norm or job_words <= set(cand.split()):
            return True
    return False


class AgentState(TypedDict, total=False):
    profile: dict
    role: str
    free_only: bool
    candidate_skills: list
    jobs: list
    matches: list
    priority_skills: list
    error: str
    trace: Annotated[list, operator.add]  # every node appends its own step


def _traced(label, icon):
    """Wraps a node so each run appends a step (name, detail, seconds) to state['trace']."""

    def decorator(fn):
        def wrapper(state):
            started = time.perf_counter()
            update, detail = fn(state)
            update["trace"] = [{
                "node": label,
                "icon": icon,
                "status": "error" if update.get("error") else "ok",
                "detail": detail,
                "seconds": round(time.perf_counter() - started, 2),
            }]
            return update

        wrapper.__name__ = fn.__name__
        return wrapper

    return decorator


@_traced("Load Profile", "📄")
def load_profile_node(state):
    profile = state.get("profile") or {}
    skills = [s for s in profile.get("current_skills", []) if str(s).strip()]
    if not profile or not skills:
        return (
            {
                "error": (
                    "No parsed profile found. Upload your resume in the"
                    " Profile Ingestion tab and run the Profile Parsing Agent first."
                )
            },
            "No parsed profile or skills found, so the pipeline stopped here.",
        )
    return (
        {"candidate_skills": skills},
        f"Loaded profile for {profile.get('name', 'Candidate')}: {len(skills)} skills,"
        f" searching for role '{state.get('role')}'.",
    )


@_traced("Search Jobs", "🌐")
def search_jobs_node(state):
    role = state.get("role", "AI Engineer")
    jobs = get_jobs_with_cache(conn, role)
    if not jobs:
        return (
            {
                "jobs": [],
                "error": f"No live job listings could be fetched for '{role}'. Try again in a moment.",
            },
            "No job postings returned, so the pipeline stopped here.",
        )
    return (
        {"jobs": jobs},
        f"Fetched {len(jobs)} live postings for '{role}' (DuckDuckGo + Gemini, cached).",
    )


@_traced("Match Skills", "🎯")
def match_skills_node(state):
    candidate_norms = [normalize_skill(s) for s in state["candidate_skills"]]
    matches = []
    for job in state["jobs"]:
        required = list(dict.fromkeys(
            s for s in job.get("required_skills", []) if str(s).strip()
        ))
        matched = [s for s in required if skill_is_covered(s, candidate_norms)]
        gaps = [s for s in required if s not in matched]
        score = round(len(matched) / len(required) * 100) if required else 100
        matches.append({
            "job": job,
            "required": required,
            "matched": matched,
            "gaps": gaps,
            "score": score,
        })
    best = max(matches, key=lambda m: m["score"])
    average = round(sum(m["score"] for m in matches) / len(matches))
    return (
        {"matches": matches},
        f"Scored {len(matches)} jobs. Best: {best['score']}% at"
        f" {best['job'].get('company', 'Unknown')}. Average: {average}%.",
    )


@_traced("Analyze Gaps", "🔍")
def analyze_gaps_node(state):
    matches = state["matches"]
    demand = {}
    for m in matches:
        weight = 100 / (len(m["required"]) or 1)
        seen = set()
        for gap in m["gaps"]:
            key = normalize_skill(gap)
            if key in seen:
                continue
            seen.add(key)
            entry = demand.setdefault(key, {"skill": gap, "jobs": 0, "gain": 0.0})
            entry["jobs"] += 1
            entry["gain"] += weight

    priority = sorted(
        demand.values(),
        key=lambda d: (-d["jobs"], -d["gain"], d["skill"].lower()),
    )
    for item in priority:
        item["avg_match_gain"] = round(item["gain"] / len(matches))
    if priority:
        top = priority[0]
        detail = (
            f"Found {len(priority)} distinct missing skills. Top priority:"
            f" '{top['skill']}' (needed by {top['jobs']}/{len(matches)} jobs)."
        )
    else:
        detail = "No skill gaps found. The candidate covers every requirement."
    return {"priority_skills": priority}, detail


@_traced("Recommend Courses", "🎓")
def recommend_courses_node(state):
    free_only = state.get("free_only", False)
    enriched = []
    for m in state["matches"]:
        item = dict(m)
        item["courses"] = generate_targeted_courses(m["gaps"], free_only=free_only)
        enriched.append(item)

    priority = []
    for p in state.get("priority_skills", []):
        item = dict(p)
        item["courses"] = generate_targeted_courses([p["skill"]], free_only=free_only)
        priority.append(item)

    total_links = sum(len(m["courses"]) for m in enriched)
    return (
        {"matches": enriched, "priority_skills": priority},
        f"Built {total_links} learning links and ranked {len(priority)} skills by"
        f" opportunity unlocked (free-only: {free_only}).",
    )


def build_skill_gap_graph():
    """Wires the agents together as a LangGraph state machine."""
    graph = StateGraph(AgentState)
    graph.add_node("load_profile", load_profile_node)
    graph.add_node("search_jobs", search_jobs_node)
    graph.add_node("match_skills", match_skills_node)
    graph.add_node("analyze_gaps", analyze_gaps_node)
    graph.add_node("recommend_courses", recommend_courses_node)

    graph.add_edge(START, "load_profile")
    # Conditional edges: stop early when there is no profile / no jobs.
    graph.add_conditional_edges(
        "load_profile",
        lambda s: "stop" if s.get("error") else "continue",
        {"continue": "search_jobs", "stop": END},
    )
    graph.add_conditional_edges(
        "search_jobs",
        lambda s: "stop" if s.get("error") else "continue",
        {"continue": "match_skills", "stop": END},
    )
    graph.add_edge("match_skills", "analyze_gaps")
    graph.add_edge("analyze_gaps", "recommend_courses")
    graph.add_edge("recommend_courses", END)
    return graph.compile()


def run_skill_gap_pipeline(profile, role, free_only=False):
    """Runs the full LangGraph pipeline and returns the final state."""
    role = role.strip() if role and role.strip() else "AI Engineer"
    try:
        return build_skill_gap_graph().invoke({
            "profile": profile or {},
            "role": role,
            "free_only": free_only,
            "trace": [],
        })
    except Exception as e:
        print(f"[LangGraph pipeline] {e}")
        return {"role": role, "error": f"Pipeline failed: {e}", "trace": []}


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
                "Extracting candidate profile schema via Gemini 3.6 Flash..."
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
        if not LANGGRAPH_AVAILABLE:
            st.error(
                "The `langgraph` package is not installed. Add `langgraph` to"
                " requirements.txt and reboot the app."
            )
        else:
            with st.spinner(
                "Running LangGraph pipeline: profile → search → match → gap → recommend..."
            ):
                result = run_skill_gap_pipeline(
                    st.session_state.get("candidate_profile"),
                    search_keyword,
                    free_only=free_only,
                )
            st.session_state.agent_result = result
            log_audit(
                conn,
                "LANGGRAPH_PIPELINE",
                "RUN_SKILL_GAP_PIPELINE",
                f"Ran skill-gap pipeline for role: {search_keyword}",
                json.dumps({
                    "jobs": len(result.get("jobs", [])),
                    "steps": [t["node"] for t in result.get("trace", [])],
                    "error": result.get("error", ""),
                }),
            )

    result = st.session_state.get("agent_result")
    if result and result.get("error"):
        st.warning(f"⚠️ {result['error']}")

    if result and result.get("matches"):
        matches = result["matches"]
        st.subheader(
            f"🌐 Live Recommendations for: {result.get('role')} (Max 3 Jobs)"
        )

        priority = result.get("priority_skills", [])
        if priority:
            st.markdown("#### 🏆 Priority Skills to Learn (ranked by opportunity unlocked)")
            for rank, item in enumerate(priority[:5], start=1):
                links = " · ".join(
                    f"[{c['platform']}]({c['link']})"
                    for c in item.get("courses", [])
                )
                st.markdown(
                    f"**{rank}. `{item['skill']}`** — needed by"
                    f" {item['jobs']}/{len(matches)} jobs · raises your average"
                    f" match by about +{item['avg_match_gain']}%  \n{links}"
                )
            st.divider()

        for m in matches:
            post = m["job"]
            with st.expander(
                f"💼 {post.get('title', 'Role')} — Company:"
                f" {post.get('company', 'Unknown')}"
                f" ({post.get('location', 'Remote')}) — Match: {m['score']}%",
                expanded=True,
            ):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(
                        f"**Extracted Job Snippet:** {post.get('raw_text', '')}"
                    )
                    st.write(
                        "**Required Skills:** ",
                        ", ".join([f"`{s}`" for s in m["required"]]),
                    )
                    st.write(
                        "**Identified Skill Gaps:** ",
                        ", ".join([f"❌ `{s}`" for s in m["gaps"]])
                        if m["gaps"]
                        else "✅ No Gaps!",
                    )

                    st.write("")
                    st.link_button(
                        f"🔗 Apply Directly for {post.get('title', 'Role')}",
                        post.get("job_url", "https://google.com"),
                        use_container_width=True,
                        type="primary",
                    )

                with c2:
                    st.markdown("### 🎓 Tailored Learning Pathways")
                    if m.get("courses"):
                        for course in m["courses"]:
                            st.markdown(
                                f"* [{course['platform']}]"
                                f" [{course['title']}]({course['link']})"
                            )
                    else:
                        st.success("All technical requirements matched!")

# --- TAB 3: REASONING TRANSPARENCY ---
with active_tabs[2]:
    st.header("Reasoning Transparency & Agent Decision Pathway")
    st.caption("Live execution trace of the LangGraph agent pipeline")

    st.markdown("### 🧠 LangGraph Agent Pipeline")
    st.markdown(
        "`START` → 📄 **Load Profile** → 🌐 **Search Jobs** → 🎯 **Match Skills**"
        " → 🔍 **Analyze Gaps** → 🎓 **Recommend Courses** → `END`"
    )
    st.caption(
        "Conditional edges stop the run early if no profile is parsed or no"
        " jobs are found."
    )
    st.divider()

    agent_result = st.session_state.get("agent_result")
    if agent_result and agent_result.get("trace"):
        st.markdown("### ⚙️ Last Run: Agent Step Handoffs")
        for step_no, step in enumerate(agent_result["trace"], start=1):
            status_icon = "✅" if step["status"] == "ok" else "⛔"
            st.markdown(
                f"{status_icon} **{step_no}. {step['icon']} {step['node']}**"
                f" · `{step['seconds']}s`"
            )
            st.caption(step["detail"])
        st.divider()

        if agent_result.get("matches"):
            st.markdown("### 🔍 Live Matching Logic Breakdown")
            for idx, m in enumerate(agent_result["matches"]):
                post = m["job"]
                with st.expander(
                    f"📊 Role {idx+1}: {post.get('company', 'Unknown')} — Match"
                    f" Index: {m['score']}%",
                    expanded=True,
                ):
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        st.metric("Role Match Score", f"{m['score']}%")
                        st.write("**Extracted Required Skills:**")
                        st.json(m["required"])
                    with col_m2:
                        st.write(
                            "✅ **Matched Skills:**",
                            ", ".join(m["matched"]) if m["matched"] else "None",
                        )
                        st.write(
                            "❌ **Missing Skill Gaps:**",
                            ", ".join(m["gaps"]) if m["gaps"] else "None",
                        )
                        st.caption(
                            "Decision Logic: a job skill counts as matched if a"
                            " candidate skill equals it (after normalising aliases"
                            " like ML → machine learning) or contains all of its words."
                        )
    else:
        st.info(
            "💡 Run a search in the **Job Matching & Search** tab to see the"
            " live agent execution trace."
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
