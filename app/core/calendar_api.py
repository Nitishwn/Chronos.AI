import os
import datetime
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz

SCOPES = ['https://www.googleapis.com/auth/calendar.events', 'https://www.googleapis.com/auth/calendar.readonly']

class GoogleCalendarAPI:
    def __init__(self, user_email: str, oauth_client_secrets_path: str = None, token_path: str = 'token_personal_calendar.json'):
        self.user_email = user_email
        self.creds = None
        self.oauth_client_secrets_path = oauth_client_secrets_path
        self.token_path = token_path
        self._authenticate()
        self.service = build('calendar', 'v3', credentials=self.creds)
        self.pune_timezone = pytz.timezone('Asia/Kolkata')

    def _authenticate(self):
        if os.path.exists(self.token_path):
            self.creds = Credentials.from_authorized_user_file(self.token_path, SCOPES)
        
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                try:
                    self.creds.refresh(Request())
                except Exception as e:
                    raise Exception(f"Failed to refresh calendar token. Please re-authenticate. Error: {e}")
            else:
                raise Exception(
                    f"Calendar token not found or is invalid. Please run the separate authentication script to generate a new token."
                )

    def get_free_busy(self, emails: list, time_min: datetime.datetime, time_max: datetime.datetime) -> dict:
        try:
            time_min_utc = time_min.astimezone(pytz.utc).isoformat()
            time_max_utc = time_max.astimezone(pytz.utc).isoformat()
            
            body = {
                "timeMin": time_min_utc,
                "timeMax": time_max_utc,
                "items": [{"id": email} for email in emails]
            }
            free_busy_result = self.service.freebusy().query(body=body).execute()
            return free_busy_result.get('calendars', {})
        except HttpError as error:
            print(f"An error occurred while fetching free/busy: {error}")
            return {'error': str(error)}
        except Exception as e:
            print(f"An unexpected error occurred in get_free_busy: {e}")
            return {'error': str(e)}

    def create_event(self, summary: str, start_time: datetime.datetime, end_time: datetime.datetime,
                     attendees_emails: list, description: str = "", conference_data_version: int = 1) -> dict:
        try:
            event = {
                'summary': summary,
                'description': description,
                'start': {
                    'dateTime': start_time.isoformat(),
                    'timeZone': str(self.pune_timezone),
                },
                'end': {
                    'dateTime': end_time.isoformat(),
                    'timeZone': str(self.pune_timezone),
                },
                'attendees': [{'email': email} for email in attendees_emails],
                'reminders': {'useDefault': True},
                'conferenceData': {'createRequest': {'requestId': 'meeting-assist-req', 'conferenceSolutionKey': {'type': 'hangoutsMeet'}}},
            }
            event = self.service.events().insert(calendarId='primary', body=event, conferenceDataVersion=conference_data_version, sendNotifications=True).execute()
        
            meet_link = next((entry_point.get('uri') for entry_point in event.get('conferenceData', {}).get('entryPoints', []) if entry_point.get('entryPointType') == 'video'), None)
            
            return {
                "htmlLink": event['htmlLink'],
                "meetLink": meet_link,
                "id": event['id']
            }
        except HttpError as error:
            print(f"An error occurred while creating event: {error}")
            return {"htmlLink": None, "meetLink": None, "id": None, "error": str(error)}
        except Exception as e:
            print(f"An unexpected error occurred in create_event: {e}")
            return {"htmlLink": None, "meetLink": None, "id": None, "error": str(e)}

    def get_event(self, event_id: str) -> dict:
        try:
            return self.service.events().get(calendarId='primary', eventId=event_id).execute()
        except HttpError as error:
            print(f"An error occurred while fetching event {event_id}: {error}")
            return None
        except Exception as e:
            print(f"An unexpected error occurred in get_event: {e}")
            return None

    def update_event(self, event_id: str, summary: str = None, start_time: datetime.datetime = None,
                     end_time: datetime.datetime = None, attendees_emails: list = None, description: str = None) -> dict:
        try:
            event = self.get_event(event_id)
            if not event:
                raise Exception("Event not found.")

            if summary: event['summary'] = summary
            if start_time:
                event['start']['dateTime'] = start_time.isoformat()
                event['start']['timeZone'] = str(self.pune_timezone)
            if end_time:
                event['end']['dateTime'] = end_time.isoformat()
                event['end']['timeZone'] = str(self.pune_timezone)
            if attendees_emails:
                event['attendees'] = [{'email': email} for email in attendees_emails]
            if description is not None:
                event['description'] = description

            updated_event = self.service.events().update(calendarId='primary', eventId=event_id, body=event, sendNotifications=True).execute()
            
            meet_link = next((entry_point.get('uri') for entry_point in updated_event.get('conferenceData', {}).get('entryPoints', []) if entry_point.get('entryPointType') == 'video'), None)

            return {
                "htmlLink": updated_event['htmlLink'],
                "meetLink": meet_link,
                "id": updated_event['id']
            }
        except HttpError as error:
            print(f"An error occurred while updating event: {error}")
            return {"htmlLink": None, "meetLink": None, "id": None, "error": str(error)}
        except Exception as e:
            print(f"An unexpected error occurred in update_event: {e}")
            return {"htmlLink": None, "meetLink": None, "id": None, "error": str(e)}

    def delete_event(self, event_id: str) -> dict:
        try:
            self.service.events().delete(calendarId='primary', eventId=event_id, sendNotifications=True).execute()
            return {"status": "success"}
        except HttpError as error:
            print(f"An error occurred while deleting event: {error}")
            return {"status": "error", "error": str(error)}
        except Exception as e:
            print(f"An unexpected error occurred in delete_event: {e}")
            return {"status": "error", "error": str(e)}
    
    def get_events(self, time_min: datetime.datetime = None, time_max: datetime.datetime = None, query: str = None) -> list:
        try:
            time_min_iso = time_min.astimezone(pytz.utc).isoformat() if time_min else datetime.datetime.utcnow().isoformat() + 'Z'
            time_max_iso = time_max.astimezone(pytz.utc).isoformat() if time_max else None

            events_result = self.service.events().list(
                calendarId='primary',
                timeMin=time_min_iso,
                timeMax=time_max_iso,
                q=query,
                singleEvents=True,
                orderBy='startTime'
            ).execute()
            events = events_result.get('items', [])
            return events
        except HttpError as error:
            print(f"An error occurred while fetching events: {error}")
            return []
        except Exception as e:
            print(f"An unexpected error occurred in get_events: {e}")
            return []