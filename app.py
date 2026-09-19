import streamlit as st
import pandas as pd
import graphviz
import json
import time
import io
import requests
import urllib.parse
from google import genai
from google.genai import types
from database import init_db, get_audit_logs, log_audit, cache_search_results, get_cached_search_results
from processor import parse_profile_agent, generate_reasoning_transparency

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Candidate AI Skill-Gap Agent",
    page_icon="🎯",
    layout="wide"
)

# --- 2. LIVE GOOGLE CUSTOM SEARCH LINKEDIN FETCHER ---
def fetch_live_linkedin_posts(search_term="ai"):
    """
    Dynamically fetches authentic, live LinkedIn hiring announcements using
    Google Custom Search JSON API with exact permalink generation.
    """
    clean_keyword = search_term.strip() if search_term.strip() else "hiring"
    
    api_key = st.secrets.get("GOOGLE_SEARCH_API_KEY", "")
    cx_id = st.secrets.get("GOOGLE_SEARCH_CX", "a19a3afa76d744393")
    
    if not api_key or not cx_id:
        st.warning("⚠️ GOOGLE_SEARCH_API_KEY or GOOGLE_SEARCH_CX is missing from secrets.toml.")
        return []

    # Search targeting LinkedIn hiring posts
    query = f'"{clean_keyword}" "hiring" OR "looking for"'
    encoded_query = urllib.parse.quote(query)
    
    url = f"https://www.googleapis.com/customsearch/v1?q={encoded_query}&key={api_key}&cx={cx_id}&num=5"
    
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
                    permalink = item.get("link", "https://www.linkedin.com")
                    
                    # Extract author/company cleanly from page title
                    company_author = title.split("|")[0].split(" - ")[0].strip() or "LinkedIn Recruiter"
                    
                    cleaned_posts.append({
                        "job_id": f"google_live_{idx}",
                        "title": f"Live Hiring Role: {clean_keyword.upper()}",
                        "company": company_author,
                        "location": "India / Remote",
                        "salary_range": "Market Standard",
                        "raw_text": snippet,
                        "apply_link": permalink  # Direct link to actual LinkedIn post
                    })
                return cleaned_posts
        else:
            st.warning(f"⚠️ Google Search API Status: {response.status_code}. Using dynamic fallback results.")
    except Exception as e:
        st.error(f"Google Search Connection Notice: {e}")

    # Dynamic fallback generation using search term
    query_encoded = urllib.parse.quote(clean_keyword)
    return [
        {
            "job_id": "fallback_1",
            "title": f"Hiring: {clean_keyword.upper()} Specialist / Engineer",
            "company": "Tech Solutions",
            "location": "India / Remote",
            "salary_range": "₹8,00,000 - ₹14,00,000 PA",
            "raw_text": f"We are actively seeking an experienced {clean_keyword.upper()} professional proficient in core domain skills, REST APIs, and modern toolchains.",
            "apply_link": f"https://www.linkedin.com/search/results/content/?keywords={query_encoded}%20hiring"
        },
        {
            "job_id": "fallback_2",
            "title": f"Senior {clean_keyword.upper()} Specialist",
            "company": "Enterprise Global Labs",
            "location": "Bengaluru (Hybrid)",
            "salary_range": "₹12,00,000 - ₹20,00,000 PA",
            "raw_text": f"Join our growing team as a Senior {clean_keyword.upper()} Lead. Key requirements include proven hands-on project experience and end-to-end execution.",
            "apply_link": f"https://www.linkedin.com/search/results/content/?keywords={query_encoded}%20developer"
        }
    ]

def extract_skills_from_text(api_key, text_content):
    """Uses Gemini 2.5 Flash to extract required technical skills from scraped snippet text."""
    if not text_content:
        return ["Python", "Machine Learning", "SQL"]
        
    client = genai.Client(api_key=api_key)
    prompt = f"Extract a clean JSON array of up to 5 technical skills required in this text:\n\n{text_content}"
    
    schema = {
        "type": "ARRAY",
        "items": {"type": "STRING"}
    }
    try:
        res = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.0
            )
        )
        return json.loads(res.text)
    except:
        return ["Python", "SQL", "Data Analysis"]

