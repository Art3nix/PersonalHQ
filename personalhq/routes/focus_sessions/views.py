

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.identities import Identity
from personalhq.services.time_service import get_local_today

focus_view_bp = Blueprint('focus_view', __name__, url_prefix='/focus-planner')

@focus_view_bp.route('/')
@login_required
def planner():
    """Renders the Focus Session planner and overview page."""
    sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(
        FocusSession.target_date.asc(),
        FocusSession.queue_order.asc()
    ).all()
    identities = Identity.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'focus_sessions/planner.html',
        sessions=sessions,
        today=get_local_today(),
        SessionStatus=SessionStatus, # Pass the Enum to Jinja for easy checking
        identities=identities
    )
