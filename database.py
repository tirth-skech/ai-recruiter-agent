import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('hr_enterprise.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, score INTEGER, summary TEXT, 
                  status TEXT, processed_by_email TEXT, 
                  api_latency REAL, timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email, latency):
    conn.execute("""INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, status, processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?)""",
                 (data['name'], data['score'], data['summary'], "Screened", email, latency, datetime.now()))
    conn.commit()
