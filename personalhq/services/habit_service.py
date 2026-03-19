"""Module handling the business logic and streak calculations for Habits."""

from datetime import datetime, timedelta
from collections import defaultdict
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.services.time_service import get_local_today

def recalculate_habit_streaks(habit):
    """Scans all logs and strictly enforces target_count and progress for streaks."""
    logs = HabitLog.query.filter_by(habit_id=habit.id).all()
    
    if not logs:
        habit.streak = 0
        habit.last_completed = None
        return

    today = get_local_today()
    current_streak = 0
    valid_dates = []

    if habit.frequency == HabitFrequency.DAILY:
        # Valid dates are days where progress actually hit the target
        valid_dates = sorted([l.completed_date for l in logs if l.progress >= l.target_at_time], reverse=True)
        
        if not valid_dates:
            habit.streak = 0
            habit.last_completed = None
            return

        # Check if most recent valid date is today or yesterday
        if (today - valid_dates[0]).days <= 1:
            current_streak = 1
            for i in range(len(valid_dates) - 1):
                if (valid_dates[i] - valid_dates[i+1]).days == 1:
                    current_streak += 1
                else: break

    else: # WEEKLY
        # Group progress by week (Monday)
        week_progress = defaultdict(int)
        week_targets = {}
        for l in logs:
            monday = l.completed_date - timedelta(days=l.completed_date.weekday())
            week_progress[monday] += l.progress
            week_targets[monday] = l.target_at_time 
            
        valid_dates = sorted([w for w, prog in week_progress.items() if prog >= week_targets.get(w, habit.target_count)], reverse=True)
        
        if not valid_dates:
            habit.streak = 0
            habit.last_completed = None
            return
            
        monday_this = today - timedelta(days=today.weekday())
        if (monday_this - valid_dates[0]).days <= 7:
            current_streak = 1
            for i in range(len(valid_dates) - 1):
                if (valid_dates[i] - valid_dates[i+1]).days == 7:
                    current_streak += 1
                else: break

    # Calculate Best Streak based only on valid periods
    best_streak = habit.best_streak or 0
    temp_streak = 1
    
    for i in range(len(valid_dates) - 1):
        diff = (valid_dates[i] - valid_dates[i+1]).days
        if (habit.frequency == HabitFrequency.DAILY and diff == 1) or \
           (habit.frequency == HabitFrequency.WEEKLY and diff == 7):
            temp_streak += 1
        else:
            best_streak = max(best_streak, temp_streak)
            temp_streak = 1

    habit.streak = current_streak
    habit.best_streak = max(best_streak, temp_streak, current_streak)
    habit.last_completed = datetime.combine(valid_dates[0], datetime.min.time())


def get_habit_status_and_sync(habit) -> str:
    """Evaluates current state for the UI styling (COMPLETED, PENDING, EXPIRING, BROKEN)."""
    recalculate_habit_streaks(habit)

    today = get_local_today()
    current_hour = datetime.now().hour

    if habit.frequency == HabitFrequency.DAILY:
        # FIX: Check progress integer, not row count
        log_today = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
        if log_today and log_today.progress >= habit.target_count: return "COMPLETED"

        yesterday = today - timedelta(days=1)
        log_yesterday = HabitLog.query.filter_by(habit_id=habit.id, completed_date=yesterday).first()
        if log_yesterday and log_yesterday.progress >= habit.target_count:
            if current_hour >= 20: return "EXPIRING"
            return "PENDING"
        return "BROKEN"
    else:
        start_of_week = today - timedelta(days=today.weekday())
        logs_this_week = HabitLog.query.filter(HabitLog.habit_id == habit.id, HabitLog.completed_date >= start_of_week).all()
        if sum(l.progress for l in logs_this_week) >= habit.target_count: return "COMPLETED"

        start_of_last_week = start_of_week - timedelta(days=7)
        logs_last_week = HabitLog.query.filter(
            HabitLog.habit_id == habit.id, 
            HabitLog.completed_date >= start_of_last_week, 
            HabitLog.completed_date < start_of_week
        ).all()
        if sum(l.progress for l in logs_last_week) >= habit.target_count:
            if today.weekday() == 6 and current_hour >= 20: return "EXPIRING"
            return "PENDING"
        return "BROKEN"

def get_habit_current_count(habit) -> int:
    """Fetches the exact progress count for today or this week."""
    today = get_local_today()
    if habit.frequency == HabitFrequency.DAILY:
        log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
        return log.progress if log else 0
    else:
        start_of_week = today - timedelta(days=today.weekday())
        logs = HabitLog.query.filter(HabitLog.habit_id == habit.id, HabitLog.completed_date >= start_of_week).all()
        return sum(l.progress for l in logs)

def run_daily_ledger_catchup(user_id):
    """Generates missing daily logs for active habits, capped at 30 days to prevent DDOS."""
    today = get_local_today()
    limit_date = today - timedelta(days=30)

    active_habits = Habit.query.filter_by(user_id=user_id, is_active=True).all()
    new_logs = []

    for habit in active_habits:
        start_date = max(limit_date, habit.created_at.date() if habit.created_at else limit_date)

        existing_logs = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed_date >= start_date
        ).with_entities(HabitLog.completed_date).all()

        existing_dates = {log[0] for log in existing_logs}

        current_date = start_date
        while current_date <= today:
            if current_date not in existing_dates:
                new_logs.append(HabitLog(
                    habit_id=habit.id,
                    completed_date=current_date,
                    progress=0,
                    target_at_time=habit.target_count 
                ))
            current_date += timedelta(days=1)

    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()