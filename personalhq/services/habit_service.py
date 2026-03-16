"""Module handling the business logic and streak calculations for Habits."""

from datetime import datetime, timedelta
from personalhq.extensions import db
from personalhq.models.habits import HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.services.time_service import get_local_today

def _is_same_day(date1: datetime, date2: datetime) -> bool:
    """Helper to check if two datetimes fall on the exact same calendar day."""
    if not date1 or not date2:
        return False
    return date1.date() == date2.date()

def _is_yesterday(last_date: datetime, current_date: datetime) -> bool:
    """Helper to check if the last completion was exactly yesterday."""
    if not last_date or not current_date:
        return False
    delta = current_date.date() - last_date.date()
    return delta.days == 1

def _is_same_week(date1: datetime, date2: datetime) -> bool:
    """Helper to check if two datetimes fall in the same ISO calendar week."""
    if not date1 or not date2:
        return False
    return date1.isocalendar()[:2] == date2.isocalendar()[:2]

def _is_last_week(last_date: datetime, current_date: datetime) -> bool:
    """Helper to check if the last completion was exactly one calendar week ago."""
    if not last_date or not current_date:
        return False
    # Move current date back by 7 days and check if it lands in the same week as last_date
    one_week_ago = current_date.date() - timedelta(days=7)
    return last_date.isocalendar()[:2] == one_week_ago.isocalendar()[:2]

def recalculate_habit_streaks(habit):
    """
    Scans all logs for a habit to find current and best streaks.
    Now supports individual habit best_streak tracking.
    """
    # 1. Get all completion dates in descending order (newest first)
    logs = db.session.query(HabitLog.completed_date)\
                     .filter_by(habit_id=habit.id)\
                     .order_by(HabitLog.completed_date.desc())\
                     .all()
    
    # Convert list of tuples to list of date objects
    log_dates = [log[0] for log in logs]
    
    if not log_dates:
        habit.streak = 0
        habit.last_completed = None
        return

    today = get_local_today()
    current_streak = 0
    
    # 2. Calculate Current Streak
    if habit.frequency == HabitFrequency.DAILY:
        # Check if the most recent log is from today or yesterday
        if (today - log_dates[0]).days <= 1:
            current_streak = 1
            for i in range(len(log_dates) - 1):
                if (log_dates[i] - log_dates[i+1]).days == 1:
                    current_streak += 1
                else:
                    break
    else: # WEEKLY
        # Weekly logic: check if most recent log is this week or last week
        monday_this = today - timedelta(days=today.weekday())
        monday_last_log = log_dates[0] - timedelta(days=log_dates[0].weekday())
        if (monday_this - monday_last_log).days <= 7:
            current_streak = 1
            for i in range(len(log_dates) - 1):
                m1 = log_dates[i] - timedelta(days=log_dates[i].weekday())
                m2 = log_dates[i+1] - timedelta(days=log_dates[i+1].weekday())
                if (m1 - m2).days == 7:
                    current_streak += 1
                else:
                    break

    # 3. Calculate Best Streak (Historical Record)
    best_streak = habit.best_streak or 0
    temp_streak = 1

    # Scan entire history to see if any old chain was longer
    for i in range(len(log_dates) - 1):
        diff = (log_dates[i] - log_dates[i+1]).days
        # For daily, a gap of 1 day continues the chain
        if habit.frequency == HabitFrequency.DAILY and diff == 1:
            temp_streak += 1
        # For weekly, a gap of 7 days continues the chain
        elif habit.frequency == HabitFrequency.WEEKLY and diff == 7:
            temp_streak += 1
        else:
            best_streak = max(best_streak, temp_streak)
            temp_streak = 1

    best_streak = max(best_streak, temp_streak, current_streak)

    # 4. Update the Model
    habit.streak = current_streak
    habit.best_streak = best_streak
    # Set last_completed to the most recent log found
    habit.last_completed = datetime.combine(log_dates[0], datetime.min.time())

def get_habit_status_and_sync(habit) -> str:
    """
    Evaluates current state without modifying the DB (recalc handles cleanup).
    Returns: 'COMPLETED', 'EXPIRING', or 'BROKEN'.
    """
    if not habit.last_completed:
        return "BROKEN"

    today = get_local_today()
    last_date = habit.last_completed.date()

    if habit.frequency == HabitFrequency.DAILY:
        days_diff = (today - last_date).days
        if days_diff == 0: return "COMPLETED"
        if days_diff == 1: return "EXPIRING"
        return "BROKEN"
    else: # WEEKLY
        monday_this = today - timedelta(days=today.weekday())
        monday_last = last_date - timedelta(days=last_date.weekday())
        weeks_diff = (monday_this - monday_last).days // 7
        if weeks_diff == 0: return "COMPLETED"
        if weeks_diff == 1: return "EXPIRING"
        return "BROKEN"
