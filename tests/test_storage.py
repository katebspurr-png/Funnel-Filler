"""Tests for the storage layer."""

import os
import tempfile

from sdr_agent.models import Channel, Lead, LeadStatus, Message, MessageType
from sdr_agent.storage import Database


def _temp_db() -> Database:
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    return Database(db_path=path)


def test_save_and_get_lead():
    db = _temp_db()
    lead = Lead(name="Jane Doe", email="jane@example.com", company="Acme", title="VP Sales")
    db.save_lead(lead)

    retrieved = db.get_lead(lead.id)
    assert retrieved is not None
    assert retrieved.name == "Jane Doe"
    assert retrieved.email == "jane@example.com"
    assert retrieved.company == "Acme"
    db.close()


def test_list_leads_by_status():
    db = _temp_db()
    lead1 = Lead(name="Alice", status=LeadStatus.NEW)
    lead2 = Lead(name="Bob", status=LeadStatus.CONTACTED)
    db.save_lead(lead1)
    db.save_lead(lead2)

    new_leads = db.list_leads(LeadStatus.NEW)
    assert len(new_leads) == 1
    assert new_leads[0].name == "Alice"

    all_leads = db.list_leads()
    assert len(all_leads) == 2
    db.close()


def test_update_lead_status():
    db = _temp_db()
    lead = Lead(name="Charlie", status=LeadStatus.NEW)
    db.save_lead(lead)

    db.update_lead_status(lead.id, LeadStatus.QUALIFIED)
    updated = db.get_lead(lead.id)
    assert updated is not None
    assert updated.status == LeadStatus.QUALIFIED
    db.close()


def test_save_and_get_messages():
    db = _temp_db()
    lead = Lead(name="Dana")
    db.save_lead(lead)

    msg = Message(
        lead_id=lead.id,
        channel=Channel.EMAIL,
        message_type=MessageType.INITIAL_OUTREACH,
        subject="Quick question",
        body="Hey Dana...",
    )
    db.save_message(msg)

    messages = db.get_messages_for_lead(lead.id)
    assert len(messages) == 1
    assert messages[0].subject == "Quick question"
    assert messages[0].channel == Channel.EMAIL
    db.close()


def test_search_leads():
    db = _temp_db()
    db.save_lead(Lead(name="Eve Smith", company="TechCorp"))
    db.save_lead(Lead(name="Frank Jones", company="SalesCo"))

    results = db.search_leads("TechCorp")
    assert len(results) == 1
    assert results[0].name == "Eve Smith"

    results = db.search_leads("Jones")
    assert len(results) == 1
    assert results[0].name == "Frank Jones"
    db.close()


def test_lead_with_research_and_tags():
    db = _temp_db()
    lead = Lead(
        name="Grace",
        research={"pain_points": "needs automation"},
        tags=["high-priority", "saas"],
    )
    db.save_lead(lead)

    retrieved = db.get_lead(lead.id)
    assert retrieved is not None
    assert retrieved.research["pain_points"] == "needs automation"
    assert "high-priority" in retrieved.tags
    db.close()
