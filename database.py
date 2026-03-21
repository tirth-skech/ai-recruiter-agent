import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('hr_enterprise.db', check_same_thread=False)
    # Added journey tracking and diversity columns
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  score INTEGER, 
                  summary TEXT, 
                  status TEXT, 
                  interview_date TEXT,
                  diversity_flag INTEGER,
                  technical_questions TEXT,
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_full_journey(conn, data):
    """Tool 4: Analytics & Tracking"""
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, status, diversity_flag, technical_questions, timestamp) 
                 VALUES (?,?,?,?,?,?,?)''',
                 (data['name'], data['score'], data['summary'], "Screened", 
                  1 if data.get('diversity_flag') else 0, 
                  str(data.get('questions', [])), datetime.now()))
    conn.commit()
