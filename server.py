from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

from src.prompts.client_inquiry_prompts import (
    client_inquiry_response_prompt,
    internal_team_query_prompt,
    meeting_scheduling_workflow_prompt,
    project_related_response_prompt,
)
from src.prompts.meeting_prompts import (
    create_meeting_from_email_prompt,
    extract_meeting_details_prompt,
)
from src.resources.company_resources import (
    get_all_info,
    get_company_docs,
    get_company_info,
    get_solution_info,
)
from src.resources.meeting_resources import (
    get_meeting_email,
    get_processed_meetings,
    get_unprocessed_meetings,
)
from src.resources.project_resources import (
    get_feature_updates,
    get_project_info,
    get_project_status,
)
from src.tools.gmail_tools import create_draft_email_and_send
from src.tools.meeting_tools import (
    cancel_meeting,
    check_conflicting_meetings,
    create_calendar_event_only,
    create_meeting_doc_only,
    # determine_workflow_prompt,
    # create_recurring_meeting,
    extract_email_details,
    extract_recent_emails,
    get_recent_emails,
    link_doc_to_calendar,
    reschedule_meeting,
)

load_dotenv()

# Initialize MCP server
mcp = FastMCP("Google Workspace Meeting Assistant")

# ============================================================================
# MCP RESOURCES
# ============================================================================


@mcp.resource("gmail://meeting-emails")
async def unprocessed_meetings_resource() -> str:
    """Get recent meeting-related emails"""
    return await get_unprocessed_meetings()


@mcp.resource("gmail://processed-meetings")
async def processed_meetings_resource() -> str:
    """Dynamic resource showing meetings extracted from emails"""
    return await get_processed_meetings()


@mcp.resource("gmail://meeting-emails/{email_id}")
async def meeting_email_resource(email_id: str) -> str:
    """Get details of a specific meeting email by ID"""
    return await get_meeting_email(email_id)


@mcp.resource("project://info")
async def project_info_resource() -> str:
    """Get project information from the knowledge repository"""
    return await get_project_info()


@mcp.resource("project://feature-updates")
async def feature_updates_resource() -> str:
    """Get feature updates from the knowledge repository"""
    return await get_feature_updates()


@mcp.resource("project://status")
async def project_status_resource() -> str:
    """Get project status from the knowledge repository"""
    return await get_project_status()


@mcp.resource("company://info")
async def company_info_resource() -> str:
    """Get company information from the knowledge repository"""
    return await get_company_info()


@mcp.resource("company://solution-info")
async def solution_info_resource() -> str:
    """Get solution information from the knowledge repository"""
    return await get_solution_info()


@mcp.resource("company://all-info")
async def all_info_resource() -> str:
    """Get all company information from the knowledge repository"""
    return await get_all_info()


@mcp.resource("company://docs")
async def company_docs_resource() -> str:
    """Get company documents from the knowledge repository"""
    return await get_company_docs()


# ============================================================================
# MCP TOOLS
# ============================================================================


@mcp.tool()
async def extract_email_details_tool(email_id: str) -> str:
    """Extract meeting details from email content"""
    return await extract_email_details(email_id)


@mcp.tool()
async def create_calendar_event_only_tool(
    email_id: str, start_time: str = "", duration_hours: int = 1
) -> str:
    """Create calendar event from meeting details"""
    return await create_calendar_event_only(email_id, start_time, duration_hours)


@mcp.tool()
async def create_meeting_doc_only_tool(meeting_id: str, email_id: str) -> str:
    """Create meeting document from details"""
    return await create_meeting_doc_only(meeting_id, email_id)


@mcp.tool()
async def link_doc_to_calendar_tool(event_id: str, doc_link: str) -> str:
    """Add document link to existing calendar event"""
    return await link_doc_to_calendar(event_id, doc_link)


@mcp.tool()
async def get_recent_emails_tool() -> str:
    """Get recent emails that appear to be about meetings"""
    return await get_recent_emails()