def generate_hackathon_courses(missing_skills, free_only=False):
    """Generates dynamic pathways across Coursera, YouTube, and Skill India Digital Hub."""
    courses = []
    for skill in missing_skills:
        skill_enc = urllib.parse.quote(skill)
        
        # Coursera course path
        courses.append({
            "platform": "Coursera",
            "title": f"Mastering {skill} Specialization",
            "teaches_skills": [skill],
            "duration_weeks": 3,
            "cost": 0 if free_only else 1499,
            "is_free": free_only,
            "link": f"https://www.coursera.org/search?query={skill_enc}"
        })
        
        # YouTube course path
        courses.append({
            "platform": "YouTube",
            "title": f"{skill} Full Crash Course & Hands-on Projects",
            "teaches_skills": [skill],
            "duration_weeks": 1,
            "cost": 0,
            "is_free": True,
            "link": f"https://www.youtube.com/results?search_query={skill_enc}+full+course"
        })
        
        # Skill India Digital Hub path
        courses.append({
            "platform": "Skill India Digital",
            "title": f"National Skill Certification: {skill}",
            "teaches_skills": [skill],
            "duration_weeks": 2,
            "cost": 0,
            "is_free": True,
            "link": f"https://www.skillindiadigital.gov.in/courses?search={skill_enc}"
        })
    return courses

# --- 3. DATABASE INITIALIZATION ---
conn = init_db()

# --- 4. AUTHENTICATION & SIDEBAR UI ---
def get_auth_status():
    if hasattr(st, "user") and st.user.get("is_logged_in"):
        return {"ok": True, "user": st.user.get("email"), "role": "Candidate"}
    if st.session_state.get("admin_login"):
        return {"ok": True, "user": st.session_state.admin_email, "role": "Admin"}
    return {"ok": True, "user": "guest_candidate@app.com", "role": "Candidate"}

auth = get_auth_status()

with st.sidebar:
    st.title(f"👤 {auth['role']}")
    st.caption(f"Active: {auth['user']}")
    user_api_key = st.text_input("Gemini API Key", type="password", value=st.secrets.get("GEMINI_API_KEY", ""))
    st.divider()
    free_only = st.toggle("🆓 Free-Only Courses Toggle", value=False)

# --- 5. DASHBOARD MAIN INTERFACE ---
st.title("🎯 Live LinkedIn & Skill-Gap Agent")
st.caption("Real-Time Google Search API LinkedIn Fetcher + Multi-Platform Learning Integration")

tabs = ["📄 Profile Upload", "📊 Target Jobs & Search API", "🤖 Reasoning Transparency", "📜 Audit Log"]
active_tabs = st.tabs(tabs)

# --- TAB 1: RESUME PARSER ---
with active_tabs[0]:
    st.header("Step 1: Upload Candidate Resume")
    uploaded_file = st.file_uploader("Upload PDF/DOCX", type=["pdf", "docx"])
    if uploaded_file and st.button("Parse Resume", type="primary"):
        if user_api_key:
            parsed_data = parse_profile_agent(user_api_key, uploaded_file, uploaded_file.name)
            if parsed_data:
                st.session_state.candidate_profile = parsed_data
                log_audit(conn, "PARSER", "PARSE_RESUME", "Parsed resume profile", json.dumps({"filename": uploaded_file.name}))
                st.success("Resume parsed successfully with Gemini 2.5 Flash!")
            else:
                st.error("Could not parse resume text.")
        else:
            # Fallback mock profile if API Key is not set in sidebar
            st.session_state.candidate_profile = {
                "candidate_id": "cand_101",
                "name": "Candidate",
                "location": "Ahmedabad",
                "education": "B.E. Computer Engineering",
                "current_skills": ["Python", "SQL", "Pandas"],
                "interests": ["Data Science", "AI Agent Development"]
            }
            log_audit(conn, "PARSER", "PARSE_RESUME", "Loaded default profile", json.dumps({"filename": uploaded_file.name}))
            st.success("Profile loaded!")
        
    if "candidate_profile" in st.session_state:
        st.json(st.session_state.candidate_profile)

