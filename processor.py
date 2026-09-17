import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import json
import streamlit as st
from google import genai
from google.genai import types
import fitz
import docx
import io

def send_real_email(sender_email, sender_password, recipient_email, candidate_name, job_role):
    """Sends background email via Gmail SMTP server."""
    try:
        msg = MIMEMultipart()
        msg['From'] = f"Goldwin Recruitment Team <{sender_email}>"
        msg['To'] = recipient_email
        msg['Subject'] = f"Interview Invitation - Skill Match Role ({job_role})"

        body = f"""Hi {candidate_name},

We have reviewed your skill gap analysis profile for the {job_role} position. 
We were impressed with your technical background and would like to schedule an interview.

Best regards,
Goldwin Recruitment Team
"""
        msg.attach(MIMEText(body, 'plain'))

        # Connect to Gmail SMTP Server
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        return True, "Email dispatched successfully!"
    except Exception as e:
        return False, str(e)

def generate_candidate_summary(api_key, query_text, candidate_records):
    """Generates an executive AI summary based on the search query."""
    if not candidate_records:
        return f"No records found matching query: '{query_text}'"

    client = genai.Client(api_key=api_key)
    
    prompt = f"""
    You are an executive HR AI assistant. 
    The recruiter searched for: "{query_text}".
    
    Here is the relevant database record(s) found:
    {json.dumps(candidate_records, indent=2)}

    Provide a concise 3-4 sentence professional executive summary highlighting:
    1. Candidate identity and targeted job role.
    2. Overall match score and current qualification status.
    3. Identified skill gaps and upskilling readiness.
    """

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(temperature=0.2)
        )
        return response.text
    except Exception as e:
        return f"Error generating AI summary: {e}"
