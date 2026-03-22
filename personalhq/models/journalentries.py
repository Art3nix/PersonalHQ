"""Module defining SQLAlchemy models for Journal entries."""

from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from personalhq.services.time_service import get_local_now

from personalhq.extensions import db

class JournalEntry(db.Model):
    """Class representing a single, timestamped entry within a journal."""
    __tablename__ = 'journal_entries'

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey('journals.id'), nullable=False)
    prompt_id: Mapped[int] = mapped_column(ForeignKey('journal_prompts.id', ondelete='SET NULL'), nullable=True)

    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=get_local_now)

    journal = relationship("Journal", back_populates="entries")
    prompt = relationship("JournalPrompt")
