%%writefile app.py
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

# 2. Simple UI
st.title("🤖 AI Recruiter Agent")

# Milestone Requirement: Database History
if st.button("📊 Show Saved Database"):
    conn = sqlite3.connect('recruiter_final.db')
    st.write(pd.read_sql_query("SELECT * FROM candidates", conn))
    conn.close()

st.write("---")

# Input Fields
api_key = "AIzaSyCtTtQsyyM478vybLmsXBgqJJRgGp00be4"
criteria = st.text_input("🎯 Criteria (e.g. Python Developer)")
uploaded_file = st.file_uploader("📤 Upload PDF", type="pdf")

if st.button("🚀 Run Analysis"):
    if api_key and criteria and uploaded_file:
        with st.spinner("AI is analyzing..."):
            try:
                init_db()
                
                # A. Text Extraction
                text = extract_text(io.BytesIO(uploaded_file.read()))
                
                # B. Configure Stable Model
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name='gemini-2.5-flash',
                    generation_config={
                        "temperature": 0.1,  # Lower temperature = More consistent scores
                        "response_mime_type": "application/json", # Direct JSON output
                    }
                )
                
                # C. Prompting
                prompt = f"Resume: {text}\nCriteria: {criteria}\nReturn ONLY JSON: {{'name': 'str', 'score': int, 'summary': 'str'}}"
                
                # D. AI Processing
                response = model.generate_content(prompt)
                data = json.loads(response.text) # Config ensures clean JSON
                
                # E. Save to SQLite
                conn = sqlite3.connect('recruiter_final.db')
                conn.execute("INSERT INTO candidates (name, score, summary) VALUES (?, ?, ?)", 
                             (data['name'], data['score'], data['summary']))
                conn.commit()
                conn.close()
                
                # F. UI Results
                st.success(f"Score: {data['score']}% - {data['name']}")
                st.info(data['summary'])
                
            except Exception as e:
                st.error(f"Error: {e}")


!pkill -f streamlit
!pkill -f lt


!pip install pdfminer.six


import urllib
print("Your Tunnel Password (IP) is:", urllib.request.urlopen('https://ipv4.icanhazip.com').read().decode('utf8').strip())


!nohup streamlit run app.py --server.port 8501 --server.headless true & sleep 10 && npx localtunnel --port 8501
