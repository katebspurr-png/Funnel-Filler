"""Data models for leads, conversations, and outreach."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4


class LeadStatus(str, Enum):
    NEW = "new"
    RESEARCHING = "researching"
    OUTREACH_PENDING = "outreach_pending"
    CONTACTED = "contacted"
    REPLIED = "replied"
    QUALIFIED = "qualified"
    MEETING_BOOKED = "meeting_booked"
    DISQUALIFIED = "disqualified"
    UNRESPONSIVE = "unresponsive"


class MessageType(str, Enum):
    INITIAL_OUTREACH = "initial_outreach"
    FOLLOW_UP = "follow_up"
    REPLY = "reply"
    MEETING_REQUEST = "meeting_request"


class Channel(str, Enum):
    EMAIL = "email"
    LINKEDIN = "linkedin"


@dataclass
class Lead:
    """A prospective lead/contact."""

    name: str
    email: str = ""
    company: str = ""
    title: str = ""
    industry: str = ""
    linkedin_url: str = ""
    notes: str = ""
    status: LeadStatus = LeadStatus.NEW
    score: int = 0  # 0-100 qualification score
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    research: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["research"] = json.dumps(d["research"])
        d["tags"] = json.dumps(d["tags"])
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Lead:
        if isinstance(d.get("research"), str):
            d["research"] = json.loads(d["research"])
        if isinstance(d.get("tags"), str):
            d["tags"] = json.loads(d["tags"])
        d["status"] = LeadStatus(d["status"])
        return cls(**d)


@dataclass
class Message:
    """A message sent to or received from a lead."""

    lead_id: str
    channel: Channel
    message_type: MessageType
    subject: str = ""
    body: str = ""
    sent_at: str = ""
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    is_inbound: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Message:
        d["channel"] = Channel(d["channel"])
        d["message_type"] = MessageType(d["message_type"])
        return cls(**d)


@dataclass
class Sequence:
    """A follow-up sequence for a lead."""

    lead_id: str
    steps: list[SequenceStep] = field(default_factory=list)
    current_step: int = 0
    is_active: bool = True
    id: str = field(default_factory=lambda: uuid4().hex[:12])
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass
class SequenceStep:
    """A single step in a follow-up sequence."""

    delay_days: int
    channel: Channel
    message_type: MessageType
    template_name: str = ""
    completed: bool = False
    completed_at: str = ""
