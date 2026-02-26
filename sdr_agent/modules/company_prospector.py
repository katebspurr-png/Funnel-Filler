"""Automated company prospecting using Apollo.io Organization Search API."""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
import urllib.error
from typing import Any

from ..config import Config
from ..models import Company, ICP


APOLLO_ORG_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_companies/search"


class CompanyProspector:
    """Finds new companies matching an Ideal Customer Profile via Apollo."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.apollo_api_key

    def search(
        self,
        icp: ICP,
        per_page: int = 25,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search Apollo for organizations matching the ICP criteria.

        Returns a list of raw organization dicts from Apollo.
        """
        if not self.api_key:
            raise ValueError(
                "APOLLO_API_KEY is required for prospecting. "
                "Set it in your .env file."
            )

        # Build JSON payload for organization search
        payload: dict[str, Any] = {
            "page": page,
            "per_page": per_page,
        }

        if icp.industries:
            payload["organization_industry_tag_ids"] = icp.industries

        if icp.locations:
            payload["organization_locations"] = icp.locations

        if icp.company_sizes:
            # Parse size ranges like "1,50" into num_employees_ranges
            ranges = []
            for size in icp.company_sizes:
                parts = [p.strip() for p in size.split(",")]
                if len(parts) == 2:
                    try:
                        ranges.append({"min": int(parts[0]), "max": int(parts[1])})
                    except ValueError:
                        pass
            if ranges:
                payload["organization_num_employees_ranges"] = ranges

        if icp.keywords:
            payload["q_organization_keyword_tags"] = icp.keywords

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            APOLLO_ORG_SEARCH_URL,
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
                return body.get("organizations", [])
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Apollo API error ({exc.code}): {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Apollo API: {exc.reason}"
            ) from exc

    def orgs_to_companies(self, orgs: list[dict[str, Any]]) -> list[Company]:
        """Convert raw Apollo organization results into Company objects."""
        companies: list[Company] = []
        for org in orgs:
            name = org.get("name", "")
            if not name:
                continue

            company = Company(
                name=name,
                domain=org.get("primary_domain", "") or "",
                industry=org.get("industry", "") or "",
                employee_count=org.get("estimated_num_employees", 0) or 0,
                website_url=org.get("website_url", "") or "",
                linkedin_url=org.get("linkedin_url", "") or "",
                description=org.get("short_description", "") or "",
                founded_year=org.get("founded_year", 0) or 0,
                annual_revenue=org.get("annual_revenue_printed", "") or "",
                notes="Found via Apollo company prospecting",
            )

            # Location
            parts = []
            if org.get("city"):
                parts.append(org["city"])
            if org.get("state"):
                parts.append(org["state"])
            if org.get("country"):
                parts.append(org["country"])
            if parts:
                company.location = ", ".join(parts)

            # Technologies and keywords
            if org.get("technology_names"):
                company.technologies = org["technology_names"]
            if org.get("keywords"):
                company.keywords = org["keywords"]

            # Store extra Apollo data in research
            apollo_data: dict[str, Any] = {}
            for key in (
                "id", "name", "primary_domain", "industry",
                "estimated_num_employees", "founded_year",
                "short_description", "annual_revenue_printed",
                "annual_revenue", "total_funding_printed",
                "latest_funding_stage", "technology_names",
                "phone", "logo_url", "publicly_traded_symbol",
            ):
                if org.get(key):
                    apollo_data[key] = org[key]

            if apollo_data:
                company.research["apollo"] = apollo_data

            companies.append(company)

        return companies
