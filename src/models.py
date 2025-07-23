"""Data models for Google Workspace MCP server."""

from dataclasses import dataclass
from typing import List


@dataclass
class MeetingContext:
    """Store meeting context for document generation"""

    meeting_title: str
    attendees: List[str]
    email_content: str
    meeting_purpose: str
    key_topics: List[str]
    action_items: List[str]
