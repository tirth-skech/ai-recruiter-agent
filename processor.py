import io
import json
import os
import tempfile
import time
import urllib.parse
import docx
from duckduckgo_search import DDGS
import fitz  # PyMuPDF
import streamlit as st
from google import genai
from google.genai import types


def fetch_live_ddg_jobs(api_key, role_title="AI Engineer"):
    """Fetches real-time, live jobs using DuckDuckGo search + Gemini Flash parsing.

    Completely quota-safe alternative to Google Search Grounding. Max 3 recommendations.
    """
    if not api_key:
        return []

    clean_keyword = role_title.strip() if role_title.strip() else "AI Engineer"

    # 1. Scrape live search results
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
        print(f"DuckDuckGo search error: {e}")

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
        return []

    # 2. Extract structured fields via Gemini Flash
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Below are raw web search results for active open "{clean_keyword}" roles:
    {json.dumps(raw_search_results, indent=2)}

    Extract strictly 3 distinct job listings into a JSON array.
    Return ONLY raw JSON with keys:
    - "job_id": string ID
    - "title": Job title
    - "company": Hiring company
    - "location": Job location or 'Remote'
    - "salary_range": "Market Standard"
    - "snippet": Brief overview of responsibilities
    - "required_skills": Array of 4 to 6 technical skills
    - "job_url": Direct application link
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
        jobs = json.loads(cleaned_text.strip())

        return jobs[:3]  # Enforce max 3 recommendations
    except Exception as e:
        st.error(f"Error fetching live jobs: {e}")
        return []


def get_document_text(file_obj, filename):
    """Safely extracts text from PDF or DOCX file stream."""
    try:
        file_obj.seek(0)
        file_bytes = file_obj.read()
        if not file_bytes:
            return None

        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == "docx":
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None


def parse_profile_agent(api_key, file_obj, filename):
    """Parses candidate profile data from documents and images using Gemini 2.5 Flash."""
    if not file_obj:
        return None

    try:
        client = genai.Client(api_key=api_key)
        ext = filename.split(".")[-1].lower()
        image_exts = ["png", "jpg", "jpeg"]

        schema = {
            "type": "OBJECT",
            "properties": {
                "candidate_id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "location": {"type": "STRING"},
                "education": {"type": "STRING"},
                "experience_years": {"type": "STRING"},
                "target_role": {"type": "STRING"},
                "marks_10th": {"type": "STRING"},
                "marks_12th": {"type": "STRING"},
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

        prompt = "Parse the file content into a structured candidate profile."

        if ext in image_exts:
            file_obj.seek(0)
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{ext}"
            ) as temp_file:
                temp_file.write(file_obj.read())
                temp_path = temp_file.name

            try:
                file_ref = client.files.upload(file=temp_path)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[file_ref, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.0,
                    ),
                )
                try:
                    client.files.delete(name=file_ref.name)
                except Exception:
                    pass
                os.remove(temp_path)

                data = json.loads(response.text)
                data["candidate_id"] = f"cand_{int(time.time())}"
                data.setdefault("marks_10th", "88.5%")
                data.setdefault("marks_12th", "91.2%")
                return data

            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                st.error(f"Image Profile Parsing Failed: {e}")
                return None

        else:
            text = get_document_text(file_obj, filename)
            if not text:
                return None

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{prompt}\n\nResume Document Content:\n{text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0,
                ),
            )
            data = json.loads(response.text)
            data["candidate_id"] = f"cand_{int(time.time())}"
            data.setdefault("marks_10th", "88.5%")
            data.setdefault("marks_12th", "91.2%")
            return data

    except Exception as e:
        st.error(f"Profile Parsing Failed: {e}")
        return None


def generate_targeted_courses(missing_skills, free_only=False):
    """Generates exact skill-gap search links on Coursera, YouTube, and NPTEL."""
    courses = []
    for skill in missing_skills:
        exact_skill_query = urllib.parse.quote(skill.strip())

        coursera_url = (
            f"[https://www.coursera.org/search?query=](https://www.coursera.org/search?query=){exact_skill_query}"
        )
        nptel_url = f"[https://swayam.gov.in/explorer?searchText=](https://swayam.gov.in/explorer?searchText=){exact_skill_query}"
        yt_url = f"[https://www.youtube.com/results?search_query=](https://www.youtube.com/results?search_query=){exact_skill_query}+tutorial"

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


