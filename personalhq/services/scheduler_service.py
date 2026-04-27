"""Module handling automated background tasks and scheduled dispatches."""

from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from personalhq.models.users import User
from personalhq.services.ai_service import generate_daily_context, sys_logger
from personalhq.services.user_service import recalculate_user_reset_hour, cleanup_old_user_activity

def run_hourly_dispatcher():
    """Runs every hour at minute 00 to trigger AI coaching and end-of-day logic."""
    now_utc = datetime.now(timezone.utc)
    
    sys_logger.info(f"[SCHEDULER_WAKE] Dispatcher woke up at {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}")

    # Only run the heavy database cleanup once a day at exactly 00:00 UTC
    if now_utc.hour == 0:
        sys_logger.info("[MAINTENANCE] Running global database maintenance (00:00 UTC)...")
        try:
            deleted_rows = cleanup_old_user_activity(days_to_keep=30)
            sys_logger.info(f"[MAINTENANCE] Success: Cleaned up {deleted_rows} old activity logs.")
        except Exception as e:
            sys_logger.error(f"[MAINTENANCE] Error during activity cleanup: {e}")

    # User specific end-of-day processing
    users = User.query.all()
    for user in users:
        try:
            user_zone = ZoneInfo(user.timezone or "UTC")
        except Exception:
            user_zone = ZoneInfo("UTC")

        user_local_now = now_utc.astimezone(user_zone)
        
        # Log the math so you can prove the timezone offsets are correct
        sys_logger.info(f"[SCHEDULER_CHECK] User: {user.email} | Local Time: {user_local_now.strftime('%H:%M')} | Target Reset: {user.day_reset_hour}:00")
        
        if user_local_now.hour == user.day_reset_hour:
            sys_logger.info(f"[SCHEDULER_TRIGGER] Initiating end-of-day sequence for {user.email}...")
            
            try:
                # 1. Trigger the AI Coach generation
                sys_logger.info(f"[{user.email}] Generating daily AI context...")
                generate_daily_context(user, user_local_now.date())
                
                # 3. Recalculate Reset Hour based on sleep activity
                sys_logger.info(f"[{user.email}] Recalculating dynamic reset hour...")
                recalculate_user_reset_hour(user)
                
                sys_logger.info(f"[SCHEDULER_SUCCESS] End-of-day sequence fully complete for {user.email}.")
                
            except Exception as e:
                sys_logger.error(f"[SCHEDULER_ERROR] Failed during end-of-day sequence for {user.email}: {e}")