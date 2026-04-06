"""Module defining SQLAlchemy model of BrainDumps."""

from datetime import datetime

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db


class BrainDump(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table brain_dumps in database."""
    __tablename__ = 'brain_dumps'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    processed: Mapped[bool | None]
    
    ai_insight: Mapped[str | None]

    user = relationship("User", back_populates="brain_dumps")
