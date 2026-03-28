import requests
import json

def trigger_hackerearth_invite(email):
    """
    Sends an automated test invitation via HackerEarth API.
    Note: You must have a 'Test ID' created in your HackerEarth recruiter dashboard.
    """
    # HackerEarth V4 API Endpoint
    url = "https://api.hackerearth.com/v4/partner/tests/invite/"
    
    headers = {
        "client-secret": st.secrets["hackerearth"]["client_secret"],
        "Content-Type": "application/json"
    }
    
    # Example Payload: You will replace 'TEST_ID' with your actual HackerEarth Test ID
    payload = {
        "test_id": "REPLACE_WITH_YOUR_ACTUAL_TEST_ID", 
        "emails": [email]
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        if response.status_code == 200:
            return True
        else:
            st.error(f"HackerEarth Error: {response.json().get('message')}")
            return False
    except Exception as e:
        st.error(f"Failed to connect to HackerEarth: {e}")
        return False

# Updated run_agent_workflow to include the new Week 5 logic
def run_agent_workflow(api_key, jd_text, resume_files, email, db_conn, save_func):
    # ... (existing graph setup) ...
    
    for f in resume_files:
        text = get_document_text(f.read(), f.name)
        if text:
            with st.spinner(f"Week 5 Pipeline: {f.name}"):
                start = time.time()
                res = app.invoke({"jd": jd_text, "resume_text": text, "steps": [], "api_key": api_key})
                
                candidate = res['candidate_data']
                
                # --- WEEK 5: AUTO-INVITE LOGIC ---
                # Invite if Tier-1 OR Score > 80
                if candidate.get('edu_tier') == "Tier-1" or candidate.get('score', 0) > 80:
                    invite_success = trigger_hackerearth_invite(email)
                    if invite_success:
                        res['steps'].append("HackerEarth Assessment Sent")
                
                save_func(db_conn, candidate, email, time.time()-start, res['steps'])
                st.success(f"✅ Processed: {candidate.get('name')}")
