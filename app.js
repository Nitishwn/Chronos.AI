const API_BASE_URL = 'http://127.0.0.1:5000';
const elements = {
    statusMessage: document.getElementById('statusMessage'),
    loadingIndicator: document.getElementById('loadingIndicator'),
    manageLoadingIndicator: document.getElementById('manageLoadingIndicator'),
    upcomingMeetingsLoadingIndicator: document.getElementById('upcomingMeetingsLoadingIndicator'),
    meetingQuery: document.getElementById('meetingQuery'),
    meetingDetailsContainer: document.getElementById('meetingDetailsContainer'),
    suggestionsArea: document.getElementById('suggestionsArea'),
    slotList: document.getElementById('slotList'),
    existingMeetingsArea: document.getElementById('existingMeetingsArea'),
    existingMeetingsList: document.getElementById('existingMeetingsList'),
    newMeetingTabBtn: document.getElementById('newMeetingTabBtn'),
    manageMeetingsTabBtn: document.getElementById('manageMeetingsTabBtn'),
    upcomingMeetingsTabBtn: document.getElementById('upcomingMeetingsTabBtn'),
    newMeetingTab: document.getElementById('newMeetingTab'),
    manageMeetingsTab: document.getElementById('manageMeetingsTab'),
    upcomingMeetingsTab: document.getElementById('upcomingMeetingsTab'),
    meetingTitle: document.getElementById('meetingTitle'),
    meetingAttendees: document.getElementById('meetingAttendees'),
    meetingStartTime: document.getElementById('meetingStartTime'),
    meetingDuration: document.getElementById('meetingDuration'),
    meetingDescription: document.getElementById('meetingDescription'),
    scheduleActionButton: document.getElementById('scheduleActionButton'),
    cancelActionButton: document.getElementById('cancelActionButton'),
    confirmationModal: document.getElementById('confirmationModal'),
    confirmCancelBtn: document.getElementById('confirmCancelBtn'),
    denyCancelBtn: document.getElementById('denyCancelBtn'),
    rescheduleSuggestionsArea: document.getElementById('rescheduleSuggestionsArea'),
    rescheduleSuggestionsMessage: document.getElementById('rescheduleSuggestionsMessage'),
    rescheduleSlotList: document.getElementById('rescheduleSlotList'),
    calendarAndListSection: document.getElementById('calendarAndListSection'),
    upcomingMeetingsArea: document.getElementById('upcomingMeetingsArea'),
    upcomingMeetingsList: document.getElementById('upcomingMeetingsList'),
    calendarGrid: document.getElementById('calendarGrid'),
    monthYearDisplay: document.getElementById('monthYearDisplay'),
    prevMonthBtn: document.querySelector('#upcomingCalendar .fa-chevron-left'),
    nextMonthBtn: document.querySelector('#upcomingCalendar .fa-chevron-right'),
    simplifiedConfirmationModal: document.getElementById('simplifiedConfirmationModal'),
    simplifiedConfirmationTitle: document.getElementById('simplifiedConfirmationTitle'),
    simplifiedConfirmationMessage: document.getElementById('simplifiedConfirmationMessage'),
    originalTitle: document.getElementById('originalTitle'),
    originalTime: document.getElementById('originalTime'),
    newTitle: document.getElementById('newTitle'),
    newTime: document.getElementById('newTime'),
    confirmSimplifiedConfirmationBtn: document.getElementById('confirmSimplifiedConfirmationBtn'),
    denySimplifiedConfirmationBtn: document.getElementById('denySimplifiedConfirmationBtn'),
};

let currentMeetingData = {};
let currentEventId = null;
let currentCalendarDate = new Date();

function formatDateTimeLocal(isoString) {
    if (!isoString) return '';
    const dt = new Date(isoString);
    const offset = dt.getTimezoneOffset() * 60000;
    const localISOString = new Date(dt.getTime() - offset).toISOString().slice(0, 16);
    return localISOString;
}

