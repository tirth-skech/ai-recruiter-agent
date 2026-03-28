import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruiter_v5.db', check_same_thread=False)
    cursor = conn.cursor()
    # Create the table with ALL the columns needed for Week 5
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
    cursor = conn.cursor()
    # Convert list of skills to a string
    skills_str = ", ".join(data.get('skills', []))
    
    # Check if assessment was sent
    status = "Assessment Sent" if "HackerEarth Assessment Sent" in steps else "Screened"
    
    cursor.execute('''INSERT INTO recruitment_pipeline 
                     (candidate_name, education_tier, skills_found, notice_period, 
                      expected_salary, relocation_willing, score, status, 
                      processed_by_email, api_latency, timestamp) 
                     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''', 
                  (data.get('name'), data.get('edu_tier'), skills_str, 
                   data.get('notice_period'), data.get('salary_exp'), 
                   data.get('relocation'), data.get('score'), status, 
                   email, latency, datetime.now()))
    conn.commit()
