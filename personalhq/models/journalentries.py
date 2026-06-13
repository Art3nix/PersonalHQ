"""Module defining SQLAlchemy models for Journal entries."""

#import os
from datetime import datetime
from flask import current_app
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine
from personalhq.services.time_service import get_utc_now
from personalhq.extensions import db

#def get_encryption_key():
#    return os.environ.get('ENCRYPTION_KEY') or current_app.config.get('ENCRYPTION_KEY')

class JournalEntry(db.Model):
    """Class representing a single, timestamped entry within a journal."""
    __tablename__ = 'journal_entries'

    id: Mapped[int] = mapped_column(primary_key=True)
    journal_id: Mapped[int] = mapped_column(ForeignKey('journals.id'), nullable=False)
    prompt_id: Mapped[int] = mapped_column(ForeignKey('journal_prompts.id', ondelete='SET NULL'), nullable=True)

# Inactive due to issues with InvalidToken when building from image
#    content: Mapped[str] = mapped_column(
#        StringEncryptedType(db.Text, get_encryption_key, FernetEngine),
#        nullable=False
#    )
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(default=get_utc_now)

    ai_insight: Mapped[str | None]

    journal = relationship("Journal", back_populates="entries")
    prompt = relationship("JournalPrompt")
