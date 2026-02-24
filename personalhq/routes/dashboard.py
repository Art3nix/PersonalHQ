"""Module defining the main dashboard view."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit
from personalhq.models.focussessions import FocusSession, SessionStatus

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""
    # Fetch all habits for the user
    habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # Check if there is an active or paused focus session
    active_session = FocusSession.query.filter(
        FocusSession.user_id == current_user.id,
        FocusSession.status.in_([SessionStatus.IN_PROGRESS, SessionStatus.PAUSED])
    ).first()

    return render_template(
        'dashboard/dashboard.html', 
        habits=habits, 
        active_session=active_session,
        SessionStatus=SessionStatus # Passing the enum to Jinja for easy state checking
    )
