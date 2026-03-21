"""Module defining SQLAlchemy model of Experience CoreThemes."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class CoreTheme(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table core_themes in database."""
    __tablename__ = 'core_themes'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    color = db.Column(db.String(20), default='stone')

    user = relationship("User", backref="themes")
    experiences = relationship("Experience", back_populates="core_theme")
