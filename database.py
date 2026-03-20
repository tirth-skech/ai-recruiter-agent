import sqlite3
from datetime import datetime
import json

def init_db():
    conn = sqlite3.connect('hr_enterprise_v2.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  score INTEGER, 
                  diversity_index INTEGER,
                  journey_steps TEXT, 
                  status TEXT, 
                  processed_by_email TEXT, 
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email, latency, steps):
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, diversity_index, journey_steps, status, processed_by_email, timestamp) 
                 VALUES (?,?,?,?,?,?,?)''',
                 (data['name'], data['score'], data.get('diversity_index', 0), 
                  json.dumps(steps), "Screened", email, datetime.now()))
    conn.commit()
