"""Configuration and constants for Google Workspace MCP server."""

import logging

# Google API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/spreadsheets",
]

# File paths
GMAIL_DIR = "src/data/gmail"
KNOWLEDGE_DIR = "src/data/knowledge-repository"
PROJECT_INFO_DIR = "src/data/project-repository"
CREDENTIALS_FILE = "src/secrets/credentials.json"
TOKEN_FILE = "src/secrets/token.json"
UNPROCESSED_EMAILS_FILE = "unprocessed_emails.json"
PROCESSED_MEETING_EMAILS_FILE = "processed_meeting_emails.json"
PROCESSED_CLIENT_EMAILS_FILE = "processed_client_emails.json"
PROCESSED_PROJECT_EMAILS_FILE = "processed_project_emails.json"
PROCESSED_TEAMS_EMAILS_FILE = "processed_teams_emails.json"

COMPANY_INFO = "company_info.json"
INTERNAL_DOCS = "internal_docs.json"
PROJECT_INFO = "project_info.json"


# Default meeting settings
DEFAULT_MEETING_TIME = "10:00 AM"
DEFAULT_MEETING_DURATION_HOURS = 1

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)
logger = logging.getLogger("GoogleWorkspaceMCP")
