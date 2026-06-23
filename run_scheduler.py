# run_scheduler.py
import os
import pytz
from apscheduler.schedulers.blocking import BlockingScheduler
from personalhq import create_app
from personalhq.services.scheduler_service import run_hourly_dispatcher

# Create the Flask app context (but don't run the web server!)
app = create_app(os.getenv('FLASK_CONFIG') or 'default')

def job_wrapper():
    """
    Wraps the external dispatcher in the Flask app context.
    Without this, SQLAlchemy will throw an "outside of application context" error.
    """
    with app.app_context():
        run_hourly_dispatcher()

if __name__ == '__main__':
    print("Starting Kairos Background Scheduler...", flush=True)
    
    # APScheduler 3.x works best with pytz
    scheduler = BlockingScheduler(timezone=pytz.utc)
    
    # Add the wrapper function to trigger at minute 00
    scheduler.add_job(job_wrapper, 'cron', minute=0)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass