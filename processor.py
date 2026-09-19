import io
import json
import os
import tempfile
import time
import fitz  # PyMuPDF
import docx
import streamlit as st
from google import genai
from google.genai import types

# --- CURATED DATABASES ---
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

def get_document_text(file_obj, filename):
    """Safely extracts text from PDF or DOCX file stream."""
    try:
        file_obj.seek(0)
        file_bytes = file_obj.read()
        if not file_bytes:
            return None

        ext = filename.split('.')[-1].lower()
        if ext == 'pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None

def parse_profile_agent(api_key, file_obj, filename):
    """
    Parses candidate profile data from documents and image formats
    (PDF, DOCX, PNG, JPG, JPEG) using Gemini 2.5 Flash.
    """
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
                "current_skills": {"type": "ARRAY", "items": {"type": "STRING"}},
                "interests": {"type": "ARRAY", "items": {"type": "STRING"}}
            },
            "required": ["name", "location", "education", "current_skills", "interests"]
        }

        prompt = "Parse the file content into a structured candidate profile."

        if ext in image_exts:
            # Handle image uploads via Gemini File API
            file_obj.seek(0)
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
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
                        temperature=0.0
                    )
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
            # Handle standard document reading (PDF / DOCX)
            text = get_document_text(file_obj, filename)
            if not text:
                return None

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{prompt}\n\nResume Document Content:\n{text}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.0
                )
            )
            data = json.loads(response.text)
            data["candidate_id"] = f"cand_{int(time.time())}"
            data.setdefault("marks_10th", "88.5%")
            data.setdefault("marks_12th", "91.2%")
            return data

    except Exception as e:
        st.error(f"Profile Parsing Failed: {e}")
        return None

def job_matching_and_gap_agent(candidate_profile):
    """Matches candidate against database and performs gap analysis."""
    user_skills = set([s.lower() for s in candidate_profile.get("current_skills", [])])
    matched_jobs = []

    for job in JOB_DATABASE:
        req_skills = set([s.lower() for s in job["required_skills"]])
        matched_set = user_skills.intersection(req_skills)
        missing_set = set(job["required_skills"]) - set([s for s in job["required_skills"] if s.lower() in user_skills])

        match_pct = round((len(matched_set) / len(req_skills)) * 100, 1) if req_skills else 0

        matched_jobs.append({
            "job": job,
            "match_pct": match_pct,
            "missing_skills": list(missing_set),
            "matched_skills": [s for s in job["required_skills"] if s.lower() in user_skills]
        })

    matched_jobs.sort(key=lambda x: x["match_pct"], reverse=True)
    return matched_jobs

def training_recommendation_agent(missing_skills, free_only=False):
    """Maps missing skills to course database with free-only filter."""
    recommended_courses = []

    for skill in missing_skills:
        for course in COURSE_DATABASE:
            if free_only and not course["is_free"]:
                continue
            if any(skill.lower() in s.lower() for s in course["teaches_skills"]):
                if course["course_id"] not in [c["course_id"] for c in recommended_courses]:
                    recommended_courses.append(course)

    total_weeks = sum(c["duration_weeks"] for c in recommended_courses)
    total_cost = sum(c["cost"] for c in recommended_courses)

    return {
        "courses": recommended_courses,
        "total_weeks": total_weeks,
        "total_cost": total_cost
    }

def generate_reasoning_transparency(api_key, profile, selected_job, gap_data, train_data):
    """Generates transparency logs explaining AI reasoning."""
    client = genai.Client(api_key=api_key)
    prompt = f"""
    Explain the reasoning step-by-step:
    1. Candidate Skills: {profile.get('current_skills')}
    2. Target Job Requirements: {selected_job.get('required_skills', []) if isinstance(selected_job, dict) else selected_job}
    3. Calculated Gaps: {gap_data}
    4. Selected Course Pathways: {[c.get('title') for c in train_data.get('courses', [])] if isinstance(train_data, dict) else train_data}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception:
        return f"Parsed profile against required skill sets. Identified missing competencies: {gap_data}. Matched target pathways to bridge gaps."