function formatDisplayDate(isoString) {
    if (!isoString) return 'N/A';
    const options = { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', timeZoneName: 'short' };
    return new Date(isoString).toLocaleString('en-US', options);
}

function setStatusMessage(text, type = 'info') {
    elements.statusMessage.innerHTML = text;
    elements.statusMessage.className = `text-center font-medium mb-4 transition-all duration-300 ease-in-out`;
    if (type === 'success') elements.statusMessage.classList.add('text-green-600');
    else if (type === 'error') elements.statusMessage.classList.add('text-red-600');
    else elements.statusMessage.classList.add('text-gray-400');
}

function showLoading(indicator) {
    Object.values(elements).forEach(el => {
        if (el && el.id && el.id.includes('LoadingIndicator')) el.classList.add('hidden');
    });
    indicator.classList.remove('hidden');
}

function hideAllSections() {
    elements.meetingDetailsContainer.classList.add('hidden');
    elements.suggestionsArea.classList.add('hidden');
    elements.existingMeetingsArea.classList.add('hidden');
    elements.rescheduleSuggestionsArea.classList.add('hidden');
    elements.calendarAndListSection.classList.add('hidden');
    elements.upcomingMeetingsArea.classList.add('hidden');
    elements.simplifiedConfirmationModal.classList.add('hidden');
}

function resetUI() {
    hideAllSections();
    currentEventId = null;
    currentMeetingData = {};
    elements.meetingQuery.value = '';
    setStatusMessage('Enter a meeting request above to begin.');
    showTab('newMeeting');
}

function showTab(tabName) {
    document.querySelectorAll('.tab-content').forEach(tab => tab.classList.add('hidden'));
    document.querySelectorAll('.tab-button').forEach(btn => btn.classList.remove('active', 'text-white'));
    
    elements[`${tabName}Tab`].classList.remove('hidden');
    elements[`${tabName}TabBtn`].classList.add('active', 'text-white');

    if (tabName === 'newMeeting') {
        hideAllSections();
    } else if (tabName === 'manageMeetings') {
        hideAllSections();
        elements.calendarAndListSection.classList.remove('hidden');
        elements.upcomingMeetingsArea.classList.remove('hidden');
        fetchAndDisplayUpcomingEvents();
    } else if (tabName === 'upcomingMeetings') {
        hideAllSections();
        elements.calendarAndListSection.classList.remove('hidden');
        elements.upcomingMeetingsArea.classList.remove('hidden');
        fetchAndDisplayUpcomingEvents();
    }
}

async function processMeetingQuery() {
    const query = elements.meetingQuery.value.trim();
    if (!query) {
        setStatusMessage("Please enter a meeting query.", 'error');
        return;
    }
    
    resetUI();
    showLoading(elements.loadingIndicator);
    setStatusMessage("Processing your request...");

    try {
        const response = await fetch(`${API_BASE_URL}/process_query`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query: query })
        });
        
        if (!response.headers.get('content-type').includes('application/json')) {
            const errorText = await response.text();
            console.error('Server returned non-JSON response:', errorText);
            setStatusMessage("Server returned an invalid response. Please check the backend logs.", 'error');
            return;
        }

        const data = await response.json();
        elements.loadingIndicator.classList.add('hidden');

        if (response.ok && (data.status === 'success' || data.status === 'info' || data.status === 'confirmation' || data.status === 'conflict')) {
            currentMeetingData = data;
            handleProcessQueryResponse(data);
        } else {
            setStatusMessage(`Error: ${data.message || 'Server error.'}`, 'error');
        }
    } catch (error) {
        elements.loadingIndicator.classList.add('hidden');
        console.error('Error processing query:', error);
        setStatusMessage(`An unexpected error occurred: ${error.message}`, 'error');
    }
}

