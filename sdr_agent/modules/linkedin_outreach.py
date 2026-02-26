"""LinkedIn outreach message generation and profile management."""

from __future__ import annotations

from anthropic import Anthropic

from ..config import Config
from ..models import Lead, Message, MessageType, Channel


CONNECTION_REQUEST_PROMPT = """You are an expert SDR writing a LinkedIn connection request note.
The note must be under 300 characters (LinkedIn limit).

SENDER INFO:
- Name: {sender_name}
- Title: {sender_title}
- Company: {company_name}

PROSPECT INFO:
- Name: {lead_name}
- Title: {lead_title}
- Company: {lead_company}
- Industry: {lead_industry}

RESEARCH:
{research}

RULES:
1. MUST be under 300 characters (this is a hard LinkedIn limit)
2. Be genuine — mention a specific shared interest or mutual connection point
3. No selling in the connection request
4. Sound like a human, not a template
5. Give a reason to connect (shared industry, common challenge, interesting content)

Return ONLY the connection note text, nothing else."""


LINKEDIN_MESSAGE_PROMPT = """You are an expert SDR writing a LinkedIn direct message to a connection.
Keep it conversational and short — people read LinkedIn messages on mobile.

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

PREVIOUS LINKEDIN MESSAGES:
{previous_messages}

RULES:
1. Keep it under 100 words
2. Lead with value — share an insight, resource, or observation relevant to them
3. Ask ONE question to start a conversation
4. No pitch, no product features, no "I'd love to show you a demo"
5. Sound natural, like texting a colleague
6. If this is a follow-up, reference the previous message and add something new

Return ONLY the message text, nothing else."""


LINKEDIN_FOLLOW_UP_PROMPT = """You are an expert SDR writing a LinkedIn follow-up message.
The prospect hasn't replied to your previous message(s).

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
1. Keep it under 60 words
2. Don't re-pitch — add NEW value
3. Be casual and brief, like a text message
4. One clear question or share
5. If 2+ follow-ups already sent, keep it ultra-brief (under 30 words)

Return ONLY the message text, nothing else."""


class LinkedInOutreach:
    """Generates LinkedIn connection requests and messages."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)

    def generate_connection_request(self, lead: Lead) -> Message:
        """Generate a LinkedIn connection request note (under 300 chars)."""
        research_text = ""
        if lead.research:
            research_text = "\n".join(
                f"- {k}: {v}" for k, v in lead.research.items()
            )

        prompt = CONNECTION_REQUEST_PROMPT.format(
            sender_name=self.config.sender.name,
            sender_title=self.config.sender.title,
            company_name=self.config.company.name,
            lead_name=lead.name,
            lead_title=lead.title,
            lead_company=lead.company,
            lead_industry=lead.industry,
            research=research_text or "No research available yet.",
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=256,
            messages=[{"role": "user", "content": prompt}],
        )

        note = response.content[0].text.strip()
        # Enforce LinkedIn's 300 character limit
        if len(note) > 300:
            note = note[:297] + "..."

        return Message(
            lead_id=lead.id,
            channel=Channel.LINKEDIN,
            message_type=MessageType.INITIAL_OUTREACH,
            subject="Connection Request",
            body=note,
        )

    def generate_message(
        self, lead: Lead, previous_messages: list[Message] | None = None
    ) -> Message:
        """Generate a LinkedIn direct message."""
        research_text = ""
        if lead.research:
            research_text = "\n".join(
                f"- {k}: {v}" for k, v in lead.research.items()
            )

        prev_text = ""
        if previous_messages:
            for msg in previous_messages:
                direction = "FROM US" if not msg.is_inbound else "FROM PROSPECT"
                prev_text += f"\n[{direction}]: {msg.body}\n"

        is_follow_up = bool(previous_messages)

        if is_follow_up:
            prompt = LINKEDIN_FOLLOW_UP_PROMPT.format(
                sender_name=self.config.sender.name,
                company_name=self.config.company.name,
                lead_name=lead.name,
                lead_title=lead.title,
                lead_company=lead.company,
                previous_messages=prev_text,
            )
        else:
            prompt = LINKEDIN_MESSAGE_PROMPT.format(
                sender_name=self.config.sender.name,
                sender_title=self.config.sender.title,
                company_name=self.config.company.name,
                company_description=self.config.company.description,
                lead_name=lead.name,
                lead_title=lead.title,
                lead_company=lead.company,
                lead_industry=lead.industry,
                research=research_text or "No research available yet.",
                previous_messages=prev_text or "None — this is the first message.",
            )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        body = response.content[0].text.strip()

        return Message(
            lead_id=lead.id,
            channel=Channel.LINKEDIN,
            message_type=MessageType.FOLLOW_UP if is_follow_up else MessageType.INITIAL_OUTREACH,
            subject="LinkedIn Message",
            body=body,
        )
