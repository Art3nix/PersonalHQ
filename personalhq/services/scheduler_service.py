"""Module handling automated background tasks and scheduled dispatches."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from personalhq.models.users import User
from personalhq.services.ai_service import generate_daily_context
from personalhq.services.user_service import recalculate_user_reset_hour

def run_hourly_dispatcher():
    """Runs every hour at minute 00 to trigger AI coaching."""
    now_utc = datetime.now(timezone.utc)
    users = User.query.all()
    
    for user in users:
        try:
            user_zone = ZoneInfo(user.timezone or "UTC")
        except Exception:
            user_zone = ZoneInfo("UTC")

        user_local_now = now_utc.astimezone(user_zone)
        
        if user_local_now.hour == user.day_reset_hour:
            print(f"[{user_local_now.strftime('%H:%M')}] Running AI Batch for {user.email}...")
            
            # Trigger the AI Coach generation
            generate_daily_context(user, user_local_now.date())
            
            # Recalculate lifestyle midnight on Sundays
            if user_local_now.weekday() == 6:
                recalculate_user_reset_hour(user)
