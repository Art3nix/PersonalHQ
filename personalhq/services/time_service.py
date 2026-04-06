"""Utility module for handling timezones and logical date calculations."""

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from flask_login import current_user

def get_utc_now() -> datetime:
    """
    Returns the current absolute time in UTC (Naive).
    USE THIS FOR ALL DATABASE DEFAULTS (logged_at, created_at, start_time).
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)

def get_local_now() -> datetime:
    """
    Returns the current user's wall-clock time. 
    USE FOR UI RENDERING ONLY, NOT FOR DATABASE STORAGE.
    """
    utc_now = datetime.now(timezone.utc)

    tz_str = "UTC"
    try:
        if current_user and current_user.is_authenticated and hasattr(current_user, 'timezone'):
            tz_str = current_user.timezone or "UTC"
    except Exception:
        pass

    try:
        user_zone = ZoneInfo(tz_str)
    except Exception:
        user_zone = ZoneInfo("UTC")

    local_time = utc_now.astimezone(user_zone)
    return local_time.replace(tzinfo=None)

def get_logical_today(user):
    """Returns the user's logical date based on their custom reset hour."""
    utc_now = datetime.now(timezone.utc)
    
    # 1. Extract timezone from the passed user object (Works perfectly in background workers)
    tz_str = "UTC"
    if hasattr(user, 'timezone') and user.timezone:
        tz_str = user.timezone

    try:
        user_zone = ZoneInfo(tz_str)
    except Exception:
        user_zone = ZoneInfo("UTC")
        
    # 2. Convert current UTC to the specific user's local time
    local_now = utc_now.astimezone(user_zone)

    # 3. Apply the offset midnight logic
    if local_now.hour < user.day_reset_hour:
        return (local_now - timedelta(days=1)).date()

    return local_now.date()