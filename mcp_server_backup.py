#!/usr/bin/env python3
import base64
import json
import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any, Dict, List

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from mcp.server.fastmcp import FastMCP

from src.config import PROCESSED_MEETING_EMAILS_FILE, UNPROCESSED_EMAILS_FILE

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("GoogleWorkspaceMCP")


@dataclass
class MeetingContext:
    """Store meeting context for document generation"""

    meeting_title: str
    attendees: List[str]
    email_content: str
    meeting_purpose: str
    key_topics: List[str]
    action_items: List[str]


class GoogleWorkspaceServer:
    def __init__(self):
        self.credentials = None
        self.gmail_service = None
        self.calendar_service = None
        self.drive_service = None
        self.docs_service = None

        self.meeting_contexts: Dict[str, MeetingContext] = {}

        self.authenticate()

    def authenticate(self):
        """Handle Google OAuth authentication"""
        logger.info("Authenticating with Google APIs...")
        creds = None

        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open("token.json", "w") as token:
                token.write(creds.to_json())

        self.credentials = creds

        self.gmail_service = build("gmail", "v1", credentials=creds)
        self.calendar_service = build("calendar", "v3", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)
        self.docs_service = build("docs", "v1", credentials=creds)

        logger.info("Authentication successful. Services initialized.")

    def extract_meeting_details(
        self, email_content: str, subject: str
    ) -> Dict[str, Any]:
        """Extract meeting details from email content"""
        # date_patterns = [
        #     r"(\d{1,2}[/-]\d{1,2}[/-]\d{4})",
        #     r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}",
        #     r"(tomorrow|today|next week|next month)",
        #     r"(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)",
        # ]

        time_patterns = [
            r"(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))",
            r"(\d{1,2}\s*(?:AM|PM|am|pm))",
            r"at\s+(\d{1,2}:\d{2})",
            r"(\d{1,2}:\d{2})",
        ]

        email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"
        attendees = re.findall(email_pattern, email_content)

        purpose_keywords = [
            "discuss",
            "review",
            "plan",
            "update",
            "meeting about",
            "regarding",
        ]
        topics = []
        purpose = ""

        for keyword in purpose_keywords:
            if keyword in email_content.lower():
                sentences = email_content.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        purpose = sentence.strip()
                        break
                break

        if not purpose:
            purpose = f"Meeting regarding {subject}"

        found_time = None
        for pattern in time_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                found_time = match.group(1)
                break

        if not found_time:
            found_time = "10:00 AM"

        return {
            "title": subject if "meeting" in subject.lower() else f"Meeting: {subject}",
            "attendees": attendees,
            "purpose": purpose,
            "topics": topics,
            "time": found_time,
        }

    def create_meeting_document(self, meeting_id: str, context: MeetingContext) -> str:
        """Create a Google Doc for the meeting"""
        try:
            doc = {"title": f"Meeting Notes - {context.meeting_title}"}

            document = self.docs_service.documents().create(body=doc).execute()
            document_id = document.get("documentId")

            content = f"""Meeting: {context.meeting_title}
Date: {datetime.now().strftime("%Y-%m-%d")}
Time: TBD

Attendees:
{chr(10).join(f"• {attendee}" for attendee in context.attendees)}

Meeting Purpose:
{context.meeting_purpose}

Key Topics to Discuss:
{chr(10).join(f"• {topic}" for topic in context.key_topics) if context.key_topics else "• TBD"}

Original Email Context:
{context.email_content[:500]}...

Agenda:
• Welcome and introductions
• Review of previous action items
• Main discussion points
• Next steps and action items
• Closing

Notes:
[To be filled during meeting]

Action Items:
[To be assigned during meeting]

Next Meeting:
[To be scheduled]
"""

            requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

            self.docs_service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            for attendee in context.attendees:
                if attendee:
                    try:
                        self.drive_service.permissions().create(
                            fileId=document_id,
                            body={
                                "type": "user",
                                "role": "writer",
                                "emailAddress": attendee,
                            },
                        ).execute()
                    except Exception as e:
                        print(f"Could not share with {attendee}: {e}")

            return f"https://docs.google.com/document/d/{document_id}"

        except Exception as e:
            print(f"Error creating document: {e}")
            return ""


