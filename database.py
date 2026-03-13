import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('hr_enterprise.db', check_same_thread=False)
    
    # 1. Create table with all Track A columns if it doesn't exist
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  score INTEGER, 
                  summary TEXT, 
                  invite_text TEXT, 
                  status TEXT, 
                  processed_by_email TEXT, 
                  api_latency REAL, 
                  interview_date TEXT, 
                  timestamp DATETIME)''')
    
    # 2. Migration Logic: Check for missing columns in existing databases
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(recruitment_pipeline)")
    existing_columns = [column[1] for column in cursor.fetchall()]
    
    # Add 'invite_text' if missing
    if 'invite_text' not in existing_columns:
        try:
            conn.execute("ALTER TABLE recruitment_pipeline ADD COLUMN invite_text TEXT")
        except sqlite3.OperationalError:
            pass
            
    # Add 'interview_date' if missing
    if 'interview_date' not in existing_columns:
        try:
            conn.execute("ALTER TABLE recruitment_pipeline ADD COLUMN interview_date TEXT")
        except sqlite3.OperationalError:
            pass

    conn.commit()
    return conn

def save_candidate(conn, data, email, latency):
    """Saves a new screened candidate from the AI Agent."""
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, invite_text, status, processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?,?)''',
                 (data['name'], data['score'], data['summary'], data.get('invite', ''), "Screened", email, latency, datetime.now()))
    conn.commit()

def update_schedule(conn, name, date_str):
    """Handles the Week 3-4 Scheduler logic."""
    conn.execute('''UPDATE recruitment_pipeline 
                    SET interview_date = ?, status = 'Scheduled' 
                    WHERE candidate_name = ?''', (date_str, name))
    conn.commit()
