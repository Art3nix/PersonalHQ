"""Module handling complex business logic for User accounts and settings."""

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump
from personalhq.models.journalentries import JournalEntry

def recalculate_user_reset_hour(user):
    """
    Finds the user's deepest period of inactivity over the last 14 days
    and updates their day_reset_hour to the exact middle of that period.
    """
    try:
        user_zone = ZoneInfo(user.timezone or "UTC")
    except Exception:
        user_zone = ZoneInfo("UTC")

    now_utc = datetime.now(timezone.utc)
    two_weeks_ago_utc = now_utc - timedelta(days=14)
    naive_two_weeks_ago = two_weeks_ago_utc.replace(tzinfo=None)
    
    dumps = db.session.scalars(select(BrainDump.created_at).filter(BrainDump.user_id == user.id, BrainDump.created_at >= naive_two_weeks_ago)).all()
    journals = db.session.scalars(select(JournalEntry.created_at).filter(JournalEntry.user_id == user.id, JournalEntry.created_at >= naive_two_weeks_ago)).all()
    
    all_utc_timestamps = dumps + journals
    
    if len(all_utc_timestamps) < 10:
        return
        
    hourly_activity = [0] * 24
    for dt in all_utc_timestamps:
        aware_utc_dt = dt.replace(tzinfo=timezone.utc)
        local_dt = aware_utc_dt.astimezone(user_zone)
        hourly_activity[local_dt.hour] += 1
        
    min_activity = float('inf')
    best_start_hour = 3
    
    for i in range(24):
        window_sum = sum(hourly_activity[(i + j) % 24] for j in range(6))
        if window_sum < min_activity:
            min_activity = window_sum
            best_start_hour = i
            
    new_reset_hour = (best_start_hour + 3) % 24
    
    user.day_reset_hour = new_reset_hour
    db.session.commit()
    
    return new_reset_hour