import sqlite3
import json
from datetime import datetime

def init_db():
    """Initializes the SQLite database with Week 5 Indian Market columns."""
    conn = sqlite3.connect('recruiter_v5.db', check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  education_tier TEXT, 
                  skills_found TEXT,
                  notice_period TEXT,
                  expected_salary REAL,
                  relocation_willing TEXT,
                  score INTEGER, 
                  status TEXT, 
                  processed_by_email TEXT, 
                  api_latency REAL,
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email, latency, steps):
    """Saves candidate data extracted by Gemini 2.5 Flash."""
    # Determine status based on whether HackerEarth was triggered
    status = "Invite Sent" if "HackerEarth Assessment Sent" in steps else "Screened"
    
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, education_tier, skills_found, notice_period, 
                  expected_salary, relocation_willing, score, status, 
                  processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                 (data.get('name', 'Unknown'), 
                  data.get('edu_tier', 'Tier-3'), 
                  json.dumps(data.get('skills', [])),
                  data.get('notice_period', '90 Days'),
                  data.get('salary_exp', 0),
                  data.get('relocation', 'No'),
                  data.get('score', 0), 
                  status, 
                  email, 
                  latency, 
                  datetime.now()))
    conn.commit()
