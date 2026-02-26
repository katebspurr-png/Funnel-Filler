"""Lead qualification and response analysis using AI."""

from __future__ import annotations

from anthropic import Anthropic

from ..config import Config
from ..models import Lead, Message


QUALIFY_PROMPT = """You are an expert SDR qualifying a prospect. Analyze the lead and their
response to determine qualification level and recommended next action.

OUR COMPANY:
- Name: {company_name}
- What we do: {company_description}
- Target industries: {target_industries}
- Target titles: {target_titles}

PROSPECT:
- Name: {lead_name}
- Title: {lead_title}
- Company: {lead_company}
- Industry: {lead_industry}

CONVERSATION HISTORY:
{conversation}

RESEARCH:
{research}

Score this lead from 0-100 based on:
- Title/role fit (0-25)
- Industry fit (0-25)
- Engagement signals from response (0-25)
- Buying intent signals (0-25)

Respond in this exact format:
SCORE: <number 0-100>
TITLE_FIT: <brief explanation>
INDUSTRY_FIT: <brief explanation>
ENGAGEMENT: <brief explanation>
INTENT: <brief explanation>
NEXT_ACTION: <one of: BOOK_MEETING, SEND_MORE_INFO, FOLLOW_UP, NURTURE, DISQUALIFY>
REASONING: <1-2 sentence summary of why>"""


RESPONSE_ANALYSIS_PROMPT = """Analyze this prospect's reply to our outreach and categorize it.

OUR LAST MESSAGE:
Subject: {our_subject}
{our_body}

THEIR REPLY:
{reply}

Categorize the response as one of:
- POSITIVE: Interested, wants to learn more or meet
- NEUTRAL: Acknowledged but non-committal
- OBJECTION: Has concerns or pushback
- NOT_NOW: Interested but bad timing
- UNSUBSCRIBE: Wants to stop receiving messages
- OUT_OF_OFFICE: Auto-reply or OOO

Respond in this format:
CATEGORY: <category>
SENTIMENT: <positive/neutral/negative>
KEY_POINTS: <bullet points of what they said>
SUGGESTED_REPLY: <brief suggested response, or NONE if not appropriate>"""


class LeadQualifier:
    """Qualifies leads and analyzes responses using AI."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)

    def qualify_lead(self, lead: Lead, messages: list[Message]) -> dict[str, str]:
        """Score and qualify a lead based on profile and conversation."""
        conversation = ""
        for msg in messages:
            direction = "US" if not msg.is_inbound else "PROSPECT"
            conversation += f"[{direction}]: {msg.subject} — {msg.body}\n\n"

        research_text = "\n".join(
            f"- {k}: {v}" for k, v in lead.research.items()
        ) if lead.research else "No research available."

        prompt = QUALIFY_PROMPT.format(
            company_name=self.config.company.name,
            company_description=self.config.company.description,
            target_industries=", ".join(self.config.company.target_industries) or "Any",
            target_titles=", ".join(self.config.company.target_titles) or "Any",
            lead_name=lead.name,
            lead_title=lead.title,
            lead_company=lead.company,
            lead_industry=lead.industry,
            conversation=conversation or "No conversation yet.",
            research=research_text,
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_qualification(response.content[0].text)

    def analyze_response(
        self, our_message: Message, their_reply: str
    ) -> dict[str, str]:
        """Analyze a prospect's reply to determine sentiment and next steps."""
        prompt = RESPONSE_ANALYSIS_PROMPT.format(
            our_subject=our_message.subject,
            our_body=our_message.body,
            reply=their_reply,
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        return self._parse_response_analysis(response.content[0].text)

    def _parse_qualification(self, text: str) -> dict[str, str]:
        result = {}
        for line in text.split("\n"):
            line = line.strip()
            if ":" in line:
                key = line.split(":")[0].strip()
                value = ":".join(line.split(":")[1:]).strip()
                if key.isupper():
                    result[key.lower()] = value
        return result

    def _parse_response_analysis(self, text: str) -> dict[str, str]:
        result = {}
        current_key = None
        current_lines: list[str] = []

        for line in text.split("\n"):
            line = line.strip()
            if ":" in line and line.split(":")[0].strip().isupper():
                if current_key:
                    result[current_key] = "\n".join(current_lines).strip()
                current_key = line.split(":")[0].strip().lower()
                rest = ":".join(line.split(":")[1:]).strip()
                current_lines = [rest] if rest else []
            elif current_key:
                current_lines.append(line)

        if current_key:
            result[current_key] = "\n".join(current_lines).strip()

        return result
