"""Service for handling timezone conversions and date/time utilities."""

from datetime import datetime, timedelta
import pytz
from flask import current_app


class TimezoneService:
    """Handles timezone conversions and date/time operations."""
    
    DEFAULT_TIMEZONE = 'UTC'
    
    @staticmethod
    def get_user_timezone(user) -> str:
        """Get user's timezone from preferences or default."""
        if hasattr(user, 'timezone') and user.timezone:
            return user.timezone
        return TimezoneService.DEFAULT_TIMEZONE
    
    @staticmethod
    def set_user_timezone(user, timezone: str) -> bool:
        """Set user's timezone preference."""
        try:
            pytz.timezone(timezone)
            user.timezone = timezone
            return True
        except pytz.exceptions.UnknownTimeZoneError:
            return False
    
    @staticmethod
    def utc_now() -> datetime:
        """Get current UTC time."""
        return datetime.now(pytz.UTC)
    
    @staticmethod
    def user_now(user) -> datetime:
        """Get current time in user's timezone."""
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        return TimezoneService.utc_now().astimezone(tz)
    
    @staticmethod
    def to_utc(dt: datetime, user_timezone: str = None) -> datetime:
        """Convert datetime to UTC."""
        if dt.tzinfo is None:
            # Assume user timezone if naive
            if user_timezone:
                tz = pytz.timezone(user_timezone)
                dt = tz.localize(dt)
            else:
                dt = pytz.UTC.localize(dt)
        return dt.astimezone(pytz.UTC)
    
    @staticmethod
    def to_user_timezone(dt: datetime, user_timezone: str) -> datetime:
        """Convert UTC datetime to user's timezone."""
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        tz = pytz.timezone(user_timezone)
        return dt.astimezone(tz)
    
    @staticmethod
    def get_today_start_end(user) -> tuple:
        """Get start and end of today in user's timezone (as UTC)."""
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        user_now = TimezoneService.utc_now().astimezone(tz)
        
        # Start of today in user's timezone
        today_start = tz.localize(datetime(user_now.year, user_now.month, user_now.day, 0, 0, 0))
        today_end = today_start + timedelta(days=1)
        
        # Convert to UTC
        return today_start.astimezone(pytz.UTC), today_end.astimezone(pytz.UTC)
    
    @staticmethod
    def is_today(dt: datetime, user) -> bool:
        """Check if datetime is today in user's timezone."""
        today_start, today_end = TimezoneService.get_today_start_end(user)
        
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        return today_start <= dt < today_end
    
    @staticmethod
    def days_since(dt: datetime, user) -> int:
        """Calculate days since datetime in user's timezone."""
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        dt_user = dt.astimezone(tz)
        now_user = TimezoneService.utc_now().astimezone(tz)
        
        return (now_user.date() - dt_user.date()).days
    
    @staticmethod
    def format_for_user(dt: datetime, user, format_str: str = '%Y-%m-%d %H:%M') -> str:
        """Format datetime for user's timezone."""
        if dt.tzinfo is None:
            dt = pytz.UTC.localize(dt)
        
        user_tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        dt_user = dt.astimezone(user_tz)
        return dt_user.strftime(format_str)
    
    @staticmethod
    def get_age_at_date(birth_date: datetime, target_date: datetime = None) -> int:
        """Calculate age at a given date."""
        if target_date is None:
            target_date = datetime.now()
        
        age = target_date.year - birth_date.year
        if (target_date.month, target_date.day) < (birth_date.month, birth_date.day):
            age -= 1
        return age
    
    @staticmethod
    def get_days_until(target_date: datetime, user) -> int:
        """Calculate days until a target date."""
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        now = TimezoneService.utc_now().astimezone(tz)
        
        if target_date.tzinfo is None:
            target_date = tz.localize(target_date)
        else:
            target_date = target_date.astimezone(tz)
        
        delta = target_date.date() - now.date()
        return delta.days
