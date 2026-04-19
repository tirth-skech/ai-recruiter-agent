import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruitment_v8_enterprise.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Enable Performance Optimization via Indexing
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         job_id INTEGER, name TEXT, email TEXT, edu_tier TEXT, 
         gender TEXT, ethnicity TEXT, -- Diversity Metrics
         skills TEXT, salary_exp REAL, score INTEGER, 
         prediction_score REAL, status TEXT, 
         timestamp DATETIME)''')
    
    # Index for high-performance searching
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_score ON candidates(score)')
    
    conn.commit()
    return conn

def save_candidate_v8(conn, data, job_id, prediction, diversity_data=None):
    cursor = conn.cursor()
    # Maintaining old logic for core data + adding diversity fields
    cursor.execute('''INSERT INTO candidates 
        (job_id, name, email, edu_tier, gender, ethnicity, skills, salary_exp, score, prediction_score, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (job_id, data['name'], data.get('email', 'N/A'), data['edu_tier'],
         diversity_data.get('gender') if diversity_data else "Undisclosed",
         diversity_data.get('ethnicity') if diversity_data else "Undisclosed",
         ", ".join(data['skills']), data['salary_exp'], data['score'], prediction, "Screened", datetime.now()))
    conn.commit()
