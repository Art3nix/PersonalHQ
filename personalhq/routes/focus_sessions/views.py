
import json
from datetime import timedelta
from collections import defaultdict
from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.identities import Identity
from personalhq.models.dailynotes import DailyNote
from personalhq.services.time_service import get_logical_today

focus_view_bp = Blueprint('focus_view', __name__, url_prefix='/focus-planner')

@focus_view_bp.route('/')
@login_required
def planner():
    today = get_logical_today(current_user)
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

    # ==========================================
    # AI COACH CONTEXT
    # ==========================================
    daily_note = DailyNote.query.filter_by(user_id=current_user.id, logical_date=get_logical_today(current_user)).first()

    # Fetch from DB (Mapping to the names we set in the model)
    ai_planner_subtitle = daily_note.ai_planner_subtitle if daily_note else None
    ai_empty_state = daily_note.ai_planner_empty_state if daily_note else None
    ai_analysis = daily_note.ai_focus_analysis if daily_note else None

    if current_app.config['TEST_AI_NUDGES'] is True:
        # 1. SIDEBAR ANALYSIS (Over-scheduling vs Elite Execution)
        if stats['week_scheduled'] > 0:
            completion_rate = (stats['week_completed'] / stats['week_scheduled']) * 100
            if completion_rate >= 80:
                ai_analysis = f"Elite execution. You have completed {completion_rate:.0f}% of your scheduled sessions this week. Don't forget to schedule recovery time."
            elif completion_rate < 50 and stats['week_scheduled'] > 4:
                ai_analysis = "You are over-scheduling. Ambition is good, but scheduling sessions you don't finish trains your brain to ignore your own calendar."
            else:
                ai_analysis = "Consistent output. Try extending one session by 15 minutes this week to stretch your focus limits."

        # 2. OVERLOAD WARNING & EMPTY STATES
        if not today_sessions:
            ai_empty_state = "Zero sessions queued. If you want to move the needle today, schedule at least one 45-minute block of deep work."
            ai_planner_subtitle = "Your day is entirely open. What is the most important thing you can do?"
        else:
            total_mins = sum(s.target_duration_minutes for s in today_sessions)
            if total_mins > 240:
                ai_planner_subtitle = f"Warning: You have {total_mins/60:.1f} hours of deep work scheduled. This exceeds the sustainable cognitive limit for most humans. Prioritize ruthlessly."
            else:
                ai_planner_subtitle = "Your focus pipeline is set. Execute the plan."

        # 3. INDIVIDUAL SESSION COACHING
        for session in today_sessions:
            name_lower = session.name.lower()
            if session.target_duration_minutes > 90:
                session.ai_insight = "This is a marathon session. Take a 5-minute visual break halfway through to prevent cognitive fatigue."
            elif any(word in name_lower for word in ["email", "slack", "admin", "messages"]):
                session.ai_insight = "This looks like shallow work. Real Deep Work pushes your cognitive capabilities. Are you sure you want to queue this here?"
            else:
                session.ai_insight = None
    # ==========================================

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
        session_history_json=json.dumps(session_history),
        ai_planner_subtitle=ai_planner_subtitle,
        ai_empty_state=ai_empty_state,
        ai_analysis=ai_analysis
    )
