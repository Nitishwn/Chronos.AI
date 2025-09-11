# 📅 AI Meeting Assistant

### An AI-powered assistant for seamless meeting management using natural language.

---

## 🚀 Overview

The **AI Meeting Assistant** is a full-stack web application and Chrome extension that simplifies scheduling, rescheduling, and canceling meetings using natural language. Built with Python's Flask framework and leveraging Google's Gemini API, the assistant translates conversational queries into actionable calendar events, ensuring you and your team are always in sync.

The project is structured into three main components:
1.  **Backend Core:** A Flask API that handles all the logic, from NLP parsing to interacting with Google Calendar and Gmail.
2.  **Web Frontend:** A modern, responsive web interface for desktop users.
3.  **Chrome Extension:** A lightweight browser extension for quick, in-context meeting management.

---

## ✨ Features

- **Natural Language Processing:** Use simple phrases like "Book a 30-min sync with John tomorrow at 2 PM" to manage your calendar.
- **Intelligent Intent Recognition:** Automatically detects if you want to `schedule`, `reschedule`, or `cancel` a meeting.
- **Participant Resolution:** Intelligently identifies meeting attendees, even from just a first name, by looking up local contacts.
- **Availability Suggestions:** Finds and suggests optimal time slots based on the availability of all attendees.
- **Seamless Integrations:** Connects directly with Google Calendar and Gmail to create events and send email notifications.
- **Multiple Interfaces:** Available as a standalone web app and a Chrome extension for convenience.
- **Speech Recognition (Chrome Extension):** Use your voice to interact with the assistant.

---

## 🏛️ Project Architecture

The system follows a classic client-server architecture with a clear separation of concerns.

- **Client (`/app.js`, `/popup.js`):** The frontends send user queries as JSON objects to the Flask API.
- **API (`/app/main.py`):** The central hub that routes requests to the `MeetingAgent`.
- **Core Logic (`/app/core/agent.py`):** The orchestrator that uses specialized classes to handle different tasks.
  - `NLPParser`: Transforms natural language into structured data using the Gemini API.
  - `CalendarAPI`: Manages all Google Calendar interactions (create, update, delete, free/busy checks).
  - `GmailAPI`: Handles email notifications for meeting changes.
  - `DirectoryAPI`: A mock service for local contact management.



---

## 🛠️ Installation and Setup

### Prerequisites

- Python 3.8+
- A Google Cloud Project with the Calendar, Gmail, and Gemini APIs enabled.
- A service account or OAuth 2.0 credentials for accessing Google APIs.

### Steps

1.  **Clone the Repository**
    ```bash
    git clone [https://github.com/your-username/book-meeting-assist-core.git](https://github.com/your-username/book-meeting-assist-core.git)
    cd book-meeting-assist-core
    ```

2.  **Set up the Backend**
    - Install dependencies:
      ```bash
      pip install -r requirements.txt
      ```
    - Configure your environment variables by creating a `.env` file in the root directory.
      ```env
      GEMINI_API_KEY=AIzaSy...
      OAUTH_CLIENT_SECRETS_PATH="client_secret_personal_calendar.json"
      GMAIL_TOKEN_PATH="token_personal_gmail.json"
      YOUR_COLLEGE_EMAIL_ID_FOR_TESTING=your.email@example.com
      DISABLE_SSL_VERIFICATION=True
      MEETING_TIMEZONE=Asia/Kolkata
      ```
    - Place your `client_secret_personal_calendar.json` file in the root directory.
    - **Authentication:** To generate your `token_personal_calendar.json` and `token_personal_gmail.json` files, you will need to run a separate authentication script (not included in the current project files, but a standard Google API setup step).

3.  **Run the Flask Server**
    ```bash
    python -m app.main
    ```
    The server will start at `http://127.0.0.1:5000`.

4.  **Access the Frontend**
    - **Web App:** Open `book-meeting-frontend.html` directly in your browser.
    - **Chrome Extension:**
      1.  Open Chrome and navigate to `chrome://extensions`.
      2.  Enable "Developer mode".
      3.  Click "Load unpacked" and select the `chrome-extension` directory.
      4.  The extension will appear in your toolbar.

---

## 🤝 Contribution

Contributions are welcome! If you have suggestions for new features, bug fixes, or improvements, please open an issue or submit a pull request.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