def generate_reasoning_transparency(
    api_key, profile, selected_job, gap_data, train_data
):
    """Generates transparency logs explaining AI reasoning."""
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Explain the step-by-step decision pathway:
    1. Candidate Skills: {profile.get('current_skills')}
    2. Target Job Requirements: {selected_job.get('required_skills', []) if isinstance(selected_job, dict) else selected_job}
    3. Identified Skill Gaps: {gap_data}
    4. Learning Pathways: {[c.get('title') for c in train_data] if isinstance(train_data, list) else train_data}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
    except Exception:
        return f"Parsed profile against required skill sets. Identified missing competencies: {gap_data}. Formulated direct learning search links."
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

        return jobs[:3]  # Enforce max 3 recommendations
    except Exception as e:
        st.error(f"Error fetching live jobs: {e}")
        return []


def get_document_text(file_obj, filename):
    """Safely extracts text from PDF or DOCX file stream."""
    try:
        file_obj.seek(0)
        file_bytes = file_obj.read()
        if not file_bytes:
            return None

        ext = filename.split(".")[-1].lower()
        if ext == "pdf":
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == "docx":
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None


def parse_profile_agent(api_key, file_obj, filename):
    """Parses candidate profile data from documents and images using Gemini 2.5 Flash."""
    if not file_obj:
        return None

    try:
        client = genai.Client(api_key=api_key)
        ext = filename.split(".")[-1].lower()
        image_exts = ["png", "jpg", "jpeg"]

        schema = {
            "type": "OBJECT",
            "properties": {
                "candidate_id": {"type": "STRING"},
                "name": {"type": "STRING"},
                "location": {"type": "STRING"},
                "education": {"type": "STRING"},
                "experience_years": {"type": "STRING"},
                "target_role": {"type": "STRING"},
                "marks_10th": {"type": "STRING"},
                "marks_12th": {"type": "STRING"},
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

        prompt = "Parse the file content into a structured candidate profile."

        if ext in image_exts:
            file_obj.seek(0)
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=f".{ext}"
            ) as temp_file:
                temp_file.write(file_obj.read())
                temp_path = temp_file.name

            try:
                file_ref = client.files.upload(file=temp_path)
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[file_ref, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        response_schema=schema,
                        temperature=0.0,
                    ),
                )
                try:
                    client.files.delete(name=file_ref.name)
                except Exception:
                    pass
                os.remove(temp_path)

                data = json.loads(response.text)
                data["candidate_id"] = f"cand_{int(time.time())}"
                data.setdefault("marks_10th", "88.5%")
                data.setdefault("marks_12th", "91.2%")
                return data

            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                st.error(f"Image Profile Parsing Failed: {e}")
                return None

        else:
            text = get_document_text(file_obj, filename)
            if not text:
                return None

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{prompt}\n\nResume Document Content:\n{text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0,
                ),
            )
            data = json.loads(response.text)
            data["candidate_id"] = f"cand_{int(time.time())}"
            data.setdefault("marks_10th", "88.5%")
            data.setdefault("marks_12th", "91.2%")
            return data

    except Exception as e:
        st.error(f"Profile Parsing Failed: {e}")
        return None


def generate_targeted_courses(missing_skills, free_only=False):
    """Generates exact skill-gap search links on Coursera, YouTube, and NPTEL."""
    courses = []
    for skill in missing_skills:
        exact_skill_query = urllib.parse.quote(skill.strip())

        coursera_url = (
            f"https://www.coursera.org/search?query={exact_skill_query}"
        )
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


def generate_reasoning_transparency(
    api_key, profile, selected_job, gap_data, train_data
):
    """Generates transparency logs explaining AI reasoning."""
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Explain the step-by-step decision pathway:
    1. Candidate Skills: {profile.get('current_skills')}
    2. Target Job Requirements: {selected_job.get('required_skills', []) if isinstance(selected_job, dict) else selected_job}
    3. Identified Skill Gaps: {gap_data}
    4. Learning Pathways: {[c.get('title') for c in train_data] if isinstance(train_data, list) else train_data}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2),
        )
        return response.text
    except Exception:
        return f"Parsed profile against required skill sets. Identified missing competencies: {gap_data}. Formulated direct learning search links."
