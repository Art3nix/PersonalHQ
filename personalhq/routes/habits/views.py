"""Module defining the HTML View routes for Habit Management."""

import json
import calendar as py_calendar
from collections import defaultdict
from datetime import date, timedelta, datetime
from flask import Blueprint, request, render_template
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
    all_habits = Habit.query.filter_by(user_id=current_user.id, is_active=True).order_by(Habit.id).all()
    archived_habits = Habit.query.filter_by(user_id=current_user.id, is_active=False).order_by(Habit.id).all()

    habit_statuses = {}
    for habit in all_habits:
        habit_statuses[habit.id] = get_habit_status_and_sync(habit)
        
    db.session.commit()

    total_habits = len(all_habits)
    best_streak = max([(h.best_streak if h.best_streak else 0) for h in all_habits], default=0)
    daily_count = sum(1 for h in all_habits if h.frequency == HabitFrequency.DAILY)
    weekly_count = total_habits - daily_count

    # 30-Day Heatmap Logic
    today = get_local_today()
    thirty_days_ago = today - timedelta(days=29)
    start_of_week = today - timedelta(days=today.weekday())
    end_of_week = start_of_week + timedelta(days=6)

    # Fetch all logs for the last 30 days
    recent_logs = HabitLog.query.join(Habit).filter(
        Habit.user_id == current_user.id,
        HabitLog.completed_date >= thirty_days_ago
    ).all()

    # Group logs by date, then by habit_id
    date_habit_counts = defaultdict(lambda: defaultdict(int))
    for log in recent_logs:
        date_habit_counts[log.completed_date][log.habit_id] += 1

    # Calculate strictly completed habits per day
    counts_dict = {}
    for d, h_counts in date_habit_counts.items():
        completed_today = 0
        for h_id, count in h_counts.items():
            habit = next((h for h in all_habits if h.id == h_id), None)
            if not habit: continue
            
            if habit.frequency == HabitFrequency.DAILY:
                if count >= habit.target_count:
                    completed_today += 1
            else:
                # For weekly habits, we award an activity point if they worked on it that day
                if count > 0:
                    completed_today += 1
        counts_dict[d] = completed_today

    # Generate the 30-day grid data
    heatmap_data = []
    max_possible = total_habits if total_habits > 0 else 1

    for i in range(30):
        current_date = thirty_days_ago + timedelta(days=i)
        count = counts_dict.get(current_date, 0)

        intensity = 0
        if count > 0:
            ratio = count / max_possible
            if ratio <= 0.25: intensity = 1
            elif ratio <= 0.50: intensity = 2
            elif ratio <= 0.75: intensity = 3
            else: intensity = 4

        heatmap_data.append({
            'date': current_date.strftime('%b %d'),
            'count': count,
            'intensity': intensity
        })

    # Day of Week Analytics
    dow_counts = [0] * 7
    for d, count in counts_dict.items():
        dow_counts[d.weekday()] += count

    # Momentum Line Chart (4-Week Trend)
    weekly_trend = [0, 0, 0, 0] 
    for i in range(28):
        current_date = today - timedelta(days=i)
        count = counts_dict.get(current_date, 0)
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

    habit_history = {}
    for habit in all_habits:
        sparkline_data = []
        for i in range(6, -1, -1): 
            check_date = today - timedelta(days=i)
            is_done = check_date in history_map[habit.id]
            # Pass the date string so the frontend can send it back to the toggle API
            sparkline_data.append((is_done, check_date.strftime('%Y-%m-%d')))
        habit_history[habit.id] = sparkline_data

    identities = Identity.query.filter_by(user_id=current_user.id).all()

    # Calculate current counts for the active cycle (Today for daily, This Week for weekly)
    current_counts = {}
    for habit in all_habits:
        if habit.frequency == HabitFrequency.DAILY:
            # How many logs today?
            count = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).count()
        else:
            # How many logs since Monday?
            count = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.completed_date >= start_of_week
            ).count()
        current_counts[habit.id] = count

    return render_template(
        'habits/manage.html',
        habits=all_habits,
        archived_habits=archived_habits,
        current_counts=current_counts,
        habit_statuses=habit_statuses,
        stats={
            "total": total_habits,
            "best_streak": best_streak,
            "daily": daily_count,
            "weekly": weekly_count
        },
        heatmap_data=heatmap_data,
        dow_counts=json.dumps(dow_counts),
        weekly_trend=json.dumps(weekly_trend),
        habit_history=habit_history,
        HabitFrequency=HabitFrequency,
        identities=identities,
        today=today,
        start_of_week=start_of_week,
        end_of_week=end_of_week
    )

