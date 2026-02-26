"""Main SDR agent orchestrator — ties all modules together."""

from __future__ import annotations

from datetime import datetime

from .config import Config
from .models import ICP, Channel, Company, CompanyStatus, Lead, LeadStatus, Message, MessageType
from .modules.company_enricher import CompanyEnricher
from .modules.company_prospector import CompanyProspector
from .modules.company_scorer import CompanyScorer
from .modules.enricher import LeadEnricher
from .modules.linkedin_outreach import LinkedInOutreach
from .modules.outreach import OutreachEngine
from .modules.prospector import Prospector
from .modules.qualifier import LeadQualifier
from .modules.resend_sender import ResendSender
from .modules.researcher import LeadResearcher
from .modules.scorer import LeadScorer
from .modules.scheduler import MeetingScheduler
from .modules.sequencer import SequenceManager
from .storage import Database


class SDRAgent:
    """The main SDR agent that orchestrates the full outbound sales workflow.

    Workflow:
        1. Add leads (manually or from CSV)
        2. Research leads to gather context
        3. Generate personalized outreach
        4. Start automated follow-up sequences
        5. Analyze responses and qualify leads
        6. Book meetings for qualified leads
    """

    def __init__(self, config: Config | None = None):
        self.config = config or Config.from_env()
        self.db = Database(self.config.db_path)
        self.enricher = LeadEnricher(self.config)
        self.prospector = Prospector(self.config)
        self.researcher = LeadResearcher(self.config)
        self.scorer = LeadScorer(self.config)
        self.outreach = OutreachEngine(self.config)
        self.qualifier = LeadQualifier(self.config)
        self.scheduler = MeetingScheduler(self.config)
        self.sequencer = SequenceManager(self.config, self.db, self.outreach)
        self.company_enricher = CompanyEnricher(self.config)
        self.company_prospector = CompanyProspector(self.config)
        self.company_scorer = CompanyScorer(self.config)
        self.resend_sender = ResendSender(self.config)
        self.linkedin = LinkedInOutreach(self.config)

    # -- Lead Management --

    def add_lead(
        self,
        name: str,
        email: str = "",
        company: str = "",
        title: str = "",
        industry: str = "",
        linkedin_url: str = "",
        notes: str = "",
    ) -> Lead:
        """Add a new lead to the pipeline."""
        lead = Lead(
            name=name,
            email=email,
            company=company,
            title=title,
            industry=industry,
            linkedin_url=linkedin_url,
            notes=notes,
        )
        self.db.save_lead(lead)
        return lead

    def import_leads_from_csv(self, csv_path: str) -> list[Lead]:
        """Import leads from a CSV file. Expected columns: name, email, company, title, industry."""
        import csv

        leads = []
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                lead = self.add_lead(
                    name=row.get("name", ""),
                    email=row.get("email", ""),
                    company=row.get("company", ""),
                    title=row.get("title", ""),
                    industry=row.get("industry", ""),
                    linkedin_url=row.get("linkedin_url", ""),
                    notes=row.get("notes", ""),
                )
                leads.append(lead)
        return leads

    def get_lead(self, lead_id: str) -> Lead | None:
        return self.db.get_lead(lead_id)

    def list_leads(self, status: LeadStatus | None = None) -> list[Lead]:
        return self.db.list_leads(status)

    def search_leads(self, query: str) -> list[Lead]:
        return self.db.search_leads(query)

    # -- Scoring --

    def score_lead(self, lead_id: str) -> dict:
        """Score a lead using AI + rule-based analysis.

        Returns scoring details dict with score, reasoning, strengths, concerns.
        """
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        result = self.scorer.score_lead(lead)
        lead.score = result["score"]
        lead.updated_at = datetime.now().isoformat()
        self.db.save_lead(lead)
        return result

    def _auto_score(self, lead: Lead) -> dict | None:
        """Auto-score a lead after data changes. Returns score details or None."""
        try:
            result = self.scorer.score_lead(lead)
            lead.score = result["score"]
            return result
        except Exception:
            return None

    # -- Enrichment --

    def enrich_lead(self, lead_id: str) -> tuple[Lead, dict]:
        """Enrich a lead with data from Apollo.io.

        Returns (updated_lead, dict_of_updated_fields).
        """
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        updated_fields = self.enricher.enrich_lead(lead)
        if updated_fields:
            score_result = self._auto_score(lead)
            if score_result:
                updated_fields["auto_score"] = score_result
            lead.updated_at = datetime.now().isoformat()
            self.db.save_lead(lead)

        return lead, updated_fields

    # -- Prospecting --

    def set_icp(
        self,
        name: str = "default",
        titles: list[str] | None = None,
        seniorities: list[str] | None = None,
        industries: list[str] | None = None,
        company_sizes: list[str] | None = None,
        locations: list[str] | None = None,
        keywords: list[str] | None = None,
    ) -> ICP:
        """Create or update an Ideal Customer Profile."""
        icp = ICP(
            name=name,
            titles=titles or [],
            seniorities=seniorities or [],
            industries=industries or [],
            company_sizes=company_sizes or [],
            locations=locations or [],
            keywords=keywords or [],
        )
        self.db.save_icp(icp)
        return icp

    def get_icp(self, name: str = "default") -> ICP | None:
        return self.db.get_icp(name)

    def prospect(
        self,
        icp_name: str = "default",
        count: int = 25,
        page: int = 1,
    ) -> list[Lead]:
        """Find new leads matching the saved ICP and add them to the pipeline."""
        icp = self.db.get_icp(icp_name)
        if not icp:
            raise ValueError(
                f"ICP '{icp_name}' not found. Create one first with set-icp."
            )

        people = self.prospector.search(icp, per_page=count, page=page)
        leads = self.prospector.people_to_leads(people)

        # Save each lead, skipping duplicates by email
        existing_emails = {
            lead.email.lower()
            for lead in self.db.list_leads()
            if lead.email
        }

        added: list[Lead] = []
        for lead in leads:
            if lead.email and lead.email.lower() in existing_emails:
                continue
            self.db.save_lead(lead)
            added.append(lead)
            if lead.email:
                existing_emails.add(lead.email.lower())

        return added

    def prospect_at_company(
        self,
        domain: str,
        icp_name: str = "default",
        count: int = 5,
    ) -> list[Lead]:
        """Find contacts at a specific company domain matching ICP titles.

        Uses the ICP's target titles to filter, but scopes the search to
        the given company domain.
        """
        icp = self.db.get_icp(icp_name)
        if not icp:
            raise ValueError(
                f"ICP '{icp_name}' not found. Create one first with set-icp."
            )

        # Create a temporary ICP scoped to this company's domain
        company_icp = ICP(
            name=f"_temp_{domain}",
            titles=icp.titles,
            seniorities=icp.seniorities,
            keywords=[domain],
            locations=icp.locations,
        )

        people = self.prospector.search(company_icp, per_page=count, page=1)
        leads = self.prospector.people_to_leads(people)

        # Deduplicate against existing leads
        existing_emails = {
            lead.email.lower()
            for lead in self.db.list_leads()
            if lead.email
        }

        added: list[Lead] = []
        for lead in leads:
            if lead.email and lead.email.lower() in existing_emails:
                continue
            self.db.save_lead(lead)
            added.append(lead)
            if lead.email:
                existing_emails.add(lead.email.lower())

        return added

    # -- Research --

    def research_lead(self, lead_id: str) -> Lead:
        """Research a lead and enrich their profile, then auto-score."""
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        self.db.update_lead_status(lead_id, LeadStatus.RESEARCHING)
        research = self.researcher.research_lead(lead)
        lead.research = research
        lead.status = LeadStatus.OUTREACH_PENDING
        self._auto_score(lead)
        lead.updated_at = datetime.now().isoformat()
        self.db.save_lead(lead)
        return lead

    # -- Outreach --

    def generate_outreach(
        self, lead_id: str, channel: Channel = Channel.EMAIL
    ) -> Message:
        """Generate an initial outreach message for a lead."""
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        message = self.outreach.generate_initial_outreach(lead, channel)
        self.db.save_message(message)
        return message

    def start_sequence(self, lead_id: str) -> str:
        """Start an automated follow-up sequence for a lead."""
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        sequence = self.sequencer.create_sequence(lead)
        return sequence.id

    def run_sequences(self) -> list[tuple[Lead, Message]]:
        """Check and execute any due sequence steps."""
        return self.sequencer.run_due_sequences()

    # -- Response Handling --

    def handle_reply(self, lead_id: str, reply_text: str) -> dict:
        """Process a prospect's reply: analyze, qualify, and recommend next action."""
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Save the inbound message
        inbound = Message(
            lead_id=lead_id,
            channel=Channel.EMAIL,
            message_type=MessageType.REPLY,
            body=reply_text,
            is_inbound=True,
            sent_at=datetime.now().isoformat(),
        )
        self.db.save_message(inbound)
        self.db.update_lead_status(lead_id, LeadStatus.REPLIED)

        # Pause any active sequences
        for seq in self.db.get_active_sequences():
            if seq.lead_id == lead_id:
                self.sequencer.pause_sequence(seq.id)

        # Analyze the response
        messages = self.db.get_messages_for_lead(lead_id)
        outbound_messages = [m for m in messages if not m.is_inbound]
        last_outbound = outbound_messages[-1] if outbound_messages else None

        analysis = {}
        if last_outbound:
            analysis = self.qualifier.analyze_response(last_outbound, reply_text)

        # Qualify the lead
        qualification = self.qualifier.qualify_lead(lead, messages)

        # Update lead score
        try:
            lead.score = int(qualification.get("score", "0"))
        except ValueError:
            lead.score = 0

        # Determine next action
        next_action = qualification.get("next_action", "FOLLOW_UP")
        if next_action == "BOOK_MEETING":
            self.db.update_lead_status(lead_id, LeadStatus.QUALIFIED)
        elif next_action == "DISQUALIFY":
            self.db.update_lead_status(lead_id, LeadStatus.DISQUALIFIED)

        lead.updated_at = datetime.now().isoformat()
        self.db.save_lead(lead)

        return {
            "analysis": analysis,
            "qualification": qualification,
            "next_action": next_action,
            "score": lead.score,
        }

    # -- Meeting Booking --

    def request_meeting(
        self, lead_id: str, channel: Channel = Channel.EMAIL
    ) -> Message:
        """Generate and save a meeting request message."""
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        messages = self.db.get_messages_for_lead(lead_id)
        message = self.scheduler.generate_meeting_request(lead, messages, channel)
        self.db.save_message(message)
        self.db.update_lead_status(lead_id, LeadStatus.MEETING_BOOKED)
        return message

    # -- Send Outreach --

    def send_email(self, lead_id: str) -> dict:
        """Generate and send an outreach email to a lead via Resend.

        Returns dict with message details and Resend response.
        """
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        if not lead.email:
            raise ValueError(
                f"Lead {lead.name} has no email. Enrich first to get their email."
            )

        # Generate the outreach message
        message = self.outreach.generate_initial_outreach(lead, Channel.EMAIL)

        # Send via Resend
        resend_result = self.resend_sender.send_outreach_message(lead, message)

        # Save message with sent timestamp
        message.sent_at = datetime.now().isoformat()
        self.db.save_message(message)

        # Update lead status
        if lead.status in (LeadStatus.NEW, LeadStatus.OUTREACH_PENDING):
            self.db.update_lead_status(lead_id, LeadStatus.CONTACTED)

        return {
            "message": message,
            "resend_id": resend_result.get("id", ""),
            "sent_to": lead.email,
        }

    def send_linkedin(self, lead_id: str, message_type: str = "connect") -> Message:
        """Generate a LinkedIn outreach message for a lead.

        message_type: 'connect' for connection request, 'message' for DM.
        Returns the generated Message (to be sent manually via LinkedIn).
        """
        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        previous = [
            m for m in self.db.get_messages_for_lead(lead_id)
            if m.channel == Channel.LINKEDIN
        ]

        if message_type == "connect":
            message = self.linkedin.generate_connection_request(lead)
        else:
            message = self.linkedin.generate_message(lead, previous or None)

        self.db.save_message(message)
        return message

    def auto_outreach(
        self, lead_id: str, channels: list[str] | None = None
    ) -> dict:
        """Full automated outreach pipeline for a lead:
        enrich → score → generate & send email → generate LinkedIn message.

        Returns a summary dict of all actions taken.
        """
        if channels is None:
            channels = ["email", "linkedin"]

        results: dict = {"lead_id": lead_id, "actions": []}

        lead = self.db.get_lead(lead_id)
        if not lead:
            raise ValueError(f"Lead {lead_id} not found")

        # Step 1: Enrich if not already enriched
        if not lead.research.get("apollo"):
            try:
                lead, enriched = self.enrich_lead(lead_id)
                if enriched:
                    results["actions"].append({
                        "step": "enrich",
                        "status": "success",
                        "fields_updated": list(enriched.keys()),
                    })
            except Exception as e:
                results["actions"].append({
                    "step": "enrich",
                    "status": "error",
                    "error": str(e),
                })

        # Step 2: Research if not already done
        if not lead.research.get("summary"):
            try:
                lead = self.research_lead(lead_id)
                results["actions"].append({
                    "step": "research",
                    "status": "success",
                })
            except Exception as e:
                results["actions"].append({
                    "step": "research",
                    "status": "error",
                    "error": str(e),
                })

        # Step 3: Send email via Resend
        if "email" in channels and lead.email:
            try:
                email_result = self.send_email(lead_id)
                results["actions"].append({
                    "step": "send_email",
                    "status": "success",
                    "sent_to": email_result["sent_to"],
                    "subject": email_result["message"].subject,
                    "resend_id": email_result["resend_id"],
                })
            except Exception as e:
                results["actions"].append({
                    "step": "send_email",
                    "status": "error",
                    "error": str(e),
                })

        # Step 4: Generate LinkedIn message
        if "linkedin" in channels:
            try:
                li_msg = self.send_linkedin(lead_id, "connect")
                results["actions"].append({
                    "step": "linkedin_connect",
                    "status": "generated",
                    "message": li_msg.body,
                    "profile_url": lead.linkedin_url or "Not available",
                })
            except Exception as e:
                results["actions"].append({
                    "step": "linkedin_connect",
                    "status": "error",
                    "error": str(e),
                })

        return results

    def full_pipeline(
        self,
        icp_name: str = "default",
        count: int = 5,
        channels: list[str] | None = None,
        callback: object | None = None,
    ) -> dict:
        """End-to-end pipeline: prospect → enrich → research → score → outreach.

        Args:
            icp_name: ICP to use for prospecting.
            count: Number of leads to prospect.
            channels: Outreach channels ('email', 'linkedin'). Defaults to both.
            callback: Optional callable(step, lead_name, detail) for progress updates.

        Returns a summary dict with all results.
        """
        if channels is None:
            channels = ["email", "linkedin"]

        def _notify(step: str, name: str = "", detail: str = ""):
            if callback and callable(callback):
                callback(step, name, detail)

        results: dict = {
            "prospected": [],
            "enriched": [],
            "researched": [],
            "outreach": [],
            "errors": [],
        }

        # Step 1: Prospect
        _notify("prospect_start", detail=f"Finding {count} leads matching ICP '{icp_name}'")
        try:
            new_leads = self.prospect(icp_name=icp_name, count=count)
            results["prospected"] = [
                {"id": l.id, "name": l.name, "company": l.company}
                for l in new_leads
            ]
            _notify("prospect_done", detail=f"Found {len(new_leads)} new leads")
        except Exception as e:
            results["errors"].append({"step": "prospect", "error": str(e)})
            _notify("prospect_error", detail=str(e))
            return results

        if not new_leads:
            return results

        # Steps 2-5: For each lead: enrich → research → score → outreach
        for lead in new_leads:
            lead_name = f"{lead.name} @ {lead.company}"

            # Step 2: Enrich
            _notify("enrich_start", name=lead_name)
            try:
                lead, enriched_fields = self.enrich_lead(lead.id)
                results["enriched"].append({
                    "id": lead.id,
                    "name": lead.name,
                    "fields": list(enriched_fields.keys()),
                })
                _notify("enrich_done", name=lead_name, detail=f"{len(enriched_fields)} fields")
            except Exception as e:
                results["errors"].append({
                    "step": "enrich", "lead": lead_name, "error": str(e),
                })
                _notify("enrich_error", name=lead_name, detail=str(e))
                # Continue — outreach can still work with partial data

            # Step 3: Research
            _notify("research_start", name=lead_name)
            try:
                lead = self.research_lead(lead.id)
                results["researched"].append({
                    "id": lead.id, "name": lead.name,
                })
                _notify("research_done", name=lead_name)
            except Exception as e:
                results["errors"].append({
                    "step": "research", "lead": lead_name, "error": str(e),
                })
                _notify("research_error", name=lead_name, detail=str(e))

            # Step 4: Score (already auto-scored by enrich/research, but ensure)
            if lead.score == 0:
                try:
                    self.score_lead(lead.id)
                except Exception:
                    pass

            # Step 5: Outreach
            outreach_result: dict = {
                "id": lead.id, "name": lead.name, "email_sent": False,
                "linkedin_generated": False,
            }

            if "email" in channels and lead.email:
                _notify("email_start", name=lead_name)
                try:
                    email_result = self.send_email(lead.id)
                    outreach_result["email_sent"] = True
                    outreach_result["email_to"] = email_result["sent_to"]
                    outreach_result["email_subject"] = email_result["message"].subject
                    _notify("email_done", name=lead_name, detail=email_result["sent_to"])
                except Exception as e:
                    results["errors"].append({
                        "step": "send_email", "lead": lead_name, "error": str(e),
                    })
                    _notify("email_error", name=lead_name, detail=str(e))

            if "linkedin" in channels:
                _notify("linkedin_start", name=lead_name)
                try:
                    li_msg = self.send_linkedin(lead.id, "connect")
                    outreach_result["linkedin_generated"] = True
                    outreach_result["linkedin_message"] = li_msg.body
                    outreach_result["linkedin_url"] = lead.linkedin_url or ""
                    _notify("linkedin_done", name=lead_name)
                except Exception as e:
                    results["errors"].append({
                        "step": "linkedin", "lead": lead_name, "error": str(e),
                    })
                    _notify("linkedin_error", name=lead_name, detail=str(e))

            results["outreach"].append(outreach_result)

        return results

    # -- Company Management --

    def add_company(
        self,
        name: str,
        domain: str = "",
        industry: str = "",
        employee_count: int = 0,
        location: str = "",
        description: str = "",
        website_url: str = "",
        linkedin_url: str = "",
        notes: str = "",
    ) -> Company:
        """Add a new company to the pipeline."""
        company = Company(
            name=name,
            domain=domain,
            industry=industry,
            employee_count=employee_count,
            location=location,
            description=description,
            website_url=website_url,
            linkedin_url=linkedin_url,
            notes=notes,
        )
        self.db.save_company(company)
        return company

    def get_company(self, company_id: str) -> Company | None:
        return self.db.get_company(company_id)

    def list_companies(self, status: CompanyStatus | None = None) -> list[Company]:
        return self.db.list_companies(status)

    def search_companies(self, query: str) -> list[Company]:
        return self.db.search_companies(query)

    # -- Company Enrichment --

    def enrich_company(self, company_id: str) -> tuple[Company, dict]:
        """Enrich a company with data from Apollo.io.

        Returns (updated_company, dict_of_updated_fields).
        """
        company = self.db.get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        updated_fields = self.company_enricher.enrich_company(company)
        if updated_fields:
            score_result = self._auto_score_company(company)
            if score_result:
                updated_fields["auto_score"] = score_result
            company.status = CompanyStatus.ENRICHED
            company.updated_at = datetime.now().isoformat()
            self.db.save_company(company)

        return company, updated_fields

    # -- Company Prospecting --

    def prospect_companies(
        self,
        icp_name: str = "default",
        count: int = 25,
        page: int = 1,
    ) -> list[Company]:
        """Find new companies matching the saved ICP and add them to the pipeline."""
        icp = self.db.get_icp(icp_name)
        if not icp:
            raise ValueError(
                f"ICP '{icp_name}' not found. Create one first with set-icp."
            )

        orgs = self.company_prospector.search(icp, per_page=count, page=page)
        companies = self.company_prospector.orgs_to_companies(orgs)

        # Skip duplicates by domain
        existing_domains = {
            c.domain.lower()
            for c in self.db.list_companies()
            if c.domain
        }

        added: list[Company] = []
        for company in companies:
            if company.domain and company.domain.lower() in existing_domains:
                continue
            self.db.save_company(company)
            added.append(company)
            if company.domain:
                existing_domains.add(company.domain.lower())

        return added

    # -- Company Scoring --

    def score_company(self, company_id: str) -> dict:
        """Score a company using AI + rule-based analysis.

        Returns scoring details dict with score, reasoning, strengths, concerns.
        """
        company = self.db.get_company(company_id)
        if not company:
            raise ValueError(f"Company {company_id} not found")

        result = self.company_scorer.score_company(company)
        company.score = result["score"]
        company.updated_at = datetime.now().isoformat()
        self.db.save_company(company)
        return result

    def _auto_score_company(self, company: Company) -> dict | None:
        """Auto-score a company after data changes. Returns score details or None."""
        try:
            result = self.company_scorer.score_company(company)
            company.score = result["score"]
            return result
        except Exception:
            return None

    # -- Full Pipelines --

    def company_full_pipeline(
        self,
        icp_name: str = "default",
        count: int = 5,
        contacts_per_company: int = 3,
        channels: list[str] | None = None,
        callback: object | None = None,
    ) -> dict:
        """End-to-end company pipeline:
        prospect companies → enrich → score → find contacts → enrich contacts → outreach.

        Args:
            icp_name: ICP to use for prospecting.
            count: Number of companies to prospect.
            contacts_per_company: Number of contacts to find at each company.
            channels: Outreach channels for contacts ('email', 'linkedin').
            callback: Optional callable(step, name, detail) for progress updates.

        Returns a summary dict.
        """
        if channels is None:
            channels = ["email", "linkedin"]

        def _notify(step: str, name: str = "", detail: str = ""):
            if callback and callable(callback):
                callback(step, name, detail)

        results: dict = {
            "companies_prospected": [],
            "companies_enriched": [],
            "contacts_found": [],
            "outreach": [],
            "errors": [],
        }

        # Step 1: Prospect companies
        _notify("prospect_companies_start", detail=f"Finding {count} companies matching ICP '{icp_name}'")
        try:
            new_companies = self.prospect_companies(icp_name=icp_name, count=count)
            results["companies_prospected"] = [
                {"id": c.id, "name": c.name, "domain": c.domain}
                for c in new_companies
            ]
            _notify("prospect_companies_done", detail=f"Found {len(new_companies)} new companies")
        except Exception as e:
            results["errors"].append({"step": "prospect_companies", "error": str(e)})
            _notify("prospect_companies_error", detail=str(e))
            return results

        if not new_companies:
            return results

        # Step 2: For each company: enrich → score → find contacts → outreach contacts
        for company in new_companies:
            company_name = company.name

            # Enrich company
            _notify("enrich_company_start", name=company_name)
            try:
                company, enriched_fields = self.enrich_company(company.id)
                results["companies_enriched"].append({
                    "id": company.id,
                    "name": company.name,
                    "fields": list(enriched_fields.keys()),
                })
                _notify("enrich_company_done", name=company_name, detail=f"{len(enriched_fields)} fields")
            except Exception as e:
                results["errors"].append({
                    "step": "enrich_company", "company": company_name, "error": str(e),
                })
                _notify("enrich_company_error", name=company_name, detail=str(e))

            # Score company
            if company.score == 0:
                try:
                    self.score_company(company.id)
                except Exception:
                    pass

            # Find contacts at this company
            domain = company.domain
            if not domain:
                _notify("contacts_skip", name=company_name, detail="No domain — skipping contact search")
                results["errors"].append({
                    "step": "find_contacts", "company": company_name,
                    "error": "No domain available to search for contacts",
                })
                continue

            _notify("find_contacts_start", name=company_name, detail=f"Finding {contacts_per_company} contacts")
            try:
                contacts = self.prospect_at_company(
                    domain=domain, icp_name=icp_name, count=contacts_per_company,
                )
                results["contacts_found"].extend([
                    {"id": l.id, "name": l.name, "company": company_name}
                    for l in contacts
                ])
                _notify("find_contacts_done", name=company_name, detail=f"Found {len(contacts)} contacts")
            except Exception as e:
                results["errors"].append({
                    "step": "find_contacts", "company": company_name, "error": str(e),
                })
                _notify("find_contacts_error", name=company_name, detail=str(e))
                continue

            # For each contact: enrich → research → outreach
            for lead in contacts:
                lead_name = f"{lead.name} @ {company_name}"

                # Enrich contact
                _notify("enrich_contact_start", name=lead_name)
                try:
                    lead, enriched = self.enrich_lead(lead.id)
                    _notify("enrich_contact_done", name=lead_name, detail=f"{len(enriched)} fields")
                except Exception as e:
                    results["errors"].append({
                        "step": "enrich_contact", "lead": lead_name, "error": str(e),
                    })
                    _notify("enrich_contact_error", name=lead_name, detail=str(e))

                # Research contact
                _notify("research_contact_start", name=lead_name)
                try:
                    lead = self.research_lead(lead.id)
                    _notify("research_contact_done", name=lead_name)
                except Exception as e:
                    results["errors"].append({
                        "step": "research_contact", "lead": lead_name, "error": str(e),
                    })
                    _notify("research_contact_error", name=lead_name, detail=str(e))

                # Outreach
                outreach_result: dict = {
                    "id": lead.id, "name": lead.name, "company": company_name,
                    "email_sent": False, "linkedin_generated": False,
                }

                if "email" in channels and lead.email:
                    try:
                        email_result = self.send_email(lead.id)
                        outreach_result["email_sent"] = True
                        outreach_result["email_to"] = email_result["sent_to"]
                        outreach_result["email_subject"] = email_result["message"].subject
                        _notify("email_done", name=lead_name, detail=email_result["sent_to"])
                    except Exception as e:
                        results["errors"].append({
                            "step": "send_email", "lead": lead_name, "error": str(e),
                        })
                        _notify("email_error", name=lead_name, detail=str(e))

                if "linkedin" in channels:
                    try:
                        li_msg = self.send_linkedin(lead.id, "connect")
                        outreach_result["linkedin_generated"] = True
                        outreach_result["linkedin_message"] = li_msg.body
                        outreach_result["linkedin_url"] = lead.linkedin_url or ""
                        _notify("linkedin_done", name=lead_name)
                    except Exception as e:
                        results["errors"].append({
                            "step": "linkedin", "lead": lead_name, "error": str(e),
                        })
                        _notify("linkedin_error", name=lead_name, detail=str(e))

                results["outreach"].append(outreach_result)

        return results

    # -- Pipeline Overview --

    def pipeline_summary(self) -> dict[str, int]:
        """Get a summary of leads by status."""
        summary: dict[str, int] = {}
        for status in LeadStatus:
            leads = self.db.list_leads(status)
            if leads:
                summary[status.value] = len(leads)
        return summary

    def company_pipeline_summary(self) -> dict[str, int]:
        """Get a summary of companies by status."""
        summary: dict[str, int] = {}
        for status in CompanyStatus:
            companies = self.db.list_companies(status)
            if companies:
                summary[status.value] = len(companies)
        return summary

    def close(self) -> None:
        self.db.close()
