"""Module defining the main dashboard view."""

from datetime import timedelta
from flask import Blueprint, render_template, redirect, url_for, current_app
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.experiences import Experience
from personalhq.models.bucket_experience import BucketExperience
from personalhq.services.time_service import get_local_now, get_logical_today
from personalhq.services.habit_service import (
    get_habit_status, bulk_load_recent_logs, run_daily_ledger_catchup
)
from personalhq.models.dailynotes import DailyNote

dashboard_bp = Blueprint('dashboard', __name__, url_prefix='/dashboard')

@dashboard_bp.route('/')
@login_required
def index():
    """Renders the main command center dashboard."""

    run_daily_ledger_catchup(current_user.id)

    habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).all()
    today = get_logical_today(current_user)
    yesterday = today - timedelta(days=1)
    start_of_week = today - timedelta(days=today.weekday())
    now = get_local_now()
    logical_today = get_logical_today(current_user)

    # ── HABIT & FOCUS LOGIC ──
    habit_ids = [h.id for h in habits]
    logs_map = bulk_load_recent_logs(current_user, habit_ids, days_back=14)
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
            is_yest_missed = not log_yest or log_yest.progress < habit.target_count

            day_before_yest = today - timedelta(days=2)
            log_day_before = hdates.get(day_before_yest)
            had_streak_before = log_day_before and log_day_before.progress >= habit.target_count
            is_today_logged = log and log.progress >= habit.target_count

            # ONLY show the recovery nudge if they haven't logged today yet!
            if is_yest_missed and had_streak_before and not is_today_logged:
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

    # ==========================================
    # AI COACH CONTEXT
    # ==========================================
    
    # 1. Fetch the DailyNote for the current logical day
    daily_note = DailyNote.query.filter_by(
        user_id=current_user.id,
        logical_date=get_logical_today(current_user)
    ).first()

    # 2. Safely extract the page-level contexts
    ai_daily_briefing = daily_note.ai_daily_briefing if daily_note else None
    ai_focus_empty_state = daily_note.ai_focus_empty_state if daily_note else None
    ai_habit_empty_state = daily_note.ai_habit_empty_state if daily_note else None
    ai_chapter_empty_state = daily_note.ai_chapter_empty_state if daily_note else None

    if current_app.config['TEST_AI_NUDGES'] is True:
        ai_daily_briefing = "You have a solid 90-minute Deep Work session queued today. Get that done early, but don't forget to move your body later."

        # TASK-SPECIFIC AI MOCK DATA
        for session in queued_sessions:
            # You would replace this with actual AI logic later
            if "Sidehustle" in session.name or "Code" in session.name:
                session.ai_intention = "System design requires unbroken logic chains. Close your email."
            else:
                session.ai_intention = "Deep work requires deep focus. Put your phone in another room."
        
        # Empty States (Replacing the static paragraphs)
        ai_focus_empty_state = "Your focus queue is clear. Even a 30-minute session reading a book builds the focus muscle. Schedule one now?"
        ai_habit_empty_state = "Based on your focus on deep work, adding a 'Morning Walk' habit might help you clear your mind before sessions."
        ai_chapter_empty_state = "You are currently in a heavy execution phase of life. Let's give this chapter a name to solidify that identity."

        # Merged Habit Notes (Inside the card)
        missed_ids = [h.id for h in missed_yesterday]
        if habits:
            for habit in habits:
                status_str = habit_statuses[habit.id]
                is_completed_today = status_str == 'COMPLETED'
                is_expiring = status_str == 'EXPIRING'
                
                if habit.id in missed_ids:
                    habit.ai_insight = "You missed this yesterday. Recover your streak before logging today."
                elif is_completed_today:
                    # 1. New Best Celebration
                    if habit.streak == habit.best_streak and habit.best_streak > 1:
                        habit.ai_insight = f"New all-time best! {habit.streak} days. You are operating at a completely new level."
                    # 2. Slump Broken
                    elif habit.streak == 1:
                        habit.ai_insight = "Slump broken. Great job showing up. Let's build on this tomorrow."
                    # 3. Milestone Celebration
                    elif habit.streak > 0 and habit.streak % 3 == 0:
                        habit.ai_insight = f"Momentum is building! You've hit a {habit.streak}-day streak. You are becoming the person who does this consistently."
                    else:
                        habit.ai_insight = "Target reached. Excellent execution today."
                # 4. At-Risk Warning
                elif is_expiring:
                    habit.ai_insight = "Your streak is at risk today. Don't lose the momentum you've built."
                elif habit.streak == 0:
                    habit.ai_insight = "Friction seems high here lately. Consider doing just 2 minutes of this today to get back on the board."
                else:
                    habit.ai_insight = None
    # ==========================================

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
        upcoming_experiences=upcoming_experiences,
        ai_daily_briefing=ai_daily_briefing,
        ai_focus_empty_state=ai_focus_empty_state,
        ai_habit_empty_state=ai_habit_empty_state,
        ai_chapter_empty_state=ai_chapter_empty_state
    )

@dashboard_bp.route('/onboarding')
@login_required
def onboarding():
    # If they somehow navigate here but already have data, send them to the dashboard
    if current_user.identities or current_user.journals or current_user.habits:
        return redirect(url_for('dashboard.index'))

    return render_template('onboarding/index.html')
