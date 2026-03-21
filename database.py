import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('hr_enterprise.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  score INTEGER, 
                  summary TEXT, 
                  invite_text TEXT, 
                  processed_by TEXT,
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email):
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, invite_text, processed_by, timestamp) 
                 VALUES (?,?,?,?,?,?)''',
                 (data['name'], data['score'], data['summary'], data['invite_text'], email, datetime.now()))
    conn.commit()
