import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from src.config import logger
from src.workspace import workspace


async def create_draft_email_and_send(
    subject: str,
    body: str,
    to: str = "",
    cc: str = "",
    bcc: str = "",
):
    """Create a draft email with the given subject and body and send it"""
    try:
        logger.info(f"Creating and sending email: {subject}")

        # Create the email message
        message = MIMEMultipart()
        message["To"] = to
        message["Subject"] = subject

        if cc:
            message["Cc"] = cc
        if bcc:
            message["Bcc"] = bcc

        # Add body to email
        message.attach(MIMEText(body, "plain"))

        # Convert to raw format
        raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode("utf-8")

        # Send the email
        send_message = {"raw": raw_message}

        result = (
            workspace.gmail_service.users()
            .messages()
            .send(userId="me", body=send_message)
            .execute()
        )

        logger.info(f"Email sent successfully. Message ID: {result['id']}")

        return {
            "status": "success",
            "message_id": result["id"],
            "thread_id": result.get("threadId"),
            "label_ids": result.get("labelIds", []),
            "details": {"subject": subject, "to": to, "cc": cc, "bcc": bcc},
        }

    except Exception as e:
        logger.error(f"Error sending email: {str(e)}")
        return {"status": "error", "message": str(e)}
