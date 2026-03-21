"""Module defining the main dashboard view."""

from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.time_service import get_local_today, get_local_now
from personalhq.services.habit_service import get_habit_status_and_sync, run_daily_ledger_catchup
from personalhq.extensions import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""
    run_daily_ledger_catchup(current_user.id)

    habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = get_local_today()
    now = get_local_now()
    start_of_week = today - timedelta(days=today.weekday())

    habit_statuses = {}
    current_counts = {}
    missed_yesterday = []  # habits with streak > 0 that weren't done yesterday

    yesterday = today - timedelta(days=1)

    for habit in habits:
        habit_statuses[habit.id] = get_habit_status_and_sync(habit)

        if habit.frequency == HabitFrequency.DAILY:
            log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
            current_counts[habit.id] = log.progress if log else 0
            # Check yesterday for nudge
            log_yest = HabitLog.query.filter_by(habit_id=habit.id, completed_date=yesterday).first()
            if habit.streak > 0 and (not log_yest or log_yest.progress < habit.target_count):
                missed_yesterday.append(habit)
        else:
            logs = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.completed_date >= start_of_week
            ).all()
            current_counts[habit.id] = sum(l.progress for l in logs)

    db.session.commit()

    # Today's completed vs total habits
    daily_habits = [h for h in habits if h.frequency == HabitFrequency.DAILY]
    daily_completed = sum(1 for h in daily_habits if habit_statuses[h.id] == 'COMPLETED')

    # Deep work sessions for today
    queued_sessions = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.target_date == today,
        FocusSession.status != SessionStatus.FINISHED
    ).order_by(FocusSession.queue_order).all()

    # Greeting based on time of day
    hour = now.hour
    if hour < 12:
        greeting = "Good morning"
    elif hour < 17:
        greeting = "Good afternoon"
    elif hour < 21:
        greeting = "Good evening"
    else:
        greeting = "Working late"

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
        missed_yesterday=missed_yesterday[:3],  # Show max 3 nudges
    )
