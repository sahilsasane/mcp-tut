from src.config import logger


async def extract_meeting_details_prompt(email_id: str) -> str:
    """Extract meeting information from email text"""
    logger.info("Called extract_meeting_details prompt.")
    return f"""Analyze this email and extract meeting-related information:

First check if the email is present using 'get_unprocessed_meetings' and then 'get_meeting_email' with the {email_id}.
Then provide the email_id to the tool 'extract_email_details' which will process the email and save it in 'processed_meeting_email.json'.

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


async def create_meeting_from_email_prompt(
    email_id: str, calendar_id: str = "primary"
) -> str:
    """Guide for creating a complete meeting workflow from an email"""
    logger.info(
        f"Called create_meeting_from_email_workflow prompt for email_id={email_id}."
    )
    return f"""You are executing a deterministic meeting creation workflow based on a source email with ID `{email_id}`.

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
