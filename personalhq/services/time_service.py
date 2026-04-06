

from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone
from flask_login import current_user
from sqlalchemy import select
from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump
from personalhq.models.users import User
from personalhq.models.journalentries import JournalEntry
from personalhq.services.ai_service import generate_daily_context

def get_local_now() -> datetime:
    """Returns the user's current wall-clock time as a naive datetime."""
    utc_now = datetime.now(timezone.utc)

    # Default to UTC if not logged in or no request context
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

    # Strip tzinfo so it works perfectly with your existing SQLAlchemy models
    return local_time.replace(tzinfo=None)

def get_local_today():
    """Returns the current local date for the user."""
    return get_local_now().date()

def get_logical_today(user):
    """Returns the user's logical date based on their custom reset hour."""
    local_now = get_local_now() # This is the timezone-aware function we just wrote

    # If it is 1:00 AM, but their day doesn't reset until 3:00 AM,
    # they are technically still living in "yesterday".
    if local_now.hour < user.day_reset_hour:
        return (local_now - timedelta(days=1)).date()

    return local_now.date()

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
    
    # Strip tzinfo for the SQLAlchemy query (assuming your DB stores naive UTC timestamps)
    naive_two_weeks_ago = two_weeks_ago_utc.replace(tzinfo=None)
    
    # 1. Fetch timestamps
    dumps = db.session.scalars(select(BrainDump.created_at).filter(BrainDump.user_id == user.id, BrainDump.created_at >= naive_two_weeks_ago)).all()
    journals = db.session.scalars(select(JournalEntry.created_at).filter(JournalEntry.user_id == user.id, JournalEntry.created_at >= naive_two_weeks_ago)).all()
    
    all_utc_timestamps = dumps + journals
    
    if len(all_utc_timestamps) < 10:
        return # Not enough data to change their baseline yet
        
    # 2. Build a 24-hour histogram based on their LOCAL time
    hourly_activity = [0] * 24
    for dt in all_utc_timestamps:
        # DB returns naive UTC. Make it aware, then convert to local.
        aware_utc_dt = dt.replace(tzinfo=timezone.utc)
        local_dt = aware_utc_dt.astimezone(user_zone)
        hourly_activity[local_dt.hour] += 1
        
    # 3. Find the quietest 6-hour continuous window
    min_activity = float('inf')
    best_start_hour = 3 # fallback
    
    for i in range(24):
        window_sum = sum(hourly_activity[(i + j) % 24] for j in range(6))
        
        if window_sum < min_activity:
            min_activity = window_sum
            best_start_hour = i
            
    # 4. The ideal cron time is exactly in the middle of this sleep window
    new_reset_hour = (best_start_hour + 3) % 24
    
    user.day_reset_hour = new_reset_hour
    db.session.commit()
    
    return new_reset_hour

def run_hourly_dispatcher():
    """Runs every hour at minute 00 to trigger AI coaching."""
    now_utc = datetime.now(timezone.utc)
    
    users = User.query.all()
    
    for user in users:
        try:
            user_zone = ZoneInfo(user.timezone or "UTC")
        except Exception:
            user_zone = ZoneInfo("UTC")

        # Convert the current UTC time to this specific user's local time
        user_local_now = now_utc.astimezone(user_zone)
        
        # If their local hour matches their custom reset hour, run their AI batch
        if user_local_now.hour == user.day_reset_hour:
            print(f"[{user_local_now.strftime('%H:%M')}] Running AI Batch for {user.email}...")
            
            # 1. Trigger the AI Coach generation
            generate_daily_context(user, user_local_now.date())
            
            # 2. Once a week (e.g., on Sundays), recalculate their lifestyle midnight
            if user_local_now.weekday() == 6:
                recalculate_user_reset_hour(user)
