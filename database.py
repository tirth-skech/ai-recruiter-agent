import sqlite3
from datetime import datetime

def init_db():
    # Upgrade to v6 for relational schema
    conn = sqlite3.connect('recruiter_v6.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # 1. Main Candidate Profile (Social & Basic Info)
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  email TEXT UNIQUE, name TEXT, edu_tier TEXT, 
                  skills_found TEXT, linkedin_url TEXT, github_url TEXT,
                  processed_by_email TEXT, timestamp DATETIME)''')

    # 2. Recruitment Lifecycle (Status & Metrics)
    cursor.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER,
                  candidate_name TEXT, education_tier TEXT,
                  expected_salary REAL, relocation_willing TEXT, 
                  notice_period TEXT, score INTEGER, status TEXT,
                  FOREIGN KEY(candidate_id) REFERENCES candidates(id))''')

    # 3. Team Collaboration (Notes/Feedback)
    cursor.execute('''CREATE TABLE IF NOT EXISTS team_notes 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  candidate_id INTEGER, author TEXT, 
                  note TEXT, timestamp DATETIME)''')

    # 4. API Error/Audit Logs (Sophisticated Error Handling)
    cursor.execute('''CREATE TABLE IF NOT EXISTS api_logs 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  service_name TEXT, status_code INTEGER, 
                  message TEXT, timestamp DATETIME)''')
    
    conn.commit()
    return conn

def save_full_lifecycle(conn, data, email, latency, steps, overrides=None):
    cursor = conn.cursor()
    try:
        # Insert/Update Master Profile
        cursor.execute('''INSERT OR REPLACE INTO candidates 
                         (email, name, edu_tier, skills_found, processed_by_email, timestamp) 
                         VALUES (?, ?, ?, ?, ?, ?)''', 
                      (data.get('email'), data.get('name'), data.get('edu_tier'), 
                       ", ".join(data.get('skills', [])), email, datetime.now()))
        
        c_id = cursor.lastrowid or cursor.execute("SELECT id FROM candidates WHERE email=?", (data['email'],)).fetchone()[0]

        # Handle UI Overrides
        sal = overrides['salary'] if overrides and overrides['salary'] > 0 else data.get('salary_exp')
        reloc = overrides['relocation'] if overrides and overrides['relocation'] != "Use AI Extraction" else data.get('relocation')

        # Insert Pipeline Entry
        status = "Assessment Sent" if steps and "Assessment Sent" in steps else "Screened"
        cursor.execute('''INSERT INTO recruitment_pipeline 
                         (candidate_id, candidate_name, education_tier, expected_salary, 
                          relocation_willing, notice_period, score, status) 
                         VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', 
                      (c_id, data.get('name'), data.get('edu_tier'), sal, 
                       reloc, data.get('notice_period'), data.get('score'), status))
        conn.commit()
    except Exception as e:
        print(f"DB Error: {e}")
