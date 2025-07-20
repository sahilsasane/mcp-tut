# Google Workspace MCP Server & Chatbot

A comprehensive Model Context Protocol (MCP) server and chatbot for automating Google Workspace operations, specifically focused on meeting management from email workflows.

## Overview

This project consists of two main components:

1. **`mcp_server.py`** - MCP Server providing Google Workspace integration tools and resources
2. **`mcp_chatbot.py`** - Interactive chatbot client for executing workflows via natural language

The system enables automated meeting creation workflows by processing meeting-related emails, extracting relevant information, creating calendar events, generating meeting documents, and linking everything together seamlessly.

## Features

### Core Functionality

- **Email Processing**: Automatically fetch and process meeting-related emails from Gmail
- **Meeting Extraction**: Extract meeting details (title, attendees, time, purpose) from email content
- **Calendar Integration**: Create Google Calendar events with extracted meeting information
- **Document Generation**: Automatically create Google Docs for meeting notes and agendas
- **Cross-Platform Linking**: Link meeting documents to calendar events for seamless access
- **Access Management**: Share meeting documents with attendees automatically

### MCP Server (`mcp_server.py`)

The MCP server provides a comprehensive set of tools and resources for Google Workspace automation:

#### Resources

- **`gmail://meeting-emails`**: Access unprocessed meeting-related emails
- **`gmail://processed-meetings`**: View processed meeting data
- **`gmail://meeting-emails/{email_id}`**: Get specific meeting email by ID

#### Tools

1. **`get_recent_meeting_emails()`**
   - Fetches recent emails containing meeting-related keywords
   - Stores results in `gmail/unprocessed_recent_meeting_emails.json`
   - Searches for terms like "meeting", "let's discuss", "schedule a call"

2. **`extract_recent_meeting_emails(emailId)`**
   - Extracts specific email content from stored meeting emails
   - Returns full email details including subject, sender, content, and metadata

3. **`extract_meeting_details(email_dict)`**
   - Analyzes email content to extract structured meeting information
   - Uses regex patterns to identify dates, times, attendees, and topics
   - Stores processed results for workflow continuation

4. **`create_calendar_event_only(meeting_details, start_time, duration_hours)`**
   - Creates Google Calendar events from extracted meeting details
   - Supports custom scheduling and duration settings
   - Returns event ID and links for further processing

5. **`create_meeting_doc_only(meeting_id, meeting_details)`**
   - Generates Google Docs with meeting templates
   - Includes agenda, attendee list, and action items sections
   - Automatically shares with all meeting participants

6. **`link_doc_to_calendar(event_id, doc_link)`**
   - Links meeting documents to existing calendar events
   - Updates event descriptions with document access links

#### Prompts

1. **`extract_meeting_details_prompt(email_id)`**
   - Guides AI to extract comprehensive meeting information from emails
   - Provides structured analysis template for consistent results

2. **`create_meeting_from_email_prompt(email_id, calendar_id)`**
   - Complete workflow orchestration prompt
   - Defines step-by-step execution pipeline for email-to-meeting automation

### Chatbot Client (`mcp_chatbot.py`)

The chatbot provides an interactive interface for executing MCP server functionality:

#### Key Features

- **Multi-Server Connection**: Connects to multiple MCP servers simultaneously
- **OpenAI Integration**: Uses GPT models for natural language processing
- **Resource Access**: Direct access to Gmail resources via simple commands
- **Prompt Execution**: Execute predefined workflows through chat interface
- **Tool Orchestration**: Automatically calls appropriate tools based on user queries

#### Interactive Commands

- **`@meeting-emails`**: Display recent meeting-related emails
- **`@processed-meetings`**: Show processed meeting data
- **`@meeting-emails/<email_id>`**: Get specific email details
- **`/resources`**: List all available MCP resources
- **`/prompts`**: Display available workflow prompts
- **`/prompt <name> <args>`**: Execute specific prompts with parameters

#### Usage Examples

```bash
# Get recent meeting emails
@meeting-emails

# Process specific email for meeting creation
/prompt create_meeting_from_email_prompt email_id=abc123

# Extract details from specific email
/prompt extract_meeting_details_prompt email_id=abc123

# Natural language queries
"Create a meeting from the email with subject 'Project Kickoff'"
"Schedule the quarterly review meeting for next week"
```

