"""Module defining SQLAlchemy model of Focus Sessions."""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class Task(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table Tasks in database."""
    __tablename__ = 'tasks'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    title_name: Mapped[str] = mapped_column(nullable=False)
    is_completed: Mapped[bool] = mapped_column(nullable=False)
    date_completed_at: Mapped[datetime | None]
    created_at: Mapped[datetime] = mapped_column(nullable=False)

    user = relationship("User", back_populates="tasks")
