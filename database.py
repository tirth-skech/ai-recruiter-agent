import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruitment_v8_enterprise.db', check_same_thread=False)
    cursor = conn.cursor()
    
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         job_id INTEGER, name TEXT, email TEXT, edu_tier TEXT, 
         gender TEXT, ethnicity TEXT, 
         skills TEXT, salary_exp REAL, score INTEGER, 
         prediction_score REAL, status TEXT, 
         timestamp DATETIME)''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_job ON candidates(email, job_id)')
    conn.commit()
    return conn

def save_candidate_v8(conn, data, job_id, prediction):
    cursor = conn.cursor()
    email = data.get('email', 'N/A')
    
    # Track B Logic: Update if exists, otherwise Insert
    cursor.execute("SELECT id FROM candidates WHERE email = ? AND job_id = ?", (email, job_id))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('''UPDATE candidates SET 
            score = ?, prediction_score = ?, timestamp = ?, gender = ?, ethnicity = ?
            WHERE id = ?''', 
            (data['score'], prediction, datetime.now(), data.get('gender'), data.get('ethnicity'), exists[0]))
    else:
        cursor.execute('''INSERT INTO candidates 
            (job_id, name, email, edu_tier, gender, ethnicity, skills, salary_exp, score, prediction_score, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (job_id, data['name'], email, data['edu_tier'], data.get('gender'), data.get('ethnicity'),
             ", ".join(data['skills']), data['salary_exp'], data['score'], prediction, "Screened", datetime.now()))
    conn.commit()
