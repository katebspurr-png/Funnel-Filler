"""Meeting scheduling and calendar link generation."""

from __future__ import annotations

from anthropic import Anthropic

from ..config import Config
from ..models import Lead, Message, MessageType, Channel


MEETING_REQUEST_PROMPT = """You are an expert SDR writing a meeting request email.
The prospect has shown interest and it's time to book a call.

SENDER INFO:
- Name: {sender_name}
- Title: {sender_title}
- Company: {company_name}
- Calendar link: {calendar_link}

PROSPECT:
- Name: {lead_name}
- Title: {lead_title}
- Company: {lead_company}

CONVERSATION CONTEXT:
{context}

RULES:
1. Keep it under 80 words
2. Reference their interest or something specific from the conversation
3. Make it easy — provide the calendar link
4. Suggest a specific timeframe ("this week" or "next Tuesday")
5. Be warm but professional
6. If no calendar link is available, suggest 2-3 specific time slots

Return your response in this exact format:
SUBJECT: <subject line>
BODY:
<email body>"""


class MeetingScheduler:
    """Handles meeting scheduling and booking requests."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)

    def generate_meeting_request(
        self, lead: Lead, messages: list[Message], channel: Channel = Channel.EMAIL
    ) -> Message:
        """Generate a personalized meeting request message."""
        context = ""
        for msg in messages[-3:]:  # Last 3 messages for context
            direction = "US" if not msg.is_inbound else "PROSPECT"
            context += f"[{direction}]: {msg.body}\n\n"

        calendar_link = self.config.sender.calendar_link or "No calendar link configured"

        prompt = MEETING_REQUEST_PROMPT.format(
            sender_name=self.config.sender.name,
            sender_title=self.config.sender.title,
            company_name=self.config.company.name,
            calendar_link=calendar_link,
            lead_name=lead.name,
            lead_title=lead.title,
            lead_company=lead.company,
            context=context or "Initial outreach — prospect expressed interest.",
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        subject, body = self._parse_message(text)

        return Message(
            lead_id=lead.id,
            channel=channel,
            message_type=MessageType.MEETING_REQUEST,
            subject=subject,
            body=body,
        )

    def _parse_message(self, text: str) -> tuple[str, str]:
        subject = ""
        body = ""
        in_body = False

        for line in text.split("\n"):
            if line.strip().upper().startswith("SUBJECT:"):
                subject = line.split(":", 1)[1].strip()
            elif line.strip().upper().startswith("BODY:"):
                in_body = True
            elif in_body:
                body += line + "\n"

        return subject, body.strip()
