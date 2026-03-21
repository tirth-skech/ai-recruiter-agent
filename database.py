import sqlite3
import json
from datetime import datetime

def init_db():
    conn = sqlite3.connect('recruiter_v3.db', check_same_thread=False)
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  score INTEGER, 
                  diversity_index INTEGER,
                  journey_steps TEXT, 
                  status TEXT, 
                  processed_by_email TEXT, 
                  api_latency REAL,
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email, latency, steps):
    status = "Qualified" if data.get('is_qualified') else "Rejected"
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, diversity_index, journey_steps, status, processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?,?)''',
                 (data.get('name', 'Unknown'), 
                  data.get('score', 0), 
                  data.get('diversity_index', 0),
                  json.dumps(steps), 
                  status, 
                  email, 
                  latency, 
                  datetime.now()))
    conn.commit()
