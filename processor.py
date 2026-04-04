import fitz, docx, io, json, time, requests
import streamlit as st
from google import genai
from google.genai import types

def run_agent_workflow(api_key, jd_text, resume_files, user_email, db_conn, save_func, overrides=None):
    client = genai.Client(api_key=api_key)
    
    for f in resume_files:
        text = get_document_text(f.read(), f.name)
        if not text: continue
        
        with st.spinner(f"Analyzing {f.name}..."):
            # System Instruction for Indian Market Context
            sys_instr = "Extract details. Tier-1 = IIT/NIT/BITS. Output JSON only."
            
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
                
                # Logic: Auto-trigger HackerEarth for Tier-1 candidates
                if candidate.get('edu_tier') == "Tier-1" and candidate.get('score', 0) > 80:
                    steps.append("HackerEarth Sent")
                
                # Save using the relational function
                save_func(db_conn, candidate, user_email, overrides=overrides, steps=steps)
                st.toast(f"Successfully processed {f.name}")
                
            except Exception as e:
                st.error(f"Agent failed on {f.name}: {e}")
                    
                    
