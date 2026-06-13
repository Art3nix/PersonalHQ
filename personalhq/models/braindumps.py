"""Module defining SQLAlchemy model of BrainDumps."""

#import os
from datetime import datetime
from flask import current_app
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy_utils import StringEncryptedType
from sqlalchemy_utils.types.encrypted.encrypted_type import FernetEngine
from personalhq.extensions import db

#def get_encryption_key():
#    return os.environ.get('ENCRYPTION_KEY') or current_app.config.get('ENCRYPTION_KEY')

class BrainDump(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table brain_dumps in database."""
    __tablename__ = 'brain_dumps'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

# Inactive due to issues with InvalidToken when building from image
#    content: Mapped[str] = mapped_column(
#        StringEncryptedType(db.Text, get_encryption_key, FernetEngine),
#        nullable=False
#    )
    content: Mapped[str] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(nullable=False)
    processed: Mapped[bool | None]
    
    ai_insight: Mapped[str | None]

    user = relationship("User", back_populates="brain_dumps")
