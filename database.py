import sqlite3
from datetime import datetime
import json

def init_db():
    conn = sqlite3.connect('hr_enterprise_v2.db', check_same_thread=False)
    # Create table for Track B: includes D&I and journey tracking
    conn.execute('''CREATE TABLE IF NOT EXISTS recruitment_pipeline 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                  candidate_name TEXT, 
                  score INTEGER, 
                  diversity_index INTEGER,
                  journey_steps TEXT, 
                  assessment_data TEXT,
                  status TEXT, 
                  processed_by_email TEXT, 
                  api_latency REAL, 
                  timestamp DATETIME)''')
    conn.commit()
    return conn

def save_candidate(conn, data, email, latency, steps):
    """Saves full agentic journey and structured analysis."""
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, score, diversity_index, journey_steps, assessment_data, status, processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?,?,?)''',
                 (data['name'], 
                  data['score'], 
                  data.get('diversity_index', 0),
                  json.dumps(steps), 
                  data.get('assessment_questions', ''),
                  "Qualified" if data.get('is_qualified') else "Rejected", 
                  email, 
                  latency, 
                  datetime.now()))
    conn.commit()
