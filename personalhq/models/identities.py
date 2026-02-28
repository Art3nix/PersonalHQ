"""Module defining SQLAlchemy model for Identities."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class Identity(db.Model):
    """Class representing table identities in database."""
    __tablename__ = 'identities'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    # e.g., "The Athlete", "The System Architect", "The Writer"
    name: Mapped[str] = mapped_column(nullable=False) 
    
    # A short reminder of the standard you hold yourself to
    description: Mapped[str | None] 

    user = relationship("User", back_populates="identities")
    
    # The actions that serve as "votes" for this identity
    habits = relationship("Habit", back_populates="identity", cascade="all, delete-orphan")
    focus_sessions = relationship("FocusSession", back_populates="identity")