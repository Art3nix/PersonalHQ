"""Module defining SQLAlchemy model of Habits."""

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from personalhq.services.time_service import get_utc_now

from personalhq.extensions import db

class HabitFrequency(enum.Enum):
    """Class representing frequency of a habit."""
    DAILY = "DAILY"
    WEEKLY = "WEEKLY"

class Habit(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table Habits in database."""
    __tablename__ = "habits"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    identity_id: Mapped[int | None] = mapped_column(ForeignKey('identities.id'))

    name: Mapped[str] = mapped_column(nullable=False)
    identity: Mapped[str | None]
    icon: Mapped[str] = mapped_column(nullable=False)
    frequency: Mapped[HabitFrequency] = mapped_column(
        SAEnum(HabitFrequency, name="frequency"),
        default=HabitFrequency.DAILY,
        nullable=False
    )
    streak: Mapped[int] = mapped_column(default=0, server_default="0")
    best_streak: Mapped[int] = mapped_column(default=0, server_default="0")
    description: Mapped[str | None]   # Response - what exactly you do
    trigger: Mapped[str | None]        # Cue - what triggers the habit
    craving: Mapped[str | None]        # Why it matters / motivation
    reward: Mapped[str | None]         # How you celebrate completion
    category: Mapped[str | None]
    last_completed: Mapped[datetime | None]
    target_count: Mapped[int] = mapped_column(db.Integer, default=1, server_default="1", nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    created_at = db.Column(db.DateTime, default=get_utc_now, nullable=True)

    identity = relationship("Identity", back_populates="habits")
    user = relationship("User", back_populates="habits")
    logs = relationship("HabitLog", back_populates="habit", cascade="all, delete-orphan", order_by="desc(HabitLog.completed_date)")
