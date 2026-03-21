"""Service for managing identities."""

from personalhq.extensions import db
from personalhq.models.identities import Identity
from personalhq.services.timezone_service import TimezoneService
from personalhq.services.validation_service import ValidationService


class IdentityService:
    """Manages identity CRUD operations."""
    
    @staticmethod
    def create_identity(user, name: str, reinforcing_sentence: str = None,
                       color: str = None) -> tuple[Identity, str]:
        """
        Create a new identity.
        
        Returns:
            (identity, error_message)
        """
        is_valid, error = ValidationService.validate_identity({
            'name': name,
            'reinforcing_sentence': reinforcing_sentence,
            'color': color
        })
        if not is_valid:
            return None, error
        
        try:
            identity = Identity(
                name=name.strip(),
                reinforcing_sentence=reinforcing_sentence.strip() if reinforcing_sentence else None,
                color=color if color else '#3B82F6',  # Default blue
                user_id=user.id,
                created_at=TimezoneService.utc_now()
            )
            db.session.add(identity)
            db.session.commit()
            return identity, ""
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to create identity: {str(e)}"
    
    @staticmethod
    def update_identity(identity: Identity, **kwargs) -> tuple[bool, str]:
        """
        Update identity properties.
        
        Returns:
            (success, error_message)
        """
        allowed_fields = ['name', 'reinforcing_sentence', 'color']
        
        try:
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                
                if key == 'name' and value:
                    is_valid, error = ValidationService.validate_identity({'name': value})
                    if not is_valid:
                        return False, error
                    identity.name = value.strip()
                elif key == 'reinforcing_sentence' and value:
                    identity.reinforcing_sentence = value.strip()
                elif key == 'color' and value:
                    if ValidationService._is_valid_hex_color(value):
                        identity.color = value
            
            identity.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update identity: {str(e)}"
    
    @staticmethod
    def delete_identity(identity: Identity) -> tuple[bool, str]:
        """
        Delete an identity and unlink all habits.
        
        Returns:
            (success, error_message)
        """
        try:
            # Unlink all habits from this identity
            from personalhq.models.habits import Habit
            Habit.query.filter_by(identity_id=identity.id).update({'identity_id': None})
            
            db.session.delete(identity)
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete identity: {str(e)}"
    
    @staticmethod
    def get_identities(user, include_deleted: bool = False) -> list:
        """Get all identities for a user."""
        query = Identity.query.filter_by(user_id=user.id)
        return query.all()
    
    @staticmethod
    def get_identity_by_id(user, identity_id: int) -> Identity:
        """Get a specific identity."""
        return Identity.query.filter_by(id=identity_id, user_id=user.id).first()
    
    @staticmethod
    def get_identity_habits(identity: Identity) -> list:
        """Get all habits linked to an identity."""
        from personalhq.models.habits import Habit
        return Habit.query.filter_by(identity_id=identity.id, is_active=True).all()
    
    @staticmethod
    def get_identity_stats(identity: Identity, user) -> dict:
        """Get statistics for an identity."""
        from personalhq.models.habits import Habit, HabitLog
        from personalhq.services.streak_calculator import StreakCalculator
        
        habits = IdentityService.get_identity_habits(identity)
        
        total_habits = len(habits)
        active_streaks = 0
        total_logs = 0
        
        for habit in habits:
            logs = HabitLog.query.filter_by(habit_id=habit.id).all()
            total_logs += len(logs)
            
            if StreakCalculator.is_streak_active(logs, user):
                active_streaks += 1
        
        return {
            'total_habits': total_habits,
            'active_streaks': active_streaks,
            'total_logs': total_logs,
            'habits': habits
        }
