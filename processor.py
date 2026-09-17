import json
import time
import io
import fitz  # PyMuPDF
import docx
import streamlit as st
from google import genai
from google.genai import types

def get_document_text(file_bytes, filename):
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([p.text for p in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None

def analyze_skill_gap(api_key, jd_text, candidate_name, candidate_email, resume_file):
    client = genai.Client(api_key=api_key)
    
    file_bytes = resume_file.read()
    resume_text = get_document_text(file_bytes, resume_file.name)
    
    if not resume_text:
        return None

    prompt = f"""
    You are an expert AI Career and Skill-Gap Matching Agent (Hackathon Problem C4).
    Analyze the following Candidate Resume against the Job Description.

    Job Description:
    {jd_text}

    Resume Text:
    {resume_text}

    Provide output matching this schema:
    1. Extract core skills from candidate.
    2. Extract primary job title/role targeted.
    3. Calculate match score percentage (0 to 100).
    4. Calculate projected match score after completing suggested upskilling.
    5. Identify missing skill gaps.
    6. Provide strategic training recommendations (Course, duration, score improvement).
    """

    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "email": {"type": "STRING"},
            "job_role": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "gaps": {"type": "ARRAY", "items": {"type": "STRING"}},
            "match_score": {"type": "NUMBER"},
            "projected_score": {"type": "NUMBER"},
            "recommendations": {
                "type": "ARRAY",
                "items": {
                    "type": "OBJECT",
                    "properties": {
                        "skill": {"type": "STRING"},
                        "course": {"type": "STRING"},
                        "duration": {"type": "STRING"},
                        "improvement": {"type": "STRING"}
                    }
                }
            }
        },
        "required": ["job_role", "skills", "gaps", "match_score", "projected_score"]
    }

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
                temperature=0.1
            )
        )
        data = json.loads(response.text)
        data["name"] = candidate_name if candidate_name else data.get("name", "Unknown Candidate")
        data["email"] = candidate_email if candidate_email else data.get("email", "N/A")
        return data
    except Exception as e:
        st.error(f"AI Extraction Failed: {e}")
        return None
