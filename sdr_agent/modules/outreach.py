"""AI-powered outreach message generation."""

from __future__ import annotations

from anthropic import Anthropic

from ..config import Config
from ..models import Lead, Message, MessageType, Channel


INITIAL_OUTREACH_PROMPT = """You are an expert SDR (Sales Development Representative) writing a
personalized cold outreach email. Your goal is to get a reply, not make a sale.

SENDER INFO:
- Name: {sender_name}
- Title: {sender_title}
- Company: {company_name}
- What we do: {company_description}

PROSPECT INFO:
- Name: {lead_name}
- Title: {lead_title}
- Company: {lead_company}
- Industry: {lead_industry}

RESEARCH:
{research}

RULES:
1. Keep it under 120 words
2. Lead with THEIR world, not yours — reference something specific to them
3. Ask ONE clear question at the end
4. No generic flattery ("I was impressed by...")
5. No pushy language or feature dumps
6. Sound like a human, not a template
7. Subject line should be lowercase, casual, and under 6 words

Return your response in this exact format:
SUBJECT: <subject line>
BODY:
<email body>"""


FOLLOW_UP_PROMPT = """You are an expert SDR writing a follow-up email. This is follow-up #{step_number}
in a sequence.

SENDER INFO:
- Name: {sender_name}
- Company: {company_name}

PROSPECT INFO:
- Name: {lead_name}
- Title: {lead_title}
- Company: {lead_company}

PREVIOUS MESSAGES:
{previous_messages}

RULES:
1. Keep it under 80 words
2. Don't re-pitch — add NEW value (insight, resource, relevant observation)
3. Reference the previous email naturally
4. Different angle than before
5. One clear call to action
6. If this is follow-up #3+, keep it very brief (under 50 words)

Return your response in this exact format:
SUBJECT: <subject line>
BODY:
<email body>"""


class OutreachEngine:
    """Generates personalized outreach messages using AI."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)

    def generate_initial_outreach(
        self, lead: Lead, channel: Channel = Channel.EMAIL
    ) -> Message:
        """Generate a personalized initial outreach message."""
        research_text = ""
        if lead.research:
            research_text = "\n".join(
                f"- {k}: {v}" for k, v in lead.research.items()
            )

        prompt = INITIAL_OUTREACH_PROMPT.format(
            sender_name=self.config.sender.name,
            sender_title=self.config.sender.title,
            company_name=self.config.company.name,
            company_description=self.config.company.description,
            lead_name=lead.name,
            lead_title=lead.title,
            lead_company=lead.company,
            lead_industry=lead.industry,
            research=research_text or "No research available yet.",
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
            message_type=MessageType.INITIAL_OUTREACH,
            subject=subject,
            body=body,
        )

    def generate_follow_up(
        self,
        lead: Lead,
        previous_messages: list[Message],
        step_number: int,
        channel: Channel = Channel.EMAIL,
    ) -> Message:
        """Generate a follow-up message based on conversation history."""
        prev_text = ""
        for msg in previous_messages:
            direction = "FROM US" if not msg.is_inbound else "FROM PROSPECT"
            prev_text += f"\n[{direction}] Subject: {msg.subject}\n{msg.body}\n"

        prompt = FOLLOW_UP_PROMPT.format(
            sender_name=self.config.sender.name,
            company_name=self.config.company.name,
            lead_name=lead.name,
            lead_title=lead.title,
            lead_company=lead.company,
            previous_messages=prev_text or "No previous messages.",
            step_number=step_number,
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
            message_type=MessageType.FOLLOW_UP,
            subject=subject,
            body=body,
        )

    def _parse_message(self, text: str) -> tuple[str, str]:
        """Parse AI response into subject and body."""
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
