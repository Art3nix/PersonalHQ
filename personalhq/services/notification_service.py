"""Service layer for managing user notifications and reminders."""

from datetime import datetime
from enum import Enum
from personalhq.extensions import db
from personalhq.models.users import User


class NotificationType(Enum):
    """Types of notifications the system can send."""
    HABIT_REMINDER = "habit_reminder"
    HABIT_EXPIRING = "habit_expiring"
    FOCUS_COMPLETE = "focus_complete"
    STREAK_BROKEN = "streak_broken"
    ACHIEVEMENT = "achievement"
    SYSTEM_MESSAGE = "system_message"


def send_notification(user_id: int, notification_type: NotificationType, 
                     title: str, message: str, data: dict = None) -> dict:
    """
    Send a notification to a user.
    In MVP, notifications are stored in-memory/session.
    Later: integrate with WebSocket, email, or push notifications.
    """
    user = db.session.get(User, user_id)
    if not user:
        return {"status": "error", "message": "User not found"}
    
    notification = {
        "id": datetime.utcnow().timestamp(),
        "type": notification_type.value,
        "title": title,
        "message": message,
        "data": data or {},
        "created_at": datetime.utcnow().isoformat(),
        "read": False
    }
    
    # TODO: Store in database or cache for persistence
    # For now, this is a placeholder for future implementation
    
    return {"status": "success", "notification": notification}


def send_habit_reminder(user_id: int, habit_name: str, identity_name: str = None) -> dict:
    """Send a reminder to complete a habit."""
    message = f"Time to reinforce your identity by completing {habit_name}."
    if identity_name:
        message = f"As {identity_name}, complete {habit_name} to reinforce your identity."
    
    return send_notification(
        user_id,
        NotificationType.HABIT_REMINDER,
        f"Complete {habit_name}",
        message,
        {"habit_name": habit_name, "identity": identity_name}
    )


def send_habit_expiring_warning(user_id: int, habit_name: str, days_until_break: int = 1) -> dict:
    """Warn user that a habit streak is about to break."""
    return send_notification(
        user_id,
        NotificationType.HABIT_EXPIRING,
        f"{habit_name} streak expiring!",
        f"You haven't completed {habit_name} today. Missing tomorrow will break your streak.",
        {"habit_name": habit_name, "days_until_break": days_until_break}
    )


def send_streak_broken_notification(user_id: int, habit_name: str, streak_length: int) -> dict:
    """Notify user that a streak has been broken."""
    return send_notification(
        user_id,
        NotificationType.STREAK_BROKEN,
        f"{habit_name} streak broken",
        f"Your {streak_length}-day streak on {habit_name} has ended. Nobody is perfect. Missing twice is a new habit—let's restart.",
        {"habit_name": habit_name, "streak_length": streak_length}
    )


def send_focus_complete_notification(user_id: int, session_name: str, 
                                    duration_minutes: int, identity_name: str = None) -> dict:
    """Congratulate user on completing a focus session."""
    message = f"You completed {duration_minutes} minutes of deep work on {session_name}."
    if identity_name:
        message = f"As {identity_name}, you completed {duration_minutes} minutes of deep work. Excellent!"
    
    return send_notification(
        user_id,
        NotificationType.FOCUS_COMPLETE,
        "Deep work session complete!",
        message,
        {"session_name": session_name, "duration": duration_minutes, "identity": identity_name}
    )


def send_achievement_notification(user_id: int, achievement_name: str, description: str) -> dict:
    """Send an achievement/milestone notification."""
    return send_notification(
        user_id,
        NotificationType.ACHIEVEMENT,
        f"🎉 {achievement_name}",
        description,
        {"achievement": achievement_name}
    )


def send_system_message(user_id: int, title: str, message: str) -> dict:
    """Send a system-wide message to a user."""
    return send_notification(
        user_id,
        NotificationType.SYSTEM_MESSAGE,
        title,
        message
    )
