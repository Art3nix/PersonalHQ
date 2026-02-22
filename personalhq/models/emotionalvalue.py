"""Module defining SQLAlchemy model of Experience EmotionalValue."""

from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class EmotionalValue(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table emotional_value in database."""
    __tablename__ = 'emotional_value'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)

    experiences = relationship("Experience", back_populates="emotional_value")
