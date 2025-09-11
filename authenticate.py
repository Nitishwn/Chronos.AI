import os.path
import pickle
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

# If modifying these scopes, delete the token_personal_calendar.json and token_personal_gmail.json files
CALENDAR_SCOPES = ['https://www.googleapis.com/auth/calendar.events']
GMAIL_SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def generate_token(token_file, client_secret_file, scopes):
    creds = None
    if os.path.exists(token_file):
        creds = Credentials.from_authorized_user_file(token_file, scopes)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(client_secret_file, scopes)
            creds = flow.run_local_server(port=0)

        with open(token_file, 'w') as token:
            token.write(creds.to_json())

    print(f"Token generated and saved to {token_file}")

if __name__ == '__main__':
    # Generate token for Google Calendar API
    print("Generating token for Google Calendar...")
    generate_token('token_personal_calendar.json', 'client_secret_personal_calendar.json', CALENDAR_SCOPES)
    print("-" * 20)

    # Generate token for Gmail API
    print("Generating token for Gmail...")
    generate_token('token_personal_gmail.json', 'client_secret_personal_calendar.json', GMAIL_SCOPES)
    print("-" * 20)