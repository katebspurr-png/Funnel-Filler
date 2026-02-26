"""Lead scoring using AI analysis + configurable rule-based adjustments."""

from __future__ import annotations

import json
import re

from anthropic import Anthropic

from ..config import Config
from ..models import Lead


SCORING_PROMPT = """You are a sales lead scoring expert. Analyze this lead and assign a score from 0 to 100
indicating how likely they are to be a good fit and convert to a meeting.

Lead info:
- Name: {name}
- Title: {title}
- Company: {company}
- Industry: {industry}
- Email: {email}
- LinkedIn: {linkedin_url}
- Notes: {notes}

Research/enrichment data:
{research}

Our company:
- Name: {company_name}
- Description: {company_description}

Scoring guidelines:
- 80-100: Excellent fit — senior decision-maker at a relevant company, strong signals
- 60-79: Good fit — right profile but missing some signals
- 40-59: Moderate — could be a fit but needs more qualification
- 20-39: Weak — unlikely fit but not impossible
- 0-19: Poor fit — wrong persona, company, or clear disqualifiers

Respond in this exact JSON format only:
{{"score": <number>, "reasoning": "<1-2 sentence explanation>", "strengths": ["<strength1>", "<strength2>"], "concerns": ["<concern1>", "<concern2>"]}}"""


# Default scoring rules — each rule adds/subtracts points from the AI base score
DEFAULT_RULES: list[dict] = [
    # Title signals
    {"field": "title", "contains": ["ceo", "cto", "cfo", "coo", "chief"], "points": 15, "label": "C-suite title"},
    {"field": "title", "contains": ["vp", "vice president"], "points": 12, "label": "VP-level"},
    {"field": "title", "contains": ["director", "head of"], "points": 10, "label": "Director-level"},
    {"field": "title", "contains": ["manager"], "points": 5, "label": "Manager-level"},
    {"field": "title", "contains": ["intern", "assistant", "coordinator"], "points": -10, "label": "Junior role"},
    # Data completeness
    {"field": "email", "exists": True, "points": 10, "label": "Has email"},
    {"field": "linkedin_url", "exists": True, "points": 5, "label": "Has LinkedIn"},
    # Engagement signals
    {"field": "research", "exists": True, "points": 5, "label": "Has research data"},
]


class LeadScorer:
    """Scores leads using AI analysis combined with rule-based adjustments."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)
        self.rules = DEFAULT_RULES

    def score_lead(self, lead: Lead) -> dict:
        """Score a lead using AI + rules. Returns score details dict."""
        ai_result = self._ai_score(lead)
        ai_score = ai_result.get("score", 50)

        rule_adjustments, rule_total = self._apply_rules(lead)

        # Combine: AI score + rule adjustments, clamped to 0-100
        final_score = max(0, min(100, ai_score + rule_total))

        return {
            "score": final_score,
            "ai_score": ai_score,
            "rule_adjustment": rule_total,
            "reasoning": ai_result.get("reasoning", ""),
            "strengths": ai_result.get("strengths", []),
            "concerns": ai_result.get("concerns", []),
            "rule_details": rule_adjustments,
        }

    def _ai_score(self, lead: Lead) -> dict:
        """Get AI-generated score and reasoning."""
        research_str = json.dumps(lead.research, indent=2) if lead.research else "No data"

        prompt = SCORING_PROMPT.format(
            name=lead.name,
            title=lead.title,
            company=lead.company,
            industry=lead.industry,
            email=lead.email,
            linkedin_url=lead.linkedin_url,
            notes=lead.notes,
            research=research_str,
            company_name=self.config.company.name,
            company_description=self.config.company.description,
        )

        response = self.client.messages.create(
            model=self.config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )

        text = response.content[0].text.strip()

        # Extract JSON from response (handle markdown code blocks)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group())
            except json.JSONDecodeError:
                pass

        return {"score": 50, "reasoning": "Could not parse AI response"}

    def _apply_rules(self, lead: Lead) -> tuple[list[dict], int]:
        """Apply rule-based scoring adjustments. Returns (details, total_points)."""
        adjustments: list[dict] = []
        total = 0

        for rule in self.rules:
            field_name = rule["field"]
            value = getattr(lead, field_name, None)

            matched = False

            if "contains" in rule:
                # Check if field value contains any of the keywords (case-insensitive)
                if isinstance(value, str) and value:
                    lower_val = value.lower()
                    matched = any(kw.lower() in lower_val for kw in rule["contains"])

            elif "exists" in rule:
                # Check if field has a non-empty value
                if field_name == "research":
                    matched = bool(lead.research)
                else:
                    matched = bool(value)

            if matched:
                points = rule["points"]
                adjustments.append({
                    "rule": rule["label"],
                    "points": points,
                })
                total += points

        return adjustments, total
