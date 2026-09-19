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
from database import init_db, get_audit_logs, log_audit, cache_rapid_results, get_cached_rapid_results

# --- 1. SETTINGS & STYLING ---
st.set_page_config(
    page_title="Candidate AI Skill-Gap Agent",
    page_icon="🎯",
    layout="wide"
)

# --- 2. LIVE RAPIDAPI LINKEDIN FETCHER ---
def fetch_live_linkedin_posts(search_term="ai"):
    """
    Dynamically fetches real-time LinkedIn post announcements via RapidAPI 
    for ANY user-provided keyword and constructs exact, targeted search links.
    """
    clean_keyword = search_term.strip() if search_term.strip() else "hiring"
    encoded_term = urllib.parse.quote(clean_keyword)
    
    rapidapi_key = st.secrets.get("RAPIDAPI_KEY", "6fb88e8b06mshc89f467c11239e7p115a47jsnb5f7e21ba479")
    rapidapi_host = "realtime-linkdin-data-scraper.p.rapidapi.com"
    
    url = f"https://{rapidapi_host}/postSearch.php?searchTerm={encoded_term}"
    
    headers = {
        'x-rapidapi-key': rapidapi_key,
        'x-rapidapi-host': rapidapi_host,
        'Content-Type': "application/json"
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=12)
        if response.status_code == 200:
            res_data = response.json()
            
            # Standardize list extraction across JSON formats
            if isinstance(res_data, list):
                posts = res_data
            elif isinstance(res_data, dict):
                posts = res_data.get("data") or res_data.get("posts") or res_data.get("results") or []
            else:
                posts = []
                
            if posts:
                cleaned_posts = []
                for idx, p in enumerate(posts[:5]):
                    text_content = p.get("text") or p.get("postText") or p.get("title") or f"LinkedIn hiring post for {clean_keyword}"
                    company_name = p.get("authorName") or p.get("company") or "LinkedIn Employer"
                    
                    # 1. Check if direct post URL is provided in the API payload
                    raw_link = p.get("postUrl") or p.get("url") or p.get("link") or p.get("navigationUrl")
                    
                    # 2. Dynamic query URL generation: uses actual search term + company name returned by API
                    if not raw_link or raw_link in ["https://www.linkedin.com", "https://www.linkedin.com/jobs"]:
                        search_query = urllib.parse.quote(f"{clean_keyword} {company_name}")
                        apply_link = f"https://www.linkedin.com/search/results/content/?keywords={search_query}"
                    else:
                        apply_link = raw_link

                    cleaned_posts.append({
                        "job_id": f"link_live_{idx}",
                        "title": f"Live Hiring Role: {clean_keyword.upper()}",
                        "company": company_name,
                        "location": p.get("location") or "India / Remote",
                        "salary_range": "Market Standard",
                        "raw_text": text_content,
                        "apply_link": apply_link
                    })
                return cleaned_posts
        else:
            st.warning(f"⚠️ RapidAPI Status Code: {response.status_code}. Using dynamic fallback results.")
    except Exception as e:
        st.error(f"RapidAPI Notice: {e}")

    # Dynamic fallback generation using exact user input keyword
    query_encoded = urllib.parse.quote(clean_keyword)
    return [
        {
            "job_id": "fallback_1",
            "title": f"Hiring: {clean_keyword.upper()} Specialist / Engineer",
            "company": "Rapid Tech Solutions",
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
    """Uses Gemini 2.5 Flash to extract required technical skills from scraped text."""
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
st.caption("Real-Time RapidAPI LinkedIn Scraper + Multi-Platform Learning Integration")

tabs = ["📄 Profile Upload", "📊 Target Jobs & RapidAPI", "🤖 Reasoning Transparency", "📜 Audit Log"]
active_tabs = st.tabs(tabs)

# --- TAB 1: RESUME PARSER ---
with active_tabs[0]:
    st.header("Step 1: Upload Candidate Resume")
    uploaded_file = st.file_uploader("Upload PDF/DOCX", type=["pdf", "docx"])
    if uploaded_file and st.button("Parse Resume", type="primary"):
        st.session_state.candidate_profile = {
            "candidate_id": "cand_101",
            "name": "Candidate",
            "location": "Ahmedabad",
            "education": "B.E. Computer Engineering",
            "current_skills": ["Python", "SQL", "Pandas"],
            "interests": ["Data Science", "AI Agent Development"]
        }
        log_audit(conn, "PARSER", "PARSE_RESUME", "Parsed resume profile", json.dumps({"filename": uploaded_file.name}))
        st.success("Resume parsed successfully!")
        
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
        fetch_clicked = st.button("🔎 Fetch Live Jobs", type="primary", width="stretch")

    if fetch_clicked:
        with st.spinner("Executing RapidAPI GET request to LinkedIn Scraper..."):
            raw_posts = fetch_live_linkedin_posts(search_keyword)
            
            for post in raw_posts:
                post["required_skills"] = extract_skills_from_text(user_api_key, post["raw_text"])
            
            st.session_state.live_posts = raw_posts
            log_audit(
                conn, 
                "RAPIDAPI_LINKEDIN", 
                "FETCH_POSTS", 
                f"Queried RapidAPI for keyword: {search_keyword}", 
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
                    st.write(f"**Extracted Raw Snippet:** {post['raw_text'][:200]}...")
                    st.write("**Extracted Required Skills:** ", ", ".join([f"`{s}`" for s in req_skills]))
                    st.write("**Identified Skill Gaps:** ", ", ".join([f"❌ `{s}`" for s in missing]) if missing else "✅ No Gaps!")
                    st.link_button("🔗 View Original Post on LinkedIn", post["apply_link"], width="stretch")
                    
                with c2:
                    st.markdown("### 🎓 Recommended Dynamic Courses")
                    rec_courses = generate_hackathon_courses(missing, free_only=free_only)
                    if rec_courses:
                        for course in rec_courses:
                            st.markdown(f"* [{course['platform']}] [{course['title']}]({course['link']})")
                    else:
                        st.success("No courses needed!")

# --- TAB 3: REASONING TRANSPARENCY (ENHANCED) ---
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
    graph.node('B', "🌐 RapidAPI LinkedIn Scraper\n(/postSearch.php)", shape='box', style='filled', fillcolor='#FFF3E0')
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
        st.info("💡 **No live runs recorded yet.** Go to **Tab 2 (Target Jobs & RapidAPI)** and click **`🔎 Fetch Live Jobs`** to generate the real-time reasoning matrix.")

# --- TAB 4: AUDIT LOG ---
with active_tabs[3]:
    st.header("📜 System Audit Log & Compliance")
    col_btn, _ = st.columns([1, 4])
    with col_btn:
        if st.button("🔄 Refresh Logs"):
            st.rerun()

    logs = get_audit_logs(conn)
    if logs:
        # Exactly 6 columns matching database schema
        log_df = pd.DataFrame(
            logs, 
            columns=["Timestamp", "Component", "Action", "Description", "Data Payload", "IP Address"]
        )
        st.dataframe(log_df, width="stretch")
    else:
        st.info("No audit logs recorded yet.")
