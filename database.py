import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('hr_enterprise.db', check_same_thread=False)
    
    # 1. Create table with all columns
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
    
    # 2. Migration: Add 'processed_by_email' if it's missing from an old version
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(recruitment_pipeline)")
    columns = [column[1] for column in cursor.fetchall()]
    
    if 'processed_by_email' not in columns:
        conn.execute("ALTER TABLE recruitment_pipeline ADD COLUMN processed_by_email TEXT")
    
    conn.commit()
    return conn

def save_candidate(conn, data, email, latency):
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, invite_text, status, processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?,?)''',
                 (data['name'], data['score'], data['summary'], data.get('invite', ''), "Screened", email, latency, datetime.now()))
    conn.commit()

def update_schedule(conn, name, date_str):
    conn.execute("UPDATE recruitment_pipeline SET interview_date = ? WHERE candidate_name = ?", (date_str, name))
    conn.commit()

def reset_db(conn):
    conn.execute("DELETE FROM recruitment_pipeline")
    conn.commit()
