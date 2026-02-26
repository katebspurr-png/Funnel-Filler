"""Automated prospecting using Apollo.io People Search API."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from ..config import Config
from ..models import ICP, Lead


APOLLO_PEOPLE_SEARCH_URL = "https://api.apollo.io/api/v1/mixed_people/api_search"


class Prospector:
    """Finds new leads matching an Ideal Customer Profile via Apollo."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.apollo_api_key

    def search(
        self,
        icp: ICP,
        per_page: int = 25,
        page: int = 1,
    ) -> list[dict[str, Any]]:
        """Search Apollo for people matching the ICP criteria.

        Returns a list of raw person dicts from Apollo.
        """
        if not self.api_key:
            raise ValueError(
                "APOLLO_API_KEY is required for prospecting. "
                "Set it in your .env file."
            )

        payload: dict[str, Any] = {
            "api_key": self.api_key,
            "page": page,
            "per_page": per_page,
        }

        if icp.titles:
            payload["person_titles"] = icp.titles
        if icp.seniorities:
            payload["person_seniorities"] = icp.seniorities
        if icp.locations:
            payload["person_locations"] = icp.locations
        if icp.industries:
            payload["organization_industry_tag_ids"] = icp.industries
        if icp.company_sizes:
            payload["organization_num_employees_ranges"] = icp.company_sizes
        if icp.keywords:
            payload["q_keywords"] = " ".join(icp.keywords)

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            APOLLO_PEOPLE_SEARCH_URL,
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
                return body.get("people", [])
        except urllib.error.HTTPError as exc:
            error_body = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"Apollo API error ({exc.code}): {error_body}"
            ) from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Could not reach Apollo API: {exc.reason}"
            ) from exc

    def people_to_leads(self, people: list[dict[str, Any]]) -> list[Lead]:
        """Convert raw Apollo person results into Lead objects."""
        leads: list[Lead] = []
        for person in people:
            name = person.get("name") or ""
            if not name:
                first = person.get("first_name", "")
                last = person.get("last_name", "")
                name = f"{first} {last}".strip()
            if not name:
                continue

            org = person.get("organization") or {}

            lead = Lead(
                name=name,
                email=person.get("email", "") or "",
                company=person.get("organization_name") or org.get("name", ""),
                title=person.get("title", "") or "",
                industry=org.get("industry", "") or "",
                linkedin_url=person.get("linkedin_url", "") or "",
                notes="Found via Apollo prospecting",
            )

            # Store extra Apollo data in research
            apollo_data: dict[str, Any] = {}
            for key in ("headline", "city", "state", "country", "seniority",
                        "departments", "phone_numbers"):
                if person.get(key):
                    apollo_data[key] = person[key]

            if org:
                org_summary: dict[str, Any] = {}
                for key in ("name", "website_url", "industry",
                            "estimated_num_employees", "short_description"):
                    if org.get(key):
                        org_summary[key] = org[key]
                if org_summary:
                    apollo_data["organization"] = org_summary

            if apollo_data:
                lead.research["apollo"] = apollo_data

            leads.append(lead)

        return leads
