"""Follow-up sequence automation."""

from __future__ import annotations

from datetime import datetime, timedelta

from ..models import (
    Channel,
    Lead,
    LeadStatus,
    Message,
    MessageType,
    Sequence,
    SequenceStep,
)
from ..storage import Database
from .outreach import OutreachEngine
from ..config import Config


# Default follow-up sequence: 5 touches over ~3 weeks
DEFAULT_SEQUENCE_STEPS = [
    SequenceStep(delay_days=0, channel=Channel.EMAIL, message_type=MessageType.INITIAL_OUTREACH),
    SequenceStep(delay_days=3, channel=Channel.EMAIL, message_type=MessageType.FOLLOW_UP),
    SequenceStep(delay_days=5, channel=Channel.EMAIL, message_type=MessageType.FOLLOW_UP),
    SequenceStep(delay_days=7, channel=Channel.EMAIL, message_type=MessageType.FOLLOW_UP),
    SequenceStep(delay_days=7, channel=Channel.EMAIL, message_type=MessageType.FOLLOW_UP),
]


class SequenceManager:
    """Manages automated follow-up sequences for leads."""

    def __init__(self, config: Config, db: Database, outreach: OutreachEngine):
        self.config = config
        self.db = db
        self.outreach = outreach

    def create_sequence(
        self, lead: Lead, steps: list[SequenceStep] | None = None
    ) -> Sequence:
        """Create a new follow-up sequence for a lead."""
        if steps is None:
            steps = [
                SequenceStep(
                    delay_days=s.delay_days,
                    channel=s.channel,
                    message_type=s.message_type,
                )
                for s in DEFAULT_SEQUENCE_STEPS
            ]

        sequence = Sequence(lead_id=lead.id, steps=steps)
        self.db.save_sequence(sequence)
        return sequence

    def get_due_sequences(self) -> list[tuple[Sequence, Lead]]:
        """Find sequences that have steps due for execution."""
        active = self.db.get_active_sequences()
        due: list[tuple[Sequence, Lead]] = []

        for seq in active:
            if seq.current_step >= len(seq.steps):
                seq.is_active = False
                self.db.save_sequence(seq)
                continue

            step = seq.steps[seq.current_step]
            if step.completed:
                continue

            # Check if enough time has passed since sequence creation or last step
            if seq.current_step == 0:
                start = datetime.fromisoformat(seq.created_at)
            else:
                prev_step = seq.steps[seq.current_step - 1]
                if prev_step.completed_at:
                    start = datetime.fromisoformat(prev_step.completed_at)
                else:
                    continue

            due_date = start + timedelta(days=step.delay_days)
            if datetime.now() >= due_date:
                lead = self.db.get_lead(seq.lead_id)
                if lead:
                    due.append((seq, lead))

        return due

    def execute_step(self, sequence: Sequence, lead: Lead) -> Message | None:
        """Execute the current step of a sequence."""
        if sequence.current_step >= len(sequence.steps):
            return None

        step = sequence.steps[sequence.current_step]
        messages = self.db.get_messages_for_lead(lead.id)

        if step.message_type == MessageType.INITIAL_OUTREACH:
            message = self.outreach.generate_initial_outreach(lead, step.channel)
        elif step.message_type == MessageType.FOLLOW_UP:
            message = self.outreach.generate_follow_up(
                lead, messages, sequence.current_step, step.channel
            )
        else:
            return None

        # Mark step as completed
        step.completed = True
        step.completed_at = datetime.now().isoformat()
        sequence.current_step += 1

        if sequence.current_step >= len(sequence.steps):
            sequence.is_active = False

        # Save everything
        self.db.save_message(message)
        self.db.save_sequence(sequence)

        if lead.status == LeadStatus.NEW:
            self.db.update_lead_status(lead.id, LeadStatus.CONTACTED)

        return message

    def pause_sequence(self, sequence_id: str) -> None:
        """Pause an active sequence (e.g., when a lead replies)."""
        sequences = self.db.get_active_sequences()
        for seq in sequences:
            if seq.id == sequence_id:
                seq.is_active = False
                self.db.save_sequence(seq)
                break

    def run_due_sequences(self) -> list[tuple[Lead, Message]]:
        """Check and execute all due sequence steps. Returns generated messages."""
        results: list[tuple[Lead, Message]] = []
        due = self.get_due_sequences()

        for sequence, lead in due:
            message = self.execute_step(sequence, lead)
            if message:
                results.append((lead, message))

        return results
