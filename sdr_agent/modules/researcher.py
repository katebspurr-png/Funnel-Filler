"""Lead research and enrichment using AI."""

from __future__ import annotations

from anthropic import Anthropic

from ..config import Config
from ..models import Lead


RESEARCH_PROMPT = """You are a sales research assistant. Given a lead's basic information,
provide a concise research brief that an SDR can use for personalized outreach.

Lead info:
- Name: {name}
- Company: {company}
- Title: {title}
- Industry: {industry}
- LinkedIn: {linkedin_url}
- Notes: {notes}

Provide your analysis in the following format:

COMPANY SUMMARY: (2-3 sentences about what the company does)
ROLE ANALYSIS: (What this person likely cares about given their title)
PAIN POINTS: (3 likely pain points based on role and industry)
CONVERSATION STARTERS: (3 personalized angles for outreach)
QUALIFICATION NOTES: (Any signals about whether this is a good fit)"""


class LeadResearcher:
    """Researches and enriches lead profiles using AI."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)

    def research_lead(self, lead: Lead) -> dict[str, str]:
        """Generate a research brief for a lead."""
        prompt = RESEARCH_PROMPT.format(
            name=lead.name,
            company=lead.company,
            title=lead.title,
            industry=lead.industry,
            linkedin_url=lead.linkedin_url,
            notes=lead.notes,
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text
        research = self._parse_research(text)
        return research

    def _parse_research(self, text: str) -> dict[str, str]:
        """Parse structured research output into a dict."""
        sections = {}
        current_key = None
        current_lines: list[str] = []

        for line in text.split("\n"):
            line = line.strip()
            if ":" in line and line.split(":")[0].isupper():
                if current_key:
                    sections[current_key] = "\n".join(current_lines).strip()
                current_key = line.split(":")[0].strip().lower().replace(" ", "_")
                rest = ":".join(line.split(":")[1:]).strip()
                current_lines = [rest] if rest else []
            elif current_key:
                current_lines.append(line)

        if current_key:
            sections[current_key] = "\n".join(current_lines).strip()

        return sections
