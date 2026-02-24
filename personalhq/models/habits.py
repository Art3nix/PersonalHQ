"""Module defining SQLAlchemy model of Habits."""

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

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

    name: Mapped[str] = mapped_column(nullable=False)
    identity: Mapped[str | None]
    icon: Mapped[str] = mapped_column(nullable=False)
    frequency: Mapped[HabitFrequency] = mapped_column(
        SAEnum(HabitFrequency, name="frequency"),
        default=HabitFrequency.DAILY,
        nullable=False
    )
    streak: Mapped[int | None]
    category: Mapped[str | None]
    last_completed: Mapped[datetime | None]

    user = relationship("User", back_populates="habits")
