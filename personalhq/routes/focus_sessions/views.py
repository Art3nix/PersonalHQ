import json
from datetime import timedelta
from collections import defaultdict
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.identities import Identity
from personalhq.services.time_service import get_local_today

focus_view_bp = Blueprint('focus_view', __name__, url_prefix='/focus-planner')

@focus_view_bp.route('/')
@login_required
def planner():
    today = get_local_today()
    thirty_days_ago = today - timedelta(days=30)
    week_ago = today - timedelta(days=7)

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
        if session.status == SessionStatus.FINISHED:
            total_minutes += session.target_duration_minutes

        if week_ago <= session.target_date <= today:
            week_scheduled += 1
            if session.status == SessionStatus.FINISHED:
                week_completed += 1

        if session.target_date == today:
            today_sessions.append(session)
        elif session.target_date > today:
            upcoming_dict[session.target_date].append(session)
        elif session.target_date >= thirty_days_ago:
            past_dict[session.target_date].append(session)

    upcoming_grouped = dict(sorted(upcoming_dict.items()))
    past_grouped = dict(sorted(past_dict.items(), reverse=True))

    win_rate = round((week_completed / week_scheduled * 100) if week_scheduled > 0 else 0)

    stats = {
        'total_hours': round(total_minutes / 60, 1),
        'week_completed': week_completed,
        'week_scheduled': week_scheduled,
        'win_rate': win_rate
    }

    identities = Identity.query.filter_by(user_id=current_user.id).all()

    # Check if there are missed sessions from yesterday for carry-over button
    yesterday = today - timedelta(days=1)
    missed_yesterday = FocusSession.query.filter_by(
        user_id=current_user.id,
        target_date=yesterday,
        status=SessionStatus.NOT_STARTED
    ).count()

    # Build 14-day session history for the sidebar chart
    session_history = []
    for i in range(13, -1, -1):
        day = today - timedelta(days=i)
        day_sessions = [s for s in all_sessions
                        if s.target_date == day and s.status == SessionStatus.FINISHED]
        total_mins = sum(s.target_duration_minutes for s in day_sessions)
        session_history.append({
            'label': day.strftime('%m/%d'),
            'minutes': total_mins
        })

    return render_template(
        'focus_sessions/planner.html',
        today=today,
        today_sessions=today_sessions,
        upcoming_grouped=upcoming_grouped,
        past_grouped=past_grouped,
        stats=stats,
        identities=identities,
        SessionStatus=SessionStatus,
        missed_yesterday=missed_yesterday,
        session_history_json=json.dumps(session_history)
    )
