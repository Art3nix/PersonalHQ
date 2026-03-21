"""Unified habit service with complete CRUD, streak calculations, and management."""

from datetime import datetime, timedelta
import pytz
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitFrequency, HabitLog
from personalhq.services.time_service import get_local_now, get_local_today
from personalhq.services.timezone_service import TimezoneService
from personalhq.services.streak_calculator import StreakCalculator
from personalhq.services.validation_service import ValidationService


# ============================================================================
# HELPER FUNCTIONS FOR STREAK CALCULATION
# ============================================================================

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
    one_week_ago = current_date.date() - timedelta(days=7)
    return last_date.isocalendar()[:2] == one_week_ago.isocalendar()[:2]


# ============================================================================
# LEGACY FUNCTIONS (KEPT FOR BACKWARD COMPATIBILITY)
# ============================================================================

def toggle_habit(habit_id: int, user_id: int) -> dict:
    """
    Toggles a habit's completion status for the current cycle (day/week).
    Calculates the new streak and updates the database.
    
    DEPRECATED: Use log_habit() and unlog_habit() instead.
    """
    habit = db.session.query(Habit).filter_by(id=habit_id, user_id=user_id).first()
    if not habit:
        return {"error": "Habit not found"}

    now = get_local_now()
    is_daily = habit.frequency == HabitFrequency.DAILY

    already_completed = False
    if habit.last_completed:
        if is_daily:
            already_completed = _is_same_day(habit.last_completed, now)
        else:
            already_completed = _is_same_week(habit.last_completed, now)

    if already_completed:
        habit.streak = max(0, habit.streak - 1)
        if habit.streak == 0:
            habit.last_completed = None
        else:
            if is_daily:
                habit.last_completed = now - timedelta(days=1)
            else:
                habit.last_completed = now - timedelta(days=7)
        db.session.commit()
        return {"status": "success", "is_completed": False, "streak": habit.streak}

    if is_daily:
        if _is_yesterday(habit.last_completed, now):
            habit.streak += 1
        else:
            habit.streak = 1
    else:
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
    else:
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


# ============================================================================
# CRUD OPERATIONS (UNIFIED)
# ============================================================================

def create_habit(user_id: int = None, name: str = None, frequency: str = 'daily',
                identity_id: int = None, description: str = None, trigger: str = None,
                icon: str = "⭐", user=None, check_ins_required: int = 1) -> tuple:
    """
    Create a new habit for a user.
    
    Supports both old signature (user_id) and new signature (user object).
    Returns: (habit, error_message) - error_message is empty string if successful
    """
    # Handle both old and new calling conventions
    if user is not None:
        user_id = user.id
    
    if not user_id or not name:
        return None, "User ID and name are required"
    
    # Validate input
    is_valid, error = ValidationService.validate_habit({
        'name': name,
        'description': description,
        'frequency': frequency,
        'check_ins_required': check_ins_required
    })
    if not is_valid:
        return None, error
    
    try:
        # Convert frequency string to enum if needed
        if isinstance(frequency, str):
            freq_enum = HabitFrequency[frequency.upper()]
        else:
            freq_enum = frequency
        
        habit = Habit(
            user_id=user_id,
            name=name.strip(),
            frequency=freq_enum,
            identity_id=identity_id,
            description=description.strip() if description else None,
            trigger=trigger.strip() if trigger else None,
            icon=icon,
            streak=0,
            check_ins_required=check_ins_required,
            is_active=True,
            created_at=TimezoneService.utc_now()
        )
        db.session.add(habit)
        db.session.commit()
        return habit, ""
    except Exception as e:
        db.session.rollback()
        return None, f"Failed to create habit: {str(e)}"


def update_habit(habit_id: int = None, user_id: int = None, habit: Habit = None, **kwargs) -> tuple:
    """
    Update habit fields.
    
    Supports both old signature (habit_id, user_id) and new signature (habit object).
    Returns: (success, error_message)
    """
    # Handle both old and new calling conventions
    if habit is None:
        if not habit_id or not user_id:
            return False, "Habit ID and user ID are required"
        habit = db.session.get(Habit, habit_id)
        if not habit or habit.user_id != user_id:
            return False, "Habit not found"
    
    allowed_fields = ['name', 'description', 'trigger', 'icon', 'frequency', 'identity_id',
                     'check_ins_required', 'is_active']
    
    try:
        for key, value in kwargs.items():
            if key not in allowed_fields or value is None:
                continue
            
            if key == 'name':
                is_valid, error = ValidationService.validate_habit({'name': value})
                if not is_valid:
                    return False, error
                habit.name = value.strip()
            elif key == 'description':
                habit.description = value.strip() if value else None
            elif key == 'trigger':
                habit.trigger = value.strip() if value else None
            elif key == 'icon':
                habit.icon = value
            elif key == 'frequency':
                if isinstance(value, str):
                    habit.frequency = HabitFrequency[value.upper()]
                else:
                    habit.frequency = value
            elif key == 'identity_id':
                habit.identity_id = value
            elif key == 'check_ins_required':
                try:
                    check_ins = int(value)
                    if 1 <= check_ins <= 100:
                        habit.check_ins_required = check_ins
                except (ValueError, TypeError):
                    pass
            elif key == 'is_active':
                habit.is_active = bool(value)
        
        habit.updated_at = TimezoneService.utc_now()
        db.session.commit()
        return True, ""
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to update habit: {str(e)}"


