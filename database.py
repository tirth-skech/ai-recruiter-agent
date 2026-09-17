import sqlite3
from datetime import datetime

DB_NAME = 'recruitgap_v9_enterprise.db'

def init_db():
    conn = sqlite3.connect(DB_NAME, check_same_thread=False)
    cursor = conn.cursor()
    
    # Candidates Schema for C4 Track
    cursor.execute('''CREATE TABLE IF NOT EXISTS candidates 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         name TEXT, email TEXT, job_role TEXT, 
         match_score REAL, projected_score REAL,
         skills TEXT, gaps TEXT, recommendations TEXT,
         status TEXT, timestamp DATETIME)''')
    
    # System Audit Logs
    cursor.execute('''CREATE TABLE IF NOT EXISTS audit_logs 
        (id INTEGER PRIMARY KEY AUTOINCREMENT, 
         timestamp DATETIME, component TEXT, 
         action TEXT, description TEXT, 
         associated_data TEXT, ip_address TEXT)''')
    
    conn.commit()
    return conn

def save_candidate_intake(conn, data):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO candidates 
        (name, email, job_role, match_score, projected_score, skills, gaps, recommendations, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
        (data['name'], data['email'], data['job_role'], 
         data['match_score'], data['projected_score'],
         ", ".join(data.get('skills', [])), 
         ", ".join(data.get('gaps', [])), 
         data.get('recommendations', ''), 
         "Processing", datetime.now()))
    conn.commit()
    
    # Log action to audit
    log_audit(conn, "Candidate Profiling Agent", "Analyze Candidate Profile", 
              f"Analyzed {data['name']} for {data['job_role']}", f"CAND-{data['name'].upper().replace(' ', '-')}")

def log_audit(conn, component, action, description, assoc_data="N/A", ip="127.0.0.1"):
    cursor = conn.cursor()
    cursor.execute('''INSERT INTO audit_logs 
        (timestamp, component, action, description, associated_data, ip_address)
        VALUES (?, ?, ?, ?, ?, ?)''', 
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S IST"), component, action, description, assoc_data, ip))
    conn.commit()

def get_candidates(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM candidates ORDER BY timestamp DESC")
    return cursor.fetchall()

def get_audit_logs(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT timestamp, component, action, description, associated_data, ip_address FROM audit_logs ORDER BY id DESC")
    return cursor.fetchall()