# --- TAB 2: LIVE LINKEDIN JOBS & GAP RECOMMENDATION ---
with active_tabs[1]:
    st.header("Step 2 & 3: Real-Time LinkedIn Search & Skill Gap Analysis")
    
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        search_keyword = st.text_input("Search LinkedIn Keyword", value="ai")
    with col_btn:
        st.write("")
        st.write("")
        fetch_clicked = st.button("🔎 Fetch Live Jobs", type="primary", use_container_width=True)

    if fetch_clicked:
        with st.spinner("Executing Google Custom Search API query for LinkedIn hiring posts..."):
            raw_posts = fetch_live_linkedin_posts(search_keyword)
            
            for post in raw_posts:
                post["required_skills"] = extract_skills_from_text(user_api_key, post["raw_text"])
            
            st.session_state.live_posts = raw_posts
            log_audit(
                conn, 
                "GOOGLE_SEARCH_API", 
                "FETCH_POSTS", 
                f"Queried Google Search API for keyword: {search_keyword}", 
                json.dumps({"count": len(raw_posts)})
            )

    if "live_posts" in st.session_state and st.session_state.live_posts:
        candidate_skills = set([s.lower() for s in st.session_state.get("candidate_profile", {}).get("current_skills", ["python", "sql"])])
        
        st.subheader("🌐 Live LinkedIn Matches")
        for post in st.session_state.live_posts:
            req_skills = post["required_skills"]
            missing = [s for s in req_skills if s.lower() not in candidate_skills]
            
            with st.expander(f"💼 {post['title']} — Author/Company: {post['company']}", expanded=True):
                c1, c2 = st.columns(2)
                with c1:
                    st.write(f"**Extracted Raw Snippet:** {post['raw_text']}")
                    st.write("**Extracted Required Skills:** ", ", ".join([f"`{s}`" for s in req_skills]))
                    st.write("**Identified Skill Gaps:** ", ", ".join([f"❌ `{s}`" for s in missing]) if missing else "✅ No Gaps!")
                    st.link_button("🔗 View Original Post on LinkedIn", post["apply_link"], use_container_width=True)
                    
                with c2:
                    st.markdown("### 🎓 Recommended Dynamic Courses")
                    rec_courses = generate_hackathon_courses(missing, free_only=free_only)
                    if rec_courses:
                        for course in rec_courses:
                            st.markdown(f"* [{course['platform']}] [{course['title']}]({course['link']})")
                    else:
                        st.success("No courses needed!")

# --- TAB 3: REASONING TRANSPARENCY ---
with active_tabs[2]:
    st.header("Step 4: Reasoning Transparency & Agent Decision Tree")
    
    cand_profile = st.session_state.get("candidate_profile", {
        "name": "Candidate",
        "current_skills": ["Python", "SQL", "Pandas"]
    })
    candidate_skills = cand_profile.get("current_skills", ["Python", "SQL"])
    
    st.markdown("### 🧠 Autonomous Execution Pipeline")
    
    # 1. Decision Graph Visualization using Graphviz
    graph = graphviz.Digraph(format="png")
    graph.attr(rankdir='LR', size='10,4')
    graph.node('A', f"📄 Parsed Profile\nSkills: {', '.join(candidate_skills)}", shape='ellipse', style='filled', fillcolor='#E3F2FD')
    graph.node('B', "🌐 Google Custom Search API\n(customsearch/v1)", shape='box', style='filled', fillcolor='#FFF3E0')
    graph.node('C', "🤖 Gemini 2.5 Flash\nSkill Extraction Engine", shape='box', style='filled', fillcolor='#E8F5E9')
    graph.node('D', "⚡ Set Difference Engine\n(Candidate Skills - Job Skills)", shape='diamond', style='filled', fillcolor='#FFFDE7')
    graph.node('E', "🎓 Dynamic Learning Router\n(Coursera, YouTube, Skill India)", shape='ellipse', style='filled', fillcolor='#F3E5F5')
    
    graph.edge('A', 'D', label='User Skill Vector')
    graph.edge('B', 'C', label='Raw Post Payload')
    graph.edge('C', 'D', label='Extracted Job Skill Array')
    graph.edge('D', 'E', label='Identified Skill Gaps')
    
    st.graphviz_chart(graph, use_container_width=True)
    st.divider()

    # 2. Detailed Breakdown Matrix
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
        st.info("💡 **No live runs recorded yet.** Go to **Tab 2 (Target Jobs & Search API)** and click **`🔎 Fetch Live Jobs`** to generate the real-time reasoning matrix.")

# --- TAB 4: AUDIT LOG ---
with active_tabs[3]:
    st.header("📜 System Audit Log & Compliance")
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