workspace = GoogleWorkspaceServer()

mcp = FastMCP("Google Workspace Meeting Assistant")
GMAIL_DIR = "gmail"


# RESOURCES
@mcp.resource("gmail://meeting-emails")
async def get_unprocessed_meetings() -> str:
    """Get recent meeting-related emails"""
    logger.info("Called get_unprocessed_meetings resource.")
    try:
        path = os.path.join(GMAIL_DIR, UNPROCESSED_EMAILS_FILE)
        if not os.path.exists(path):
            logger.warning(f"No recent meeting emails found at {path}.")
            return json.dumps({"error": "No recent meeting emails found."})
        with open(path, "r") as file:
            emails_data = json.load(file)
        return json.dumps(emails_data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching meeting emails: {e}")
        return json.dumps({"error": str(e)})


@mcp.resource("gmail://processed-meetings")
async def get_processed_meetings() -> str:
    """Dynamic resource showing meetings extracted from emails"""
    # Returns JSON of all processed meeting data
    logger.info("Called get_processed_meetings resource.")
    try:
        path = os.path.join(GMAIL_DIR, PROCESSED_MEETING_EMAILS_FILE)
        if not os.path.exists(path):
            logger.warning(f"No processed meetings found at {path}.")
            return json.dumps({"error": "No processed meetings found."})
        with open(path, "r") as file:
            meetings_data = json.load(file)
        return json.dumps(meetings_data, indent=2)
    except Exception as e:
        logger.error(f"Error fetching processed meetings: {e}")
        return json.dumps({"error": str(e)})


@mcp.resource("gmail://meeting-emails/{email_id}")
async def get_meeting_email(email_id: str) -> str:
    """Get details of a specific meeting email by ID"""
    logger.info(f"Called get_meeting_email resource with email_id={email_id}.")
    try:
        path = os.path.join(GMAIL_DIR, PROCESSED_MEETING_EMAILS_FILE)
        if not os.path.exists(path):
            logger.warning(f"No processed meetings found at {path}.")
            return json.dumps({"error": "No processed meetings found."})

        with open(path, "r") as file:
            meetings_data = json.load(file)

        for meeting in meetings_data:
            if meeting.get("email_id") == email_id:
                return json.dumps(meeting, indent=2)

        return json.dumps({"error": f"No meeting found with email_id={email_id}."})

    except Exception as e:
        logger.error(f"Error fetching meeting email: {e}")
        return json.dumps({"error": str(e)})


# breakdown of email_to_meeting_workflow tool
@mcp.tool()  # extract meeting details from email content
async def extract_meeting_details(email_dict: dict) -> str:
    """Extract meeting details from email content"""
    logger.info("Extracting meeting details from email")
    try:
        email_items = list(email_dict.items())
        if not email_items:
            return "❌ Error: No email data provided"

        email_id = email_items[0][1]
        email_info = email_items
        logger.info(f"Processing email: {email_info}, email_items: {email_items}")
        email_body = email_info.get("content", "")
        subject = email_info.get("subject", "No Subject")
        meeting_details = workspace.extract_meeting_details(email_body, subject)

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

        return json.dumps(meeting_details, indent=2)

    except Exception as e:
        logger.error(f"Error extracting meeting details: {e}")
        return f"❌ Error extracting details: {str(e)}"


@mcp.tool()
async def create_calendar_event_only(
    meeting_details: dict, start_time: str = "", duration_hours: int = 1
) -> str:
    """Create calendar event from meeting details"""
    try:
        details = meeting_details

        # Use provided time or default
        if start_time:
            start_dt = datetime.fromisoformat(start_time)
        else:
            start_dt = datetime.now().replace(
                hour=10, minute=0, second=0, microsecond=0
            ) + timedelta(days=1)

        end_dt = start_dt + timedelta(hours=duration_hours)

        event = {
            "summary": details["title"],
            "description": f"Meeting Purpose: {details['purpose']}\n\nKey Topics:\n"
            + "\n".join(f"• {topic}" for topic in details.get("topics", [])),
            "start": {"dateTime": start_dt.isoformat(), "timeZone": "UTC"},
            "end": {"dateTime": end_dt.isoformat(), "timeZone": "UTC"},
            "attendees": [{"email": email} for email in details["attendees"]],
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
        return f"❌ Error creating calendar event: {str(e)}"


@mcp.tool()
async def create_meeting_doc_only(meeting_id: str, meeting_details: dict) -> str:
    """Create meeting document from details"""
    try:
        details = meeting_details

        meeting_context = MeetingContext(
            meeting_title=details["title"],
            attendees=details["attendees"],
            email_content=details.get("email_content", ""),
            meeting_purpose=details["purpose"],
            key_topics=details.get("topics", []),
            action_items=[],
        )

        workspace.meeting_contexts[meeting_id] = meeting_context
        doc_link = workspace.create_meeting_document(meeting_id, meeting_context)

        return json.dumps({"doc_link": doc_link, "meeting_id": meeting_id})
    except Exception as e:
        return f"❌ Error creating meeting doc: {str(e)}"


@mcp.tool()
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


@mcp.tool()  # get recent meeting emails and store them in recent_meeting_emails.json
async def get_recent_meeting_emails() -> str:
    """Get recent emails that appear to be about meetings"""
    try:
        results = (
            workspace.gmail_service.users()
            .messages()
            .list(
                userId="me",
                q='meeting OR "let\'s discuss" OR "schedule a call" OR "set up a meeting"',
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

            sender = ""
            date = ""
            subject = ""
            receiver = ""

            content = base64.urlsafe_b64decode(
                email["payload"]["parts"][0]["body"]["data"]
            ).decode("utf-8")
            snippet = email["snippet"]
            for i in email["payload"]["headers"]:
                if i["name"] == "From":
                    sender = i["value"]
                if i["name"] == "Date":
                    date = i["value"]
                if i["name"] == "Subject":
                    subject = i["value"]
                if i["name"] == "To":
                    receiver = i["value"]

            emails_data[msg["id"]] = {
                "email_id": msg["id"],
                "subject": subject,
                "sender": sender,
                "receiver": receiver,
                "date": date,
                "content": content,
                "snippet": snippet,
            }
        with open(file_path, "w") as file:
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

        print(
            f"Found {len(emails_data)} recent meeting-related emails and stored them in {file_path}"
        )

        return f"✅ Found {len(emails_data)} recent meeting-related emails and stored them in {file_path}"

    except Exception as e:
        return f"❌ Error fetching emails: {str(e)}"


@mcp.tool()  # extract recent meeting emails from recent_meeting_emails.json
async def extract_recent_meeting_emails(emailId: str = None) -> str:
    """Extract recent meeting-related emails from Gmail."""
    try:
        path = os.path.join(GMAIL_DIR, UNPROCESSED_EMAILS_FILE)
        logger.info(f"Reading recent meeting emails from {path}")

        if os.path.exists(path):
            with open(path, "r") as file:
                data = json.load(file)
                for emails_dict in data:
                    for email_id, email_info in emails_dict.items():
                        if emailId and emailId == email_id:
                            return json.dumps({email_id: email_info}, indent=2)
                        elif not emailId:
                            # If no specific emailId provided, return all emails
                            return json.dumps(emails_dict, indent=2)
                # logger.info(f"Loaded {email_data} recent meeting emails from {path}")
        else:
            return "No recent meeting emails found."

        return "No recent meeting emails found."

    except Exception as e:
        return f"❌ Error fetching emails: {str(e)}"


# PROMPTS
@mcp.prompt()
async def extract_meeting_details_prompt(email_id: str) -> str:
    """Extract meeting information from email text"""
    logger.info("Called extract_meeting_details prompt.")
    return """Analyze this email and extract meeting-related information:

First extract the email using the tool 'extract_recent_meeting_emails' and use the response json when invoking 'extract_meeting_details'.
Then call the tool 'extract_meeting_details' to get meeting details with email_dict got from the 'exttract_recent_meeting_emails' response with the same json structure that was given by the 'extract_recent_meeting_emails' tool.

Please identify and extract the following information:

1. **Meeting Title/Subject**: What should this meeting be called?
2. **Meeting Purpose**: What is the main objective or reason for this meeting?
3. **Date and Time**: When is this meeting supposed to happen? Look for:
   - Specific dates (MM/DD/YYYY, Month Day, Year)
   - Relative dates (tomorrow, next week, etc.)
   - Times (10:00 AM, 2:30 PM, etc.)
4. **Duration**: How long is the meeting expected to last?
5. **Attendees**: Who should be invited? Look for:
   - Email addresses
   - Names mentioned
   - Departments or roles referenced
6. **Key Topics**: What will be discussed? Look for:
   - Agenda items
   - Discussion points
   - Questions to address
7. **Location**: Where will the meeting take place?
   - Physical location
   - Virtual meeting details
   - Conference room information
8. **Preparation Required**: What do attendees need to prepare?
   - Documents to review
   - Materials to bring
   - Pre-work assignments

Format your response as a structured analysis that can be used to create a calendar event and meeting document."""


@mcp.prompt()
async def create_meeting_from_email_prompt(
    email_id: str, calendar_id: str = "primary"
) -> str:
    """Guide for creating a complete meeting workflow from an email"""
    logger.info(
        f"Called create_meeting_from_email_workflow prompt for email_id={email_id}."
    )
    return f"""

You are executing a deterministic meeting creation workflow based on a source email with ID `{email_id}`.

**Resources and Toolchain:**

* `get_recent_meeting_emails`       
* `extract_recent_meeting_emails`   
* `extract_meeting_details_prompt`  
* `create_calendar_event_only`
* `create_meeting_doc_only`
* `link_doc_to_calendar`

**Execution Pipeline:**

1. **Ingest Recent Emails**
   Invoke `get_recent_meeting_emails`.
   → Output: `unprocessed_recent_meeting_emails.json`

2. **Locate Target Email**
   Run `extract_recent_meeting_emails` with `{email_id}`.
   → Output: Full email content associated with the specified ID.

3. **Extract Structured Details**
   Use `extract_meeting_details_prompt` on the retrieved email content.
   Pass the same json which was given by the `extract_recent_meeting_emails` tool.
   → Output: Structured meeting details (title, time, participants, agenda, etc.)

4. **Generate Calendar Event**
   Use `create_calendar_event_only` with extracted meeting details.
   Calendar ID to use: `{calendar_id}`
   → Output: Calendar event object including meeting ID and event link.

5. **Generate Meeting Document**
   Use `create_meeting_doc_only` with:

   * Extracted meeting details
   * Meeting ID from the calendar event
     → Output: Meeting document link

6. **Link Document to Calendar**
   Use `link_doc_to_calendar` with:

   * Calendar event ID
   * Meeting document link
     → Result: Calendar event is updated with the linked doc.

7. **Grant Attendee Access**
   Ensure the meeting document is shared with all attendees identified in the meeting details.
   → Result: Each attendee has edit or view access, and the doc link appears in the calendar description.

8. **Return Final Summary**
   Provide a concise JSON-formatted summary including:

   * `meeting_title`
   * `calendar_event_link`
   * `meeting_doc_link`
   * `attendees`
   * `meeting_id`
   * `meeting_details`
   * `meeting_doc_link` (duplicate inclusion intentional for validation)

**Requirements:**

* Maintain referential integrity across all artifacts (ID ↔ link ↔ metadata).
* Ensure no step is skipped or approximated.
* Output must reflect completed linkage across calendar and document layers.
* All tool calls must be real or simulated based on context capability.

Execute this workflow step by step, using the available resources and tools to gather information and create the meeting."""


if __name__ == "__main__":
    # import asyncio
    mcp.run()

    # asyncio.run(extract_recent_meeting_emails("197e639effcaaab3"))
