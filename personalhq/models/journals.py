"""Module defining the SQLAlchemy model for Journals."""

import enum
from sqlalchemy import ForeignKey, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class JournalFrequency(enum.Enum):
    """Enumeration for how often a journal's prompts should rotate."""
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    YEARLY = "yearly"
    ON_DEMAND = "random"

class Journal(db.Model):
    """Class representing a specific journal category."""
    __tablename__ = 'journals'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str | None]
    icon: Mapped[str | None]
    color = db.Column(db.String(20), default='stone')
    frequency: Mapped[JournalFrequency] = mapped_column(Enum(JournalFrequency), default=JournalFrequency.DAILY)

    ai_insight: Mapped[str | None]

    user = relationship("User", back_populates="journals")
    prompts = relationship("JournalPrompt", back_populates="journal", cascade="all, delete-orphan", order_by="JournalPrompt.id")
    entries = relationship("JournalEntry", back_populates="journal", cascade="all, delete-orphan", order_by="desc(JournalEntry.created_at)")
