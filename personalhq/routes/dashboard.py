"""Module defining the main dashboard view."""

from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.experiences import Experience
from personalhq.models.bucket_experience import BucketExperience
from personalhq.services.time_service import get_local_today, get_local_now
from personalhq.services.habit_service import (
    get_habit_status, bulk_load_recent_logs, run_daily_ledger_catchup
)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""
    run_daily_ledger_catchup(current_user.id) 

    habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = get_local_today()
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())
    now = get_local_now()

    # ── HABIT & FOCUS LOGIC ──
    habit_ids = [h.id for h in habits]
    logs_map = bulk_load_recent_logs(habit_ids, days_back=14)
    habit_statuses = {}
    current_counts = {}
    missed_yesterday = []

    for habit in habits:
        hdates = logs_map.get(habit.id, {})
        habit_statuses[habit.id] = get_habit_status(habit, hdates)

        if habit.frequency == HabitFrequency.DAILY:
            log = hdates.get(today)
            current_counts[habit.id] = log.progress if log else 0
            log_yest = hdates.get(yesterday)
            if habit.streak > 0 and (not log_yest or log_yest.progress < habit.target_count):
                missed_yesterday.append(habit)
        else:
            current_counts[habit.id] = sum(l.progress for d, l in hdates.items() if d >= start_of_week)

    daily_habits = [h for h in habits if h.frequency == HabitFrequency.DAILY]
    daily_completed = sum(1 for h in daily_habits if habit_statuses[h.id] == 'COMPLETED')

    queued_sessions = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.target_date == today,
        FocusSession.status != SessionStatus.FINISHED
    ).order_by(FocusSession.queue_order).all()

    # ── TIME BUCKETS & URGENCY MATH ──
    time_buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.start_date.asc()).all()

    active_bucket = None
    for bucket in time_buckets:
        if bucket.start_date <= today <= bucket.end_date:
            active_bucket = bucket
            break

    bucket_progress = 0
    time_left_str = ""
    is_urgent = False
    upcoming_experiences = []

    if active_bucket:
        # 1. Calculate the ruthless passage of time (Progress Bar %)
        total_days = (active_bucket.end_date - active_bucket.start_date).days
        days_passed = (today - active_bucket.start_date).days
        if total_days > 0:
            bucket_progress = min(max((days_passed / total_days) * 100, 0), 100)

        # 2. Calculate Time Left and trip the Urgency alarms
        days_left = (active_bucket.end_date - today).days
        if days_left <= 30:
            time_left_str = f"Only {days_left} days left!"
            is_urgent = True
        elif days_left <= 365:
            months_left = days_left // 30
            time_left_str = f"Only {months_left} months left!"
            is_urgent = True
        else:
            years_left = days_left // 365
            time_left_str = f"{years_left} years remaining"
            # Turn urgent if the bucket is more than 80% over, even if years are left
            is_urgent = (bucket_progress > 80)

        # 3. Fetch exactly what needs to be done before time runs out
        upcoming_experiences = Experience.query.join(BucketExperience).filter(
            BucketExperience.bucket_id == active_bucket.id,
            Experience.is_completed == False
        ).all()

    # ── GREETING ──
    hour = now.hour
    if hour < 12: greeting = "Good morning"
    elif hour < 17: greeting = "Good afternoon"
    elif hour < 21: greeting = "Good evening"
    else: greeting = "Working late"

    return render_template(
        'dashboard/dashboard.html',
        habits=habits,
        habit_statuses=habit_statuses,
        current_counts=current_counts,
        queued_sessions=queued_sessions,
        SessionStatus=SessionStatus,
        today=today,
        greeting=greeting,
        daily_completed=daily_completed,
        daily_total=len(daily_habits),
        missed_yesterday=missed_yesterday[:3],
        active_bucket=active_bucket,
        bucket_progress=bucket_progress,
        time_left_str=time_left_str,
        is_urgent=is_urgent,
        upcoming_experiences=upcoming_experiences
    )
