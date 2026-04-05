from google import genai
import streamlit as st

# Use the key from your secrets
client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

def show_my_models():
    print("--- Available Models for your API Key ---")
    models = client.models.list()
    for model in models:
        # We only care about models that can 'generateContent'
        if 'generateContent' in model.supported_generation_methods:
            print(f"Model Name: {model.name}")
            print(f"Display Name: {model.display_name}")
            print("-" * 30)

if __name__ == "__main__":
    show_my_models()
