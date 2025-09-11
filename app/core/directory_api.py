# app/core/directory_api.py
import os
import json

class GoogleDirectoryAPI:
    def __init__(self, service_account_email: str = None, admin_user_to_impersonate: str = None, service_account_key_path: str = None):
        """
        Initializes the Directory API client.
        In this updated version, user lookups are handled via a local JSON file.
        """
        self.contacts_file = 'contacts.json'
        self._load_contacts()

    def _load_contacts(self):
        """Loads contacts from a JSON file. Creates an empty file if it doesn't exist."""
        if not os.path.exists(self.contacts_file):
            with open(self.contacts_file, 'w') as f:
                json.dump({}, f)
        
        with open(self.contacts_file, 'r') as f:
            try:
                self.contacts = json.load(f)
            except json.JSONDecodeError:
                self.contacts = {} # Fallback to empty dictionary on load error

    def _save_contacts(self):
        """Saves the current contacts dictionary to the JSON file."""
        with open(self.contacts_file, 'w') as f:
            json.dump(self.contacts, f, indent=4)

    def get_user_by_email(self, email: str) -> dict:
        """
        Retrieves user details by exact email from the contact list.
        """
        return self.contacts.get(email.lower())

    def search_users(self, query: str) -> list:
        """
        Searches users by partial name or email from the contact list.
        """
        query_lower = query.lower()
        found = []
        for email, user_data in self.contacts.items():
            if query_lower in user_data['primaryEmail'].lower() or \
               query_lower in user_data['displayName'].lower():
                found.append(user_data)
        return found
    
    def add_contact(self, email: str, display_name: str) -> dict:
        """Adds a new contact to the list and saves the file."""
        email_lower = email.lower()
        if email_lower in self.contacts:
            return {"status": "error", "message": "Contact with this email already exists."}
        
        self.contacts[email_lower] = {
            "primaryEmail": email,
            "displayName": display_name,
            "firstName": display_name.split(' ')[0],
            "lastName": ' '.join(display_name.split(' ')[1:])
        }
        self._save_contacts()
        return {"status": "success", "message": "Contact added successfully."}

    def delete_contact(self, email: str) -> dict:
        """Deletes a contact from the list and saves the file."""
        email_lower = email.lower()
        if email_lower in self.contacts:
            del self.contacts[email_lower]
            self._save_contacts()
            return {"status": "success", "message": "Contact deleted successfully."}
        else:
            return {"status": "error", "message": "Contact not found."}

    def list_contacts(self) -> list:
        """Returns the full list of contacts."""
        return list(self.contacts.values())