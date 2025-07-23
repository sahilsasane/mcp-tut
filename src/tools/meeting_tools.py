"""MCP tools for Google Workspace server."""

import base64
import json
import os
from datetime import datetime, timedelta

from src.config import (
    GMAIL_DIR,
    PROCESSED_MEETING_EMAILS_FILE,
    UNPROCESSED_EMAILS_FILE,
    logger,
)
from src.models import MeetingContext
from src.utils.intent_classifier import extract_intent
from src.workspace import workspace


async def extract_email_details(email_id: str) -> str:
    """Extract meeting details from email content"""
    logger.info(f"Extracting meeting details from email with email_id: {email_id}")
    try:
        if not email_id:
            return "❌ Error: No email ID provided"

        # Check if the email ID is already processed
        processed_email = await extract_processed_emails(email_id)
        processed_email_details = json.loads(processed_email)

        if processed_email_details.get("email_id") == email_id:
            return (
                f"✅ Email ID {email_id} has already been processed. \n"
                + json.dumps(processed_email_details, indent=2)
            )
        logger.info(f"Processing email ID: {email_id}")

        email = await extract_recent_emails(email_id)
        email_info = json.loads(email).get(email_id, {})

        if not email_info:
            return "❌ Error: No email data found"

        logger.info(f"Processing email ID: {email_id}")

        # Handle the case where email_info contains email ID as key and email info as value
        if len(email_info) == 1:
            email_id, email_info = list(email_info.items())[0]
        else:
            # If it's just the email info directly
            email_info = email_info
            email_id = email_info.get("email_id", "unknown")

        logger.info(f"Processing email ID: {email_id}")
        logger.info(
            f"Email info keys: {list(email_info.keys()) if isinstance(email_info, dict) else 'Not a dict'}"
        )

        email_body = email_info.get("content", "")
        subject = email_info.get("subject", "No Subject")

        if not email_body:
            return "❌ Error: No email content found"

        # Check intent of the email
        intent = email_info.get("intent", "")
        if not intent:
            intent = await extract_intent(email_content=email_body)
        logger.info(f"Extracted intent: {intent}")

        match intent:
            case "meeting_invitation":
                meeting_details = workspace.extract_meeting_details(email_body, subject)
            case "reschedule_meeting":
                meeting_details = workspace.extract_meeting_details(email_body, subject)
            case "cancel_meeting":
                meeting_details = workspace.extract_meeting_details(email_body, subject)
            case "client_inquiry":
                meeting_details = workspace.extract_client_req(email_body, subject)
            case "information_request":
                meeting_details = workspace.extract_client_req(email_body, subject)
            case "feature_update":
                meeting_details = workspace.extract_client_req(email_body, subject)
            case "project_status":
                meeting_details = workspace.extract_project_query(email_body, subject)
            case "doc_sharing_request":
                meeting_details = workspace.extract_teams_req(email_body, subject)

        # Save to processed emails file
        path = os.path.join(GMAIL_DIR)
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, PROCESSED_MEETING_EMAILS_FILE)

        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as existing_file:
                try:
                    existing_data = json.load(existing_file)
                except json.JSONDecodeError:
                    existing_data = []

        existing_data.append(
            {
                "email_id": email_id,
                "email_info": email_info,
                "details": meeting_details,
            }
        )

        with open(file_path, "w") as file:
            json.dump(existing_data, file, indent=4)

        logger.info(f"Successfully extracted meeting details: {meeting_details}")
        return json.dumps(meeting_details, indent=2)

    except Exception as e:
        logger.error(f"Error extracting meeting details: {e}")
        return f"❌ Error extracting details: {str(e)}"


async def extract_processed_emails(emailId: str = None) -> str:
    """Extract processed meeting-related emails from Gmail."""
    try:
        path = os.path.join(GMAIL_DIR, PROCESSED_MEETING_EMAILS_FILE)
        logger.info(f"Reading processed meeting emails from {path}")

        if os.path.exists(path):
            with open(path, "r") as file:
                data = json.load(file)
                if not emailId:
                    return json.dumps(data, indent=2)

                # Search for the specific email_id in the processed emails array
                for entry in data:
                    if entry.get("email_id") == emailId:
                        # Return the details (meeting details) directly as JSON string
                        return json.dumps(entry, indent=2)

                return json.dumps({}, indent=2)  # Return empty dict if not found
        else:
            return json.dumps({}, indent=2)

    except Exception as e:
        return f"❌ Error fetching processed emails: {str(e)}"


