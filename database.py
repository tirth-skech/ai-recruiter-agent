import sqlite3
from datetime import datetime

def init_db():
    """Initializes the database. No custom project imports allowed here."""
    conn = sqlite3.connect('recruiter_v6.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Main Candidates Master Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  email TEXT UNIQUE, 
                  name TEXT, 
                  edu_tier TEXT, 
                  skills_found TEXT, 
                  processed_by_email TEXT, 
                  timestamp DATETIME)''')

    # 2. Recruitment Pipeline Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER,
                  candidate_name TEXT, 
                  education_tier TEXT,
                  expected_salary REAL, 
                  relocation_willing TEXT, 
                  notice_period TEXT, 
                  score INTEGER, 
                  status TEXT,
                  FOREIGN KEY(candidate_id) REFERENCES candidates(id))''')
    
    conn.commit()
    return conn

def save_full_lifecycle(conn, data, email, latency=0, steps=None, overrides=None):
    """Saves candidate data. This function is self-contained to avoid loops."""
    cursor = conn.cursor()
    try:
        c_email = data.get('email') if data.get('email') else f"unknown_{datetime.now().timestamp()}@goldwin.com"
        
        cursor.execute('''INSERT OR REPLACE INTO candidates 
                         (email, name, edu_tier, skills_found, processed_by_email, timestamp) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (c_email, data.get('name'), data.get('edu_tier'), 
                       ", ".join(data.get('skills', [])), email, datetime.now()))
        
        cursor.execute("SELECT id FROM candidates WHERE name=?", (data.get('name'),))
        c_id = cursor.fetchone()[0]

        sal = overrides['salary'] if overrides and overrides.get('salary', 0) > 0 else data.get('salary_exp', 0)
        reloc = overrides['relocation'] if overrides and overrides.get('relocation') != "Use AI Extraction" else data.get('relocation', 'No')

        status = "Assessment Sent" if steps and "HackerEarth Sent" in steps else "Screened"
        cursor.execute('''INSERT INTO recruitment_pipeline 
                         (candidate_id, candidate_name, education_tier, expected_salary, 
                          relocation_willing, notice_period, score, status) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (c_id, data.get('name'), data.get('edu_tier'), sal, 
                       reloc, data.get('notice_period'), data.get('score'), status))
        conn.commit()
    except Exception as e:
        print(f"Database Error: {e}")
