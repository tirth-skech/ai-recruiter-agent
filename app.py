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
    conn.execute('''CREATE TABLE IF NOT EXISTS candidates 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  name TEXT, 
                  score INTEGER, 
                  summary TEXT)''')
    conn.close()

# 2. UI Setup
st.set_page_config(page_title="AI Recruiter Agent", layout="centered")
st.title("🤖 AI Recruiter Agent")

# Sidebar for Database History
if st.sidebar.button("📊 Show Saved Database"):
    try:
        conn = sqlite3.connect('recruiter_final.db')
        df = pd.read_sql_query("SELECT * FROM candidates", conn)
        if not df.empty:
            st.sidebar.write(df)
        else:
            st.sidebar.write("Database is empty.")
        conn.close()
    except:
        st.sidebar.write("No data found yet.")

st.write("---")

# 3. Input Fields - These must stay outside the button to be visible
api_key = st.text_input("🔑 Enter Gemini API Key", type="password")
criteria = st.text_area("🎯 Hiring Criteria", placeholder="e.g. React Developer with 2+ years experience")
uploaded_file = st.file_uploader("📤 Upload Resume (PDF)", type="pdf")

# 4. Processing Logic
if st.button("🚀 Run Analysis"):
    if not api_key or not criteria or not uploaded_file:
        st.error("Please provide API Key, Criteria, and a PDF Resume.")
    else:
        with st.spinner("AI is analyzing..."):
            try:
                # Initialize DB
                init_db()
                
                # A. Text Extraction
                text = extract_text(io.BytesIO(uploaded_file.read()))
                
                # B. Configure Model
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel(
                    model_name='gemini-2.5-flash', # Note: Using stable 1.5-flash
                    generation_config={
                        "temperature": 0.1,
                        "response_mime_type": "application/json",
                    }
                )
                
                # C. Prompt & AI Call
                prompt = f"Resume: {text}\nCriteria: {criteria}\nReturn ONLY JSON: {{'name': 'str', 'score': int, 'summary': 'str'}}"
                response = model.generate_content(prompt)
                data = json.loads(response.text)
                
                # D. Save to SQLite
                conn = sqlite3.connect('recruiter_final.db')
                conn.execute("INSERT INTO candidates (name, score, summary) VALUES (?, ?, ?)",
                             (data['name'], data['score'], data['summary']))
                conn.commit()
                conn.close()
                
                # E. Display Results
                st.success(f"Candidate: {data['name']} | Score: {data['score']}%")
                st.info(data['summary'])
                st.balloons()
                
            except Exception as e:
                st.error(f"Error: {str(e)}")
