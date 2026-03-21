"""Enhanced habit service with complete CRUD and streak operations."""

from datetime import datetime, timedelta
import pytz
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitLog
from personalhq.services.timezone_service import TimezoneService
from personalhq.services.streak_calculator import StreakCalculator
from personalhq.services.validation_service import ValidationService


class HabitServiceV2:
    """Enhanced habit service with full CRUD and streak management."""
    
    @staticmethod
    def create_habit(user, name: str, description: str = None, frequency: str = 'daily',
                     identity_id: int = None, check_ins_required: int = 1,
                     trigger: str = None) -> tuple[Habit, str]:
        """
        Create a new habit.
        
        Returns:
            (habit, error_message) - error_message is empty string if successful
        """
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
            habit = Habit(
                name=name.strip(),
                description=description.strip() if description else None,
                frequency=frequency,
                user_id=user.id,
                identity_id=identity_id,
                check_ins_required=check_ins_required,
                trigger=trigger.strip() if trigger else None,
                created_at=TimezoneService.utc_now()
            )
            db.session.add(habit)
            db.session.commit()
            return habit, ""
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to create habit: {str(e)}"
    
    @staticmethod
    def update_habit(habit: Habit, **kwargs) -> tuple[bool, str]:
        """
        Update habit properties.
        
        Returns:
            (success, error_message)
        """
        allowed_fields = ['name', 'description', 'frequency', 'identity_id', 
                         'check_ins_required', 'trigger', 'is_active']
        
        try:
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                
                if key == 'name' and value:
                    is_valid, error = ValidationService.validate_habit({'name': value})
                    if not is_valid:
                        return False, error
                    habit.name = value.strip()
                elif key == 'description' and value:
                    habit.description = value.strip()
                elif key == 'frequency' and value in ['daily', 'weekly', 'custom']:
                    habit.frequency = value
                elif key == 'check_ins_required' and value:
                    try:
                        check_ins = int(value)
                        if 1 <= check_ins <= 100:
                            habit.check_ins_required = check_ins
                    except ValueError:
                        pass
                elif key == 'trigger' and value:
                    habit.trigger = value.strip()
                elif key == 'is_active':
                    habit.is_active = bool(value)
                elif key == 'identity_id':
                    habit.identity_id = value
            
            habit.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update habit: {str(e)}"
    
    @staticmethod
    def delete_habit(habit: Habit) -> tuple[bool, str]:
        """
        Delete a habit and all its logs.
        
        Returns:
            (success, error_message)
        """
        try:
            # Delete all habit logs
            HabitLog.query.filter_by(habit_id=habit.id).delete()
            db.session.delete(habit)
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete habit: {str(e)}"
    
    @staticmethod
    def log_habit(habit: Habit, user, date_logged: datetime = None, 
                  check_ins: int = None) -> tuple[HabitLog, str]:
        """
        Log a habit completion.
        
        Returns:
            (habit_log, error_message)
        """
        try:
            if date_logged is None:
                date_logged = TimezoneService.utc_now()
            
            if check_ins is None:
                check_ins = 1
            
            # Check if already logged today
            today_start, today_end = TimezoneService.get_today_start_end(user)
            existing = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.date_logged >= today_start,
                HabitLog.date_logged < today_end
            ).first()
            
            if existing:
                # Update existing log
                existing.check_ins_completed = check_ins
                existing.updated_at = TimezoneService.utc_now()
                db.session.commit()
                return existing, ""
            
            # Create new log
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
    
    @staticmethod
    def unlog_habit(habit: Habit, user, date: datetime = None) -> tuple[bool, str]:
        """
        Remove a habit log for a specific date.
        
        Returns:
            (success, error_message)
        """
        try:
            if date is None:
                today_start, today_end = TimezoneService.get_today_start_end(user)
                log = HabitLog.query.filter(
                    HabitLog.habit_id == habit.id,
                    HabitLog.date_logged >= today_start,
                    HabitLog.date_logged < today_end
                ).first()
            else:
                log = HabitLog.query.filter(
                    HabitLog.habit_id == habit.id,
                    HabitLog.date_logged == date
                ).first()
            
            if log:
                db.session.delete(log)
                db.session.commit()
                return True, ""
            
            return False, "No log found for this date"
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to unlog habit: {str(e)}"
    
    @staticmethod
    def get_habit_logs(habit: Habit, days_back: int = 90) -> list:
        """Get habit logs for the past N days."""
        cutoff_date = TimezoneService.utc_now() - timedelta(days=days_back)
        return HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.date_logged >= cutoff_date
        ).order_by(HabitLog.date_logged.desc()).all()
    
    @staticmethod
    def get_streak_info(habit: Habit, user) -> dict:
        """Get comprehensive streak information for a habit."""
        logs = HabitServiceV2.get_habit_logs(habit, days_back=365)
        return StreakCalculator.get_streak_status(logs, user)
    
    @staticmethod
    def import_habit_streak(user, name: str, existing_streak: int, 
                           frequency: str = 'daily') -> tuple[Habit, str]:
        """
        Import a habit with an existing streak.
        
        Returns:
            (habit, error_message)
        """
        # Create the habit
        habit, error = HabitServiceV2.create_habit(user, name, frequency=frequency)
        if error:
            return None, error
        
        try:
            # Create logs for the streak
            tz = pytz.timezone(TimezoneService.get_user_timezone(user))
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
    
    @staticmethod
    def get_habits_by_frequency(user, frequency: str) -> list:
        """Get all habits of a specific frequency."""
        return Habit.query.filter_by(user_id=user.id, frequency=frequency, is_active=True).all()
    
    @staticmethod
    def get_all_habits(user, include_inactive: bool = False) -> list:
        """Get all habits for a user."""
        query = Habit.query.filter_by(user_id=user.id)
        if not include_inactive:
            query = query.filter_by(is_active=True)
        return query.all()
    
    @staticmethod
    def get_habits_by_identity(user, identity_id: int) -> list:
        """Get all habits linked to an identity."""
        return Habit.query.filter_by(user_id=user.id, identity_id=identity_id, is_active=True).all()
    
    @staticmethod
    def toggle_habit_active(habit: Habit, is_active: bool) -> tuple[bool, str]:
        """Toggle habit active/inactive status."""
        try:
            habit.is_active = is_active
            habit.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to toggle habit: {str(e)}"
