"""Module defining SQLAlchemy model of Experience CoreThemes."""

from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class CoreTheme(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table core_themes in database."""
    __tablename__ = 'core_themes'

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True, nullable=False)
    color = db.Column(db.String(20), default='stone')

    experiences = relationship("Experience", back_populates="core_theme")