@habits_view_bp.route('/calendar')
@login_required
def habit_calendar():
    today = get_local_today()
    year = request.args.get('year', today.year, type=int)
    month = request.args.get('month', today.month, type=int)
    
    # 1. Grab a LIST of filters from the URL (e.g., ?habit_id=1&habit_id=3)
    habit_ids = request.args.getlist('habit_id', type=int)

    cal = py_calendar.monthcalendar(year, month)
    start_date = date(year, month, 1)
    next_month = month % 12 + 1
    next_year = year + 1 if month == 12 else year
    end_date = date(next_year, next_month, 1) - timedelta(days=1)

    # 2. Fetch ALL user habits for the dropdown menu
    user_all_habits = Habit.query.filter_by(user_id=current_user.id).all()
    
    # 3. Isolate the specifically selected habits
    selected_habits = [h for h in user_all_habits if h.id in habit_ids]
    
    # If no filters are active, calculate math against ALL habits
    active_habits = selected_habits if selected_habits else user_all_habits

    total_habits = len(active_habits)
    max_possible = total_habits if total_habits > 0 else 1

    # 4. Filter the SQL Query
    logs_query = HabitLog.query.join(Habit).filter(
        Habit.user_id == current_user.id,
        HabitLog.completed_date >= start_date,
        HabitLog.completed_date <= end_date
    )
    if selected_habits:
        logs_query = logs_query.filter(HabitLog.habit_id.in_([h.id for h in selected_habits]))
    logs = logs_query.all()

    # Pass only the active habits to the JS UI
    habits_list = [{
        'id': h.id, 
        'name': h.name, 
        'icon': h.icon,
        'target': h.target_count, 
        'freq': h.frequency.name,
        'theme': h.identity.color if h.identity and h.identity.color else 'indigo'
    } for h in active_habits]

    date_habit_counts = defaultdict(lambda: defaultdict(int))
    for log in logs:
        date_habit_counts[log.completed_date.strftime('%Y-%m-%d')][str(log.habit_id)] += 1

    counts_dict = {}
    day_dots = defaultdict(set)
    
    for d_str, h_counts in date_habit_counts.items():
        d_obj = datetime.strptime(d_str, '%Y-%m-%d').date()
        completed_today = 0
        
        for h_id_str, count in h_counts.items():
            habit = next((h for h in active_habits if str(h.id) == h_id_str), None)
            if not habit: continue
            
            if (habit.frequency == HabitFrequency.DAILY and count >= habit.target_count) or \
               (habit.frequency == HabitFrequency.WEEKLY and count > 0):
                completed_today += 1
                theme = habit.identity.color if habit.identity and habit.identity.color else 'indigo'
                day_dots[d_obj].add(theme)
                
        counts_dict[d_obj] = completed_today

    days_in_month = py_calendar.monthrange(year, month)[1]
    total_possible = max_possible * days_in_month
    total_completions_month = sum(counts_dict.values())
    
    consistency_score = int((total_completions_month / total_possible) * 100) if total_possible > 0 else 0
    perfect_days = sum(1 for count in counts_dict.values() if count >= max_possible)

    identity_counts = defaultdict(int)
    for log in logs:
        if log.habit.identity:
            identity_counts[log.habit.identity] += 1

    top_identity_name = "Mixed Focus"
    top_identity_color = "stone"
    top_identity_score = 0
    
    if identity_counts:
        top_identity = max(identity_counts, key=identity_counts.get)
        top_identity_name = top_identity.name
        top_identity_color = top_identity.color or "indigo"
        top_identity_score = identity_counts[top_identity]
    elif len(selected_habits) == 1:
        # Fallback if filtered to 1 habit but no logs exist yet
        top_identity_name = selected_habits[0].identity.name if selected_habits[0].identity else "Unassigned"
        top_identity_color = selected_habits[0].identity.color if selected_habits[0].identity and selected_habits[0].identity.color else "indigo"

    calendar_data = []
    for week in cal:
        week_data = []
        for day in week:
            if day == 0:
                week_data.append(None)
            else:
                current_date = date(year, month, day)
                count = counts_dict.get(current_date, 0)
                week_data.append({
                    'day': day,
                    'date_str': current_date.strftime('%Y-%m-%d'),
                    'display_date': current_date.strftime('%A, %B %d'),
                    'count': count,
                    'is_today': current_date == today,
                    'dots': list(day_dots.get(current_date, []))[:5]
                })
        calendar_data.append(week_data)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1

    return render_template(
        'habits/calendar.html',
        calendar_data=calendar_data,
        month_name=date(year, month, 1).strftime('%B'),
        year=year, month=month,
        prev_month=prev_month, prev_year=prev_year,
        next_month=next_month, next_year=next_year,
        habits_json=json.dumps(habits_list),
        day_counts_json=json.dumps(date_habit_counts),
        max_possible=max_possible,
        consistency_score=consistency_score,
        perfect_days=perfect_days,
        days_in_month=days_in_month,
        total_possible=total_possible,
        top_identity_name=top_identity_name,
        top_identity_color=top_identity_color,
        top_identity_score=top_identity_score,
        # 5. Pass data for the UI Dropdown and Tags
        user_all_habits=user_all_habits,
        selected_habits=selected_habits
    )