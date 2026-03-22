import fitz
import docx
import google.generativeai as genai
import time
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
    except Exception as e:
        return None

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    genai.configure(api_key=api_key)
    models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
    target = next((m for m in models if "2.5-flash" in m), models[0])
    model = genai.GenerativeModel(target)
    
    all_results = []
    
    for f in resume_files:
        text = get_document_text(f.getvalue(), f.name)
        if text:
            prompt = f"""
            JD: {jd_text}
            Resume: {text}
            Task: Return ONLY JSON: {{"name": "string", "score": int, "summary": "string", "invite": "string"}}
            Note: The 'invite' should be from ai26agent@gmail.com.
            """
            start_time = time.time()
            response = model.generate_content(prompt)
            res_text = response.text.strip().replace('```json', '').replace('```', '')
            data = json.loads(res_text)
            
            latency = time.time() - start_time
            save_func(db_conn, data, email, latency)
            
            # This allows the UI to show "Success" for each specific name
            st.success(f"✅ {data['name']} in resume scanned successfully!")
            all_results.append(data)
            time.sleep(1) # Rate limit safety
            
    return all_results