function handleProcessQueryResponse(data) {
    const { intent, message, suggested_slots, existing_meetings, initial_meeting_details, confirmation_details } = data;
    setStatusMessage(message, data.status === 'success' ? 'success' : 'info');

    hideAllSections();
    elements.meetingQuery.value = '';

    if (data.status === 'confirmation') {
        displaySimplifiedConfirmation(confirmation_details);
    } else if (existing_meetings && existing_meetings.length > 0) {
        showTab('manageMeetings');
        displayExistingMeetings(existing_meetings, intent);
    } else if (suggested_slots && suggested_slots.length > 0) {
        // Handle suggestions for a new meeting or a reschedule conflict
        if (intent === 'schedule') {
            showTab('newMeeting');
            elements.suggestionsArea.classList.remove('hidden');
            document.getElementById('suggestionsMessage').textContent = message;
            displaySuggestions(suggested_slots, initial_meeting_details);
            fillMeetingForm(initial_meeting_details);
        } else if (intent === 'reschedule') {
            showTab('manageMeetings');
            elements.rescheduleSuggestionsArea.classList.remove('hidden');
            elements.rescheduleSuggestionsMessage.textContent = message;
            displayRescheduleSuggestions(suggested_slots, existing_meetings?.[0]?.id, existing_meetings?.[0]);
        } else {
            // Fallback for other cases
            showTab('newMeeting');
            elements.suggestionsArea.classList.remove('hidden');
            document.getElementById('suggestionsMessage').textContent = message;
            displaySuggestions(suggested_slots, initial_meeting_details);
            fillMeetingForm(initial_meeting_details);
        }
    } else if (initial_meeting_details) {
        showTab('newMeeting');
        fillMeetingForm(initial_meeting_details);
    } else {
        showTab('newMeeting');
    }
}

function findMeetingById(eventId) {
    const allMeetings = (currentMeetingData.existing_meetings || []).concat(currentMeetingData.upcoming_meetings || []);
    return allMeetings.find(m => m.id === eventId);
}

function fillMeetingForm(details, eventId = null) {
    elements.meetingTitle.value = details?.summary || '';
    elements.meetingAttendees.value = details?.attendees || '';
    elements.meetingStartTime.value = formatDateTimeLocal(details?.startTime);
    elements.meetingDuration.value = details?.duration_minutes || '';
    elements.meetingDescription.value = details?.description || '';
    currentEventId = eventId;
    elements.meetingDetailsContainer.classList.remove('hidden');

    if (eventId) {
        elements.scheduleActionButton.textContent = 'Update Meeting';
        elements.scheduleActionButton.onclick = () => updateMeeting();
        elements.scheduleActionButton.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
        elements.scheduleActionButton.classList.add('bg-amber-600', 'hover:bg-amber-700');
    } else {
        elements.scheduleActionButton.textContent = 'Schedule Meeting';
        elements.scheduleActionButton.onclick = () => scheduleMeeting();
        elements.scheduleActionButton.classList.add('bg-indigo-600', 'hover:bg-indigo-700');
        elements.scheduleActionButton.classList.remove('bg-amber-600', 'hover:bg-amber-700');
    }
}

