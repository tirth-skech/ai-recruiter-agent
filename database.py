import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruitment_v8_enterprise.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Tables for Week 8 Relational Schema
    cursor.execute('''CREATE TABLE IF NOT EXISTS jobs 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT, description TEXT, status TEXT)''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         job_id INTEGER, name TEXT, email TEXT, edu_tier TEXT, 
         gender TEXT, ethnicity TEXT, 
         skills TEXT, salary_exp REAL, score INTEGER, 
         prediction_score REAL, status TEXT, 
         timestamp DATETIME)''')
    
    # Performance Optimization: Search Indexing
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON candidates(score)')
    conn.commit()
    return conn

def save_candidate_v8(conn, data, job_id, prediction, diversity_data=None):
    cursor = conn.cursor()
    email = data.get('email', 'N/A')
    
    # CHECK IF CANDIDATE ALREADY EXISTS FOR THIS JOB
    cursor.execute("SELECT id FROM candidates WHERE email = ? AND job_id = ?", (email, job_id))
    existing = cursor.fetchone()

    if existing:
        # UPDATE OLD RECORD (Maintains data consistency)
        cursor.execute('''UPDATE candidates SET 
            score = ?, prediction_score = ?, timestamp = ? 
            WHERE id = ?''', (data['score'], prediction, datetime.now(), existing[0]))
    else:
        # INSERT NEW RECORD
        cursor.execute('''INSERT INTO candidates 
            (job_id, name, email, edu_tier, gender, ethnicity, skills, salary_exp, score, prediction_score, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (job_id, data['name'], email, data['edu_tier'],
             "Undisclosed", "Undisclosed", ", ".join(data['skills']), 
             data['salary_exp'], data['score'], prediction, "Screened", datetime.now()))
    conn.commit()
