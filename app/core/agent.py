import os
from datetime import datetime, timedelta
import pytz
import traceback
import json

from app.core.nlp_parser import NLPParser
from app.core.calendar_api import GoogleCalendarAPI
from app.core.directory_api import GoogleDirectoryAPI
from app.core.gmail_api import GmailAPI

class MeetingAgent:
    def __init__(self, api_key: str, oauth_client_secrets_path: str, user_email: str, gmail_token_path: str, calendar_token_path: str = 'token_personal_calendar.json', timezone: str = 'Asia/Kolkata', directory_api: GoogleDirectoryAPI = None):
        """Initializes the MeetingAgent with all necessary API clients."""
        self.nlp_parser = NLPParser(api_key=api_key)
        self.directory_api = directory_api if directory_api else GoogleDirectoryAPI()
        self.calendar_api = GoogleCalendarAPI(user_email=user_email, oauth_client_secrets_path=oauth_client_secrets_path, token_path=calendar_token_path)
        self.gmail_api = GmailAPI(user_email='me', oauth_client_secrets_path=oauth_client_secrets_path, token_path=gmail_token_path)
        self.user_email = user_email
        self.pune_timezone = pytz.timezone(timezone)

    def _resolve_participants(self, participants_names: list) -> list:
        """
        Resolves a list of participant names or emails to a canonical list of emails.
        Prioritizes a match from the user's contacts before falling back to a guess.
        """
        resolved_emails = []
        all_contacts = self.directory_api.list_contacts()
        contacts_by_name = {contact['displayName'].lower(): contact for contact in all_contacts}
        contacts_by_email = {contact['primaryEmail'].lower(): contact for contact in all_contacts}
        
        for name_or_email in participants_names:
            normalized_input = name_or_email.lower().strip()
            found = False

            # Check for exact email match first
            if "@" in normalized_input and normalized_input in contacts_by_email:
                resolved_emails.append(contacts_by_email[normalized_input])
                found = True
            
            # Check for a display name match from our contacts
            elif normalized_input in contacts_by_name:
                resolved_emails.append(contacts_by_name[normalized_input])
                found = True
            
            # Fallback to the original logic if no contacts match
            if not found:
                print(f"Warning: Could not find user for name '{name_or_email}' in contacts. Using original logic.")
                
                # Check for partial match in our contacts
                found_by_partial_search = self.directory_api.search_users(name_or_email)
                if found_by_partial_search:
                    resolved_emails.append(found_by_partial_search[0])
                    found = True
            
            # Final fallback to a generic email guess
            if not found:
                print(f"Warning: No match found. Defaulting to @gmail.com.")
                resolved_emails.append({"primaryEmail": f"{normalized_input.replace(' ', '')}@gmail.com", "displayName": name_or_email})

        # Add the user's own email if not already present
        if not any(self.user_email.lower() == p.get('primaryEmail', '').lower() for p in resolved_emails):
            resolved_emails.insert(0, {"primaryEmail": self.user_email, "displayName": "You"})
        
        return resolved_emails

    def process_meeting_request(self, query: str) -> dict:
        parsed_data = self.nlp_parser.parse_meeting_request(query)
    
        if parsed_data.get("error"):
            return {"status": "error", "message": parsed_data.get("error"), "parsed_data": parsed_data}

        intent = parsed_data.get("intent")
        participants_raw = parsed_data.get("participants", [])
        duration_minutes = parsed_data.get("duration_minutes")
    
        resolved_participants = self._resolve_participants(participants_raw)
        participant_emails = [p['primaryEmail'] for p in resolved_participants]

        response_payload = {
            "status": "success",
            "parsed_data": parsed_data,
            "resolved_participants": resolved_participants,
            "suggested_slots": [],
            "message": "Query parsed successfully."
        }
    
        if intent == "schedule":
            start_date_hint = parsed_data.get("start_date_hint")
            start_time_hint = parsed_data.get("start_time_hint")

            if duration_minutes and start_date_hint and start_time_hint:
                try:
                    start_dt_str = f"{start_date_hint} {start_time_hint}"
                    start_dt_naive = datetime.strptime(start_dt_str, '%Y-%m-%d %H:%M')
                    start_dt_localized = self.pune_timezone.localize(start_dt_naive)
                    end_dt_localized = start_dt_localized + timedelta(minutes=duration_minutes)

                    free_busy = self.calendar_api.get_free_busy(participant_emails, start_dt_localized, end_dt_localized)
                
                    is_available = True
                    for email in participant_emails:
                        if email in free_busy and free_busy[email].get('busy'):
                            is_available = False
                            break
                
                    if is_available:
                        response_payload["message"] = "Proposed time looks available. Confirm to schedule."
                        response_payload["suggested_slots"] = [{
                            "start": {"dateTime": start_dt_localized.isoformat()},
                            "end": {"dateTime": end_dt_localized.isoformat()}
                        }]
                        response_payload["initial_meeting_details"] = {
                            "summary": parsed_data.get("meeting_title", "New Meeting"),
                            "attendees": ", ".join(participant_emails),
                            "startTime": start_dt_localized.isoformat(),
                            "endTime": end_dt_localized.isoformat(),
                            "description": "Meeting scheduled via Book Meeting Assistant."
                        }
                    else:
                        response_payload["message"] = "Proposed time is busy. Looking for alternatives."
                        response_payload["suggested_slots"] = self._find_suggested_slots(participant_emails, duration_minutes, start_dt_localized)

                except Exception as e:
                    print(f"Error processing direct schedule attempt: {e}")
                    traceback.print_exc()
                    response_payload["message"] = f"Error processing direct schedule attempt. Looking for suggestions."
                    response_payload["suggested_slots"] = self._find_suggested_slots(participant_emails, duration_minutes)

            elif duration_minutes and (start_date_hint or start_time_hint):
                response_payload["message"] = "Looking for available time slots."
                response_payload["suggested_slots"] = self._find_suggested_slots(participant_emails, duration_minutes)
            else:
                response_payload["message"] = "Not enough information to find specific slots. Please provide duration and/or time preferences. You can fill out details manually."
                response_payload["initial_meeting_details"] = {
                    "summary": parsed_data.get("meeting_title", "New Meeting"),
                    "attendees": ", ".join(participant_emails),
                    "startTime": None,
                    "endTime": None,
                    "description": "Meeting request: " + query
                }

        elif intent in ["reschedule", "cancel"]:
            original_date_hint = parsed_data.get("original_meeting_date_hint")
            original_time_hint = parsed_data.get("original_meeting_time_hint")
            
            if original_date_hint and original_time_hint:
                try:
                    original_dt_str = f"{original_date_hint}T{original_time_hint}"
                    original_dt_naive = datetime.strptime(original_dt_str, '%Y-%m-%dT%H:%M')
                    original_dt_localized = self.pune_timezone.localize(original_dt_naive)
                    
                    time_min = original_dt_localized - timedelta(minutes=1)
                    time_max = original_dt_localized + timedelta(minutes=1)

                    query_str = " ".join(parsed_data.get("original_meeting_keywords", [])) or parsed_data.get("meeting_title", "")
                    
                    matching_events = self.calendar_api.get_events(time_min=time_min, time_max=time_max, query=query_str)
                
                    if not matching_events:
                        response_payload["message"] = f"Could not find a meeting to {intent}. Please provide more specific keywords or a date."
                        response_payload["status"] = "info"
                        return response_payload
                    else:
                        event_to_manage = matching_events[0]
                        
                        if intent == "reschedule":
                            new_start_dt = None
                            new_end_dt = None
                            
                            start_date_hint = parsed_data.get("start_date_hint")
                            start_time_hint = parsed_data.get("start_time_hint")

                            if start_date_hint and start_time_hint:
                                new_start_dt_str = f"{start_date_hint} {start_time_hint}"
                                new_start_dt_naive = datetime.strptime(new_start_dt_str, '%Y-%m-%d %H:%M')
                                new_start_dt = self.pune_timezone.localize(new_start_dt_naive)
                                
                                inferred_duration = int((datetime.fromisoformat(event_to_manage['end']['dateTime']) - datetime.fromisoformat(event_to_manage['start']['dateTime'])).total_seconds() / 60)
                                new_end_dt = new_start_dt + timedelta(minutes=inferred_duration)

                                free_busy = self.calendar_api.get_free_busy([e.get('email', '') for e in event_to_manage.get('attendees', []) if 'email' in e], new_start_dt, new_end_dt)
                                
                                is_available = True
                                for email in [e.get('email', '') for e in event_to_manage.get('attendees', []) if 'email' in e]:
                                    if email in free_busy and free_busy[email].get('busy'):
                                        is_available = False
                                        break
                                
                                if is_available:
                                    response_payload["status"] = "confirmation"
                                    response_payload["message"] = "Proposed time is available. Please confirm."
                                    response_payload["confirmation_details"] = {
                                        "intent": intent,
                                        "original": {
                                            "id": event_to_manage['id'],
                                            "summary": event_to_manage.get('summary', ''),
                                            "start": event_to_manage['start'].get('dateTime', ''),
                                            "end": event_to_manage['end'].get('dateTime', ''),
                                            "attendees": [a.get('email', '') for a in event_to_manage.get('attendees', []) if 'email' in a]
                                        },
                                        "new": {
                                            "summary": event_to_manage.get('summary', ''),
                                            "start": new_start_dt.isoformat(),
                                            "end": new_end_dt.isoformat(),
                                            "attendees": [a.get('email', '') for a in event_to_manage.get('attendees', []) if 'email' in a]
                                        }
                                    }
                                    return response_payload
                                else:
                                    attendees_for_search = [a.get('email', '') for a in event_to_manage.get('attendees', []) if 'email' in a]
                                    suggested_slots = self._find_suggested_slots(attendees_for_search, inferred_duration, new_start_dt)
                                    response_payload["message"] = "Proposed time is busy. Here are some alternative slots."
                                    response_payload["status"] = "info"
                                    response_payload["suggested_slots"] = suggested_slots
                                    return response_payload
                                
                            else:
                                response_payload["message"] = f"Found a matching meeting. Please provide a new date and time for rescheduling."
                                response_payload["status"] = "info"
                                response_payload["existing_meetings"] = [{
                                    "id": event['id'],
                                    "summary": event.get('summary'),
                                    "start": event['start'].get('dateTime', event['start'].get('date')),
                                    "end": event['end'].get('dateTime', event['end'].get('date')),
                                    "htmlLink": event['htmlLink'],
                                    "attendees": [a.get('email', '') for a in event.get('attendees', []) if 'email' in a]
                                } for event in matching_events]
                                return response_payload
                                
                        elif intent == "cancel":
                             response_payload["status"] = "confirmation"
                             response_payload["message"] = "Please confirm cancellation."
                             response_payload["confirmation_details"] = {
                                 "intent": intent,
                                 "original": {
                                     "id": event_to_manage['id'],
                                     "summary": event_to_manage.get('summary', ''),
                                     "start": event_to_manage['start'].get('dateTime', ''),
                                     "end": event_to_manage['end'].get('dateTime', ''),
                                     "attendees": [a.get('email', '') for a in event_to_manage.get('attendees', []) if 'email' in a]
                                 }
                             }
                             return response_payload
                
                except ValueError:
                    response_payload["message"] = f"Could not parse the original meeting date and time. Please use a format like 'YYYY-MM-DD HH:MM'."
                    response_payload["status"] = "info"
                    return response_payload

            else:
                response_payload["message"] = f"Please provide both the date and time of the meeting you want to {intent}."
                response_payload["status"] = "info"
                return response_payload


        elif intent == "unknown":
            response_payload["status"] = "info"
            response_payload["message"] = "I couldn't understand your request. Please try rephrasing or provide more details for scheduling, rescheduling, or canceling a meeting. You can also fill out details manually below."
            response_payload["initial_meeting_details"] = {
                "summary": parsed_data.get("meeting_title", "New Meeting"),
                "attendees": ", ".join(participant_emails),
                "startTime": None,
                "endTime": None,
                "description": "Meeting request: " + query
            }

        return response_payload
    def _find_suggested_slots(self, participant_emails: list, duration_minutes: int, search_start_time: datetime = None) -> list:
        suggested_slots = []
        now = datetime.now(self.pune_timezone)
        
        search_start_time = search_start_time if search_start_time and search_start_time > now else now
        
        # Round up to the next 15-minute interval
        if search_start_time.minute % 15 != 0:
            search_start_time = search_start_time + timedelta(minutes=(15 - search_start_time.minute % 15))
            search_start_time = search_start_time.replace(second=0, microsecond=0)

        for i in range(7):
            current_day_start = search_start_time + timedelta(days=i)
            day_start_limit = current_day_start.replace(hour=9, minute=0, second=0, microsecond=0)
            day_end_limit = current_day_start.replace(hour=17, minute=0, second=0, microsecond=0)

            if current_day_start.date() == now.date() and current_day_start > day_start_limit:
                day_start_limit = current_day_start

            if day_start_limit >= day_end_limit:
                continue

            free_busy_info = self.calendar_api.get_free_busy(participant_emails, day_start_limit, day_end_limit)

            occupied_slots = []
            for email in participant_emails:
                for busy_period in free_busy_info.get(email, {}).get('busy', []):
                    busy_start = datetime.fromisoformat(busy_period['start']).astimezone(self.pune_timezone)
                    busy_end = datetime.fromisoformat(busy_period['end']).astimezone(self.pune_timezone)
                    occupied_slots.append({'start': busy_start, 'end': busy_end})
            
            occupied_slots.sort(key=lambda x: x['start'])
            merged_occupied = []
            if occupied_slots:
                current_merge = occupied_slots[0]
                for j in range(1, len(occupied_slots)):
                    if occupied_slots[j]['start'] <= current_merge['end']:
                        current_merge['end'] = max(current_merge['end'], occupied_slots[j]['end'])
                    else:
                        merged_occupied.append(current_merge)
                        current_merge = occupied_slots[j]
                merged_occupied.append(current_merge)

            current_time = day_start_limit
            while current_time + timedelta(minutes=duration_minutes) <= day_end_limit:
                is_free = True
                proposed_end_time = current_time + timedelta(minutes=duration_minutes)
            
                for occupied in merged_occupied:
                    if current_time < occupied['end'] and proposed_end_time > occupied['start']:
                        is_free = False
                        current_time = occupied['end']
                        break
            
                if is_free:
                    if current_time >= day_start_limit and proposed_end_time <= day_end_limit:
                        suggested_slots.append({
                            "start": {"dateTime": current_time.isoformat()},
                            "end": {"dateTime": proposed_end_time.isoformat()}
                        })
                    current_time += timedelta(minutes=15)

                if len(suggested_slots) >= 5:
                    return suggested_slots
    
        return suggested_slots

    def schedule_meeting(self, summary: str, attendees_emails: list, start_time_iso: str, end_time_iso: str, description: str = "") -> dict:
        try:
            start_time = datetime.fromisoformat(start_time_iso).astimezone(self.pune_timezone)
            end_time = datetime.fromisoformat(end_time_iso).astimezone(self.pune_timezone)
        
            if not attendees_emails or not all(email for email in attendees_emails):
                raise ValueError("Attendee emails cannot be empty.")

            event_result = self.calendar_api.create_event(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                attendees_emails=attendees_emails,
                description=description
            )
        
            if event_result and event_result.get("htmlLink"):
                email_subject = f"Meeting Confirmation: {summary}"
                email_body = f"Hi,\n\nYour meeting '{summary}' has been scheduled.\n\n" \
                                f"Time: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} ({start_time.strftime('%Z')})\n" \
                                f"Attendees: {', '.join(attendees_emails)}\n" \
                                f"Description: {description or 'N/A'}\n" \
                                f"Calendar Link: {event_result['htmlLink']}\n" \
                                f"Meet Link: {event_result['meetLink'] or 'N/A'}\n\n" \
                                "Thank you."
            
                self.gmail_api.send_email(to_emails=attendees_emails, subject=email_subject, message_text=email_body)

                return {"status": "success", "message": f"Meeting scheduled and email sent!",
                        "calendar_link": event_result['htmlLink'], "meet_link": event_result['meetLink'],
                        "event_id": event_result['id']}
            else:
                return {"status": "error", "message": event_result.get("error", "Failed to create calendar event. Unknown error.")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Error scheduling meeting: {e}"}

    def update_meeting(self, event_id: str, summary: str = None, attendees_emails: list = None,
                       start_time_iso: str = None, end_time_iso: str = None, description: str = None, dry_run: bool = False) -> dict:
        try:
            start_time = datetime.fromisoformat(start_time_iso).astimezone(self.pune_timezone) if start_time_iso else None
            end_time = datetime.fromisoformat(end_time_iso).astimezone(self.pune_timezone) if end_time_iso else None
            
            if dry_run and start_time and end_time:
                if not attendees_emails:
                    original_event = self.calendar_api.get_event(event_id)
                    if not original_event:
                        return {"status": "error", "message": "Original event not found for dry run."}
                    attendees_emails = [a.get('email', '') for a in original_event.get('attendees', []) if 'email' in a]

                free_busy = self.calendar_api.get_free_busy(attendees_emails, start_time, end_time)
                
                is_available = True
                for email in attendees_emails:
                    if email in free_busy and free_busy[email].get('busy'):
                        is_available = False
                        break
                        
                if is_available:
                    return {"status": "success", "message": "Proposed time is available."}
                else:
                    duration_minutes = int((end_time - start_time).total_seconds() / 60)
                    suggested_slots = self._find_suggested_slots(
                        attendees_emails,
                        duration_minutes,
                        start_time
                    )
                    return {
                        "status": "conflict",
                        "message": "The proposed time is busy. Here are some alternative slots.",
                        "suggested_slots": suggested_slots
                    }

            event_result = self.calendar_api.update_event(
                event_id=event_id,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                attendees_emails=attendees_emails,
                description=description
            )
            
            # --- START of new email notification logic ---
            if event_result and event_result.get("htmlLink"):
                email_subject = f"Rescheduled: {summary}"
                email_body = f"Hi,\n\nYour meeting '{summary}' has been successfully rescheduled.\n\n" \
                                f"New Time: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} ({start_time.strftime('%Z')})\n" \
                                f"Attendees: {', '.join(attendees_emails)}\n" \
                                f"Description: {description or 'N/A'}\n" \
                                f"Calendar Link: {event_result['htmlLink']}\n" \
                                f"Meet Link: {event_result['meetLink'] or 'N/A'}\n\n" \
                                "Thank you."
                
                self.gmail_api.send_email(to_emails=attendees_emails, subject=email_subject, message_text=email_body)

                return {"status": "success", "message": f"Meeting updated and email sent!",
                        "calendar_link": event_result['htmlLink'], "meet_link": event_result['meetLink'],
                        "event_id": event_result['id']}
            # --- END of new email notification logic ---
            else:
                return {"status": "error", "message": event_result.get("error", "Failed to update calendar event.")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Error updating meeting: {e}"}

    def cancel_meeting(self, event_id: str) -> dict:
        try:
            result = self.calendar_api.delete_event(event_id)
            if result.get("status") == "success":
                return {"status": "success", "message": "Meeting cancelled!"}
            else:
                return {"status": "error", "message": result.get("error", "Failed to cancel calendar event.")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Error cancelling meeting: {e}"}

    def _find_suggested_slots(self, participant_emails: list, duration_minutes: int, search_start_time: datetime = None) -> list:
        suggested_slots = []
        now = datetime.now(self.pune_timezone)
        
        search_start_time = search_start_time if search_start_time and search_start_time > now else now
        
        # Round up to the next 15-minute interval
        if search_start_time.minute % 15 != 0:
            search_start_time = search_start_time + timedelta(minutes=(15 - search_start_time.minute % 15))
            search_start_time = search_start_time.replace(second=0, microsecond=0)

        for i in range(7):
            current_day_start = search_start_time + timedelta(days=i)
            day_start_limit = current_day_start.replace(hour=9, minute=0, second=0, microsecond=0)
            day_end_limit = current_day_start.replace(hour=17, minute=0, second=0, microsecond=0)

            if current_day_start.date() == now.date() and current_day_start > day_start_limit:
                day_start_limit = current_day_start

            if day_start_limit >= day_end_limit:
                continue

            free_busy_info = self.calendar_api.get_free_busy(participant_emails, day_start_limit, day_end_limit)

            occupied_slots = []
            for email in participant_emails:
                for busy_period in free_busy_info.get(email, {}).get('busy', []):
                    busy_start = datetime.fromisoformat(busy_period['start']).astimezone(self.pune_timezone)
                    busy_end = datetime.fromisoformat(busy_period['end']).astimezone(self.pune_timezone)
                    occupied_slots.append({'start': busy_start, 'end': busy_end})
            
            occupied_slots.sort(key=lambda x: x['start'])
            merged_occupied = []
            if occupied_slots:
                current_merge = occupied_slots[0]
                for j in range(1, len(occupied_slots)):
                    if occupied_slots[j]['start'] <= current_merge['end']:
                        current_merge['end'] = max(current_merge['end'], occupied_slots[j]['end'])
                    else:
                        merged_occupied.append(current_merge)
                        current_merge = occupied_slots[j]
                merged_occupied.append(current_merge)

            current_time = day_start_limit
            while current_time + timedelta(minutes=duration_minutes) <= day_end_limit:
                is_free = True
                proposed_end_time = current_time + timedelta(minutes=duration_minutes)
            
                for occupied in merged_occupied:
                    if current_time < occupied['end'] and proposed_end_time > occupied['start']:
                        is_free = False
                        current_time = occupied['end']
                        break
            
                if is_free:
                    if current_time >= day_start_limit and proposed_end_time <= day_end_limit:
                        suggested_slots.append({
                            "start": {"dateTime": current_time.isoformat()},
                            "end": {"dateTime": proposed_end_time.isoformat()}
                        })
                    current_time += timedelta(minutes=15)

                if len(suggested_slots) >= 5:
                    return suggested_slots
    
        return suggested_slots

    def schedule_meeting(self, summary: str, attendees_emails: list, start_time_iso: str, end_time_iso: str, description: str = "") -> dict:
        try:
            start_time = datetime.fromisoformat(start_time_iso).astimezone(self.pune_timezone)
            end_time = datetime.fromisoformat(end_time_iso).astimezone(self.pune_timezone)
        
            if not attendees_emails or not all(email for email in attendees_emails):
                raise ValueError("Attendee emails cannot be empty.")

            event_result = self.calendar_api.create_event(
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                attendees_emails=attendees_emails,
                description=description
            )
        
            if event_result and event_result.get("htmlLink"):
                email_subject = f"Meeting Confirmation: {summary}"
                email_body = f"Hi,\n\nYour meeting '{summary}' has been scheduled.\n\n" \
                                f"Time: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} ({start_time.strftime('%Z')})\n" \
                                f"Attendees: {', '.join(attendees_emails)}\n" \
                                f"Description: {description or 'N/A'}\n" \
                                f"Calendar Link: {event_result['htmlLink']}\n" \
                                f"Meet Link: {event_result['meetLink'] or 'N/A'}\n\n" \
                                "Thank you."
            
                self.gmail_api.send_email(to_emails=attendees_emails, subject=email_subject, message_text=email_body)

                return {"status": "success", "message": f"Meeting scheduled and email sent!",
                        "calendar_link": event_result['htmlLink'], "meet_link": event_result['meetLink'],
                        "event_id": event_result['id']}
            else:
                return {"status": "error", "message": event_result.get("error", "Failed to create calendar event. Unknown error.")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Error scheduling meeting: {e}"}

    def update_meeting(self, event_id: str, summary: str = None, attendees_emails: list = None,
                       start_time_iso: str = None, end_time_iso: str = None, description: str = None, dry_run: bool = False) -> dict:
        try:
            start_time = datetime.fromisoformat(start_time_iso).astimezone(self.pune_timezone) if start_time_iso else None
            end_time = datetime.fromisoformat(end_time_iso).astimezone(self.pune_timezone) if end_time_iso else None
            
            if dry_run and start_time and end_time:
                if not attendees_emails:
                    original_event = self.calendar_api.get_event(event_id)
                    if not original_event:
                        return {"status": "error", "message": "Original event not found for dry run."}
                    attendees_emails = [a.get('email', '') for a in original_event.get('attendees', []) if 'email' in a]

                free_busy = self.calendar_api.get_free_busy(attendees_emails, start_time, end_time)
                
                is_available = True
                for email in attendees_emails:
                    if email in free_busy and free_busy[email].get('busy'):
                        is_available = False
                        break
                        
                if is_available:
                    return {"status": "success", "message": "Proposed time is available."}
                else:
                    duration_minutes = int((end_time - start_time).total_seconds() / 60)
                    suggested_slots = self._find_suggested_slots(
                        attendees_emails,
                        duration_minutes,
                        start_time
                    )
                    return {
                        "status": "conflict",
                        "message": "The proposed time is busy. Here are some alternative slots.",
                        "suggested_slots": suggested_slots
                    }

            event_result = self.calendar_api.update_event(
                event_id=event_id,
                summary=summary,
                start_time=start_time,
                end_time=end_time,
                attendees_emails=attendees_emails,
                description=description
            )
            
            # --- START of new email notification logic ---
            if event_result and event_result.get("htmlLink"):
                email_subject = f"Rescheduled: {summary}"
                email_body = f"Hi,\n\nYour meeting '{summary}' has been successfully rescheduled.\n\n" \
                                f"New Time: {start_time.strftime('%Y-%m-%d %H:%M')} to {end_time.strftime('%H:%M')} ({start_time.strftime('%Z')})\n" \
                                f"Attendees: {', '.join(attendees_emails)}\n" \
                                f"Description: {description or 'N/A'}\n" \
                                f"Calendar Link: {event_result['htmlLink']}\n" \
                                f"Meet Link: {event_result['meetLink'] or 'N/A'}\n\n" \
                                "Thank you."
                
                self.gmail_api.send_email(to_emails=attendees_emails, subject=email_subject, message_text=email_body)

                return {"status": "success", "message": f"Meeting updated and email sent!",
                        "calendar_link": event_result['htmlLink'], "meet_link": event_result['meetLink'],
                        "event_id": event_result['id']}
            # --- END of new email notification logic ---
            else:
                return {"status": "error", "message": event_result.get("error", "Failed to update calendar event.")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Error updating meeting: {e}"}

    def cancel_meeting(self, event_id: str) -> dict:
        try:
            result = self.calendar_api.delete_event(event_id)
            if result.get("status") == "success":
                return {"status": "success", "message": "Meeting cancelled!"}
            else:
                return {"status": "error", "message": result.get("error", "Failed to cancel calendar event.")}
        except Exception as e:
            traceback.print_exc()
            return {"status": "error", "message": f"Error cancelling meeting: {e}"}