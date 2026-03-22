import fitz
import docx
import google.generativeai as genai
import json
import streamlit as st
import io

def get_document_text(file_bytes, filename):
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            return "\n".join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([para.text for para in doc.paragraphs]).strip()
    except: return None

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    genai.configure(api_key=api_key)
    # Using the state-of-the-art Flash model
    model = genai.GenerativeModel("gemini-2.5-flash") 
    all_results = []
    
    for f in resume_files:
        text = get_document_text(f.getvalue(), f.name)
        if text:
            prompt = f"""
            JD: {jd_text}
            Resume: {text}
            Task: Return ONLY JSON: {{"name": "string", "score": int, "summary": "string", "invite": "string"}}
            Note: Drafting invite from ai26agent@gmail.com.
            """
            try:
                response = model.generate_content(prompt)
                res_text = response.text.strip().replace('```json', '').replace('```', '')
                data = json.loads(res_text)
                
                # Save to database
                save_func(db_conn, data, email, 0.5)
                
                # Feedback: Message recruiter that the NAME was scanned successfully
                st.success(f"✅ '{data['name']}' in resume scanned successfully!")
                all_results.append(data)
            except Exception as e:
                st.error(f"Error processing {f.name}: {e}")
                
    return all_results
