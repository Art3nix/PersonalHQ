"""Utility module for handling timezones and logical date calculations."""

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from flask_login import current_user

def get_local_now() -> datetime:
    """Returns the user's current wall-clock time as a naive datetime."""
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
    local_now = get_local_now() 

    if local_now.hour < user.day_reset_hour:
        return (local_now - timedelta(days=1)).date()

    return local_now.date()