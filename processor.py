import fitz, docx, io, json, time, requests
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

def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    client = genai.Client(api_key=api_key)
    
    for f in resume_files:
        file_content = f.read()
        text = get_document_text(file_content, f.name)
        if not text: continue
        
        with st.spinner(f"Agent analyzing {f.name}..."):
            sys_instr = "Identify Tier-1 (IIT/NIT/BITS) vs Tier-2/3. Extract Salary (LPA). Output JSON only."
            
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"JD: {jd_text}\nResume: {text}",
                    config=types.GenerateContentConfig(
                        system_instruction=sys_instr,
                        response_mime_type="application/json"
                    )
                )
                candidate = json.loads(response.text)
                steps = ["AI Extraction Complete"]
                
                # Auto-trigger HackerEarth for High-Score Tier-1
                if candidate.get('edu_tier') == "Tier-1" and candidate.get('score', 0) > 80:
                    steps.append("HackerEarth Sent")
                
                # Save with HITL Overrides
                save_func(db_conn, candidate, user_email, latency=0, steps=steps, overrides=overrides)
                st.success(f"✅ Processed: {candidate.get('name')}")
                
            except Exception as e:
                st.error(f"Failed on {f.name}: {e}")
