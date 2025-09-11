import os
import json
import google.generativeai as genai
from datetime import datetime, timedelta, date

class NLPParser:
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-pro-latest')

    def parse_meeting_request(self, text: str) -> dict:
        current_date_str = datetime.now().strftime('%Y-%m-%d')
        prompt = f"""
        Analyze the following meeting request and extract all relevant details into a structured JSON object.
        The current date is {current_date_str}.

        Follow these rules for extraction:
        1.  **intent**: Identify the core intent, which must be one of: "schedule", "reschedule", "cancel", or "unknown".
        2.  **participants**: Extract all names and email addresses. If only a name is given, just list the name.
        3.  **duration_minutes**: Convert any duration (e.g., "1 hour", "45-min", "2h 15m") into total minutes (integer). If unspecified, default to 30 minutes. If a "quick" meeting is mentioned, default to 15 minutes.
        4.  **time_preferences_raw**: Capture the original natural language phrase describing the time (e.g., "tomorrow at 2 PM", "next week", "this Friday afternoon").
        5.  **start_date_hint**: Convert relative dates (e.g., "today", "tomorrow", "next Tuesday") to an absolute date in 'YYYY-MM-DD' format based on the current date {current_date_str}. If a specific date is mentioned, use that. If no date is mentioned but a time is, assume today's date.
        6.  **start_time_hint**: Extract the time in 'HH:MM' (24-hour) format. If a time phrase like "morning", "afternoon", or "evening" is used, infer a representative time (e.g., "09:00" for morning, "14:00" for afternoon, "19:00" for evening) if no specific time is given.
        7.  **meeting_title**: Extract the subject or title of the meeting (e.g., "project alpha sync", "team update").
        8.  **original_meeting_keywords**: For "reschedule" or "cancel" intents, list keywords from the original meeting title or description to help find it (e.g., ["team update"]).
        9.  **original_meeting_date_hint**: For "reschedule" or "cancel" intents, extract the date of the original meeting in 'YYYY-MM-DD' format if mentioned.
        10. **original_meeting_time_hint**: For "reschedule" or "cancel" intents, extract the time of the original meeting in 'HH:MM' format if mentioned.

        Input: "{text}"

        Output must be a valid JSON object, and only the JSON object. Do not include any other text or markdown fences like ```json.

        Example 1:
        Input: "Schedule a 45-minute sync with Akash and Raj next Tuesday at 10 AM to discuss project alpha."
        Output: {{
            "intent": "schedule",
            "participants": ["Akash", "Raj"],
            "duration_minutes": 45,
            "time_preferences_raw": "next Tuesday at 10 AM",
            "start_date_hint": "2025-08-26",
            "start_time_hint": "10:00",
            "meeting_title": "project alpha sync",
            "original_meeting_keywords": null,
            "original_meeting_date_hint": null,
            "original_meeting_time_hint": null
        }}

        Example 2:
        Input: "Reschedule my meeting with Nitish for a quick chat this Friday afternoon."
        Output: {{
            "intent": "reschedule",
            "participants": ["Nitish"],
            "duration_minutes": 15,
            "time_preferences_raw": "this Friday afternoon",
            "start_date_hint": "2025-08-29",
            "start_time_hint": "14:00",
            "meeting_title": null,
            "original_meeting_keywords": ["meeting with John"],
            "original_meeting_date_hint": null,
            "original_meeting_time_hint": null
        }}
        
        Example 3:
        Input: "Cancel the 'team update' meeting for today."
        Output: {{
            "intent": "cancel",
            "participants": [],
            "duration_minutes": 30,
            "time_preferences_raw": "for today",
            "start_date_hint": "2025-08-24",
            "start_time_hint": null,
            "meeting_title": "team update",
            "original_meeting_keywords": ["team update"],
            "original_meeting_date_hint": "2025-08-24",
            "original_meeting_time_hint": null
        }}
        
        Example 4:
        Input: "reschedule the meeting with nitish2 which was on 25 august at 9:15 am to 30 aug 3 pm"
        Output: {{
            "intent": "reschedule",
            "participants": ["nitish2"],
            "duration_minutes": 30,
            "time_preferences_raw": "30 aug 3 pm",
            "start_date_hint": "2025-08-30",
            "start_time_hint": "15:00",
            "meeting_title": null,
            "original_meeting_keywords": ["meeting with nitish2"],
            "original_meeting_date_hint": "2025-08-25",
            "original_meeting_time_hint": "09:15"
        }}
        """

        try:
            response = self.model.generate_content(prompt)
            json_string = response.text.strip()
            
            # Clean up potential markdown fences if they appear
            if json_string.startswith('```json'):
                json_string = json_string[7:].strip()
            if json_string.endswith('```'):
                json_string = json_string[:-3].strip()

            parsed_data = json.loads(json_string)
            return parsed_data
        except json.JSONDecodeError as e:
            print(f"JSON Decode Error: {e}")
            print(f"Raw LLM response causing error: '{response.text}'" if 'response' in locals() else "No raw response available.")
            return {"error": "Failed to parse LLM response into JSON.", "details": str(e), "intent": "unknown"}
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
            return {"error": "An unexpected error occurred during NLP parsing.", "details": str(e), "intent": "unknown"}