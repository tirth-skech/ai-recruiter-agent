import io
import json
import os
import tempfile
from google import genai
from google.genai import types

def parse_profile_agent(api_key, uploaded_file, filename):
    """
    Parses candidate profile data from multiple input formats including
    PDF, DOCX, Images, and Audio/Video (MP3, WAV, M4A, MP4, MPEG, etc.) using Gemini 2.5 Flash.
    """
    if not uploaded_file:
        return None

    try:
        client = genai.Client(api_key=api_key)
        ext = filename.split(".")[-1].lower()
        
        # Multimodal formats that should be processed via Gemini File API
        multimodal_exts = ["mp3", "wav", "m4a", "mp4", "avi", "mov", "mpeg", "png", "jpg", "jpeg"]
        
        prompt = """
        Analyze this file content (resume, voice profile, or audio introduction) and extract the following candidate profile details as a clean JSON object:
        {
            "candidate_id": "cand_101",
            "name": "Candidate Name",
            "location": "Candidate Location",
            "education": "Degree / Education Details",
            "experience_years": "Years of Experience",
            "target_role": "Target Job Position",
            "marks_10th": "10th Percentage or Grade (e.g. 85%)",
            "marks_12th": "12th Percentage or Grade (e.g. 88%)",
            "current_skills": ["Skill1", "Skill2", "Skill3"],
            "interests": ["Interest1", "Interest2"]
        }
        Return ONLY valid JSON. If a value is not found, fill it with reasonable defaults or "Not Specified".
        """

        if ext in multimodal_exts:
            # Save file temporarily to disk for Gemini File API upload
            with tempfile.NamedTemporaryFile(delete=False, suffix=f".{ext}") as temp_file:
                temp_file.write(uploaded_file.getvalue())
                temp_path = temp_file.name

            try:
                # Upload file to Gemini API
                file_ref = client.files.upload(file=temp_path)
                
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=[file_ref, prompt],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.1
                    )
                )
                
                # Cleanup file from Gemini server and local disk
                try:
                    client.files.delete(name=file_ref.name)
                except Exception:
                    pass
                os.remove(temp_path)

                return json.loads(response.text)

            except Exception as e:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                raise e

        else:
            # Fallback text/PDF file reading
            file_bytes = uploaded_file.getvalue()
            text_content = ""

            if ext == "pdf":
                try:
                    import pypdf
                    reader = pypdf.PdfReader(io.BytesIO(file_bytes))
                    for page in reader.pages:
                        text_content += page.extract_text() or ""
                except Exception:
                    text_content = file_bytes.decode("utf-8", errors="ignore")
            elif ext == "docx":
                try:
                    import docx
                    doc = docx.Document(io.BytesIO(file_bytes))
                    text_content = "\n".join([p.text for p in doc.paragraphs])
                except Exception:
                    text_content = file_bytes.decode("utf-8", errors="ignore")
            else:
                text_content = file_bytes.decode("utf-8", errors="ignore")

            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"{prompt}\n\nDocument Text:\n{text_content}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            return json.loads(response.text)

    except Exception as err:
        print(f"Error in parse_profile_agent: {err}")
        return None


def generate_reasoning_transparency(candidate_skills, required_skills):
    """
    Generates dynamic skill matching transparency statistics and logic breakdowns.
    """
    user_skills_lower = [s.lower() for s in candidate_skills]
    matched_skills = [s for s in required_skills if s.lower() in user_skills_lower]
    missing_skills = [s for s in required_skills if s.lower() not in user_skills_lower]
    
    match_score = round((len(matched_skills) / len(required_skills)) * 100) if required_skills else 100
    
    return {
        "match_score": match_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "total_required": len(required_skills)
    }
