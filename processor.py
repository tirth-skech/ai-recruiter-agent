import fitz, docx, io, json, time, requests
import streamlit as st
from google import genai
from google.genai import types
import time

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
    """
    Main entry point for the Agentic Workflow with Rate Limit Protection.
    """
    # ... (Workflow/Graph setup code)
    
    for f in resume_files:
        file_bytes = f.read()
        text = get_document_text(file_bytes, f.name)
        
        if text:
            with st.spinner(f"Agent analyzing {f.name}..."):
                # 1. PREVENTATIVE DELAY: Wait 4 seconds between files to stay under RPM limits
                time.sleep(4) 
                
                start_time = time.time()
                try:
                    # Invoke the LangGraph/Agent logic
                    result = app.invoke({
                        "jd": jd_text, 
                        "resume_text": text, 
                        "steps": [], 
                        "api_key": api_key
                    })
                    
                    candidate = result['candidate_data']
                    latency = time.time() - start_time
                    
                    # Apply Manual Overrides
                    if overrides:
                        if overrides.get("salary") is not None:
                            candidate['salary_exp'] = overrides['salary']
                        if overrides.get("relocation") is not None:
                            candidate['relocation'] = overrides['relocation']
                    
                    # Save to Relational Database
                    save_func(db_conn, candidate, user_email, latency, result['steps'], overrides=overrides)
                    st.success(f"✅ Processed: {candidate.get('name')}")
                    
                except Exception as e:
                    # 2. RETRY LOGIC: If a 429 error occurs, wait longer and retry
                    if "429" in str(e):
                        st.warning(f"Rate limit hit on {f.name}. Pausing for 10 seconds...")
                        time.sleep(10)
                        # Optional: You could recursively call or loop to retry the specific file here
                    else:
                        st.error(f"Failed on {f.name}: {e}")
        else:
            st.error(f"Failed to read {f.name}")
