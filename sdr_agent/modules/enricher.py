"""Lead enrichment using Apollo.io API."""

from __future__ import annotations

import json
import urllib.request
import urllib.error
from typing import Any

from ..config import Config
from ..models import Lead


APOLLO_PEOPLE_MATCH_URL = "https://api.apollo.io/api/v1/people/match"


class LeadEnricher:
    """Enriches lead profiles with real data from Apollo.io."""

    def __init__(self, config: Config):
        self.config = config
        self.api_key = config.apollo_api_key

    def enrich_lead(self, lead: Lead) -> dict[str, Any]:
        """Enrich a lead via Apollo's People Match API.

        Returns a dict of fields that were updated (field_name -> new_value).
        """
        if not self.api_key:
            raise ValueError(
                "APOLLO_API_KEY is required for enrichment. "
                "Set it in your .env file."
            )

        person = self._people_match(lead)
        if not person:
            return {}

        return self._apply_enrichment(lead, person)

    def _people_match(self, lead: Lead) -> dict[str, Any] | None:
        """Call Apollo People Match API to find and enrich a person."""
        # Build the request payload from available lead info
        payload: dict[str, Any] = {"api_key": self.api_key}

        # Split name into first/last
        parts = lead.name.strip().split(None, 1)
        if parts:
            payload["first_name"] = parts[0]
            if len(parts) > 1:
                payload["last_name"] = parts[1]

        if lead.email:
            payload["email"] = lead.email
        if lead.company:
            payload["organization_name"] = lead.company
        if lead.linkedin_url:
            payload["linkedin_url"] = lead.linkedin_url

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            APOLLO_PEOPLE_MATCH_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Cache-Control": "no-cache",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("person")
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
        self, lead: Lead, person: dict[str, Any]
    ) -> dict[str, Any]:
        """Map Apollo person data onto lead fields. Returns updated fields."""
        updated: dict[str, Any] = {}

        # Email
        if not lead.email and person.get("email"):
            lead.email = person["email"]
            updated["email"] = lead.email

        # Title
        if not lead.title and person.get("title"):
            lead.title = person["title"]
            updated["title"] = lead.title

        # Company
        org = person.get("organization") or {}
        if not lead.company and (person.get("organization_name") or org.get("name")):
            lead.company = person.get("organization_name") or org.get("name", "")
            updated["company"] = lead.company

        # Industry
        if not lead.industry and org.get("industry"):
            lead.industry = org["industry"]
            updated["industry"] = lead.industry

        # LinkedIn
        if not lead.linkedin_url and person.get("linkedin_url"):
            lead.linkedin_url = person["linkedin_url"]
            updated["linkedin_url"] = lead.linkedin_url

        # Store the full Apollo payload in research for reference
        apollo_data: dict[str, Any] = {}

        if person.get("headline"):
            apollo_data["headline"] = person["headline"]
        if person.get("city"):
            apollo_data["city"] = person["city"]
        if person.get("state"):
            apollo_data["state"] = person["state"]
        if person.get("country"):
            apollo_data["country"] = person["country"]
        if person.get("phone_numbers"):
            apollo_data["phone_numbers"] = person["phone_numbers"]
        if person.get("departments"):
            apollo_data["departments"] = person["departments"]
        if person.get("seniority"):
            apollo_data["seniority"] = person["seniority"]

        # Organization details
        if org:
            org_summary: dict[str, Any] = {}
            for key in (
                "name", "website_url", "industry", "estimated_num_employees",
                "founded_year", "short_description", "annual_revenue_printed",
                "technology_names", "keywords",
            ):
                if org.get(key):
                    org_summary[key] = org[key]
            if org_summary:
                apollo_data["organization"] = org_summary

        if apollo_data:
            lead.research["apollo"] = apollo_data
            updated["apollo_data"] = apollo_data

        return updated
