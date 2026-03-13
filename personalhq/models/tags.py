"""Module defining SQLAlchemy model of Tags."""

from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class Tag(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table Tags in database."""
    __tablename__ = 'tags'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    color = db.Column(db.String(20), default='stone')

    experiences = relationship("TagExperience", back_populates="tag")
