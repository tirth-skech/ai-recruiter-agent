import time
import json
import streamlit as st
from google import genai
from google.genai import types
import fitz  # PyMuPDF
import docx
import io

def get_document_text(file_bytes, filename):
    """Extracts text from PDF or DOCX files."""
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

class PredictiveAnalytics:
    @staticmethod
    def calculate_retention_score(data):
        """Calculates score based on Week 8 logic."""
        base = data.get('score', 0)
        tier_bonus = 15 if data.get('edu_tier') == "Tier-1" else 5
        return round(min((base * 0.7) + tier_bonus, 100), 2)

def preview_resumes(api_key, jd_text, resume_files, manual_name="", manual_email=""):
    """Analyzes resumes for C4 Skill Gap & Recruiting Data. Returns a list of dicts for Review."""
    client = genai.Client(api_key=api_key)
    
    # Enhanced schema covering both recruiting metrics and Track C4 Skill-Gap analysis
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
        file_content = f.read()
        text = get_document_text(file_content, f.name)
        
        if text:
            with st.spinner(f"AI reading {f.name}..."):
                try:
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
                except Exception as e:
                    st.error(f"AI failed to parse {f.name}: {e}")
        
        time.sleep(2) 
        
    return previews
