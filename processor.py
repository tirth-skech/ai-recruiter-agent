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

def preview_resumes(api_key, jd_text, resume_files):
    """Analyzes resumes but does NOT save them yet. Returns a list of dicts for Review."""
    client = genai.Client(api_key=api_key)
    
    # Strictly defined schema for consistency
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "email": {"type": "STRING"},
            "edu_tier": {"type": "STRING", "enum": ["Tier-1", "Tier-2", "Tier-3"]},
            "gender": {"type": "STRING", "enum": ["Male", "Female", "Other"]},
            "ethnicity": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"},
            "score": {"type": "INTEGER"}
        },
        "required": ["name", "email", "edu_tier", "score", "gender", "ethnicity"]
    }
    
    previews = []
    for f in resume_files:
        # Read file bytes once per loop
        file_content = f.read()
        text = get_document_text(file_content, f.name)
        
        if text:
            with st.spinner(f"AI reading {f.name}..."):
                try:
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=f"JD: {jd_text}\n\nResume: {text}",
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json", 
                            response_schema=schema,
                            temperature=0.0
                        )
                    )
                    data = json.loads(response.text)
                    data['filename'] = f.name # Track source file
                    previews.append(data)
                except Exception as e:
                    st.error(f"AI failed to parse {f.name}: {e}")
        
        # Free Tier Rate Limit Protection
        time.sleep(2) 
        
    return previews
