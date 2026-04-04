import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruiter_v6.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Main Candidate Profile
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  email TEXT UNIQUE, name TEXT, edu_tier TEXT, 
                  skills TEXT, linkedin_url TEXT, github_url TEXT,
                  processed_by TEXT, timestamp DATETIME)''')

    # 2. Recruitment Lifecycle (Status & Logic)
    cursor.execute('''CREATE TABLE IF NOT EXISTS pipeline 
                 (candidate_id INTEGER, 
                  status TEXT, score INTEGER, 
                  salary_exp REAL, relocation TEXT, 
                  notice_period TEXT,
                  FOREIGN KEY(candidate_id) REFERENCES candidates(id))''')

    # 3. Assessment & API Logs (Error Handling Track)
    cursor.execute('''CREATE TABLE IF NOT EXISTS api_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER, service_name TEXT, 
                  status_code INTEGER, response_msg TEXT, 
                  timestamp DATETIME)''')

    # 4. Team Collaboration (Notes)
    cursor.execute('''CREATE TABLE IF NOT EXISTS team_notes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER, author TEXT, 
                  note TEXT, created_at DATETIME)''')

    conn.commit()
    return conn

def save_full_lifecycle(conn, data, email, overrides=None):
    cursor = conn.cursor()
    try:
        # Insert or Update Candidate
        cursor.execute('''INSERT OR REPLACE INTO candidates 
                         (email, name, edu_tier, skills, processed_by, timestamp) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (data['email'], data['name'], data['edu_tier'], 
                       ", ".join(data['skills']), email, datetime.now()))
        
        c_id = cursor.lastrowid or cursor.execute("SELECT id FROM candidates WHERE email=?", (data['email'],)).fetchone()[0]

        # Insert Pipeline Data with Overrides
        salary = overrides['salary'] if overrides and overrides['salary'] > 0 else data['salary_exp']
        reloc = overrides['relocation'] if overrides and overrides['relocation'] != "Use AI Extraction" else data['relocation']

        cursor.execute('''INSERT INTO pipeline 
                         (candidate_id, status, score, salary_exp, relocation, notice_period) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (c_id, "Sourced", data['score'], salary, reloc, data['notice_period']))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
