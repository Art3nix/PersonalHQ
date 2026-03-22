"""Module defining the main dashboard view."""

from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.time_service import get_local_today, get_local_now
from personalhq.services.habit_service import (
    get_habit_status, bulk_load_recent_logs, run_daily_ledger_catchup
)

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""
    run_daily_ledger_catchup(current_user.id)  # gated — skips if already ran today

    habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = get_local_today()
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())
    now = get_local_now()

    # ── ONE query for all habit logs (last 14 days covers today + yesterday + week) ──
    habit_ids = [h.id for h in habits]
    logs_map = bulk_load_recent_logs(habit_ids, days_back=14)
    # logs_map: {habit_id: {date: HabitLog}}

    habit_statuses = {}
    current_counts = {}
    missed_yesterday = []

    for habit in habits:
        hdates = logs_map.get(habit.id, {})
        habit_statuses[habit.id] = get_habit_status(habit, hdates)

        if habit.frequency == HabitFrequency.DAILY:
            log = hdates.get(today)
            current_counts[habit.id] = log.progress if log else 0
            # Nudge: streak > 0 but yesterday not done
            log_yest = hdates.get(yesterday)
            if habit.streak > 0 and (not log_yest or log_yest.progress < habit.target_count):
                missed_yesterday.append(habit)
        else:
            current_counts[habit.id] = sum(
                l.progress for d, l in hdates.items() if d >= start_of_week
            )

    # No db.session.commit() needed — get_habit_status is read-only now
    daily_habits = [h for h in habits if h.frequency == HabitFrequency.DAILY]
    daily_completed = sum(1 for h in daily_habits if habit_statuses[h.id] == 'COMPLETED')

    queued_sessions = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.target_date == today,
        FocusSession.status != SessionStatus.FINISHED
    ).order_by(FocusSession.queue_order).all()

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
        missed_yesterday=missed_yesterday[:3],
    )
