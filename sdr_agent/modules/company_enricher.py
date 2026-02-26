"""Company/organization enrichment using Apollo.io Organization Enrich API."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from ..config import Config
from ..models import Company


APOLLO_ORG_ENRICH_URL = "https://api.apollo.io/api/v1/organizations/enrich"


class CompanyEnricher:
    """Enriches company profiles with real data from Apollo.io."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.apollo_api_key

    def enrich_company(self, company: Company) -> dict[str, Any]:
        """Enrich a company via Apollo's Organization Enrich API.

        Returns a dict of fields that were updated (field_name -> new_value).
        """
        if not self.api_key:
            raise ValueError(
                "APOLLO_API_KEY is required for enrichment. "
                "Set it in your .env file."
            )

        org = self._org_enrich(company)
        if not org:
            return {}

        return self._apply_enrichment(company, org)

    def _org_enrich(self, company: Company) -> dict[str, Any] | None:
        """Call Apollo Organization Enrich API."""
        payload: dict[str, Any] = {"api_key": self.api_key}

        if company.domain:
            payload["domain"] = company.domain
        elif company.name:
            payload["organization_name"] = company.name
        else:
            return None

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            APOLLO_ORG_ENRICH_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
                "X-Api-Key": self.api_key,
                "User-Agent": "FunnelFiller/0.1",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("organization")
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Apollo API error ({exc.code}): {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Apollo API: {exc.reason}"
            ) from exc

    def _apply_enrichment(
        self, company: Company, org: dict[str, Any]
    ) -> dict[str, Any]:
        """Map Apollo organization data onto company fields. Returns updated fields."""
        updated: dict[str, Any] = {}

        # Domain / website
        if not company.domain and org.get("primary_domain"):
            company.domain = org["primary_domain"]
            updated["domain"] = company.domain

        if not company.website_url and org.get("website_url"):
            company.website_url = org["website_url"]
            updated["website_url"] = company.website_url

        # Industry
        if not company.industry and org.get("industry"):
            company.industry = org["industry"]
            updated["industry"] = company.industry

        # Employee count
        if not company.employee_count and org.get("estimated_num_employees"):
            company.employee_count = org["estimated_num_employees"]
            updated["employee_count"] = company.employee_count

        # Location
        if not company.location:
            parts = []
            if org.get("city"):
                parts.append(org["city"])
            if org.get("state"):
                parts.append(org["state"])
            if org.get("country"):
                parts.append(org["country"])
            if parts:
                company.location = ", ".join(parts)
                updated["location"] = company.location

        # Description
        if not company.description and org.get("short_description"):
            company.description = org["short_description"]
            updated["description"] = company.description

        # Founded year
        if not company.founded_year and org.get("founded_year"):
            company.founded_year = org["founded_year"]
            updated["founded_year"] = company.founded_year

        # Revenue
        if not company.annual_revenue and org.get("annual_revenue_printed"):
            company.annual_revenue = org["annual_revenue_printed"]
            updated["annual_revenue"] = company.annual_revenue

        # LinkedIn
        if not company.linkedin_url and org.get("linkedin_url"):
            company.linkedin_url = org["linkedin_url"]
            updated["linkedin_url"] = company.linkedin_url

        # Technologies
        if not company.technologies and org.get("technology_names"):
            company.technologies = org["technology_names"]
            updated["technologies"] = company.technologies

        # Keywords
        if not company.keywords and org.get("keywords"):
            company.keywords = org["keywords"]
            updated["keywords"] = company.keywords

        # Store extra Apollo data in research
        apollo_data: dict[str, Any] = {}
        for key in (
            "name", "primary_domain", "industry", "estimated_num_employees",
            "founded_year", "short_description", "annual_revenue_printed",
            "annual_revenue", "total_funding", "total_funding_printed",
            "latest_funding_round_date", "latest_funding_stage",
            "technology_names", "keywords", "city", "state", "country",
            "phone", "logo_url", "publicly_traded_symbol",
            "publicly_traded_exchange", "crunchbase_url",
            "alexa_ranking", "languages", "num_suborganizations",
        ):
            if org.get(key):
                apollo_data[key] = org[key]

        if apollo_data:
            company.research["apollo"] = apollo_data
            updated["apollo_data"] = apollo_data

        return updated
