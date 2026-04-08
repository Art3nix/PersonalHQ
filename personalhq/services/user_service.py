"""Module handling complex business logic for User accounts and settings."""

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump
from personalhq.models.journalentries import JournalEntry
from personalhq.models.user_activity import UserActivity
from personalhq.models.focussessions import FocusSession
from personalhq.models.habit_logs import HabitLog

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

    # Query all activity sources
    dumps = db.session.scalars(select(BrainDump.created_at).filter(BrainDump.user_id == user.id, BrainDump.created_at >= naive_two_weeks_ago)).all()
    journals = db.session.scalars(select(JournalEntry.created_at).filter(JournalEntry.user_id == user.id, JournalEntry.created_at >= naive_two_weeks_ago)).all()
    page_views = db.session.scalars(select(UserActivity.timestamp).filter(UserActivity.user_id == user.id, UserActivity.timestamp >= naive_two_weeks_ago)).all()
    focus = db.session.scalars(select(FocusSession.start_time).filter(FocusSession.user_id == user.id, FocusSession.start_time >= naive_two_weeks_ago)).all()
    habits = db.session.scalars(select(HabitLog.logged_at).filter(HabitLog.habit.has(user_id=user.id), HabitLog.logged_at >= naive_two_weeks_ago)).all()

    # Combine everything into one master timeline
    all_utc_timestamps = dumps + journals + page_views + focus + habits
    
    # Remove any Nones just in case
    all_utc_timestamps = [dt for dt in all_utc_timestamps if dt is not None]

    if len(all_utc_timestamps) < 10:
        return
        
    hourly_activity = [0] * 24
    for dt in all_utc_timestamps:
        aware_utc_dt = dt.replace(tzinfo=timezone.utc)
        local_dt = aware_utc_dt.astimezone(user_zone)
        hourly_activity[local_dt.hour] += 1
        
    min_activity = float('inf')
    best_start_hour = 3 # Defaults to 3 (which means proposed_hour will be 6 AM)
    
    for i in range(24):
        # Calculate what the reset hour WOULD be if we picked this window
        test_reset_hour = (i + 3) % 24
        
        # ---------------------------------------------------------
        # THE DAYTIME CONSTRAINT
        # Strictly forbid the day reset from falling between 9:00 AM and 9:00 PM.
        # This prevents the 9-to-5 workday from being mistaken for a sleep window.
        # Allowed reset hours: 22, 23, 0, 1, 2, 3, 4, 5, 6, 7, 8.
        # ---------------------------------------------------------
        if 9 <= test_reset_hour <= 21:
            continue
            
        # Sum the activity for this 6-hour window
        window_sum = sum(hourly_activity[(i + j) % 24] for j in range(6))
        
        if window_sum < min_activity:
            min_activity = window_sum
            best_start_hour = i
            
    # Calculate the final winning hour
    proposed_hour = (best_start_hour + 3) % 24
    current_hour = user.day_reset_hour
    
    # ---------------------------------------------------------
    # HYSTERESIS: THE ANTI-JITTER LOCK
    # Calculate the absolute difference across the 24-hour circle
    # ---------------------------------------------------------
    diff = min(abs(proposed_hour - current_hour), 24 - abs(proposed_hour - current_hour))
    
    # Only update the database if their routine has shifted by 2 or more hours
    if diff >= 2:
        user.day_reset_hour = proposed_hour
        db.session.commit()
        return proposed_hour
        
    return current_hour

def cleanup_old_user_activity(days_to_keep: int = 30):
    """
    Performs a bulk-delete of UserActivity records older than the specified cutoff.
    Returns the number of deleted rows.
    """
    # Calculate the exact cutoff timestamp in pure UTC
    cutoff_date = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(days=days_to_keep)
    
    # Execute a direct database-level deletion (extremely fast)
    deleted_count = db.session.query(UserActivity).filter(UserActivity.timestamp < cutoff_date).delete()
    db.session.commit()
    
    return deleted_count
