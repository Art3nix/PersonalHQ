"""Module defining the SQLAlchemy model for Habit Logs."""

from datetime import date, datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class HabitLog(db.Model):
    """Class representing table habit_logs in database."""
    __tablename__ = 'habit_logs'

    id: Mapped[int] = mapped_column(primary_key=True)

    # When habit is deleted, its entire history is wiped too
    habit_id: Mapped[int] = mapped_column(ForeignKey('habits.id', ondelete='CASCADE'), nullable=False)

    # The calendar day this completion counts towards
    completed_date: Mapped[date] = mapped_column(nullable=False, default=date.today)

    # The exact timestamp the database recorded the click
    logged_at: Mapped[datetime] = mapped_column(default=datetime.now)
    # Relationship back to the parent habit
    habit = relationship("Habit", back_populates="logs")
