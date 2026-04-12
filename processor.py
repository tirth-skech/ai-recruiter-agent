import time
import json
import random
from google import genai
from google.genai import types

class APIHandler:
    """Sophisticated Error Handling with Retries"""
    @staticmethod
    def call_with_retry(func, *args, **kwargs):
        for attempt in range(3):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if attempt == 2: raise e
                time.sleep(2 ** attempt) # Exponential backoff

class PredictiveAnalytics:
    """Predicts hiring success based on Score, Tier, and Market Data"""
    @staticmethod
    def calculate_retention_score(candidate_data):
        base = candidate_data.get('score', 0)
        tier_bonus = 15 if candidate_data.get('edu_tier') == "Tier-1" else 5
        # Predictive Logic: Higher score + Tier-1 = High Retention Probability
        prediction = (base * 0.7) + (tier_bonus)
        return round(min(prediction, 100), 2)

def screening_node_v7(api_key, jd, resume_text):
    client = genai.Client(api_key=api_key)
    
    # Week 7 Schema
    schema = {
        "type": "OBJECT",
        "properties": {
            "name": {"type": "STRING"},
            "email": {"type": "STRING"},
            "edu_tier": {"type": "STRING"},
            "skills": {"type": "ARRAY", "items": {"type": "STRING"}},
            "salary_exp": {"type": "NUMBER"},
            "score": {"type": "INTEGER"}
        },
        "required": ["name", "edu_tier", "skills", "salary_exp", "score"]
    }

    def api_call():
        return client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"JD: {jd}\n\nResume: {resume_text}",
            config=types.GenerateContentConfig(response_mime_type="application/json", response_schema=schema)
        )

    response = APIHandler.call_with_retry(api_call)
    return json.loads(response.text)
