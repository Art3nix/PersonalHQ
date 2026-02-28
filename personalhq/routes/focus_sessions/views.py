from datetime import date
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.focussessions import FocusSession, SessionStatus

focus_view_bp = Blueprint('focus_view', __name__, url_prefix='/focus-planner')

@focus_view_bp.route('/')
@login_required
def planner():
    """Renders the Focus Session planner and overview page."""
    sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(
        FocusSession.target_date.asc(),
        FocusSession.queue_order.asc()
    ).all()
    
    return render_template(
        'focus_sessions/planner.html',
        sessions=sessions,
        today=date.today(),
        SessionStatus=SessionStatus # Pass the Enum to Jinja for easy checking
    )
