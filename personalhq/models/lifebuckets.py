"""Module defining SQLAlchemy model of LifeBuckets."""

from datetime import date

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class LifeBucket(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table life_buckets in database."""
    __tablename__ = 'life_buckets'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)

    name: Mapped[str] = mapped_column(nullable=False)
    theme: Mapped[str] = mapped_column(nullable=False)
    start_date: Mapped[date] = mapped_column(nullable=False)
    end_date: Mapped[date] = mapped_column(nullable=False)

    user = relationship("User", back_populates="life_buckets")
    experiences = relationship("BucketExperience", back_populates="bucket")
