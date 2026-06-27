"""
sendgrid_tool.py

Tool used by the Monitor Agent.

Responsibility
--------------
Send an email containing:

1. Conversation transcript
2. AI generated summary

This file contains NO AutoGen code.
It is simply a reusable Python tool.
"""

import os

from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from config import EMAIL_SUBJECT

load_dotenv()


class SendGridTool:
    """
    Simple wrapper around the SendGrid API.
    """

    def __init__(self):

        self.api_key = os.getenv("SENDGRID_API_KEY")
        self.from_email = os.getenv("FROM_EMAIL")

        if not self.api_key:
            raise ValueError(
                "SENDGRID_API_KEY not found in .env"
            )

        if not self.from_email:
            raise ValueError(
                "FROM_EMAIL not found in .env"
            )

    async def send_summary(
        self,
        to_email: str,
        summary: str,
        transcript: str,
    ) -> None:
        """
        Send the conversation summary.
        """

        body = f"""
AI Agent Conversation Summary

==================================================

SUMMARY

{summary}

==================================================

FULL CONVERSATION

{transcript}

==================================================

Generated automatically by the Monitor Agent.
"""

        message = Mail(
            from_email=self.from_email,
            to_emails=to_email,
            subject=EMAIL_SUBJECT,
            plain_text_content=body,
        )

        try:

            client = SendGridAPIClient(self.api_key)

            response = client.send(message)

            print()
            print("=" * 60)
            print("EMAIL SENT")
            print("=" * 60)
            print(f"Status Code : {response.status_code}")
            print(f"Recipient   : {to_email}")
            print("=" * 60)
            print()

        except Exception as ex:

            print()
            print("=" * 60)
            print("EMAIL FAILED")
            print("=" * 60)
            print(ex)
            print("=" * 60)
            print()