function displaySuggestions(slots, initialDetails) {
    elements.slotList.innerHTML = '';
    slots.forEach(slot => {
        const start = formatDisplayDate(slot.start.dateTime);
        const end = new Date(slot.end.dateTime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const item = document.createElement('div');
        item.className = 'flex justify-between items-center bg-sky-100 p-4 rounded-lg shadow-sm';
        item.innerHTML = `
            <span class="text-sky-900 font-medium">${start} - ${end}</span>
            <button onclick="scheduleMeetingWithSlot('${slot.start.dateTime}', '${slot.end.dateTime}', '${initialDetails?.attendees || ''}', '${initialDetails?.summary || ''}', '${initialDetails?.description || ''}')"
                    class="bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-all duration-300">
                Select
            </button>
        `;
        elements.slotList.appendChild(item);
    });
}

async function scheduleMeetingWithSlot(startTimeISO, endTimeISO, attendees, summary, description) {
    const payload = {
        action: 'schedule',
        summary: summary || "New Meeting",
        attendees: attendees,
        startTime: startTimeISO,
        endTime: endTimeISO,
        description: description || "Meeting scheduled via Meeting Scheduler."
    };
    await sendMeetingRequest(payload, 'schedule');
}

function displayExistingMeetings(meetings, intent) {
    elements.existingMeetingsList.innerHTML = '';
    elements.existingMeetingsArea.classList.remove('hidden');
    const msg = elements.existingMeetingsArea.querySelector('#existingMeetingsMessage');
    msg.textContent = meetings.length > 0 ? "Click 'Reschedule' or 'Cancel' to manage a meeting." : "No meetings found matching your query.";
    
    meetings.forEach(meeting => {
        const start = formatDisplayDate(meeting.start);
        const end = new Date(meeting.end).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const attendeesDisplay = meeting.attendees.length > 0 ? meeting.attendees.join(', ') : 'No attendees';
        const itemHtml = `
            <div class="p-4 bg-gray-700 rounded-lg shadow-sm">
                <div class="flex items-center justify-between">
                    <div>
                        <a href="${meeting.htmlLink}" target="_blank" class="font-semibold text-gray-50 hover:underline">${meeting.summary}</a>
                        <p class="text-sm text-gray-400 mt-1">${start} - ${end}</p>
                    </div>
                    <div class="flex space-x-2">
                        <button onclick="startRescheduleFlow('${meeting.id}')"
                                class="bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2 px-4 rounded-full text-sm transition-all duration-300">
                            Reschedule
                        </button>
                        <button onclick="confirmCancellation('${meeting.id}')"
                                class="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-full text-sm transition-all duration-300">
                            Cancel
                        </button>
                    </div>
                </div>
            </div>`;
        elements.existingMeetingsList.insertAdjacentHTML('beforeend', itemHtml);
    });
}

async function startRescheduleFlow(eventId) {
    console.log("startRescheduleFlow called for event ID:", eventId);
    const meeting = findMeetingById(eventId);
    if (!meeting) {
        setStatusMessage("Meeting details not found for reschedule.", 'error');
        console.error("Meeting details not found for event ID:", eventId);
        return;
    }
    const duration = (new Date(meeting.end) - new Date(meeting.start)) / 60000;

    const parsedData = currentMeetingData.parsed_data;
    const newStartTimeString = parsedData?.new_start_time || meeting.start;
    
    fillMeetingForm({
        summary: meeting.summary,
        attendees: meeting.attendees.join(', '),
        startTime: newStartTimeString,
        duration_minutes: duration,
        description: meeting.description
    }, eventId);
    
    elements.scheduleActionButton.textContent = 'Update Meeting';
    elements.scheduleActionButton.onclick = () => updateMeeting();
    elements.scheduleActionButton.classList.remove('bg-indigo-600', 'hover:bg-indigo-700');
    elements.scheduleActionButton.classList.add('bg-amber-600', 'hover:bg-amber-700');
    
    setStatusMessage("Meeting details have been pre-filled for rescheduling. Adjust the time and click 'Update Meeting'.", 'info');
    showTab('newMeeting');
    elements.meetingDetailsContainer.classList.remove('hidden');
}

function displaySimplifiedConfirmation(details) {
    elements.originalTitle.textContent = details.original.summary;
    elements.originalTime.textContent = formatDisplayDate(details.original.start) + ' - ' + new Date(details.original.end).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
    
    if (details.intent === 'reschedule') {
        elements.simplifiedConfirmationTitle.textContent = 'Confirm Meeting Reschedule';
        elements.newTitle.textContent = details.new.summary;
        elements.newTime.textContent = formatDisplayDate(details.new.start) + ' - ' + new Date(details.new.end).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        document.getElementById('newDetails').classList.remove('hidden');
    } else if (details.intent === 'cancel') {
        elements.simplifiedConfirmationTitle.textContent = 'Confirm Meeting Cancellation';
        elements.newTime.textContent = 'N/A';
        document.getElementById('newDetails').classList.add('hidden');
    }
    
    currentEventId = details.original.id;

    elements.simplifiedConfirmationModal.classList.remove('hidden');
    
    elements.confirmSimplifiedConfirmationBtn.onclick = () => {
        const payload = {
            action: details.intent === 'reschedule' ? 'update' : details.intent,
            eventId: currentEventId,
        };
        if (details.intent === 'reschedule') {
            payload.summary = details.new.summary;
            payload.attendees = details.new.attendees.join(',');
            payload.startTime = details.new.start;
            payload.endTime = details.new.end;
        }
        sendMeetingRequest(payload, details.intent);
    };

    elements.denySimplifiedConfirmationBtn.onclick = () => {
        elements.simplifiedConfirmationModal.classList.add('hidden');
        resetUI();
    };
}


async function scheduleMeeting() {
    const startTimeValue = elements.meetingStartTime.value;
    const durationValue = elements.meetingDuration.value;
    if (!startTimeValue || !durationValue) {
        setStatusMessage("Please provide a start time and duration.", 'error');
        return;
    }
    const startTime = new Date(startTimeValue);
    const durationMinutes = parseInt(durationValue, 10);
    const endTime = new Date(startTime.getTime() + durationMinutes * 60000);
    const payload = {
        action: 'schedule',
        summary: elements.meetingTitle.value.trim(),
        attendees: elements.meetingAttendees.value.trim(),
        startTime: startTime.toISOString(),
        endTime: endTime.toISOString(),
        description: elements.meetingDescription.value.trim()
    };
    await sendMeetingRequest(payload, 'schedule');
}

async function updateMeeting() {
    if (!currentEventId) {
        setStatusMessage("No event ID found for update.", 'error');
        return;
    }
    const startTimeValue = elements.meetingStartTime.value;
    const durationValue = elements.meetingDuration.value;
    if (!startTimeValue || !durationValue) {
        setStatusMessage("Please provide a start time and duration.", 'error');
        return;
    }
    
    const startTime = new Date(startTimeValue);
    const durationMinutes = parseInt(durationValue, 10);
    const endTime = new Date(startTime.getTime() + durationMinutes * 60000);
    
    const startISO = startTime.getFullYear() + '-' +
                         String(startTime.getMonth() + 1).padStart(2, '0') + '-' +
                         String(startTime.getDate()).padStart(2, '0') + 'T' +
                         String(startTime.getHours()).padStart(2, '0') + ':' +
                         String(startTime.getMinutes()).padStart(2, '0') + ':00' +
                         getTimezoneOffset(startTime);
    const endISO = endTime.getFullYear() + '-' +
                         String(endTime.getMonth() + 1).padStart(2, '0') + '-' +
                         String(endTime.getDate()).padStart(2, '0') + 'T' +
                         String(endTime.getHours()).padStart(2, '0') + ':' +
                         String(endTime.getMinutes()).padStart(2, '0') + ':00' +
                         getTimezoneOffset(endTime);

    const payload = {
        action: 'update',
        eventId: currentEventId,
        summary: elements.meetingTitle.value.trim(),
        attendees: elements.meetingAttendees.value.trim(),
        startTime: startISO,
        endTime: endISO,
        description: elements.meetingDescription.value.trim(),
        dry_run: true
    };
    
    showLoading(elements.loadingIndicator);
    try {
        const response = await fetch(`${API_BASE_URL}/meetings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        
        if (!response.headers.get('content-type').includes('application/json')) {
            const errorText = await response.text();
            console.error('Server returned non-JSON response on dry-run:', errorText);
            setStatusMessage("Server returned an invalid response. Please check the backend logs.", 'error');
            return;
        }

        const data = await response.json();
        elements.loadingIndicator.classList.add('hidden');
        
        if (data.status === 'success') {
            await sendMeetingRequest({...payload, dry_run: false}, 'update');
        } else if (data.status === 'conflict' && data.suggested_slots) {
            setStatusMessage(`Proposed time is busy. Here are some alternatives.`, 'error');
            elements.rescheduleSuggestionsArea.classList.remove('hidden');
            elements.rescheduleSuggestionsMessage.textContent = "The selected time is busy. Here are some alternatives:";
            displayRescheduleSuggestions(data.suggested_slots, currentEventId);
        } else {
            setStatusMessage(`Error updating meeting: ${data.message || 'Unknown error.'}`, 'error');
        }
    } catch (error) {
        elements.loadingIndicator.classList.add('hidden');
        console.error('Error updating meeting:', error);
        setStatusMessage(`An unexpected error occurred: ${error.message}`, 'error');
    }
}

function getTimezoneOffset(date) {
    const offset = -date.getTimezoneOffset();
    const sign = offset >= 0 ? '+' : '-';
    const hours = Math.floor(Math.abs(offset) / 60);
    const minutes = Math.abs(offset) % 60;
    return sign + String(hours).padStart(2, '0') + ':' + String(minutes).padStart(2, '0');
}

async function confirmCancellation(eventId) {
    elements.confirmationModal.classList.remove('hidden');
    elements.confirmCancelBtn.dataset.eventId = eventId;
}

async function sendMeetingRequest(payload, actionType) {
    showLoading(elements.loadingIndicator);
    try {
        const response = await fetch(`${API_BASE_URL}/meetings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });

        if (!response.headers.get('content-type').includes('application/json')) {
            const errorText = await response.text();
            console.error('Server returned non-JSON response:', errorText);
            setStatusMessage("Server returned an invalid response. Please check the backend logs.", 'error');
            return;
        }

        const data = await response.json();
        elements.loadingIndicator.classList.add('hidden');
        if (response.ok && data.status === 'success') {
            setStatusMessage(`Meeting ${actionType === 'schedule' ? 'Scheduled' : 'Updated'}! ${data.message}.`, 'success');
            resetUI();
        } else {
            setStatusMessage(`Error ${actionType === 'schedule' ? 'scheduling' : 'updating'} meeting: ${data.message || 'Unknown error.'}`, 'error');
        }
    } catch (error) {
        elements.loadingIndicator.classList.add('hidden');
        console.error(`Error ${actionType === 'schedule' ? 'scheduling' : 'updating'} meeting:`, error);
        setStatusMessage(`An unexpected error occurred: ${error.message}`, 'error');
    }
}

