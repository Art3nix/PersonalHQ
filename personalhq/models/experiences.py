"""Module defining SQLAlchemy model of Experiences."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class Experience(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table Experiences in database."""
    __tablename__ = 'experiences'

    id: Mapped[int] = mapped_column(primary_key=True)
    theme_id: Mapped[int] = mapped_column(ForeignKey('themes.id'))
    emotional_value_id: Mapped[int] = mapped_column(ForeignKey('emotional_values.id'))

    name: Mapped[str] = mapped_column(nullable=False)
    details: Mapped[str]

    core_theme = relationship("CoreTheme", back_populates="experiences")
    emotional_value = relationship("EmotionalValue", back_populates="experiences")
    buckets = relationship("BucketExperience", back_populates="experience")
    tags = relationship("TagExperience", back_populates="experience")
