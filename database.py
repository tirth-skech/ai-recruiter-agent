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
                  diversity_flag INTEGER,
                  processed_by TEXT, 
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email):
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, invite_text, diversity_flag, processed_by, timestamp) 
                 VALUES (?,?,?,?,?,?,?)''',
                 (data['name'], data['score'], data['summary'], data.get('invite_text', ''),
                  1 if data.get('diversity_flag') else 0, email, datetime.now()))
    conn.commit()