function displayRescheduleSuggestions(slots, eventId, originalMeetingDetails) {
    elements.rescheduleSlotList.innerHTML = '';
    elements.rescheduleSuggestionsArea.classList.remove('hidden');
    if (!eventId) {
        elements.rescheduleSuggestionsMessage.textContent = "Cannot reschedule: The original meeting could not be found. Here are some slots to create a new meeting.";
        displaySuggestions(slots, originalMeetingDetails);
        return;
    }
    slots.forEach(slot => {
        const start = formatDisplayDate(slot.start.dateTime);
        const end = new Date(slot.end.dateTime).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' });
        const item = document.createElement('div');
        item.className = 'flex justify-between items-center bg-sky-100 p-4 rounded-lg shadow-sm';
        item.innerHTML = `
            <span class="text-sky-900 font-medium">${start} - ${end}</span>
            <button onclick="selectRescheduleSlot('${eventId}', '${slot.start.dateTime}', '${slot.end.dateTime}')"
                    class="bg-sky-600 hover:bg-sky-700 text-white font-semibold py-2 px-4 rounded-lg text-sm transition-all duration-300">
                Select
            </button>
        `;
        elements.rescheduleSlotList.appendChild(item);
    });
}

async function selectRescheduleSlot(eventId, startTimeISO, endTimeISO) {
    const meeting = findMeetingById(eventId);
    if (!meeting) {
        setStatusMessage("Meeting details not found for reschedule.", 'error');
        return;
    }
    const attendeesEmailString = meeting.attendees.join(',');
    const payload = {
        action: 'update',
        eventId: eventId,
        summary: meeting.summary,
        attendees: attendeesEmailString,
        startTime: startTimeISO,
        endTime: endTimeISO,
        description: meeting.description || '',
        dry_run: false
    };
    await sendMeetingRequest(payload, 'update');
}

