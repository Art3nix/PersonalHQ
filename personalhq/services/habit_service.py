"""Module handling the business logic and streak calculations for Habits."""

from datetime import datetime, timedelta
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitFrequency

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

def toggle_habit(habit_id: int, user_id: int) -> dict:
    """
    Toggles a habit's completion status for the current cycle (day/week).
    Calculates the new streak and updates the database.
    """
    habit = db.session.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        return {"error": "Habit not found"}

    now = datetime.now()
    is_daily = (habit.frequency == HabitFrequency.DAILY)
    
    # 1. Determine if the habit is already completed for the current cycle
    already_completed = False
    if habit.last_completed:
        if is_daily:
            already_completed = _is_same_day(habit.last_completed, now)
        else:
            already_completed = _is_same_week(habit.last_completed, now)

    # 2. Toggle Logic
    if already_completed:
        # UNDO action: The user is un-checking the habit for today/this week.
        habit.streak = max(0, habit.streak - 1)
        # Note: In a perfect world we'd store a history of all completions to revert 
        # to the exact previous datetime. For this OS, setting to None or leaving 
        # it mathematically handles the UI state well enough for an undo.
        if habit.streak == 0:
            habit.last_completed = None
        db.session.commit()
        return {"status": "success", "is_completed": False, "streak": habit.streak}

    # 3. DO action: The user is checking the habit.
    if is_daily:
        if _is_yesterday(habit.last_completed, now):
            habit.streak += 1
        else:
            habit.streak = 1 # Streak broken or starting fresh
    else:
        # Weekly logic
        if _is_last_week(habit.last_completed, now):
            habit.streak += 1
        else:
            habit.streak = 1
            
    habit.last_completed = now
    db.session.commit()
    
    return {"status": "success", "is_completed": True, "streak": habit.streak}