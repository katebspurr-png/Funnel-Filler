"""Configuration management for the SDR agent."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


def _load_env() -> None:
    """Load environment variables from .env file if it exists."""
    env_path = Path.cwd() / ".env"
    if env_path.exists():
        load_dotenv(env_path)


@dataclass
class CompanyProfile:
    """Your company's info, used for personalizing outreach."""

    name: str = ""
    description: str = ""
    value_props: list[str] = field(default_factory=list)
    target_industries: list[str] = field(default_factory=list)
    target_titles: list[str] = field(default_factory=list)


@dataclass
class SenderProfile:
    """The SDR sender's info."""

    name: str = ""
    title: str = "Sales Development Representative"
    email: str = ""
    calendar_link: str = ""


@dataclass
class SmtpConfig:
    """SMTP configuration for sending emails."""

    host: str = "smtp.gmail.com"
    port: int = 587
    username: str = ""
    password: str = ""


@dataclass
class Config:
    """Global configuration for the SDR agent."""

    anthropic_api_key: str = ""
    apollo_api_key: str = ""
    resend_api_key: str = ""
    resend_from_email: str = ""
    model: str = "claude-sonnet-4-6"
    db_path: str = "funnel_filler.db"
    company: CompanyProfile = field(default_factory=CompanyProfile)
    sender: SenderProfile = field(default_factory=SenderProfile)
    smtp: SmtpConfig = field(default_factory=SmtpConfig)

    @classmethod
    def from_env(cls) -> Config:
        """Load configuration from environment variables."""
        _load_env()
        return cls(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            apollo_api_key=os.getenv("APOLLO_API_KEY", ""),
            resend_api_key=os.getenv("RESEND_API_KEY", ""),
            resend_from_email=os.getenv("RESEND_FROM_EMAIL", ""),
            model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
            db_path=os.getenv("DB_PATH", "funnel_filler.db"),
            company=CompanyProfile(
                name=os.getenv("COMPANY_NAME", ""),
                description=os.getenv("COMPANY_DESCRIPTION", ""),
            ),
            sender=SenderProfile(
                name=os.getenv("SENDER_NAME", ""),
                title=os.getenv("SENDER_TITLE", "Sales Development Representative"),
                email=os.getenv("SMTP_USERNAME", ""),
                calendar_link=os.getenv("CALENDAR_LINK", ""),
            ),
            smtp=SmtpConfig(
                host=os.getenv("SMTP_HOST", "smtp.gmail.com"),
                port=int(os.getenv("SMTP_PORT", "587")),
                username=os.getenv("SMTP_USERNAME", ""),
                password=os.getenv("SMTP_PASSWORD", ""),
            ),
        )
