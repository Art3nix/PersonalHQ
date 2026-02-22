"""Module defining SQLAlchemy model of Subscriptions."""

import enum
from datetime import datetime

from sqlalchemy import ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class SubscriptionStatus(enum.Enum):
    """Class representing status of a subscription."""
    ACTIVE = "ACTIVE"
    CANCELED = "CANCELED"
    EXPIRED = "EXPIRED"

class Subscription(db.Model):  # pylint: disable=R0903; # sqlalchemy class used to only store data
    """Class representing table Subscriptions in database."""
    __tablename__ = "subscriptions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'))
    plan_id: Mapped[int] = mapped_column(ForeignKey('plans.id'))

    start_date: Mapped[datetime] = mapped_column(nullable=False)
    end_date: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[SubscriptionStatus] = mapped_column(
        SAEnum(SubscriptionStatus, name="subscription_status"),
        default=SubscriptionStatus.ACTIVE,
        nullable=False
    )

    user = relationship("User", back_populates="subscriptions")
    plan = relationship("Plan", back_populates="subscriptions")

    def __init__(self, user_id: int, movie_id: int, date_watched: datetime):
        self.user_id = user_id
        self.movie_id = movie_id
        self.date_watched = date_watched

    def __repr__(self):
        return (
            f'<Subscription {self.id} for {self.user_id}>'
            f' {self.plan_id}'
            f' {self.status}'
            f' {self.start_date}'
            f' {self.end_date}'
        )
