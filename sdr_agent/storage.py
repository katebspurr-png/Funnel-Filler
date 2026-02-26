"""SQLite storage layer for leads, messages, and sequences."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .models import ICP, Lead, LeadStatus, Message, Sequence, SequenceStep, Channel, MessageType


class Database:
    """Simple SQLite database for persisting SDR data."""

    def __init__(self, db_path: str = "funnel_filler.db"):
        self.db_path = db_path
        self._conn: sqlite3.Connection | None = None
        self._ensure_tables()

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_tables(self) -> None:
        self.conn.executescript("""
            CREATE TABLE IF NOT EXISTS leads (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT,
                company TEXT,
                title TEXT,
                industry TEXT,
                linkedin_url TEXT,
                notes TEXT,
                status TEXT DEFAULT 'new',
                score INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT,
                research TEXT DEFAULT '{}',
                tags TEXT DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                channel TEXT,
                message_type TEXT,
                subject TEXT,
                body TEXT,
                sent_at TEXT,
                created_at TEXT,
                is_inbound INTEGER DEFAULT 0,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            );

            CREATE TABLE IF NOT EXISTS icps (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                titles TEXT DEFAULT '[]',
                seniorities TEXT DEFAULT '[]',
                industries TEXT DEFAULT '[]',
                company_sizes TEXT DEFAULT '[]',
                locations TEXT DEFAULT '[]',
                keywords TEXT DEFAULT '[]',
                created_at TEXT
            );

            CREATE TABLE IF NOT EXISTS sequences (
                id TEXT PRIMARY KEY,
                lead_id TEXT NOT NULL,
                steps TEXT DEFAULT '[]',
                current_step INTEGER DEFAULT 0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                FOREIGN KEY (lead_id) REFERENCES leads(id)
            );
        """)
        self.conn.commit()

    # -- Lead operations --

    def save_lead(self, lead: Lead) -> Lead:
        data = lead.to_dict()
        self.conn.execute(
            """INSERT OR REPLACE INTO leads
            (id, name, email, company, title, industry, linkedin_url,
             notes, status, score, created_at, updated_at, research, tags)
            VALUES (:id, :name, :email, :company, :title, :industry, :linkedin_url,
                    :notes, :status, :score, :created_at, :updated_at, :research, :tags)""",
            data,
        )
        self.conn.commit()
        return lead

    def get_lead(self, lead_id: str) -> Lead | None:
        row = self.conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,)).fetchone()
        if row is None:
            return None
        return Lead.from_dict(dict(row))

    def list_leads(self, status: LeadStatus | None = None) -> list[Lead]:
        if status:
            rows = self.conn.execute(
                "SELECT * FROM leads WHERE status = ? ORDER BY updated_at DESC",
                (status.value,),
            ).fetchall()
        else:
            rows = self.conn.execute(
                "SELECT * FROM leads ORDER BY updated_at DESC"
            ).fetchall()
        return [Lead.from_dict(dict(r)) for r in rows]

    def update_lead_status(self, lead_id: str, status: LeadStatus) -> None:
        from datetime import datetime

        self.conn.execute(
            "UPDATE leads SET status = ?, updated_at = ? WHERE id = ?",
            (status.value, datetime.now().isoformat(), lead_id),
        )
        self.conn.commit()

    def search_leads(self, query: str) -> list[Lead]:
        rows = self.conn.execute(
            """SELECT * FROM leads
            WHERE name LIKE ? OR company LIKE ? OR email LIKE ? OR title LIKE ?
            ORDER BY updated_at DESC""",
            (f"%{query}%",) * 4,
        ).fetchall()
        return [Lead.from_dict(dict(r)) for r in rows]

    # -- Message operations --

    def save_message(self, message: Message) -> Message:
        data = message.to_dict()
        data["is_inbound"] = int(data["is_inbound"])
        self.conn.execute(
            """INSERT OR REPLACE INTO messages
            (id, lead_id, channel, message_type, subject, body, sent_at, created_at, is_inbound)
            VALUES (:id, :lead_id, :channel, :message_type, :subject, :body,
                    :sent_at, :created_at, :is_inbound)""",
            data,
        )
        self.conn.commit()
        return message

    def get_messages_for_lead(self, lead_id: str) -> list[Message]:
        rows = self.conn.execute(
            "SELECT * FROM messages WHERE lead_id = ? ORDER BY created_at ASC",
            (lead_id,),
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            d["is_inbound"] = bool(d["is_inbound"])
            results.append(Message.from_dict(d))
        return results

    # -- ICP operations --

    def save_icp(self, icp: ICP) -> ICP:
        data = icp.to_dict()
        self.conn.execute(
            """INSERT OR REPLACE INTO icps
            (id, name, titles, seniorities, industries, company_sizes,
             locations, keywords, created_at)
            VALUES (:id, :name, :titles, :seniorities, :industries,
                    :company_sizes, :locations, :keywords, :created_at)""",
            data,
        )
        self.conn.commit()
        return icp

    def get_icp(self, name: str = "default") -> ICP | None:
        row = self.conn.execute(
            "SELECT * FROM icps WHERE name = ?", (name,)
        ).fetchone()
        if row is None:
            return None
        return ICP.from_dict(dict(row))

    def list_icps(self) -> list[ICP]:
        rows = self.conn.execute(
            "SELECT * FROM icps ORDER BY created_at DESC"
        ).fetchall()
        return [ICP.from_dict(dict(r)) for r in rows]

    # -- Sequence operations --

    def save_sequence(self, sequence: Sequence) -> Sequence:
        steps_json = json.dumps([
            {
                "delay_days": s.delay_days,
                "channel": s.channel.value,
                "message_type": s.message_type.value,
                "template_name": s.template_name,
                "completed": s.completed,
                "completed_at": s.completed_at,
            }
            for s in sequence.steps
        ])
        self.conn.execute(
            """INSERT OR REPLACE INTO sequences
            (id, lead_id, steps, current_step, is_active, created_at)
            VALUES (?, ?, ?, ?, ?, ?)""",
            (sequence.id, sequence.lead_id, steps_json,
             sequence.current_step, int(sequence.is_active), sequence.created_at),
        )
        self.conn.commit()
        return sequence

    def get_active_sequences(self) -> list[Sequence]:
        rows = self.conn.execute(
            "SELECT * FROM sequences WHERE is_active = 1"
        ).fetchall()
        results = []
        for r in rows:
            d = dict(r)
            steps_data = json.loads(d["steps"])
            steps = [
                SequenceStep(
                    delay_days=s["delay_days"],
                    channel=Channel(s["channel"]),
                    message_type=MessageType(s["message_type"]),
                    template_name=s.get("template_name", ""),
                    completed=s.get("completed", False),
                    completed_at=s.get("completed_at", ""),
                )
                for s in steps_data
            ]
            results.append(Sequence(
                id=d["id"],
                lead_id=d["lead_id"],
                steps=steps,
                current_step=d["current_step"],
                is_active=bool(d["is_active"]),
                created_at=d["created_at"],
            ))
        return results

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
