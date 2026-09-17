import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import time
import io
import fitz  # PyMuPDF
import docx
import streamlit as st
from google import genai
from google.genai import types

def send_real_email(sender_email, sender_password, recipient_email, candidate_name, job_role):
    """Sends background email via Gmail SMTP server."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Goldwin Recruitment Team <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = f"Interview Invitation - Skill Match Role ({job_role})"

        body = f"""Hi {candidate_name},

We have reviewed your skill gap analysis profile for the {job_role} position. 
We were impressed with your technical background and would like to schedule an interview.

Best regards,
Goldwin Recruitment Team
"""
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email dispatched successfully!"
    except Exception as e:
        return False, str(e)

def generate_candidate_summary(api_key, query_text, candidate_records):
    """Generates an executive AI summary based on the search query."""
    if not candidate_records:
        return f"No records found matching query: '{query_text}'"

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an executive HR AI assistant. 
    The recruiter searched for: "{query_text}".
    
    Here is the relevant database record(s) found:
    {json.dumps(candidate_records, indent=2)}

    Provide a concise 3-4 sentence professional executive summary highlighting:
    1. Candidate identity and targeted job role.
    2. Overall match score and current qualification status.
    3. Identified skill gaps and upskilling readiness.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as e:
        return f"Error generating AI summary: {e}"

def get_document_text(file_obj, filename):
    """Safely extracts text from PDF or DOCX file by resetting stream pointer."""
    try:
        file_obj.seek(0)  # RESET FILE POINTER TO START
        file_bytes = file_obj.read()
        
        if not file_bytes:
            st.error(f"File {filename} appears to be empty.")
            return None

        ext = filename.split('.')[-1].lower()
        if ext == 'pdf':
            doc = fitz.open(stream=io.BytesIO(file_bytes), filetype="pdf")
            text = chr(12).join([page.get_text() for page in doc]).strip()
            return text if text else None
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            text = "\n".join([p.text for p in doc.paragraphs]).strip()
            return text if text else None
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None

class PredictiveAnalytics:
    @staticmethod
    def calculate_retention_score(data):
        """Calculates retention prediction score."""
        base = data.get('score', 0)
        tier_bonus = 15 if data.get('edu_tier') == "Tier-1" else 5
        return round(min((base * 0.7) + tier_bonus, 100), 2)

def preview_resumes(api_key, jd_text, resume_files, manual_name="", manual_email=""):
    """Analyzes resumes for Track C4 Skill Gap & Recruiting Data with rate-limit handling."""
    if not api_key:
        st.error("Gemini API Key is missing. Please check your sidebar or secrets.toml.")
        return []

    client = genai.Client(api_key=api_key)
    
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "email": {"type": "STRING"},
            "job_role": {"type": "STRING"},
            "edu_tier": {"type": "STRING", "enum": ["Tier-1", "Tier-2", "Tier-3"]},
            "gender": {"type": "STRING", "enum": ["Male", "Female", "Other"]},
            "ethnicity": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "gaps": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"},
            "score": {"type": "INTEGER"},
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
        "required": ["name", "email", "job_role", "edu_tier", "score", "match_score", "projected_score", "skills", "gaps"]
    }
    
    previews = []
    for f in resume_files:
        text = get_document_text(f, f.name)
        
        if not text:
            st.warning(f"Could not extract readable text from {f.name}. Moving to next file...")
            continue

        with st.spinner(f"AI Analyzing {f.name}..."):
            prompt = f"""
            You are an Agentic AI system operating for Track C4: Skill-Gap-to-Job Matching.
            Analyze this candidate's resume against the Job Description.

            Job Description:
            {jd_text}

            Resume Text:
            {text}

            Perform candidate profiling, identify specific missing skill gaps, compute match_score (0-100), 
            projected_score (match score after upskilling), and provide targeted training recommendations.
            """
            
            # Retry loop with backoff for rate limits
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json", 
                            response_schema=schema,
                            temperature=0.0
                        )
                    )
                    data = json.loads(response.text)
                    data['filename'] = f.name
                    if manual_name: data['name'] = manual_name
                    if manual_email: data['email'] = manual_email
                    previews.append(data)
                    break  # Success, exit retry loop
                except Exception as e:
                    if "429" in str(e) or "quota" in str(e).lower():
                        st.warning(f"Rate limit hit. Retrying in 3 seconds... (Attempt {attempt + 1}/{max_retries})")
                        time.sleep(3)
                    else:
                        st.error(f"AI Extraction error for {f.name}: {e}")
                        break
        
        # Pause briefly between files to prevent exceeding API limits
        time.sleep(2) 
        
    return previews
