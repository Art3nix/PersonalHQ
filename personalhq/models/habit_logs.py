"""Module defining the SQLAlchemy model for Habit Logs."""

from datetime import date, datetime
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from personalhq.services.time_service import get_utc_now

from personalhq.extensions import db

class HabitLog(db.Model):
    """Class representing table habit_logs in database."""
    __tablename__ = 'habit_logs'

    id: Mapped[int] = mapped_column(primary_key=True)

    # When habit is deleted, its entire history is wiped too
    habit_id: Mapped[int] = mapped_column(ForeignKey('habits.id', ondelete='CASCADE'), nullable=False)

    # The calendar day this log belongs to
    completed_date: Mapped[date] = mapped_column(nullable=False)

    # The Ledger Data
    progress: Mapped[int] = mapped_column(default=0, nullable=False)
    target_at_time: Mapped[int] = mapped_column(default=1, nullable=False) # Freezes historical target

    # The exact timestamp the database last updated this log
    logged_at: Mapped[datetime] = mapped_column(default=get_utc_now, onupdate=get_utc_now)

    ai_celebration: Mapped[str | None]  # e.g., "Boom! 5 days straight."
    ai_intervention: Mapped[str | None] # e.g., "You missed this yesterday. Do 2 minutes today."
    
    # Relationship back to the parent habit
    habit = relationship("Habit", back_populates="logs")

    # Absolutely guarantees only ONE row can exist per habit, per day
    __table_args__ = (
        UniqueConstraint('habit_id', 'completed_date', name='uq_habit_date'),
    )