import fitz  # PyMuPDF
import docx  # python-docx
import google.generativeai as genai
import time
import json
import streamlit as st
import io

def get_document_text(file_bytes, filename):
    """Handles both PDF and DOCX formats."""
    ext = filename.split('.')[-1].lower()
    try:
        if ext == 'pdf':
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            return chr(12).join([page.get_text() for page in doc]).strip()
        elif ext == 'docx':
            doc = docx.Document(io.BytesIO(file_bytes))
            return "\n".join([para.text for para in doc.paragraphs]).strip()
    except Exception as e:
        st.error(f"Error reading {filename}: {e}")
        return None

def run_agent_workflow(jd_text, resume_files, email, db_conn, save_func):
    """The Track A End-to-End Agent logic with real-time UI and Automated API Key."""
    
    # Check for API Key in Secrets
    if "GEMINI_API_KEY" not in st.secrets:
        st.error("Missing API Key! Please add 'GEMINI_API_KEY' to your Streamlit Secrets.")
        return

    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    
    try:
        # Model Discovery
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in models if "2.5-flash" in m), models[0])
        model = genai.GenerativeModel(target)
        
        st.divider()
        st.subheader("📝 Real-Time Screening Results")

        for f in resume_files:
            with st.spinner(f"Agent Analyzing: {f.name}..."):
                raw_bytes = f.read()
                resume_text = get_document_text(raw_bytes, f.name)
                
                if not resume_text:
                    continue
                
                start_time = time.time()
                
                prompt = f"""
                JOB DESCRIPTION: {jd_text}
                RESUME: {resume_text}
                
                TASK: Extract name, score (0-100), brief summary, and 2-line invite email.
                Return ONLY valid JSON: 
                {{
                    "name": "str", 
                    "score": int, 
                    "summary": "str", 
                    "invite": "str"
                }}
                """
                
                response = model.generate_content(prompt)
                res_text = response.text.strip().replace('```json', '').replace('```', '')
                data = json.loads(res_text)
                
                latency = time.time() - start_time
                
                # --- LIVE FEEDBACK ON RECRUITER PAGE ---
                with st.container(border=True):
                    c1, c2 = st.columns([1, 4])
                    c1.metric("Match", f"{data['score']}%")
                    c2.markdown(f"### {data['name']}")
                    c2.info(f"**AI Summary:** {data['summary']}")
                    with c2.expander("View Drafted Invite"):
                        st.code(data['invite'])
                
                # Save to database
                save_func(db_conn, data, email, latency)
                st.toast(f"✅ Saved {data['name']}")
                time.sleep(2) 
                
    except Exception as e:
        st.error(f"Processor Error: {e}")
