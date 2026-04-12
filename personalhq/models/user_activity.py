"""Module defining the User Activity log for sleep window calculation."""

from datetime import datetime
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from personalhq.extensions import db
from personalhq.services.time_service import get_utc_now

class UserActivity(db.Model):
    __tablename__ = 'user_activities'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(default=get_utc_now, index=True, nullable=False)