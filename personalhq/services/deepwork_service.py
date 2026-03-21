"""Service for managing deep work sessions."""

from datetime import datetime, timedelta
from personalhq.extensions import db
from personalhq.models.focussessions import FocusSession
from personalhq.services.timezone_service import TimezoneService
from personalhq.services.validation_service import ValidationService


class DeepWorkService:
    """Manages deep work session CRUD and timer operations."""
    
    @staticmethod
    def create_session(user, task_name: str, duration_minutes: int = 25,
                      identity_id: int = None) -> tuple[FocusSession, str]:
        """
        Create a new deep work session.
        
        Returns:
            (session, error_message)
        """
        is_valid, error = ValidationService.validate_deep_work_session({
            'task_name': task_name,
            'duration_minutes': duration_minutes
        })
        if not is_valid:
            return None, error
        
        try:
            session = FocusSession(
                user_id=user.id,
                task_name=task_name.strip(),
                duration_minutes=duration_minutes,
                identity_id=identity_id,
                status='planned',  # planned, active, paused, completed, discarded
                created_at=TimezoneService.utc_now()
            )
            db.session.add(session)
            db.session.commit()
            return session, ""
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to create session: {str(e)}"
    
    @staticmethod
    def start_session(session: FocusSession) -> tuple[bool, str]:
        """
        Start a deep work session.
        
        Returns:
            (success, error_message)
        """
        try:
            if session.status not in ['planned', 'paused']:
                return False, f"Cannot start session with status: {session.status}"
            
            session.status = 'active'
            session.started_at = TimezoneService.utc_now()
            
            # If resuming from pause, adjust end time
            if session.paused_at:
                pause_duration = session.started_at - session.paused_at
                if session.end_time:
                    session.end_time += pause_duration
                session.paused_at = None
            else:
                # First start
                session.end_time = session.started_at + timedelta(minutes=session.duration_minutes)
            
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to start session: {str(e)}"
    
    @staticmethod
    def pause_session(session: FocusSession) -> tuple[bool, str]:
        """
        Pause a deep work session.
        
        Returns:
            (success, error_message)
        """
        try:
            if session.status != 'active':
                return False, f"Cannot pause session with status: {session.status}"
            
            session.status = 'paused'
            session.paused_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to pause session: {str(e)}"
    
    @staticmethod
    def resume_session(session: FocusSession) -> tuple[bool, str]:
        """
        Resume a paused deep work session.
        
        Returns:
            (success, error_message)
        """
        return DeepWorkService.start_session(session)
    
    @staticmethod
    def end_session(session: FocusSession, early: bool = False) -> tuple[bool, str]:
        """
        End a deep work session.
        
        Args:
            session: FocusSession to end
            early: Whether session ended early
            
        Returns:
            (success, error_message)
        """
        try:
            if session.status not in ['active', 'paused']:
                return False, f"Cannot end session with status: {session.status}"
            
            session.status = 'completed'
            session.ended_at = TimezoneService.utc_now()
            session.ended_early = early
            
            # Calculate actual duration
            if session.started_at and session.ended_at:
                actual_duration = session.ended_at - session.started_at
                session.actual_duration_minutes = int(actual_duration.total_seconds() / 60)
            
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to end session: {str(e)}"
    
    @staticmethod
    def discard_session(session: FocusSession) -> tuple[bool, str]:
        """
        Discard a deep work session without saving.
        
        Returns:
            (success, error_message)
        """
        try:
            if session.status == 'completed':
                return False, "Cannot discard completed session"
            
            session.status = 'discarded'
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to discard session: {str(e)}"
    
    @staticmethod
    def get_session_time_remaining(session: FocusSession) -> int:
        """
        Get remaining time in minutes for a session.
        
        Returns:
            Minutes remaining (0 if expired)
        """
        if not session.end_time:
            return session.duration_minutes
        
        now = TimezoneService.utc_now()
        remaining = session.end_time - now
        
        if remaining.total_seconds() <= 0:
            return 0
        
        return int(remaining.total_seconds() / 60)
    
    @staticmethod
    def extend_session(session: FocusSession, additional_minutes: int) -> tuple[bool, str]:
        """
        Extend a session by additional minutes.
        
        Returns:
            (success, error_message)
        """
        try:
            if session.status not in ['active', 'paused']:
                return False, "Can only extend active or paused sessions"
            
            if additional_minutes < 1 or additional_minutes > 120:
                return False, "Extension must be between 1 and 120 minutes"
            
            if session.end_time:
                session.end_time += timedelta(minutes=additional_minutes)
            else:
                session.end_time = TimezoneService.utc_now() + timedelta(minutes=additional_minutes)
            
            session.duration_minutes += additional_minutes
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to extend session: {str(e)}"
    
    @staticmethod
    def get_today_sessions(user) -> list:
        """Get all sessions for today."""
        today_start, today_end = TimezoneService.get_today_start_end(user)
        return FocusSession.query.filter(
            FocusSession.user_id == user.id,
            FocusSession.created_at >= today_start,
            FocusSession.created_at < today_end
        ).order_by(FocusSession.created_at.desc()).all()
    
    @staticmethod
    def get_active_session(user) -> FocusSession:
        """Get the currently active session for a user."""
        return FocusSession.query.filter_by(
            user_id=user.id,
            status='active'
        ).first()
    
    @staticmethod
    def get_session_stats(user, days_back: int = 30) -> dict:
        """Get deep work statistics for a user."""
        cutoff_date = TimezoneService.utc_now() - timedelta(days=days_back)
        
        sessions = FocusSession.query.filter(
            FocusSession.user_id == user.id,
            FocusSession.created_at >= cutoff_date,
            FocusSession.status == 'completed'
        ).all()
        
        total_sessions = len(sessions)
        total_minutes = sum(s.actual_duration_minutes or 0 for s in sessions)
        early_ends = sum(1 for s in sessions if s.ended_early)
        
        return {
            'total_sessions': total_sessions,
            'total_minutes': total_minutes,
            'average_minutes': total_minutes // total_sessions if total_sessions > 0 else 0,
            'early_ends': early_ends,
            'completion_rate': ((total_sessions - early_ends) / total_sessions * 100) if total_sessions > 0 else 0
        }