async function fetchAndDisplayUpcomingEvents() {
    elements.upcomingMeetingsList.innerHTML = '';
    showLoading(elements.upcomingMeetingsLoadingIndicator);
    setStatusMessage('Fetching your upcoming meetings...', 'info');
    elements.rescheduleSuggestionsArea.classList.add('hidden');
    try {
        const response = await fetch(`${API_BASE_URL}/list_upcoming_events`, { method: 'GET' });

        if (!response.headers.get('content-type').includes('application/json')) {
            const errorText = await response.text();
            console.error('Server returned non-JSON response on list events:', errorText);
            setStatusMessage("Server returned an invalid response. Please check the backend logs.", 'error');
            return;
        }

        const data = await response.json();
        elements.upcomingMeetingsLoadingIndicator.classList.add('hidden');
        if (response.ok && data.status === 'success') {
            currentMeetingData.upcoming_meetings = data.events;
            renderCalendar(currentCalendarDate, data.events);
            if (data.events.length === 0) {
                elements.upcomingMeetingsList.innerHTML = '<p class="text-center text-gray-500">You have no upcoming meetings in the next 30 days.</p>';
                setStatusMessage('You have no upcoming meetings in the next 30 days.', 'info');
            } else {
                setStatusMessage(`Found ${data.events.length} upcoming meetings.`, 'success');
                data.events.forEach(event => {
                    const attendees = event.attendees.length > 0 ? `<p class="text-xs text-gray-500 mt-1">Attendees: ${event.attendees.join(', ')}</p>` : '';
                    const eventHtml = `
                        <div id="meeting-${event.id}" class="p-4 bg-gray-700 rounded-lg shadow-sm">
                            <div class="flex items-center justify-between">
                                <div>
                                    <a href="${event.htmlLink}" target="_blank" class="font-semibold text-gray-50 hover:underline">${event.summary}</a>
                                    <p class="text-sm text-gray-400 mt-1">
                                        <i class="fa-solid fa-clock mr-2"></i>
                                        ${formatDisplayDate(event.start)} - ${new Date(event.end).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                                    </p>
                                    ${attendees}
                                </div>
                                <div class="flex space-x-2">
                                    <button onclick="startRescheduleFlow('${event.id}')" class="reschedule-btn bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2 px-4 rounded-full text-sm transition-all duration-300">Reschedule</button>
                                    <button onclick="confirmCancellation('${event.id}')" class="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-full text-sm transition-all duration-300">Cancel</button>
                                </div>
                            </div>
                        </div>`;
                    elements.upcomingMeetingsList.insertAdjacentHTML('beforeend', eventHtml);
                });
            }
        } else {
            elements.upcomingMeetingsList.innerHTML = '<p class="text-center text-red-500">Error fetching meetings.</p>';
            setStatusMessage(`Error fetching meetings: ${data.message || 'Unknown error.'}`, 'error');
        }
    } catch (error) {
        elements.upcomingMeetingsLoadingIndicator.classList.add('hidden');
        console.error('Error fetching meetings:', error);
        elements.upcomingMeetingsList.innerHTML = '<p class="text-center text-red-500">An unexpected error occurred. Please try again.</p>';
        setStatusMessage(`An unexpected error occurred: ${error.message}`, 'error');
    }
}