@mcp.tool()
async def extract_recent_emails_tool(emailId: str = None) -> str:
    """Extract recent meeting-related emails from Gmail."""
    return await extract_recent_emails(emailId)


@mcp.tool()
async def check_conflicting_meetings_tool(
    start_time: str, end_time: str, calendar_id: str = "primary"
) -> str:
    """Check for conflicting meetings in the calendar."""
    return await check_conflicting_meetings(start_time, end_time, calendar_id)


@mcp.tool()
async def cancel_meeting_tool(meeting_id: str) -> str:
    """Cancel a meeting in the calendar."""
    return await cancel_meeting(meeting_id)


@mcp.tool()
async def reschedule_meeting_tool(
    meeting_id: str, new_start_time: str, new_end_time: str
) -> str:
    """Reschedule a meeting in the calendar."""
    return await reschedule_meeting(meeting_id, new_start_time, new_end_time)


@mcp.tool()
async def create_draft_email_and_send_tool(
    subject: str,
    body: str,
    to: str = "",
    cc: str = "",
    bcc: str = "",
) -> dict:
    """Create a draft email with the given subject and body and send it."""
    return await create_draft_email_and_send(subject, body, to, cc, bcc)


@mcp.tool()
async def get_resource_info_tool(resource_uri: str) -> str:
    """Get information from a specific resource URI (e.g., project://info, company://solution-info)"""
    # Map resource URIs to their corresponding functions
    resource_map = {
        "project://info": get_project_info,
        "project://feature-updates": get_feature_updates,
        "project://status": get_project_status,
        "company://info": get_company_info,
        "company://solution-info": get_solution_info,
        "company://all-info": get_all_info,
        "company://docs": get_company_docs,
        "gmail://meeting-emails": get_unprocessed_meetings,
        "gmail://processed-meetings": get_processed_meetings,
    }

    if resource_uri in resource_map:
        return await resource_map[resource_uri]()
    elif resource_uri.startswith("gmail://meeting-emails/"):
        # Handle specific email ID requests
        email_id = resource_uri.split("/")[-1]
        return await get_meeting_email(email_id)
    else:
        return f"Resource '{resource_uri}' not found or not accessible."


# ============================================================================
# MCP PROMPTS
# ============================================================================


@mcp.prompt()
async def extract_meeting_details_prompt_handler(email_id: str) -> str:
    """Extract meeting information from email text"""
    return await extract_meeting_details_prompt(email_id)


@mcp.prompt()
async def create_meeting_from_email_prompt_handler(
    email_id: str, calendar_id: str = "primary"
) -> str:
    """Guide for creating a complete meeting workflow from an email"""
    return await create_meeting_from_email_prompt(email_id, calendar_id)


@mcp.prompt()
async def meeting_scheduling_prompt_handler(
    email_id: str = None, calendar_id: str = "primary"
) -> str:
    """Handle meeting and scheduling workflows"""
    return await meeting_scheduling_workflow_prompt(email_id, calendar_id)


@mcp.prompt()
async def client_inquiry_prompt_handler(email_id: str = None) -> str:
    """Handle client inquiry workflows with email response"""
    return await client_inquiry_response_prompt(email_id)


@mcp.prompt()
async def project_response_prompt_handler(email_id: str = None) -> str:
    """Handle project-related communications with email response"""
    return await project_related_response_prompt(email_id)


@mcp.prompt()
async def internal_team_prompt_handler(email_id: str = None) -> str:
    """Handle internal team queries with email response"""
    return await internal_team_query_prompt(email_id)


# @mcp.prompt()
# async def auto_classify_workflow_prompt_handler(
#     email_content: str, email_id: str = None
# ) -> str:
#     """Automatically determine and return appropriate workflow prompt"""
#     return await determine_workflow_prompt(email_content, email_id)


# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    mcp.run()
