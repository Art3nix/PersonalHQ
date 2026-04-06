# run_scheduler.py
import os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from apscheduler.schedulers.blocking import BlockingScheduler
from personalhq import create_app
from personalhq.extensions import db
from personalhq.models.users import User
from personalhq.services.time_service import recalculate_user_reset_hour
from personalhq.services.ai_service import generate_daily_context

# Create the Flask app context (but don't run the web server!)
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def run_hourly_dispatcher():
    """The task that runs at minute 00 of every hour."""
    # We MUST run inside the app context so SQLAlchemy works
    with app.app_context():
        now_utc = datetime.now(timezone.utc)
        users = User.query.all()

        for user in users:
            try:
                user_zone = ZoneInfo(user.timezone or "UTC")
            except Exception:
                user_zone = ZoneInfo("UTC")

            user_local_now = now_utc.astimezone(user_zone)

            # If the current hour matches their custom reset hour
            if user_local_now.hour == user.day_reset_hour:
                print(f"[{user_local_now.strftime('%H:%M')}] Dispatching AI Batch for {user.email}...")

                # 1. Trigger the AI Coach generation for their new logical day
                logical_date_to_prep = user_local_now.date() 
                generate_daily_context(user, logical_date_to_prep)

                # 2. Once a week (e.g., on Sundays), recalculate their lifestyle midnight
                if user_local_now.weekday() == 6: 
                    recalculate_user_reset_hour(user)

if __name__ == '__main__':
    print("Starting Life HQ Background Scheduler...")
    
    # Pass standard timezone.utc instead of pytz.utc
    scheduler = BlockingScheduler(timezone=timezone.utc)
    scheduler.add_job(run_hourly_dispatcher, 'cron', minute=0)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
