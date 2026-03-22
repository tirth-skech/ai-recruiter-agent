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
                  interview_date TEXT,
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, user_email):
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, summary, invite_text, processed_by, timestamp) 
                 VALUES (?,?,?,?,?,?)''',
                 (data['name'], data['score'], data['summary'], data.get('invite', ''), user_email, datetime.now()))
    conn.commit()

def update_schedule(conn, name, date_str):
    conn.execute("UPDATE recruitment_pipeline SET interview_date = ? WHERE candidate_name = ?", (date_str, name))
    conn.commit()

def reset_database(conn):
    conn.execute("DELETE FROM recruitment_pipeline")
    conn.commit()