elements.confirmCancelBtn.addEventListener('click', async () => {
    const eventId = elements.confirmCancelBtn.dataset.eventId;
    elements.confirmationModal.classList.add('hidden');
    showLoading(elements.loadingIndicator);
    setStatusMessage("Cancelling meeting...", 'info');
    try {
        const response = await fetch(`${API_BASE_URL}/meetings`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ action: 'cancel', eventId: eventId })
        });
        
        if (!response.headers.get('content-type').includes('application/json')) {
            const errorText = await response.text();
            console.error('Server returned non-JSON response on cancel:', errorText);
            setStatusMessage("Server returned an invalid response. Please check the backend logs.", 'error');
            return;
        }

        const data = await response.json();
        elements.loadingIndicator.classList.add('hidden');
        if (response.ok && data.status === 'success') {
            setStatusMessage(`Meeting Cancelled! ${data.message}.`, 'success');
            fetchAndDisplayUpcomingEvents();
        } else {
            setStatusMessage(`Error cancelling meeting: ${data.message || 'Unknown error.'}`, 'error');
        }
    } catch (error) {
        elements.loadingIndicator.classList.add('hidden');
        console.error('Error cancelling meeting:', error);
        setStatusMessage(`An unexpected error occurred: ${error.message}`, 'error');
    }
});
elements.denyCancelBtn.addEventListener('click', () => elements.confirmationModal.classList.add('hidden'));

function renderCalendar(date, meetings = []) {
    elements.calendarGrid.innerHTML = `
        <div class="text-gray-400 font-semibold">Sun</div>
        <div class="text-gray-400 font-semibold">Mon</div>
        <div class="text-gray-400 font-semibold">Tue</div>
        <div class="text-gray-400 font-semibold">Wed</div>
        <div class="text-gray-400 font-semibold">Thu</div>
        <div class="text-gray-400 font-semibold">Fri</div>
        <div class="text-gray-400 font-semibold">Sat</div>
    `;
    const options = { month: 'long', year: 'numeric' };
    elements.monthYearDisplay.textContent = date.toLocaleDateString('en-US', options);
    const year = date.getFullYear();
    const month = date.getMonth();
    const meetingsPerDay = getMeetingsPerDay(meetings, year, month);
    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const today = new Date();
    const isCurrentMonth = today.getFullYear() === year && today.getMonth() === month;
    for (let i = 0; i < firstDay; i++) {
        const emptyDay = document.createElement('div');
        emptyDay.className = 'calendar-day inactive';
        elements.calendarGrid.appendChild(emptyDay);
    }
    for (let day = 1; day <= daysInMonth; day++) {
        const dayElement = document.createElement('div');
        dayElement.className = 'calendar-day';
        dayElement.textContent = day;
        dayElement.dataset.day = day;
        if (isCurrentMonth && day === today.getDate()) {
            dayElement.classList.add('today');
        }
        const meetingCount = meetingsPerDay[day] || 0;
        if (meetingCount > 0) {
            if (meetingCount >= 10) dayElement.classList.add('has-meetings-red');
            else if (meetingCount >= 4) dayElement.classList.add('has-meetings-yellow');
            else dayElement.classList.add('has-meetings-green');
        }
        dayElement.addEventListener('click', () => showMeetingsForDay(day, month, year));
        elements.calendarGrid.appendChild(dayElement);
    }
}

