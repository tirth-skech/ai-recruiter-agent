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

def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    """The Track A End-to-End Agent logic with real-time UI feedback."""
    genai.configure(api_key=api_key)
    try:
        # Model Discovery
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in models if "2.5-flash" in m), models[0])
        model = genai.GenerativeModel(target)
        
        # Create a header for the live results
        st.divider()
        st.subheader("📝 Real-Time Screening Results")

        for f in resume_files:
            with st.spinner(f"Agent Analyzing: {f.name}..."):
                # Read file content
                raw_bytes = f.read()
                resume_text = get_document_text(raw_bytes, f.name)
                
                if not resume_text:
                    continue
                
                start_time = time.time()
                
                # Enhanced Track A Prompt
                prompt = f"""
                JOB DESCRIPTION: {jd_text}
                RESUME: {resume_text}
                
                TASK: Act as a professional HR Agent. 
                1. Extract candidate name.
                2. Score matching (0-100) based on JD requirements.
                3. Provide a brief summary of why they are or aren't a match.
                4. Draft a 2-line interview invite email.
                
                Return ONLY valid JSON: 
                {{
                    "name": "str", 
                    "score": int, 
                    "summary": "str", 
                    "invite": "str"
                }}
                """
                
                response = model.generate_content(prompt)
                
                # Clean JSON response
                res_text = response.text.strip().replace('```json', '').replace('```', '')
                data = json.loads(res_text)
                
                latency = time.time() - start_time
                
                # --- REAL-TIME SUMMARY UI (For the Recruiter Page) ---
                with st.container(border=True):
                    col1, col2 = st.columns([1, 4])
                    
                    # Display the score as a metric
                    col1.metric("Match Score", f"{data['score']}%")
                    
                    # Display Name and Summary
                    col2.markdown(f"### {data['name']}")
                    col2.markdown(f"**AI Analysis:** {data['summary']}")
                    
                    # Show the invite draft in an expander
                    with col2.expander("View Drafted Invite Email"):
                        st.code(data['invite'], language="markdown")
                
                # Save using the database function (for the Manager Dashboard)
                save_func(db_conn, data, email, latency)
                
                st.toast(f"✅ Processed and Saved: {data['name']}")
                
                # Rate limit safety for free tier keys
                time.sleep(2) 
                
    except Exception as e:
        st.error(f"Processor Error: {e}")