## Installation & Setup

### Prerequisites

- Python 3.13+
- Google Workspace account with API access
- OpenAI API key (for chatbot)

### Dependencies

```toml
dependencies = [
    "google-api-python-client>=2.175.0",
    "google-auth-httplib2>=0.2.0", 
    "google-auth-oauthlib>=1.2.2",
    "mcp[cli]>=1.10.1",
    "openai>=1.93.1",
    # ... see pyproject.toml for complete list
]
```

### Google API Setup

1. **Enable APIs**: Enable Gmail API, Calendar API, Drive API, and Docs API in Google Cloud Console
2. **Create Credentials**: Download `credentials.json` from Google Cloud Console
3. **OAuth Flow**: Run the server once to complete OAuth authentication
4. **Token Storage**: `token.json` will be created for future authentication

### Environment Configuration

1. **Server Configuration**: Update `server_config.json` with proper server parameters
2. **Environment Variables**: Create `.env` file with OpenAI API key:
   ```
   OPENAI_API_KEY=your_openai_api_key_here
   ```

## Usage

### Running the MCP Server

```bash
# Direct execution
python mcp_server.py

# Via UV (recommended)
uv run mcp_server.py
```

### Running the Chatbot

```bash
python mcp_chatbot.py
```

### Complete Workflow Example

1. **Start the chatbot**:
   ```bash
   python mcp_chatbot.py
   ```

2. **Fetch recent meeting emails**:
   ```
   Query: @meeting-emails
   ```

3. **Create meeting from specific email**:
   ```
   Query: /prompt create_meeting_from_email_prompt email_id=197e639effcaaab3
   ```

4. **Natural language interaction**:
   ```
   Query: Create a calendar event and meeting doc for the project discussion email
   ```

## Architecture

### Data Flow

```
Gmail API → Email Processing → Meeting Extraction → Calendar Event Creation
                                      ↓
Google Docs Creation ← Document Linking ← Meeting Document Template
```

### File Structure

```
gmail/
├── unprocessed_recent_meeting_emails.json  # Raw email data
└── processed_recent_meeting_emails.json    # Extracted meeting details

credentials.json                             # Google API credentials
token.json                                   # OAuth tokens
server_config.json                          # MCP server configuration
```

### Core Classes

- **`GoogleWorkspaceServer`**: Main server class handling Google API integrations
- **`MeetingContext`**: Data structure for meeting information storage
- **`MCP_ChatBot`**: Client interface for interactive MCP usage

## Security & Privacy

- **OAuth 2.0**: Secure authentication with Google APIs
- **Scoped Access**: Minimal required permissions for Gmail, Calendar, Drive, and Docs
- **Local Storage**: Credentials stored locally, not transmitted to external services
- **Access Control**: Meeting documents automatically shared only with identified attendees

## Error Handling

- Comprehensive error logging throughout both server and client
- Graceful fallbacks for missing email data
- Automatic retry mechanisms for API failures
- User-friendly error messages in chatbot interface

## Limitations

- Requires active Google Workspace account
- Email parsing relies on common meeting-related keywords and patterns
- Time zone handling defaults to UTC
- Calendar events created in primary calendar only

## Contributing

When modifying the system:

1. **Server Extensions**: Add new tools as `@mcp.tool()` decorated functions
2. **Resource Additions**: Use `@mcp.resource()` for new data sources  
3. **Prompt Development**: Create new workflow prompts with `@mcp.prompt()`
4. **Testing**: Test both server and chatbot components independently

## API Scopes Required

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",      # Email access
    "https://www.googleapis.com/auth/calendar",          # Calendar management  
    "https://www.googleapis.com/auth/drive",             # File sharing
    "https://www.googleapis.com/auth/documents",         # Document creation
    "https://www.googleapis.com/auth/spreadsheets",      # Future spreadsheet support
]
```

## Future Enhancements

- Support for recurring meetings
- Integration with Google Meet for video calls
- Advanced email parsing with NLP models
- Multi-language support for international teams
- Integration with project management tools
- Automated follow-up email generation

---

*This project demonstrates advanced MCP server development with real-world Google Workspace integration, showcasing automated workflow orchestration through natural language interfaces.*