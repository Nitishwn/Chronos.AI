const API_BASE_URL = 'http://127.0.0.1:5000';
const elements = {
    meetingQuery: document.getElementById('meetingQuery'),
    meetingSearch: document.getElementById('meetingSearch'),
    sendBtn: document.getElementById('sendBtn'),
    micBtn: document.getElementById('micBtn'),
    searchBtn: document.getElementById('searchBtn'),
    addContactBtn: document.getElementById('addContactBtn'),
    contactName: document.getElementById('contactName'),
    contactEmail: document.getElementById('contactEmail'),
    statusMessage: document.getElementById('statusMessage'),
    contactsStatusMessage: document.getElementById('contactsStatusMessage'),
    tabBtns: document.querySelectorAll('.tab-btn'),
    tabPages: document.querySelectorAll('.tab-page'),
    newMeetingTab: document.getElementById('newMeeting'),
    upcomingMeetingsTab: document.getElementById('upcomingMeetings'),
    contactsTab: document.getElementById('contacts'),
    loadingIndicator: document.getElementById('loadingIndicator'),
    searchLoadingIndicator: document.getElementById('searchLoadingIndicator'),
    contactsLoadingIndicator: document.getElementById('contactsLoadingIndicator'),
    confirmationArea: document.getElementById('confirmationArea'),
    suggestionsArea: document.getElementById('suggestionsArea'),
    generalMessageArea: document.getElementById('generalMessageArea'),
    slotList: document.getElementById('slotList'),
    upcomingMeetingsList: document.getElementById('upcomingMeetingsList'),
    contactsList: document.getElementById('contactsList')
};

let allUpcomingMeetings = [];
let allContacts = [];

// Helper function to format date and time for display
function formatDisplayDateTime(isoString) {
    if (!isoString) return 'N/A';
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' };
    return new Date(isoString).toLocaleString('en-US', options);
}

function showTab(tabName) {
    elements.tabBtns.forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabName);
    });
    elements.tabPages.forEach(page => {
        page.classList.toggle('active', page.id === tabName);
    });
    elements.statusMessage.textContent = '';
    elements.confirmationArea.classList.add('hidden');
    elements.suggestionsArea.classList.add('hidden');
    elements.generalMessageArea.classList.add('hidden');
}

