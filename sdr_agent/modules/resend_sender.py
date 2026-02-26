"""Email sending via Resend API."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from ..config import Config
from ..models import Lead, Message


RESEND_SEND_URL = "https://api.resend.com/emails"


class ResendSender:
    """Sends outreach emails via the Resend API."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.resend_api_key
        self.from_email = config.resend_from_email

    def send_email(
        self,
        to: str,
        subject: str,
        body: str,
        reply_to: str = "",
    ) -> dict[str, Any]:
        """Send an email via Resend.

        Returns the Resend API response dict (contains 'id' on success).
        """
        if not self.api_key:
            raise ValueError(
                "RESEND_API_KEY is required for sending emails. "
                "Set it in your .env file."
            )
        if not self.from_email:
            raise ValueError(
                "RESEND_FROM_EMAIL is required. "
                "Set it in your .env file (e.g. you@yourdomain.com or Your Name <you@yourdomain.com>)."
            )

        payload: dict[str, Any] = {
            "from": self.from_email,
            "to": [to],
            "subject": subject,
            "text": body,
        }

        if reply_to:
            payload["reply_to"] = reply_to

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            RESEND_SEND_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
                "User-Agent": "FunnelFiller/0.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Resend API error ({exc.code}): {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Resend API: {exc.reason}"
            ) from exc

    def send_outreach_message(
        self, lead: Lead, message: Message
    ) -> dict[str, Any]:
        """Send an outreach Message to a lead via Resend.

        Returns the Resend API response.
        """
        if not lead.email:
            raise ValueError(
                f"Lead {lead.name} ({lead.id}) has no email address. "
                "Enrich the lead first to get their email."
            )

        return self.send_email(
            to=lead.email,
            subject=message.subject,
            body=message.body,
            reply_to=self.config.sender.email,
        )
