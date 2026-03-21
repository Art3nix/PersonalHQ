"""Module handling the business logic and streak calculations for Habits."""

from datetime import datetime, timedelta
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.services.time_service import get_local_now, get_local_today

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

    now = get_local_now()
    is_daily = habit.frequency == HabitFrequency.DAILY

    # Determine if the habit is already completed for the current cycle
    already_completed = False
    if habit.last_completed:
        if is_daily:
            already_completed = _is_same_day(habit.last_completed, now)
        else:
            already_completed = _is_same_week(habit.last_completed, now)

    # Toggle Logic
    if already_completed:
        # UNDO action: The user is un-checking the habit for today/this week.
        habit.streak = max(0, habit.streak - 1)
        # Note: In a perfect world we'd store a history of all completions to revert
        # to the exact previous datetime. For this OS, setting to None or previous
        # cycle is fine
        if habit.streak == 0:
            habit.last_completed = None
        else:
            if is_daily:
                habit.last_completed = now - timedelta(days=1)
            else:
                habit.last_completed = now - timedelta(days=7)
        db.session.commit()
        return {"status": "success", "is_completed": False, "streak": habit.streak}

    # DO action: The user is checking the habit.
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

def get_habit_status_and_sync(habit) -> str:
    """
    Evaluates the current state of a habit and resets broken streaks.
    Returns: 'COMPLETED', 'EXPIRING' (needs to be done this cycle), or 'BROKEN'.
    """
    if not habit.last_completed:
        if habit.streak != 0:
            habit.streak = 0
        return "BROKEN"

    today = get_local_today()
    # Safely extract the date whether it's an old 'date' object or a new 'datetime' object
    last_date = habit.last_completed.date() if hasattr(habit.last_completed, 'date') else habit.last_completed

    if habit.frequency == HabitFrequency.DAILY:
        days_diff = (today - last_date).days
        if days_diff == 0:
            return "COMPLETED"
        elif days_diff == 1:
            return "EXPIRING"
        else:
            if habit.streak != 0:
                habit.streak = 0
            return "BROKEN"
    else: # WEEKLY
        # Find the Monday of both dates to accurately measure calendar weeks apart
        monday_this = today - timedelta(days=today.weekday())
        monday_last = last_date - timedelta(days=last_date.weekday())
        weeks_diff = (monday_this - monday_last).days // 7

        if weeks_diff == 0:
            return "COMPLETED"
        elif weeks_diff == 1:
            return "EXPIRING"
        else:
            if habit.streak != 0:
                habit.streak = 0
            return "BROKEN"


def create_habit(user_id: int, name: str, frequency: str, identity_id: int = None, 
                 description: str = None, trigger: str = None, icon: str = "⭐") -> Habit:
    """Create a new habit for a user."""
    habit = Habit(
        user_id=user_id,
        name=name.strip(),
        frequency=HabitFrequency[frequency.upper()],
        identity_id=identity_id,
        description=description.strip() if description else None,
        trigger=trigger.strip() if trigger else None,
        icon=icon,
        streak=0
    )
    db.session.add(habit)
    db.session.commit()
    return habit


def update_habit(habit_id: int, user_id: int, **kwargs) -> dict:
    """Update habit fields (name, description, trigger, icon, etc.)."""
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != user_id:
        return {"status": "error", "message": "Habit not found"}
    
    allowed_fields = ['name', 'description', 'trigger', 'icon', 'frequency', 'identity_id']
    for field, value in kwargs.items():
        if field in allowed_fields and value is not None:
            if field == 'frequency':
                setattr(habit, field, HabitFrequency[value.upper()])
            else:
                setattr(habit, field, value)
    
    db.session.commit()
    return {"status": "success", "message": "Habit updated"}


def delete_habit(habit_id: int, user_id: int) -> dict:
    """Delete a habit and all its logs."""
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != user_id:
        return {"status": "error", "message": "Habit not found"}
    
    db.session.delete(habit)
    db.session.commit()
    return {"status": "success", "message": "Habit deleted"}


def import_habit_streak(user_id: int, name: str, existing_streak: int, 
                       frequency: str = "DAILY", identity_id: int = None) -> dict:
    """Import a habit with an existing streak from another system."""
    habit = create_habit(user_id, name, frequency, identity_id)
    habit.streak = existing_streak
    db.session.commit()
    return {"status": "success", "habit_id": habit.id, "message": "Habit imported with streak"}