async def create_calendar_event_only(
    email_id: str, start_time: str = "", duration_hours: int = 1
) -> str:
    """Create calendar event from meeting details"""
    try:
        meeting_details_json = await extract_processed_emails(email_id)
        email_details = json.loads(meeting_details_json)

        meeting_details = email_details.get("details", {})

        # Check if meeting details were found
        if not meeting_details:
            return "❌ Error: No meeting details found for the provided email ID"

        # Use provided time or default
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
        else:
            start_dt = datetime.now().replace(
                hour=10, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

        end_dt = start_dt + timedelta(hours=duration_hours)

        event = {
            "summary": meeting_details["title"],
            "description": f"Meeting Purpose: {meeting_details['purpose']}\n\nKey Topics:\n"
            + "\n".join(f"• {topic}" for topic in meeting_details.get("topics", [])),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": email} for email in meeting_details["attendees"]],
        }

        created_event = (
            workspace.calendar_service.events()
            .insert(calendarId="primary", body=event)
            .execute()
        )

        return json.dumps(
            {
                "event_id": created_event["id"],
                "html_link": created_event.get("htmlLink"),
                "start_time": start_dt.isoformat(),
                "attendees": meeting_details["attendees"],
            }
        )
    except Exception as e:
        return f"❌ Error creating calendar event: {str(e)}"


async def create_meeting_doc_only(meeting_id: str, email_id: str) -> str:
    """Create meeting document from details"""
    try:
        meeting_details_json = await extract_processed_emails(email_id)
        meeting_details = json.loads(meeting_details_json)

        # Check if meeting details were found
        if not meeting_details:
            return "❌ Error: No meeting details found for the provided email ID"

        meeting_context = MeetingContext(
            meeting_title=meeting_details.get("details", {}).get("title", ""),
            attendees=meeting_details.get("details", {}).get("attendees", []),
            email_content=meeting_details.get("email_info", {}).get("content", ""),
            meeting_purpose=meeting_details.get("details", {}).get("purpose", ""),
            key_topics=meeting_details.get("details", {}).get("topics", []),
            action_items=[],
        )

        workspace.meeting_contexts[meeting_id] = meeting_context
        doc_link = workspace.create_meeting_document(meeting_id, meeting_context)

        return json.dumps({"doc_link": doc_link, "meeting_id": meeting_id})
    except Exception as e:
        return f"❌ Error creating meeting doc: {str(e)}"


async def link_doc_to_calendar(event_id: str, doc_link: str) -> str:
    """Add document link to existing calendar event"""
    try:
        # Get existing event
        event = (
            workspace.calendar_service.events()
            .get(calendarId="primary", eventId=event_id)
            .execute()
        )

        # Update description with doc link
        current_desc = event.get("description", "")
        updated_desc = f"{current_desc}\n\nMeeting Notes Document: {doc_link}"
        event["description"] = updated_desc

        # Update the event
        updated_event = (
            workspace.calendar_service.events()
            .update(calendarId="primary", eventId=event_id, body=event)
            .execute()
        )

        return f"✅ Document linked to calendar event: {updated_event.get('htmlLink')}"
    except Exception as e:
        return f"❌ Error linking document: {str(e)}"


async def get_recent_emails() -> str:
    """Get recent emails that appear to be about meetings"""
    try:
        results = (
            workspace.gmail_service.users()
            .messages()
            .list(
                userId="me",
                q="is:unread",
                maxResults=5,
            )
            .execute()
        )

        path = os.path.join(GMAIL_DIR)
        os.makedirs(path, exist_ok=True)
        file_path = os.path.join(path, UNPROCESSED_EMAILS_FILE)

        messages = results.get("messages", [])
        emails_data = {}

        for msg in messages:
            email = (
                workspace.gmail_service.users()
                .messages()
                .get(userId="me", id=msg["id"])
                .execute()
            )

            # Extract email data
            sender = ""
            date = ""
            subject = ""
            receiver = ""

            content = base64.urlsafe_b64decode(
                email["payload"]["parts"][0]["body"]["data"]
            ).decode("utf-8")
            snippet = email["snippet"]

            for header in email["payload"]["headers"]:
                if header["name"] == "From":
                    sender = header["value"]
                elif header["name"] == "Date":
                    date = header["value"]
                elif header["name"] == "Subject":
                    subject = header["value"]
                elif header["name"] == "To":
                    receiver = header["value"]

            intent = await extract_intent(email_content=content)

            emails_data[msg["id"]] = {
                "email_id": msg["id"],
                "subject": subject,
                "sender": sender,
                "receiver": receiver,
                "date": date,
                "content": content,
                "snippet": snippet,
                "intent": intent,
            }

        # Save emails data
        existing_data = []
        if os.path.exists(file_path):
            with open(file_path, "r") as existing_file:
                try:
                    existing_data = json.load(existing_file)
                except json.JSONDecodeError:
                    pass

        existing_data.append(emails_data)
        with open(file_path, "w") as file:
            json.dump(existing_data, file, indent=4)

        logger.info(f"Found {len(emails_data)} recent meeting-related emails")
        return f"✅ Found {len(emails_data)} recent meeting-related emails and stored them in {file_path}"

    except Exception as e:
        return f"❌ Error fetching emails: {str(e)}"


async def extract_recent_emails(emailId: str = None) -> str:
    """Extract recent meeting-related emails from Gmail."""
    try:
        path = os.path.join(GMAIL_DIR, UNPROCESSED_EMAILS_FILE)
        logger.info(f"Reading recent meeting emails from {path}")

        if os.path.exists(path):
            with open(path, "r") as file:
                data = json.load(file)
                if not emailId:
                    return json.dumps(data, indent=2)
                for emails_dict in data:
                    for email_id, email_info in emails_dict.items():
                        if emailId and emailId == email_id:
                            return json.dumps({email_id: email_info}, indent=2)
                        elif not emailId:
                            # If no specific emailId provided, return all emails
                            return json.dumps(emails_dict, indent=2)
        else:
            return "No recent meeting emails found."

        return "No recent meeting emails found."

    except Exception as e:
        return f"❌ Error fetching emails: {str(e)}"


async def check_conflicting_meetings(
    start_time: str, end_time: str, calendar_id: str = "primary"
) -> str:
    """Check for conflicting meetings in the calendar."""
    try:
        # meeting_details = { "start": "2023-10-01T10:00:00Z", "end": "2023-10-01T11:00:00Z" }

        events_result = (
            workspace.calendar_service.events()
            .list(
                calendarId="primary",
                timeMin=start_time,
                timeMax=end_time,
                maxResults=10,
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
        events = events_result.get("items", [])

        if not events:
            return "No upcoming meetings found."

        conflicts = []
        for event in events:
            start = event["start"].get("dateTime", event["start"].get("date"))
            end = event["end"].get("dateTime", event["end"].get("date"))
            conflicts.append(f"{event['summary']} from {start} to {end}")

        return "\n".join(conflicts)

    except Exception as e:
        return f"❌ Error checking for conflicts: {str(e)}"


async def cancel_meeting(meeting_id: str) -> str:
    """Cancel a meeting by its ID."""
    try:
        # Delete the event from the calendar
        workspace.calendar_service.events().delete(
            calendarId="primary", eventId=meeting_id
        ).execute()
        return f"✅ Meeting with ID {meeting_id} has been cancelled."
    except Exception as e:
        return f"❌ Error cancelling meeting: {str(e)}"


async def reschedule_meeting(
    meeting_id: str, new_start_time: str, new_end_time: str
) -> str:
    """Reschedule a meeting to a new time."""
    try:
        # Update the event in the calendar
        event = (
            workspace.calendar_service.events()
            .get(calendarId="primary", eventId=meeting_id)
            .execute()
        )
        event["start"] = {"dateTime": new_start_time}
        event["end"] = {"dateTime": new_end_time}
        workspace.calendar_service.events().update(
            calendarId="primary", eventId=meeting_id, body=event
        ).execute()
        return f"✅ Meeting with ID {meeting_id} has been rescheduled."
    except Exception as e:
        return f"❌ Error rescheduling meeting: {str(e)}"


async def create_recurring_meeting(meeting_details: dict, recurrence_rule: str) -> str:
    """Create a recurring meeting in the calendar."""
    try:
        details = meeting_details

        start_dt = datetime.fromisoformat(details["start"])
        end_dt = datetime.fromisoformat(details["end"])

        event = {
            "summary": details["title"],
            "description": f"Meeting Purpose: {details['purpose']}\n\nKey Topics:\n"
            + "\n".join(f"• {topic}" for topic in details.get("topics", [])),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": email} for email in details["attendees"]],
            "recurrence": [recurrence_rule],
        }

        created_event = (
            workspace.calendar_service.events()
            .insert(calendarId="primary", body=event)
            .execute()
        )

        return json.dumps(
            {
                "event_id": created_event["id"],
                "html_link": created_event.get("htmlLink"),
                "start_time": start_dt.isoformat(),
                "attendees": details["attendees"],
            }
        )
    except Exception as e:
        return f"❌ Error creating recurring meeting: {str(e)}"
