def save_candidate(conn, data, email, latency, steps):
    # Map the localized Indian context fields
    status = "Invite Sent" if "HackerEarth Assessment Sent" in steps else "Screened"
    
    conn.execute('''INSERT INTO recruitment_pipeline 
                 (candidate_name, education_tier, skills_found, notice_period, 
                  expected_salary, relocation_willing, score, status, 
                  processed_by_email, api_latency, timestamp) 
                 VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                 (data.get('name', 'Unknown'), 
                  data.get('edu_tier', 'Tier-3'), # Default to Tier-3 if not specified
                  json.dumps(data.get('skills', [])),
                  data.get('notice_period', '90 Days'), # Standard Indian Notice Period
                  data.get('salary_exp', 0),
                  data.get('relocation', 'No'),
                  data.get('score', 0), 
                  status, 
                  email, 
                  latency, 
                  datetime.now()))
    conn.commit()
