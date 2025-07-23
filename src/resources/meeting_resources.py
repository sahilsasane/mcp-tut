"""MCP resources for Google Workspace server."""

import json
import os

from src.config import (
    GMAIL_DIR,
    PROCESSED_MEETING_EMAILS_FILE,
    UNPROCESSED_EMAILS_FILE,
    logger,
)


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


async def get_processed_meetings() -> str:
    """Dynamic resource showing meetings extracted from emails"""
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
