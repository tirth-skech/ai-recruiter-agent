import streamlit as st
import google.generativeai as genai
import sqlite3
import json
import pandas as pd
from pdfminer.high_level import extract_text
import io

# 1. Database logic for Track A Milestone
def init_db():
    conn = sqlite3.connect('recruiter_final.db')
    conn.execute('CREATE TABLE IF NOT EXISTS candidates (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, score INTEGER, summary TEXT)')
    conn.close()

# 2. UI Setup
st.set_page_config(page_title="AI Recruiter Agent", layout="wide")
st.title("🤖 AI Recruiter Agent")

# Milestone Requirement: Database History
if st.sidebar.button("📊 Show Saved Database"):
    try:
        conn = sqlite3.connect('recruiter_final.db')
        df = pd.read_sql_query("SELECT * FROM candidates", conn)
        st.sidebar.write(df)
        conn.close()
    except:
        st.sidebar.write("Database is currently empty.")

st.write("---")

# 3. Input Fields (Fixed to prevent 403 Leaked Key Error)
api_key = st.text_input("🔑 Enter Gemini API Key", type="password", help="Get your key from aistudio.google.com")
criteria = st.text_area("🎯 Hiring Criteria", placeholder="e.g., Python expert with 3 years experience", height=100)
uploaded_file = st.file_uploader("📤 Upload Resume (PDF)", type="pdf")

if st.button("🚀 Run Analysis"):
    if not api_key:
        st.error("Please provide a valid Gemini API Key.")
    elif not criteria or not uploaded_file:
        st.error("Please provide both criteria and a resume.")
    else:
        with st.spinner("AI is analyzing..."):
            try:
                # Initialize Database
                init_db()
                
                # A. Text Extraction from PDF
                pdf_bytes = io.BytesIO(uploaded_file.read())
                text = extract_text(pdf_bytes)
                
                # B. Configure Gemini Flash
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    generation_config={
                        "temperature": 0.1, # Professional stability
                        "response_mime_type": "application/json", # Clean JSON only
                    }
                )
                
                # C. Analysis Prompt
                prompt = f"""
                Resume Text: {text}
                Criteria: {criteria}
                Return ONLY a JSON object:
                {{
                  "name": "Full Name",
                  "score": 85,
                  "summary": "Short 2-sentence explanation."
                }}
                """
                
                # D. AI Processing
                response = model.generate_content(prompt)
                data = json.loads(response.text)
                
                # E. Save to SQLite
                conn = sqlite3.connect('recruiter_final.db')
                conn.execute("INSERT INTO candidates (name, score, summary) VALUES (?, ?, ?)", 
                             (data['name'], data['score'], data['summary']))
                conn.commit()
                conn.close()
                
                # F. Display Results
                st.success(f"Analysis Complete for: {data['name']}")
                st.metric("Match Score", f"{data['score']}%")
                st.info(f"**AI Reasoning:** {data['summary']}")
                st.balloons()
                
            except Exception as e:
                st.error(f"Error occurred: {str(e)}")
                
!pkill -f streamlit
!pkill -f lt


!pip install pdfminer.six

import urllib
print("Your Tunnel Password (IP) is:", urllib.request.urlopen('https://ipv4.icanhazip.com').read().decode('utf8').strip())


!nohup streamlit run app.py --server.port 8501 --server.headless true & sleep 10 && npx localtunnel --port 8501
