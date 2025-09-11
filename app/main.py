import os
import json
import ssl
from datetime import datetime, timedelta
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

if os.getenv('DISABLE_SSL_VERIFICATION', 'False').lower() == 'true':
    ssl._create_default_https_context = ssl._create_unverified_context
    print("SSL verification disabled.")

from app.core.agent import MeetingAgent
from app.core.directory_api import GoogleDirectoryAPI # Import the updated Directory API

app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app)

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OAUTH_CLIENT_SECRETS_PATH = os.getenv("OAUTH_CLIENT_SECRETS_PATH")
GMAIL_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH")
CALENDAR_TOKEN_PATH = os.getenv("CALENDAR_TOKEN_PATH", "token_personal_calendar.json")
USER_EMAIL = os.getenv("YOUR_COLLEGE_EMAIL_ID_FOR_TESTING")
MEETING_TIMEZONE = os.getenv("MEETING_TIMEZONE", 'Asia/Kolkata')

try:
    # --- CHANGE START ---
    # First, initialize the GoogleDirectoryAPI instance
    directory_api = GoogleDirectoryAPI()

    # Then, initialize the MeetingAgent and pass the directory_api instance to it
    meeting_agent = MeetingAgent(
        api_key=GEMINI_API_KEY,
        oauth_client_secrets_path=OAUTH_CLIENT_SECRETS_PATH,
        gmail_token_path=GMAIL_TOKEN_PATH,
        calendar_token_path=CALENDAR_TOKEN_PATH,
        user_email=USER_EMAIL,
        timezone=MEETING_TIMEZONE,
        directory_api=directory_api # Pass the initialized object
    )
    print("MeetingAgent and DirectoryAPI initialized successfully.")
except Exception as e:
    print(f"Failed to initialize MeetingAgent: {e}")
    meeting_agent = None

@app.route('/')
def serve_frontend():
    return send_file('book-meeting-frontend.html')

@app.route('/process_query', methods=['POST'])
def process_query():
    if not meeting_agent:
        return jsonify({"status": "error", "message": "Backend not initialized. Check server logs for errors."}), 500

    user_query = request.json.get('query')
    if not user_query:
        return jsonify({"status": "error", "message": "No query provided."}), 400

    print(f"Received query: {user_query}")
    response_data = meeting_agent.process_meeting_request(user_query)
    print(f"Sending response: {response_data}")
    return jsonify(response_data)

@app.route('/meetings', methods=['POST'])
def handle_meetings():
    if not meeting_agent:
        return jsonify({"status": "error", "message": "Backend not initialized. Check server logs for errors."}), 500

    try:
        data = request.json
        print(f"handle_meetings endpoint received raw JSON data: {data}")
        action = data.get('action')
        
        if action == 'schedule':
            summary = data.get('summary')
            attendees_raw = data.get('attendees', '')
            start_time_iso = data.get('startTime')
            end_time_iso = data.get('endTime')
            description = data.get('description', '')

            if not all([summary, attendees_raw, start_time_iso, end_time_iso]):
                return jsonify({"status": "error", "message": "Missing required fields for scheduling."}), 400
        
            attendees_emails = [email.strip() for email in attendees_raw.split(',') if email.strip()]
            if not attendees_emails:
                return jsonify({"status": "error", "message": "No valid attendees emails provided."}), 400
            
            print(f"handle_meetings: action=schedule, summary='{summary}', attendees='{attendees_emails}', start='{start_time_iso}', end='{end_time_iso}'")
            result = meeting_agent.schedule_meeting(summary, attendees_emails, start_time_iso, end_time_iso, description)
            print(f"Scheduling result: {result}")
            return jsonify(result)
        
        elif action == 'update':
            event_id = data.get('eventId')
            summary = data.get('summary')
            attendees_raw = data.get('attendees', '')
            start_time_iso = data.get('startTime')
            end_time_iso = data.get('endTime')
            description = data.get('description')
            dry_run = data.get('dry_run', False)

            if not event_id:
                return jsonify({"status": "error", "message": "Event ID is required for updating."}), 400

            attendees_emails = [email.strip() for email in attendees_raw.split(',') if email.strip()] if attendees_raw else None

            print(f"handle_meetings: action=update, dry_run={dry_run}, event_id='{event_id}', summary='{summary}', attendees='{attendees_emails}', start='{start_time_iso}', end='{end_time_iso}'")
            result = meeting_agent.update_meeting(event_id, summary, attendees_emails, start_time_iso, end_time_iso, description, dry_run=dry_run)
            print(f"Update result: {result}")
            return jsonify(result)

        elif action == 'cancel':
            event_id = data.get('eventId')

            if not event_id:
                return jsonify({"status": "error", "message": "Event ID is required for canceling."}), 400
            
            print(f"handle_meetings: action=cancel, event_id='{event_id}'")
            result = meeting_agent.cancel_meeting(event_id)
            print(f"Cancellation result: {result}")
            return jsonify(result)

        else:
            print(f"handle_meetings: Invalid action '{action}' specified.")
            return jsonify({"status": "error", "message": f"Invalid action specified: {action}"}), 400

    except Exception as e:
        print(f"handle_meetings: An unexpected error occurred: {e}")
        return jsonify({"status": "error", "message": f"An unexpected error occurred: {e}"}), 500

@app.route('/list_upcoming_events', methods=['GET'])
def list_upcoming_events():
    if not meeting_agent:
        return jsonify({"status": "error", "message": "Backend not initialized. Check server logs for errors."}), 500

    try:
        now = datetime.now(meeting_agent.pune_timezone)
        thirty_days_later = now + timedelta(days=30)
        events = meeting_agent.calendar_api.get_events(time_min=now, time_max=thirty_days_later)

        cleaned_events = []
        for event in events:
            attendees = [a.get('email', '') for a in event.get('attendees', []) if 'email' in a]
            
            cleaned_events.append({
                "id": event['id'],
                "summary": event.get('summary', 'No Title'),
                "start": event['start'].get('dateTime', event['start'].get('date')),
                "end": event['end'].get('dateTime', event['end'].get('date')),
                "htmlLink": event['htmlLink'],
                "attendees": attendees,
                "description": event.get('description', '')
            })
        return jsonify({"status": "success", "events": cleaned_events})

    except Exception as e:
        print(f"Error listing upcoming events: {e}")
        return jsonify({"status": "error", "message": f"Failed to retrieve events: {e}"}), 500


@app.route('/contacts', methods=['GET', 'POST', 'DELETE'])
def manage_contacts():
    global directory_api
    if request.method == 'GET':
        contacts = directory_api.list_contacts()
        return jsonify({"status": "success", "contacts": contacts})
    
    elif request.method == 'POST':
        data = request.json
        email = data.get('email')
        display_name = data.get('displayName')
        if not email or not display_name:
            return jsonify({"status": "error", "message": "Email and display name are required."}), 400
        result = directory_api.add_contact(email, display_name)
        return jsonify(result)
    
    elif request.method == 'DELETE':
        data = request.json
        email = data.get('email')
        if not email:
            return jsonify({"status": "error", "message": "Email is required for deletion."}), 400
        result = directory_api.delete_contact(email)
        return jsonify(result)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)