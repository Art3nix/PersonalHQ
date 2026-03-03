
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from flask_login import current_user

def get_local_now() -> datetime:
    """Returns the user's current wall-clock time as a naive datetime."""
    utc_now = datetime.now(timezone.utc)

    # Default to UTC if not logged in
    tz_str = "UTC"
    if current_user and current_user.is_authenticated and hasattr(current_user, 'timezone'):
        tz_str = current_user.timezone or "UTC"

    try:
        user_zone = ZoneInfo(tz_str)
    except Exception:
        user_zone = ZoneInfo("UTC")

    local_time = utc_now.astimezone(user_zone)

    # Strip tzinfo so it works perfectly with your existing SQLAlchemy models
    return local_time.replace(tzinfo=None)

def get_local_today():
    """Returns the current local date for the user."""
    return get_local_now().date()
