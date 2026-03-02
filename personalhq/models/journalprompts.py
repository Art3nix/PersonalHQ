"""Module defining SQLAlchemy models for Journal Prompts."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class JournalPrompt(db.Model):
    """Class representing a rotating question/theme for a journal."""
    __tablename__ = 'journal_prompts'

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey('journals.id'), nullable=False)

    text: Mapped[str] = mapped_column(nullable=False)

    journal = relationship("Journal", back_populates="prompts")
