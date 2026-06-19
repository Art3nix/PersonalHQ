from personalhq.extensions import db
from sqlalchemy.orm import Mapped, mapped_column
from personalhq.services.time_service import get_utc_now
from datetime import datetime

class WaitlistLead(db.Model):
    __tablename__ = 'waitlist_leads'
    
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(db.String(255), nullable=False)
    plan_interest: Mapped[str] = mapped_column(db.String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(db.DateTime, default=get_utc_now)