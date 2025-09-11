import os
import base64
from email.mime.text import MIMEText
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import traceback

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

class GmailAPI:
    def __init__(self, user_email: str = 'me', oauth_client_secrets_path: str = None, token_path: str = 'token_personal_gmail.json'):
        self.user_email = user_email
        self.creds = None
        self.oauth_client_secrets_path = oauth_client_secrets_path
        self.token_path = token_path
        self._authenticate()
        self.service = build('gmail', 'v1', credentials=self.creds)

    def _authenticate(self):
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)

        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    raise Exception(f"Failed to refresh Gmail token. Please re-authenticate. Error: {e}")
            else:
                raise Exception(
                    f"Gmail token not found or is invalid. Please run the separate authentication script to generate a new token."
                )

    def send_email(self, to_emails: list, subject: str, message_text: str, sender_email: str = None) -> dict:
        try:
            message = MIMEText(message_text)
            message['to'] = ', '.join(to_emails)
            message['subject'] = subject
            if sender_email:
                message['from'] = sender_email
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            body = {'raw': raw_message}

            sent_message = self.service.users().messages().send(userId=self.user_email, body=body).execute()
            print(f"Email sent! Message Id: {sent_message['id']}")
            return {"status": "success", "messageId": sent_message['id']}
        except HttpError as error:
            print(f"An error occurred while sending email: {error}")
            return {"status": "error", "error": str(error)}
        except Exception as e:
            print(f"An unexpected error occurred in send_email: {e}")
            traceback.print_exc()
            return {"status": "error", "error": str(e)}