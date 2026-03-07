
from datetime import date, timedelta
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.identities import Identity

focus_view_bp = Blueprint('focus_view', __name__, url_prefix='/focus-planner')

@focus_view_bp.route('/')
@login_required
def planner():
    today = date.today()
    thirty_days_ago = today - timedelta(days=30)
    week_ago = today - timedelta(days=7)
    
    # Grab all sessions to calculate lifetime stats, ordered properly
    all_sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(
        FocusSession.target_date, 
        FocusSession.queue_order
    ).all()

    today_sessions = []
    upcoming_dict = defaultdict(list)
    past_dict = defaultdict(list)

    total_minutes = 0
    week_scheduled = 0
    week_completed = 0

    for session in all_sessions:
        # 1. Lifetime & Weekly Analytics
        if session.status == SessionStatus.FINISHED:
            total_minutes += session.target_duration_minutes
            
        # 7-Day Win Rate Logic
        if week_ago <= session.target_date <= today:
            week_scheduled += 1
            if session.status == SessionStatus.FINISHED:
                week_completed += 1

        # 2. Sort into UI Buckets (Limiting the archive!)
        if session.target_date == today:
            today_sessions.append(session)
        elif session.target_date > today:
            upcoming_dict[session.target_date].append(session)
        elif session.target_date >= thirty_days_ago:
            # ONLY send the last 30 days to the HTML to prevent infinite scrolling/lag
            past_dict[session.target_date].append(session)

    upcoming_grouped = dict(sorted(upcoming_dict.items()))
    past_grouped = dict(sorted(past_dict.items(), reverse=True))

    # Calculate Win Rate Percentage safely
    win_rate = round((week_completed / week_scheduled * 100) if week_scheduled > 0 else 0)

    stats = {
        'total_hours': round(total_minutes / 60, 1),
        'week_completed': week_completed,
        'week_scheduled': week_scheduled,
        'win_rate': win_rate
    }

    identities = Identity.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'focus_sessions/planner.html',
        today=today,
        today_sessions=today_sessions,
        upcoming_grouped=upcoming_grouped,
        past_grouped=past_grouped,
        stats=stats,
        identities=identities,
        SessionStatus=SessionStatus
    )
