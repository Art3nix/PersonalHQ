"""Module defining the main dashboard view."""

import random
from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.timebuckets import TimeBucket
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import get_habit_status_and_sync, run_daily_ledger_catchup
from personalhq.extensions import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""
    # 1. Pad the database with 0s for any missing days!
    run_daily_ledger_catchup(current_user.id)

    habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).order_by(Habit.sort_order).all()
    today = get_local_today()
    start_of_week = today - timedelta(days=today.weekday())
    
    habit_statuses = {}
    current_counts = {}
    
    for habit in habits:
        habit_statuses[habit.id] = get_habit_status_and_sync(habit)
        
        # 2. Read the ledger's 'progress' column instead of counting rows
        if habit.frequency == HabitFrequency.DAILY:
            log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
            current_counts[habit.id] = log.progress if log else 0
        else:
            # For weekly, sum up all the progress they made this week
            logs = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.completed_date >= start_of_week
            ).all()
            current_counts[habit.id] = sum(l.progress for l in logs)
            
    db.session.commit()

    # Fetch all deep work sessions scheduled for today that aren't finished
    queued_sessions = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.target_date == today,
        FocusSession.status != SessionStatus.FINISHED
    ).order_by(FocusSession.queue_order).all()

    # Time Buckets
    active_bucket = TimeBucket.query.filter(
        TimeBucket.user_id == current_user.id,
        TimeBucket.start_date <= today,
        TimeBucket.end_date >= today
    ).first()

    bucket_progress = 0
    upcoming_experiences = []
    time_left_str = ""
    is_urgent = False

    if active_bucket:
        # Exact Day Math
        total_days = (active_bucket.end_date - active_bucket.start_date).days
        days_passed = (today - active_bucket.start_date).days
        days_left = (active_bucket.end_date - today).days

        # Progress Bar Percentage
        if total_days > 0:
            bucket_progress = min(max((days_passed / total_days) * 100, 0), 100)

        # Dynamic Time Remaining Logic
        if days_left >= 365:
            years = days_left // 365
            time_left_str = f"{years} yr{'s' if years > 1 else ''} left"
            is_urgent = years <= 2  # Turns red at 2 years
        elif days_left >= 30:
            months = days_left // 30
            time_left_str = f"{months} mo{'s' if months > 1 else ''} left"
            is_urgent = True        # Always red if under a year
        elif days_left > 0:
            time_left_str = f"{days_left} day{'s' if days_left > 1 else ''} left"
            is_urgent = True
        else:
            time_left_str = "Ends today!"
            is_urgent = True

        # Grab up to 4 UNCOMPLETED experiences
        uncompleted_exps = [link.experience for link in active_bucket.experiences if not link.experience.is_completed]
        if uncompleted_exps:
            # random.sample safely grabs up to 4 unique items without crashing if there are fewer than 4
            upcoming_experiences = random.sample(uncompleted_exps, min(4, len(uncompleted_exps)))

    return render_template(
        'dashboard/dashboard.html', 
        habits=habits,
        habit_statuses=habit_statuses,
        current_counts=current_counts, # 3. Pass the counts to Jinja!
        queued_sessions=queued_sessions,
        SessionStatus=SessionStatus,
        active_bucket=active_bucket,
        bucket_progress=bucket_progress,
        upcoming_experiences=upcoming_experiences,
        time_left_str=time_left_str,
        is_urgent=is_urgent,
        today=today
    )
