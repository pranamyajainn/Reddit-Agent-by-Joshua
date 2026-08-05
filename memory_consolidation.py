"""
SARNA v4.0 — Memory Consolidation Engine
===========================================
Reads Pranamya's feedback from the Google Form Responses Sheet.
Sends the raw feedback to Groq to synthesize into edge-case rules.
Writes the rules to pranamya_guidelines.txt so the main ingestion loop
can inject them into future scoring prompts.
"""

import json
import os
import requests
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from config import GROQ_MODEL, GROQ_API_BASE

def get_feedback_sheet_data():
    creds_json_str = os.environ.get("GOOGLE_SHEETS_CREDENTIALS")
    sheet_id = os.environ.get("FEEDBACK_SHEET_ID", "155r3ek1NR1p8uvLmrF8luuF2s2nbyz0LWg57_pP0lxw")
    
    if not creds_json_str or not sheet_id:
        print("❌ Missing GOOGLE_SHEETS_CREDENTIALS or FEEDBACK_SHEET_ID")
        return []
        
    try:
        creds_data = json.loads(creds_json_str)
        credentials = Credentials.from_service_account_info(
            creds_data, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        service = build("sheets", "v4", credentials=credentials)
        
        # Assuming Form responses are in 'Form Responses 1!A:D'
        # A: Timestamp, B: Post Title, C: Quality, D: Reason
        result = service.spreadsheets().values().get(
            spreadsheetId=sheet_id, range="Form Responses 1!B2:D"
        ).execute()
        
        return result.get("values", [])
    except Exception as e:
        print(f"❌ Error reading feedback sheet: {e}")
        return []

def synthesize_feedback(rows):
    if not rows:
        print("😴 No feedback data found to synthesize.")
        return
        
    print(f"🧠 Synthesizing {len(rows)} pieces of feedback...")
    
    # Format feedback for LLM
    feedback_text = ""
    for row in rows:
        if len(row) >= 2:
            title = row[0]
            quality = row[1]
            reason = row[2] if len(row) > 2 else "No reason provided"
            feedback_text += f"- POST: {title}\n  RATING: {quality}\n  REASON: {reason}\n\n"
            
    system_prompt = """You are the Memory Consolidation Engine for an AI Lead Scraper.
Your job is to read the human founder's feedback on past leads and synthesize it into exactly 5 concise, actionable edge-case guardrails for future grading.
These rules will be injected directly into the prompt of the lead grading agent.
DO NOT contradict the core Additive Bucket framework. Focus on edge-cases and nuances the founder cares about.
Output ONLY the 5 bullet points. No intro, no outro."""
    
    headers = {
        "Authorization": f"Bearer {os.environ.get('GROQ_API_KEY')}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Here is the recent feedback data:\n\n{feedback_text}"}
        ],
        "temperature": 0.2
    }
    
    try:
        resp = requests.post(GROQ_API_BASE, json=payload, headers=headers)
        resp.raise_for_status()
        rules = resp.json()["choices"][0]["message"]["content"].strip()
        
        with open("pranamya_guidelines.txt", "w", encoding="utf-8") as f:
            f.write(rules)
            
        print("✅ Successfully consolidated memory to pranamya_guidelines.txt")
        print("--- NEW RULES ---")
        print(rules)
        
    except Exception as e:
        print(f"❌ Groq Synthesis Error: {e}")

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    
    rows = get_feedback_sheet_data()
    if rows:
        synthesize_feedback(rows)
    else:
        print("No rows found. Check your sheet or FEEDBACK_SHEET_ID.")
