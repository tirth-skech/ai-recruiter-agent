import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruitment_v7_prod.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Jobs Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, status TEXT)''')

    # 2. Candidates Table (The Core)
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         job_id INTEGER, name TEXT, email TEXT, edu_tier TEXT, 
         skills TEXT, salary_exp REAL, score INTEGER, 
         prediction_score REAL, status TEXT, 
         linkedin_url TEXT, github_url TEXT,
         FOREIGN KEY(job_id) REFERENCES jobs(id))''')

    # 3. Interviews & Collaboration Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS interviews 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, candidate_id INTEGER, 
         interviewer_email TEXT, scheduled_at DATETIME, notes TEXT,
         FOREIGN KEY(candidate_id) REFERENCES candidates(id))''')

    conn.commit()
    return conn

def save_candidate(conn, data, job_id, prediction):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO candidates 
        (job_id, name, email, edu_tier, skills, salary_exp, score, prediction_score, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (job_id, data['name'], data.get('email', 'N/A'), data['edu_tier'], 
         ", ".join(data['skills']), data['salary_exp'], data['score'], prediction, "Screened"))
    conn.commit()
