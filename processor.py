import fitz
import docx
import google.generativeai as genai
import json
import streamlit as st
import io
import time

def extract_text(file):
    ext = file.name.split('.')[-1].lower()
    if ext == 'pdf':
        doc = fitz.open(stream=file.getvalue(), filetype="pdf")
        return "\n".join([page.get_text() for page in doc])
    elif ext == 'docx':
        doc = docx.Document(io.BytesIO(file.getvalue()))
        return "\n".join([para.text for para in doc.paragraphs])
    return None

def run_agent_workflow(api_key, jd_text, files, user_email, conn, save_func):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    results = []

    for f in files:
        resume_text = extract_text(f)
        if resume_text:
            prompt = f"""
            JD: {jd_text}
            Resume: {resume_text}
            Task: Return ONLY JSON: 
            {{"name": "Full Name", "score": 85, "summary": "Short fit analysis", "invite": "Email body from ai26agent@gmail.com"}}
            """
            try:
                response = model.generate_content(prompt)
                data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
                
                # Save to DB
                save_func(conn, data, user_email)
                
                # Feedback to Recruiter
                st.success(f"✅ {data['name']} scanned successfully!")
                results.append(data)
                time.sleep(0.5) 
            except Exception as e:
                st.error(f"Error processing {f.name}: {e}")
    return results
