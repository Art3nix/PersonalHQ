"""Module defining SQLAlchemy model of BucketExperience."""

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from personalhq.extensions import db


class BucketExperience(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Association class for Many-to-Many relationship between LifeBuckets and Experiences"""
    __tablename__ = 'bucket_experiences'
    bucket_id: Mapped[int] = mapped_column(ForeignKey("life_buckets.id"), primary_key=True)
    experience_id: Mapped[int] = mapped_column(ForeignKey("experiences.id"), primary_key=True)

    bucket = db.relationship('LifeBucket', back_populates='experiences')
    experience = db.relationship('Experience', back_populates='buckets')