function getMeetingsPerDay(meetings, year, month) {
    const counts = {};
    meetings.forEach(meeting => {
        const meetingDate = new Date(meeting.start);
        if (meetingDate.getFullYear() === year && meetingDate.getMonth() === month) {
            const day = meetingDate.getDate();
            counts[day] = (counts[day] || 0) + 1;
        }
    });
    return counts;
}

function showMeetingsForDay(day, month, year) {
    const selectedDate = new Date(year, month, day);
    const meetingsForDay = (currentMeetingData.upcoming_meetings || []).filter(meeting => {
        const meetingDate = new Date(meeting.start);
        return meetingDate.getDate() === day && meetingDate.getMonth() === month && meetingDate.getFullYear() === year;
    });
    elements.upcomingMeetingsList.innerHTML = '';
    if (meetingsForDay.length === 0) {
        elements.upcomingMeetingsList.innerHTML = `<p class="text-center text-gray-500">No meetings on ${selectedDate.toDateString()}.</p>`;
    } else {
        meetingsForDay.forEach(event => {
            const attendees = event.attendees.length > 0 ? `<p class="text-xs text-gray-500 mt-1">Attendees: ${event.attendees.join(', ')}</p>` : '';
            const eventHtml = `
                <div class="p-4 bg-gray-700 rounded-lg shadow-sm">
                    <div class="flex items-center justify-between">
                        <div>
                            <a href="${event.htmlLink}" target="_blank" class="font-semibold text-gray-50 hover:underline">${event.summary}</a>
                            <p class="text-sm text-gray-400 mt-1">
                                <i class="fa-solid fa-clock mr-2"></i>
                                ${formatDisplayDate(event.start)} - ${new Date(event.end).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}
                            </p>
                            ${attendees}
                        </div>
                        <div class="flex space-x-2">
                            <button onclick="startRescheduleFlow('${event.id}')" class="reschedule-btn bg-amber-600 hover:bg-amber-700 text-white font-semibold py-2 px-4 rounded-full text-sm transition-all duration-300">Reschedule</button>
                            <button onclick="confirmCancellation('${event.id}')" class="bg-red-600 hover:bg-red-700 text-white font-semibold py-2 px-4 rounded-full text-sm transition-all duration-300">Cancel</button>
                        </div>
                    </div>
                </div>`;
            elements.upcomingMeetingsList.insertAdjacentHTML('beforeend', eventHtml);
        });
    }
}

elements.prevMonthBtn.addEventListener('click', () => {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() - 1);
    fetchAndDisplayUpcomingEvents();
});
elements.nextMonthBtn.addEventListener('click', () => {
    currentCalendarDate.setMonth(currentCalendarDate.getMonth() + 1);
    fetchAndDisplayUpcomingEvents();
});

document.getElementById('meetingQuery').addEventListener('keypress', (e) => {
    if (e.key === 'Enter') processMeetingQuery();
});
document.getElementById('newMeetingTabBtn').addEventListener('click', () => showTab('newMeeting'));
document.getElementById('manageMeetingsTabBtn').addEventListener('click', () => showTab('manageMeetings'));
document.getElementById('upcomingMeetingsTabBtn').addEventListener('click', () => showTab('upcomingMeetings'));
elements.cancelActionButton.addEventListener('click', resetUI);
elements.scheduleActionButton.addEventListener('click', scheduleMeeting);

document.addEventListener('DOMContentLoaded', () => {
    resetUI();
});