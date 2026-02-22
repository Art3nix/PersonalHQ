"""Module defining SQLAlchemy model of TagExperience."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from personalhq.extensions import db


class TagExperience(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Association class for Many-to-Many relationship between Tags and Experiences"""
    __tablename__ = 'experience_tags'
    experience_id: Mapped[int] = mapped_column(ForeignKey("experiences.id"), primary_key=True)
    tag_id: Mapped[int] = mapped_column(ForeignKey("tags.id"), primary_key=True)

    tag = db.relationship('Tag', back_populates='experiences')
    experience = db.relationship('Experience', back_populates='tags')
