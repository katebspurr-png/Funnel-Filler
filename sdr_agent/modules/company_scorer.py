"""Company scoring using AI analysis + configurable rule-based adjustments."""

from __future__ import annotations

import json
import re

from anthropic import Anthropic

from ..config import Config
from ..models import Company


COMPANY_SCORING_PROMPT = """You are a B2B sales company scoring expert. Analyze this company and assign a score from 0 to 100
indicating how likely they are to be a good target account for our business.

Company info:
- Name: {name}
- Domain: {domain}
- Industry: {industry}
- Employee count: {employee_count}
- Location: {location}
- Description: {description}
- Founded year: {founded_year}
- Annual revenue: {annual_revenue}
- Technologies: {technologies}
- Keywords: {keywords}
- Website: {website_url}
- LinkedIn: {linkedin_url}
- Notes: {notes}

Research/enrichment data:
{research}

Our company:
- Name: {company_name}
- Description: {company_description}

Scoring guidelines:
- 80-100: Excellent target — strong industry fit, right company size, clear need for our solution
- 60-79: Good target — reasonable fit but missing some ideal criteria
- 40-59: Moderate — could be a fit but needs more investigation
- 20-39: Weak — unlikely target but not impossible
- 0-19: Poor fit — wrong industry, too small/large, or clear disqualifiers

Respond in this exact JSON format only:
{{"score": <number>, "reasoning": "<1-2 sentence explanation>", "strengths": ["<strength1>", "<strength2>"], "concerns": ["<concern1>", "<concern2>"]}}"""


# Default company scoring rules
DEFAULT_COMPANY_RULES: list[dict] = [
    # Company size signals
    {"field": "employee_count", "min": 50, "max": 500, "points": 15, "label": "Mid-market (50-500 employees)"},
    {"field": "employee_count", "min": 501, "max": 5000, "points": 10, "label": "Enterprise (501-5000 employees)"},
    {"field": "employee_count", "min": 1, "max": 10, "points": -5, "label": "Very small company (<10)"},
    # Data completeness
    {"field": "domain", "exists": True, "points": 10, "label": "Has domain"},
    {"field": "website_url", "exists": True, "points": 5, "label": "Has website"},
    {"field": "linkedin_url", "exists": True, "points": 5, "label": "Has LinkedIn"},
    {"field": "annual_revenue", "exists": True, "points": 5, "label": "Has revenue data"},
    {"field": "description", "exists": True, "points": 5, "label": "Has description"},
    # Enrichment signals
    {"field": "research", "exists": True, "points": 5, "label": "Has research data"},
    {"field": "technologies", "exists": True, "points": 5, "label": "Has technology data"},
]


class CompanyScorer:
    """Scores companies using AI analysis combined with rule-based adjustments."""

    def __init__(self, config: Config):
        self.config = config
        self.client = Anthropic(api_key=config.anthropic_api_key)
        self.rules = DEFAULT_COMPANY_RULES

    def score_company(self, company: Company) -> dict:
        """Score a company using AI + rules. Returns score details dict."""
        ai_result = self._ai_score(company)
        ai_score = ai_result.get("score", 50)

        rule_adjustments, rule_total = self._apply_rules(company)

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

    def _ai_score(self, company: Company) -> dict:
        """Get AI-generated score and reasoning."""
        research_str = json.dumps(company.research, indent=2) if company.research else "No data"

        prompt = COMPANY_SCORING_PROMPT.format(
            name=company.name,
            domain=company.domain,
            industry=company.industry,
            employee_count=company.employee_count or "Unknown",
            location=company.location,
            description=company.description,
            founded_year=company.founded_year or "Unknown",
            annual_revenue=company.annual_revenue or "Unknown",
            technologies=", ".join(company.technologies) if company.technologies else "Unknown",
            keywords=", ".join(company.keywords) if company.keywords else "Unknown",
            website_url=company.website_url,
            linkedin_url=company.linkedin_url,
            notes=company.notes,
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

    def _apply_rules(self, company: Company) -> tuple[list[dict], int]:
        """Apply rule-based scoring adjustments. Returns (details, total_points)."""
        adjustments: list[dict] = []
        total = 0

        for rule in self.rules:
            field_name = rule["field"]
            matched = False

            if "min" in rule and "max" in rule:
                # Numeric range check
                value = getattr(company, field_name, 0) or 0
                if isinstance(value, (int, float)):
                    matched = rule["min"] <= value <= rule["max"]

            elif "exists" in rule:
                # Check if field has a non-empty value
                if field_name == "research":
                    matched = bool(company.research)
                elif field_name == "technologies":
                    matched = bool(company.technologies)
                else:
                    value = getattr(company, field_name, None)
                    matched = bool(value)

            if matched:
                points = rule["points"]
                adjustments.append({
                    "rule": rule["label"],
                    "points": points,
                })
                total += points

        return adjustments, total
