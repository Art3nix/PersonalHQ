"""Module defining the HTML View routes for Habit Management."""

import json
from datetime import timedelta
from sqlalchemy import func
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.models.identities import Identity
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import get_habit_status_and_sync

habits_view_bp = Blueprint('habits_view', __name__, url_prefix='/habits')

@habits_view_bp.route('/')
@login_required
def manage():
    """Renders the detailed habit analytics and management page."""
    all_habits = Habit.query.filter_by(user_id=current_user.id).all()

    habit_statuses = {}
    for habit in all_habits:
        habit_statuses[habit.id] = get_habit_status_and_sync(habit)
        
    db.session.commit()

    total_habits = len(all_habits)
    best_streak = max([(h.streak if h.streak else 0) for h in all_habits], default=0)
    daily_count = sum(1 for h in all_habits if h.frequency == HabitFrequency.DAILY)
    weekly_count = total_habits - daily_count

    # 30-Day Heatmap Logic
    today = get_local_today()
    thirty_days_ago = today - timedelta(days=29)

    # Query completion counts grouped by date for the last 30 days
    daily_counts = db.session.query(
        HabitLog.completed_date,
        func.count(HabitLog.id).label('count')  # pylint: disable=not-callable
    ).join(Habit).filter(
        Habit.user_id == current_user.id,
        HabitLog.completed_date >= thirty_days_ago
    ).group_by(HabitLog.completed_date).all()

    # Convert query results to a fast lookup dictionary: {date_obj: count}
    counts_dict = {row.completed_date: row.count for row in daily_counts}

    # Generate the 30-day grid data
    heatmap_data = []
    max_possible = total_habits if total_habits > 0 else 1 # Prevent division by zero

    for i in range(30):
        current_date = thirty_days_ago + timedelta(days=i)
        count = counts_dict.get(current_date, 0)

        # Calculate color intensity (0 to 4 scale)
        intensity = 0
        if count > 0:
            ratio = count / max_possible
            if ratio <= 0.25:
                intensity = 1
            elif ratio <= 0.50:
                intensity = 2
            elif ratio <= 0.75:
                intensity = 3
            else:
                intensity = 4

        heatmap_data.append({
            'date': current_date.strftime('%b %d'),
            'count': count,
            'intensity': intensity
        })

    # Day of Week Analytics (0=Monday, 6=Sunday)
    dow_counts = [0] * 7
    # Re-use the `daily_counts` query from your heatmap logic
    for row in daily_counts: 
        dow = row.completed_date.weekday()
        dow_counts[dow] += row.count

    # Momentum Line Chart (4-Week Trend)
    weekly_trend = [0, 0, 0, 0] # [3 weeks ago, 2 weeks ago, Last Week, This Week]
    for i in range(28):
        current_date = today - timedelta(days=i)
        count = counts_dict.get(current_date, 0)
        # Map the day offset to a week bucket (3 is current week, 0 is oldest week)
        week_idx = 3 - (i // 7) 
        weekly_trend[week_idx] += count

    # 7-Day Sparkline for Individual Habit Cards
    seven_days_ago = today - timedelta(days=6)

    # Fetch all logs from the last 7 days in ONE query to avoid N+1 database hits
    recent_logs = HabitLog.query.filter(
        HabitLog.habit_id.in_([h.id for h in all_habits]) if all_habits else False,
        HabitLog.completed_date >= seven_days_ago
    ).all()

    # Build a fast lookup dictionary: { habit_id: set(dates_completed) }
    history_map = {h.id: set() for h in all_habits}
    for log in recent_logs:
        history_map[log.habit_id].add(log.completed_date)

    # Generate a list of 7 True/False values for each habit
    habit_sparklines = {}
    for habit in all_habits:
        sparkline = []
        for i in range(6, -1, -1): # Loop from 6 days ago up to today
            check_date = today - timedelta(days=i)
            sparkline.append(check_date in history_map[habit.id])
        habit_sparklines[habit.id] = sparkline

    identities = Identity.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'habits/manage.html',
        habits=all_habits,
        stats={
            "total": total_habits,
            "best_streak": best_streak,
            "daily": daily_count,
            "weekly": weekly_count
        },
        heatmap_data=heatmap_data,
        dow_counts=json.dumps(dow_counts),
        weekly_trend=json.dumps(weekly_trend),
        habit_sparklines=habit_sparklines,
        HabitFrequency=HabitFrequency,
        identities=identities
    )