// Function to handle scheduling, updating, or canceling a meeting
async function manageMeeting(payload, messageElement, onSuccess) {
    messageElement.textContent = 'Processing...';
    try {
        const response = await fetch(`${API_BASE_URL}/meetings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (data.status === 'success') {
            messageElement.textContent = `Success: ${data.message}`;
            if (onSuccess) onSuccess(data);
        } else {
            messageElement.textContent = `Error: ${data.message}`;
        }
    } catch (error) {
        messageElement.textContent = `An unexpected error occurred: ${error.message}`;
        console.error('Fetch error:', error);
    }
}

// Main function to process the user's text query
async function processQuery(query) {
    if (!query) {
        elements.statusMessage.textContent = 'Please enter a query.';
        return;
    }

    elements.loadingIndicator.classList.remove('hidden');
    elements.statusMessage.textContent = 'Processing...';
    elements.suggestionsArea.classList.add('hidden');
    elements.generalMessageArea.classList.add('hidden');
    elements.confirmationArea.classList.add('hidden');

    try {
        const response = await fetch(`${API_BASE_URL}/process_query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        const data = await response.json();
        elements.loadingIndicator.classList.add('hidden');

        if (response.ok && (data.status === 'success' || data.status === 'info' || data.status === 'confirmation')) {
            handleProcessQueryResponse(data);
        } else {
            elements.statusMessage.textContent = `Error: ${data.message || 'Server error.'}`;
        }
    } catch (error) {
        elements.loadingIndicator.classList.add('hidden');
        elements.statusMessage.textContent = `An unexpected error occurred: ${error.message}`;
        console.error('Error processing query:', error);
    }
}

function handleProcessQueryResponse(data) {
    const { intent, message, suggested_slots, confirmation_details } = data;
    elements.statusMessage.textContent = message;

    if (data.status === 'confirmation') {
        elements.confirmationArea.classList.remove('hidden');
        const details = data.confirmation_details;
        const originalStart = formatDisplayDateTime(details.original.start);
        const originalEnd = new Date(details.original.end).toLocaleTimeString();
        let newDetailsHtml = '';
        let confirmButtonText = '';
        
        if (details.intent === 'reschedule') {
            const newStart = formatDisplayDateTime(details.new.start);
            const newEnd = new Date(details.new.end).toLocaleTimeString();
            newDetailsHtml = `<p><strong>New Time:</strong> ${newStart} to ${newEnd}</p>`;
            confirmButtonText = 'Yes, Reschedule';
        } else if (details.intent === 'cancel') {
            newDetailsHtml = '<em>This meeting will be cancelled.</em>';
            confirmButtonText = 'Yes, Cancel';
        }

        elements.confirmationArea.innerHTML = `
            <h3>Confirm Action</h3>
            <p><strong>Original Meeting:</strong> ${details.original.summary}</p>
            <p><strong>Time:</strong> ${originalStart} - ${originalEnd}</p>
            ${newDetailsHtml}
            <button id="confirmActionBtn" class="action-btn">${confirmButtonText}</button>
        `;

        document.getElementById('confirmActionBtn').addEventListener('click', async () => {
            const actionPayload = {
                action: details.intent === 'reschedule' ? 'update' : details.intent,
                eventId: details.original.id,
            };
            if (details.intent === 'reschedule') {
                actionPayload.summary = details.new.summary;
                actionPayload.attendees = details.new.attendees.join(',');
                actionPayload.startTime = details.new.start;
                actionPayload.endTime = details.new.end;
            }
            await manageMeeting(actionPayload, elements.statusMessage, () => showTab('upcomingMeetings'));
        });

    } else if (suggested_slots && suggested_slots.length > 0) {
        elements.suggestionsArea.classList.remove('hidden');
        elements.slotList.innerHTML = '';
        const initialDetails = data.initial_meeting_details || {};
        
        suggested_slots.forEach(slot => {
            const start = formatDisplayDateTime(slot.start.dateTime);
            const end = new Date(slot.end.dateTime).toLocaleTimeString();
            const slotItem = document.createElement('div');
            slotItem.className = 'slot-item';
            slotItem.innerHTML = `
                <span>${start} - ${end}</span>
                <button class="select-btn">Select</button>
            `;
            slotItem.querySelector('.select-btn').addEventListener('click', async () => {
                const schedulePayload = {
                    action: 'schedule',
                    summary: initialDetails.summary,
                    attendees: initialDetails.attendees,
                    startTime: slot.start.dateTime,
                    endTime: slot.end.dateTime,
                    description: initialDetails.description
                };
                await manageMeeting(schedulePayload, elements.statusMessage, () => showTab('upcomingMeetings'));
            });
            elements.slotList.appendChild(slotItem);
        });
        
    } else {
        elements.generalMessageArea.classList.remove('hidden');
        elements.generalMessageArea.textContent = message;
    }
}

async function fetchUpcomingEvents() {
    elements.searchLoadingIndicator.classList.remove('hidden');
    elements.upcomingMeetingsList.innerHTML = '';
    try {
        const response = await fetch(`${API_BASE_URL}/list_upcoming_events`);
        const data = await response.json();
        elements.searchLoadingIndicator.classList.add('hidden');
        if (data.status === 'success') {
            allUpcomingMeetings = data.events;
            displayMeetings(allUpcomingMeetings);
        } else {
            elements.statusMessage.textContent = `Error fetching meetings: ${data.message}`;
        }
    } catch (error) {
        elements.searchLoadingIndicator.classList.add('hidden');
        elements.statusMessage.textContent = `An unexpected error occurred: ${error.message}`;
    }
}

function displayMeetings(meetings) {
    elements.upcomingMeetingsList.innerHTML = '';
    if (meetings.length === 0) {
        elements.upcomingMeetingsList.innerHTML = '<p class="no-meetings">No upcoming meetings found.</p>';
        return;
    }

    meetings.forEach(event => {
        const eventItem = document.createElement('div');
        eventItem.className = 'meeting-item';
        eventItem.innerHTML = `
            <div class="meeting-details">
                <div class="meeting-title">${event.summary}</div>
                <div class="meeting-time">${formatDisplayDateTime(event.start)}</div>
            </div>
            <div class="meeting-actions">
                <button class="action-btn reschedule" data-event-id="${event.id}">Reschedule</button>
                <button class="action-btn cancel" data-event-id="${event.id}">Cancel</button>
            </div>
        `;
        elements.upcomingMeetingsList.appendChild(eventItem);
    });

    document.querySelectorAll('.action-btn.reschedule').forEach(btn => {
        btn.addEventListener('click', () => {
            const eventId = btn.dataset.eventId;
            const meeting = allUpcomingMeetings.find(m => m.id === eventId);
            if (meeting) {
                
                const newStartTime = new Date(new Date(meeting.start).getTime() + 60 * 60 * 1000).toISOString();
                const newEndTime = new Date(new Date(meeting.end).getTime() + 60 * 60 * 1000).toISOString();

                const payload = {
                    action: 'update',
                    eventId: eventId,
                    summary: meeting.summary,
                    attendees: meeting.attendees.join(','),
                    startTime: newStartTime,
                    endTime: newEndTime
                };
                manageMeeting(payload, elements.statusMessage, () => fetchUpcomingEvents());
            }
        });
    });

    document.querySelectorAll('.action-btn.cancel').forEach(btn => {
        btn.addEventListener('click', () => {
            const eventId = btn.dataset.eventId;
            const payload = {
                action: 'cancel',
                eventId: eventId
            };
            manageMeeting(payload, elements.statusMessage, () => fetchUpcomingEvents());
        });
    });
}

// Contact Management Functions
async function fetchContacts() {
    elements.contactsLoadingIndicator.classList.remove('hidden');
    elements.contactsStatusMessage.textContent = '';
    elements.contactsList.innerHTML = '';
    try {
        const response = await fetch(`${API_BASE_URL}/contacts`);
        const data = await response.json();
        elements.contactsLoadingIndicator.classList.add('hidden');
        if (data.status === 'success') {
            allContacts = data.contacts;
            displayContacts(allContacts);
        } else {
            elements.contactsStatusMessage.textContent = `Error fetching contacts: ${data.message}`;
        }
    } catch (error) {
        elements.contactsLoadingIndicator.classList.add('hidden');
        elements.contactsStatusMessage.textContent = `An unexpected error occurred: ${error.message}`;
    }
}

function displayContacts(contacts) {
    elements.contactsList.innerHTML = '';
    if (contacts.length === 0) {
        elements.contactsList.innerHTML = '<p class="no-contacts">No contacts found. Add one above.</p>';
        return;
    }
    contacts.forEach(contact => {
        const contactItem = document.createElement('div');
        contactItem.className = 'contact-item';
        contactItem.innerHTML = `
            <div class="contact-details">
                <div class="contact-name">${contact.displayName}</div>
                <div class="contact-email">${contact.primaryEmail}</div>
            </div>
            <button class="action-btn delete-contact" data-email="${contact.primaryEmail}">Delete</button>
        `;
        elements.contactsList.appendChild(contactItem);
    });

    document.querySelectorAll('.action-btn.delete-contact').forEach(btn => {
        btn.addEventListener('click', async () => {
            const email = btn.dataset.email;
            const payload = { email: email };
            const response = await fetch(`${API_BASE_URL}/contacts`, {
                method: 'DELETE',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            const data = await response.json();
            elements.contactsStatusMessage.textContent = data.message;
            if (data.status === 'success') {
                fetchContacts(); 
            }
        });
    });
}

// Event Listeners
elements.sendBtn.addEventListener('click', () => {
    processQuery(elements.meetingQuery.value);
});

elements.searchBtn.addEventListener('click', () => {
    const searchTerm = elements.meetingSearch.value.toLowerCase();
    const filteredMeetings = allUpcomingMeetings.filter(meeting => {
        const title = meeting.summary.toLowerCase();
        const attendees = meeting.attendees.join(', ').toLowerCase();
        return title.includes(searchTerm) || attendees.includes(searchTerm) || meeting.start.includes(searchTerm);
    });
    displayMeetings(filteredMeetings);
});

elements.addContactBtn.addEventListener('click', async () => {
    const name = elements.contactName.value.trim();
    const email = elements.contactEmail.value.trim();
    if (!name || !email) {
        elements.contactsStatusMessage.textContent = 'Please fill in both fields.';
        return;
    }

    const payload = {
        displayName: name,
        email: email
    };

    const response = await fetch(`${API_BASE_URL}/contacts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });
    const data = await response.json();
    elements.contactsStatusMessage.textContent = data.message;
    if (data.status === 'success') {
        elements.contactName.value = '';
        elements.contactEmail.value = '';
        fetchContacts(); // Refresh the list
    }
});

elements.tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
        const tab = btn.dataset.tab;
        showTab(tab);
        if (tab === 'upcomingMeetings') {
            fetchUpcomingEvents();
        } else if (tab === 'contacts') {
            fetchContacts();
        }
    });
});


const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
if (SpeechRecognition) {
    const recognition = new SpeechRecognition();
    recognition.lang = 'en-US';
    recognition.interimResults = false;
    recognition.maxAlternatives = 1;

    elements.micBtn.addEventListener('click', () => {
        if (elements.micBtn.classList.contains('listening')) {
            recognition.stop();
        } else {
            recognition.start();
        }
    });

    recognition.addEventListener('start', () => {
        elements.micBtn.classList.add('listening');
        elements.statusMessage.textContent = 'Listening...';
    });

    recognition.addEventListener('result', (event) => {
        let speechText = event.results[0][0].transcript;
        
        // Fix for "nitish 3" -> "nitish3" and similar issues
        // This regex finds a word character (\w) followed by a space (\s) and a digit (\d)
        // and replaces the space with nothing, effectively joining the word and number.
        speechText = speechText.replace(/(\w)\s(\d)/g, '$1$2');

        elements.meetingQuery.value = speechText;
        elements.statusMessage.textContent = 'Speech recognized. Sending query...';
        processQuery(speechText);
    });

    recognition.addEventListener('end', () => {
        elements.micBtn.classList.remove('listening');
    });

    recognition.addEventListener('error', (event) => {
        elements.micBtn.classList.remove('listening');
        elements.statusMessage.textContent = `Speech recognition error: ${event.error}`;
    });
} else {
    elements.micBtn.style.display = 'none';
    elements.statusMessage.textContent = 'Speech Recognition is not supported in this browser.';
}

document.addEventListener('DOMContentLoaded', () => {
    showTab('newMeeting');
});