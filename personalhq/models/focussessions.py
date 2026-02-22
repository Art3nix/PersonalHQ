"""Module defining SQLAlchemy model of Focus Sessions."""

import enum
from datetime import datetime, date

from sqlalchemy import ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class SessionStatus(enum.Enum):
    """Class representing status of a focus session."""
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    PAUSED = "PAUSED"
    FINISHED = "FINISHED"

class FocusSession(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table focus_sessions in database."""
    __tablename__ = 'focus_sessions'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    target_date: Mapped[date] = mapped_column(nullable=False)
    start_time: Mapped[datetime]
    end_time: Mapped[datetime]
    status: Mapped[SessionStatus] = mapped_column(
        SAEnum(SessionStatus, name="session_status"),
        default=SessionStatus.NOT_STARTED,
        nullable=False
    )
    queue_order: Mapped[int] = mapped_column(nullable=False)
    total_paused_seconds: Mapped[int]
    last_paused_tick: Mapped[datetime]

    user = relationship("User", back_populates="focus_sessions")
