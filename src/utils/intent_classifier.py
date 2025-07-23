from openai import OpenAI

from src.config import logger


async def extract_intent(email_content: str) -> str:
    """Extract intent from email content using OpenAI"""
    categories = [
        "meeting_invitation",
        "reschedule_meeting",
        "cancel_meeting",
        "recurring_meeting_setup",
        "client_inquiry",
        "information_request",
        "feature_update",
        "project_status",
        "doc_sharing_request",
    ]

    client = OpenAI()

    response = client.responses.create(
        model="gpt-4o-mini",
        instructions=f"You will be provided with the content of an email. You have to identify the intent of the email from the categories {categories} and respond with the most appropriate one word category only.",
        input=email_content,
    )

    response_json = response.model_dump()

    intent = ""
    try:
        # Navigate the response structure correctly
        output = response_json.get("output", [])
        if output and len(output) > 0:
            content = output[0].get("content", [])
            if content and len(content) > 0:
                intent = content[0].get("text", "").strip()

        if not intent:
            intent = "information_request"  # Default fallback

    except (IndexError, AttributeError, KeyError) as e:
        logger.error(f"Error parsing OpenAI response: {e}")
        logger.error(f"Response structure: {response_json}")
        intent = "information_request"  # Default fallback

    return intent
