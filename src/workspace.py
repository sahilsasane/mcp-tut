# import os
# import sys

# from dotenv import load_dotenv

# load_dotenv()

# sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import os
import re
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from openai import OpenAI

from src.config import (
    CREDENTIALS_FILE,
    DEFAULT_MEETING_TIME,
    SCOPES,
    TOKEN_FILE,
    logger,
)
from src.models import MeetingContext

load_dotenv()


class GoogleWorkspaceServer:
    """Handles Google Workspace API interactions"""

    def __init__(self):
        self.credentials = None
        self.gmail_service = None
        self.calendar_service = None
        self.drive_service = None
        self.docs_service = None
        self.meeting_contexts: Dict[str, MeetingContext] = {}
        self.authenticate()
        self.openai = OpenAI()

    def authenticate(self):
        """Handle Google OAuth authentication"""
        logger.info("Authenticating with Google APIs...")
        creds = None

        if os.path.exists(TOKEN_FILE):
            creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES
                )
                creds = flow.run_local_server(port=0)

            with open(TOKEN_FILE, "w") as token:
                token.write(creds.to_json())

        self.credentials = creds
        self._initialize_services(creds)
        logger.info("Authentication successful. Services initialized.")

    def _initialize_services(self, creds):
        """Initialize Google API services"""
        self.gmail_service = build("gmail", "v1", credentials=creds)
        self.calendar_service = build("calendar", "v3", credentials=creds)
        self.drive_service = build("drive", "v3", credentials=creds)
        self.docs_service = build("docs", "v1", credentials=creds)

    def extract_meeting_details(
        self, email_content: str, subject: str
    ) -> Dict[str, Any]:
        """Extract meeting details from email content"""
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

        # Find meeting purpose
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

        # Find meeting time
        found_time = None
        for pattern in time_patterns:
            match = re.search(pattern, email_content, re.IGNORECASE)
            if match:
                found_time = match.group(1)
                break

        if not found_time:
            found_time = DEFAULT_MEETING_TIME

        return {
            "title": subject if "meeting" in subject.lower() else f"Meeting: {subject}",
            "attendees": attendees,
            "purpose": purpose,
            "topics": topics,
            "time": found_time,
        }

    def extract_client_req(self, email_content: str, subject: str) -> Dict[str, Any]:
        """Extract client requirement from email"""
        requirement_keywords = [
            "need",
            "require",
            "want",
            "looking for",
            "expecting",
            "request",
        ]

        client_email_pattern = r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"
        clients = re.findall(client_email_pattern, email_content)

        requirement_summary = ""
        for keyword in requirement_keywords:
            if keyword in email_content.lower():
                sentences = email_content.split(".")
                for sentence in sentences:
                    if keyword in sentence.lower():
                        requirement_summary = sentence.strip()
                        break
                break

        if not requirement_summary:
            requirement_summary = f"Requirement regarding {subject}"

        return {
            "title": subject,
            "client_emails": clients,
            "requirement_summary": requirement_summary,
            "source_excerpt": email_content[:500],
        }

    def extract_project_query(self, email_content: str, subject: str) -> Dict[str, Any]:
        """Extract project query or status update request from email"""
        query_keywords = [
            "status",
            "progress",
            "update",
            "delay",
            "milestone",
            "ETA",
            "when",
        ]

        relevant_lines = []
        for line in email_content.split("\n"):
            if any(keyword in line.lower() for keyword in query_keywords):
                relevant_lines.append(line.strip())

        project_reference = (
            subject if "project" in subject.lower() else f"Project: {subject}"
        )

        return {
            "project_subject": project_reference,
            "queries": relevant_lines or ["General inquiry"],
            "source_excerpt": email_content[:500],
        }

    def extract_teams_req(self, email_content: str, subject: str) -> Dict[str, Any]:
        """Extract internal team document sharing or resource request"""
        doc_keywords = [
            "share",
            "document",
            "access",
            "file",
            "upload",
            "attachment",
            "send",
        ]

        link_pattern = r"https?://[^\s]+"
        links_found = re.findall(link_pattern, email_content)

        matched_lines = []
        for line in email_content.split("\n"):
            if any(keyword in line.lower() for keyword in doc_keywords):
                matched_lines.append(line.strip())

        return {
            "title": subject,
            "requested_docs": matched_lines or ["General document request"],
            "linked_resources": links_found,
            "source_excerpt": email_content[:500],
        }

    def create_meeting_document(self, meeting_id: str, context: MeetingContext) -> str:
        """Create a Google Doc for the meeting"""
        try:
            doc = {"title": f"Meeting Notes - {context.meeting_title}"}
            document = self.docs_service.documents().create(body=doc).execute()
            document_id = document.get("documentId")

            content = self._generate_meeting_document_content(context)
            requests = [{"insertText": {"location": {"index": 1}, "text": content}}]

            self.docs_service.documents().batchUpdate(
                documentId=document_id, body={"requests": requests}
            ).execute()

            # Share document with attendees
            self._share_document_with_attendees(document_id, context.attendees)

            return f"https://docs.google.com/document/d/{document_id}"

        except Exception as e:
            logger.error(f"Error creating document: {e}")
            return ""

    def _generate_meeting_document_content(self, context: MeetingContext) -> str:
        """Generate the content for the meeting document"""
        return f"""Meeting: {context.meeting_title}
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

    def _share_document_with_attendees(self, document_id: str, attendees: list):
        """Share the document with all attendees"""
        for attendee in attendees:
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
                    logger.warning(f"Could not share with {attendee}: {e}")


# Global workspace instance
workspace = GoogleWorkspaceServer()
# workspace.extract_email_details(
#     email_content="Hi Team,\r\n\r\nI hope you\u2019re doing well. I\u2019d like to schedule a project kickoff meeting to\r\ndiscuss the next steps for the new product launch. We need to align on the\r\nproject timeline, key deliverables, and responsibilities.\r\n\r\nProposed topics:\r\n\r\n    Finalizing the project scope\r\n\r\n    Assigning roles and tasks\r\n\r\n    Setting key milestones and deadlines\r\n\r\n    Addressing any immediate concerns\r\n\r\nSuggested date and time: Friday at 3:00 PM. Please confirm if this works or\r\npropose an alternative.\r\n\r\nAttendees: alice@example.com, bob@example.com, charlie@example.com\r\n\r\nLet me know if there\u2019s anything else to prepare in advance.\r\n\r\nBest regards,\r\nDavid\r\n",
#     subject="Project Kickoff Meeting",
# )
