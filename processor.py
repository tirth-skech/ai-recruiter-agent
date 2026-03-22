import fitz
import docx
import google.generativeai as genai
import json
import streamlit as st
import io
import time

def extract_text(file):
    ext = file.name.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=file.getvalue(), filetype="pdf")
            return "\n".join([page.get_text() for page in doc])
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file.getvalue()))
            return "\n".join([para.text for para in doc.paragraphs])
    except: return None

def run_agent_workflow(api_key, jd_text, files, email, conn, save_func):
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-1.5-flash")
    results = []

    for f in files:
        text = extract_text(f)
        if text:
            start_time = time.time()
            prompt = f"JD: {jd_text}\nResume: {text}\nReturn ONLY JSON: {{'name': 'str', 'score': int, 'summary': 'str', 'invite': 'str'}}"
            response = model.generate_content(prompt)
            data = json.loads(response.text.strip().replace('```json', '').replace('```', ''))
            
            latency = time.time() - start_time
            save_func(conn, data, email, latency)
            
            # PRO FEEDBACK:
            st.success(f"✅ '{data['name']}' in resume scanned successfully!")
            results.append(data)
    return results
