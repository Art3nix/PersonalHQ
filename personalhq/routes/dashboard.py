"""Module defining the main dashboard view."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.timebuckets import TimeBucket
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import get_habit_status_and_sync
from personalhq.extensions import db

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""
    # Habits
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    today = get_local_today()
    habit_statuses = {}
    for habit in habits:
        habit_statuses[habit.id] = get_habit_status_and_sync(habit)
        
    db.session.commit()

    # Fetch all deep work sessions scheduled for today that aren't finished
    queued_sessions = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.target_date == today,
        FocusSession.status != SessionStatus.FINISHED
    ).order_by(FocusSession.queue_order).all()

    # Time Buckets
    time_buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.id).all()    

    return render_template(
        'dashboard/dashboard.html', 
        habits=habits,
        habit_statuses=habit_statuses,
        queued_sessions=queued_sessions,
        SessionStatus=SessionStatus,
        time_buckets=time_buckets,
        current_date=today
    )
