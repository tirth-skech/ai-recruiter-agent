import fitz
import google.generativeai as genai
import time
import json
import streamlit as st

def get_pdf_text(file_bytes):
    try:
        doc = fitz.open(stream=file_bytes, filetype="pdf")
        text = chr(12).join([page.get_text() for page in doc])
        doc.close()
        return text.strip()
    except Exception as e:
        st.error(f"PDF Error: {e}")
        return None

def run_ai_workflow(api_key, criteria, files, email, db_conn, save_func):
    genai.configure(api_key=api_key)
    try:
        # Model Discovery for 2.5 Flash
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in models if "2.5-flash" in m), next((m for m in models if "1.5-flash" in m), models[0]))
        model = genai.GenerativeModel(target)
        
        for f in files:
            with st.spinner(f"Analyzing {f.name}..."):
                text = get_pdf_text(f.read())
                if not text: continue
                
                start = time.time()
                prompt = f"Resume: {text}\nCriteria: {criteria}\nReturn ONLY JSON: {{'name': 'str', 'score': int, 'summary': 'str'}}"
                
                res = model.generate_content(prompt).text
                if "```" in res: res = res.split("```")[1].replace("json","")
                data = json.loads(res)
                
                latency = time.time() - start
                save_func(db_conn, data, email, latency)
                st.toast(f"✅ {data['name']} processed")
                time.sleep(5) # Rate limit safety
    except Exception as e:
        st.error(f"AI Workflow Error: {e}")
