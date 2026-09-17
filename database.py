import sqlite3
from datetime import datetime

DB_NAME = 'recruitment_v8_enterprise.db'

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # Candidates Table supporting both C4 skill gaps & core recruiting metadata
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         job_id INTEGER, name TEXT, email TEXT, job_role TEXT,
         edu_tier TEXT, gender TEXT, ethnicity TEXT, 
         skills TEXT, gaps TEXT, recommendations TEXT,
         salary_exp REAL, score INTEGER, 
         match_score REAL, projected_score REAL, prediction_score REAL, 
         status TEXT, timestamp DATETIME)''')
    
    # System Audit Logs Table
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         timestamp DATETIME, component TEXT, 
         action TEXT, description TEXT, 
         associated_data TEXT, ip_address TEXT)''')
    
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_job ON candidates(email, job_id)')
    conn.commit()
    return conn

def save_candidate_v8(conn, data, job_id, prediction):
    cursor = conn.cursor()
    email = data.get('email', 'N/A')
    
    skills_str = ", ".join(data.get('skills', [])) if isinstance(data.get('skills'), list) else str(data.get('skills', ''))
    gaps_str = ", ".join(data.get('gaps', [])) if isinstance(data.get('gaps'), list) else str(data.get('gaps', ''))
    recs_str = str(data.get('recommendations', ''))

    cursor.execute("SELECT id FROM candidates WHERE email = ? AND job_id = ?", (email, job_id))
    exists = cursor.fetchone()

    if exists:
        cursor.execute('''UPDATE candidates SET 
            score = ?, prediction_score = ?, match_score = ?, projected_score = ?, 
            job_role = ?, gaps = ?, recommendations = ?, timestamp = ?, gender = ?, ethnicity = ?
            WHERE id = ?''', 
            (data.get('score', 0), prediction, data.get('match_score', 0.0), data.get('projected_score', 0.0),
             data.get('job_role', ''), gaps_str, recs_str, datetime.now(), data.get('gender'), data.get('ethnicity'), exists[0]))
    else:
        cursor.execute('''INSERT INTO candidates 
            (job_id, name, email, job_role, edu_tier, gender, ethnicity, skills, gaps, recommendations, salary_exp, score, match_score, projected_score, prediction_score, status, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (job_id, data.get('name', 'Unknown'), email, data.get('job_role', 'Applicant'), data.get('edu_tier', 'Tier-2'), 
             data.get('gender'), data.get('ethnicity'), skills_str, gaps_str, recs_str,
             data.get('salary_exp', 0.0), data.get('score', 0), data.get('match_score', 0.0), 
             data.get('projected_score', 0.0), prediction, "Screened", datetime.now()))
    conn.commit()
    
    log_audit(conn, "Candidate Profiling Agent", "Analyze Candidate Profile", 
              f"{data.get('name')} profile analyzed against {data.get('job_role', 'Job Role')}", 
              f"CAND-{str(data.get('name')).upper().replace(' ', '-')}")

def log_audit(conn, component, action, description, assoc_data="N/A", ip="127.0.0.1"):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO audit_logs 
        (timestamp, component, action, description, associated_data, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)''', 
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"), component, action, description, assoc_data, ip))
    conn.commit()

def get_audit_logs(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, component, action, description, associated_data, ip_address FROM audit_logs ORDER BY id DESC")
    return cursor.fetchall()