def delete_habit(habit_id: int = None, user_id: int = None, habit: Habit = None) -> tuple:
    """
    Delete a habit and all its logs.
    
    Supports both old signature (habit_id, user_id) and new signature (habit object).
    Returns: (success, error_message)
    """
    # Handle both old and new calling conventions
    if habit is None:
        if not habit_id or not user_id:
            return False, "Habit ID and user ID are required"
        habit = db.session.get(Habit, habit_id)
        if not habit or habit.user_id != user_id:
            return False, "Habit not found"
    
    try:
        HabitLog.query.filter_by(habit_id=habit.id).delete()
        db.session.delete(habit)
        db.session.commit()
        return True, ""
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to delete habit: {str(e)}"


# ============================================================================
# HABIT LOGGING (NEW UNIFIED APPROACH)
# ============================================================================

def log_habit(habit: Habit, user=None, date_logged: datetime = None, 
             check_ins: int = None) -> tuple:
    """
    Log a habit completion.
    
    Returns: (habit_log, error_message)
    """
    try:
        if date_logged is None:
            date_logged = TimezoneService.utc_now()
        
        if check_ins is None:
            check_ins = 1
        
        # Check if already logged today
        if user:
            today_start, today_end = TimezoneService.get_today_start_end(user)
            existing = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.date_logged >= today_start,
                HabitLog.date_logged < today_end
            ).first()
        else:
            existing = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.date_logged == date_logged.date()
            ).first()
        
        if existing:
            existing.check_ins_completed = check_ins
            existing.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return existing, ""
        
        log = HabitLog(
            habit_id=habit.id,
            date_logged=date_logged,
            check_ins_completed=check_ins,
            created_at=TimezoneService.utc_now()
        )
        db.session.add(log)
        db.session.commit()
        return log, ""
    except Exception as e:
        db.session.rollback()
        return None, f"Failed to log habit: {str(e)}"


def unlog_habit(habit: Habit, user=None, date: datetime = None) -> tuple:
    """
    Remove a habit log for a specific date.
    
    Returns: (success, error_message)
    """
    try:
        if date is None and user:
            today_start, today_end = TimezoneService.get_today_start_end(user)
            log = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.date_logged >= today_start,
                HabitLog.date_logged < today_end
            ).first()
        elif date:
            log = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.date_logged == date
            ).first()
        else:
            return False, "Date or user is required"
        
        if log:
            db.session.delete(log)
            db.session.commit()
            return True, ""
        
        return False, "No log found for this date"
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to unlog habit: {str(e)}"


# ============================================================================
# STREAK & STATISTICS
# ============================================================================

def get_habit_logs(habit: Habit, days_back: int = 90) -> list:
    """Get habit logs for the past N days."""
    cutoff_date = TimezoneService.utc_now() - timedelta(days=days_back)
    return HabitLog.query.filter(
        HabitLog.habit_id == habit.id,
        HabitLog.date_logged >= cutoff_date
    ).order_by(HabitLog.date_logged.desc()).all()


def get_streak_info(habit: Habit, user=None) -> dict:
    """Get comprehensive streak information for a habit."""
    logs = get_habit_logs(habit, days_back=365)
    if user:
        return StreakCalculator.get_streak_status(logs, user)
    else:
        return {"current_streak": habit.streak, "best_streak": habit.streak, "logs": len(logs)}


def import_habit_streak(user_id: int = None, name: str = None, existing_streak: int = 0,
                       frequency: str = "daily", identity_id: int = None, user=None) -> tuple:
    """
    Import a habit with an existing streak from another system.
    
    Returns: (habit, error_message)
    """
    # Handle both old and new calling conventions
    if user is not None:
        user_id = user.id
    
    if not user_id or not name:
        return None, "User ID and name are required"
    
    # Create the habit
    habit, error = create_habit(user_id=user_id, name=name, frequency=frequency, 
                               identity_id=identity_id)
    if error:
        return None, error
    
    try:
        # Create logs for the streak
        tz = pytz.timezone(TimezoneService.get_user_timezone_by_id(user_id))
        now = TimezoneService.utc_now().astimezone(tz)
        
        for i in range(existing_streak):
            log_date = now - timedelta(days=i)
            log = HabitLog(
                habit_id=habit.id,
                date_logged=log_date.astimezone(pytz.UTC),
                check_ins_completed=1,
                created_at=TimezoneService.utc_now()
            )
            db.session.add(log)
        
        db.session.commit()
        return habit, ""
    except Exception as e:
        db.session.rollback()
        return None, f"Failed to import streak: {str(e)}"


# ============================================================================
# QUERIES & FILTERING
# ============================================================================

def get_habits_by_frequency(user_id: int, frequency: str, include_inactive: bool = False) -> list:
    """Get all habits of a specific frequency."""
    query = Habit.query.filter_by(user_id=user_id, frequency=HabitFrequency[frequency.upper()])
    if not include_inactive:
        query = query.filter_by(is_active=True)
    return query.all()


def get_all_habits(user_id: int, include_inactive: bool = False) -> list:
    """Get all habits for a user."""
    query = Habit.query.filter_by(user_id=user_id)
    if not include_inactive:
        query = query.filter_by(is_active=True)
    return query.all()


def get_habits_by_identity(user_id: int, identity_id: int, include_inactive: bool = False) -> list:
    """Get all habits linked to an identity."""
    query = Habit.query.filter_by(user_id=user_id, identity_id=identity_id)
    if not include_inactive:
        query = query.filter_by(is_active=True)
    return query.all()


def toggle_habit_active(habit: Habit, is_active: bool) -> tuple:
    """Toggle habit active/inactive status."""
    try:
        habit.is_active = is_active
        habit.updated_at = TimezoneService.utc_now()
        db.session.commit()
        return True, ""
    except Exception as e:
        db.session.rollback()
        return False, f"Failed to toggle habit: {str(e)}"
