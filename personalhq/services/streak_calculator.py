"""Service for calculating habit streaks and tracking."""

from datetime import datetime, timedelta
import pytz
from personalhq.services.timezone_service import TimezoneService


class StreakCalculator:
    """Calculates consecutive day streaks for habits."""
    
    @staticmethod
    def calculate_current_streak(habit_logs: list, user) -> int:
        """
        Calculate current consecutive day streak.
        
        Args:
            habit_logs: List of HabitLog objects sorted by date (newest first)
            user: User object for timezone
            
        Returns:
            Current streak count (consecutive days)
        """
        if not habit_logs:
            return 0
        
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        streak = 0
        today = TimezoneService.utc_now().astimezone(tz).date()
        
        for i, log in enumerate(habit_logs):
            log_date = log.date_logged.astimezone(tz).date() if log.date_logged.tzinfo else log.date_logged.date()
            expected_date = today - timedelta(days=i)
            
            if log_date == expected_date:
                streak += 1
            else:
                break
        
        return streak
    
    @staticmethod
    def calculate_best_streak(habit_logs: list, user) -> int:
        """
        Calculate best consecutive day streak ever.
        
        Args:
            habit_logs: List of HabitLog objects sorted by date (oldest first)
            user: User object for timezone
            
        Returns:
            Best streak count
        """
        if not habit_logs:
            return 0
        
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        best_streak = 0
        current_streak = 0
        last_date = None
        
        # Sort by date ascending (oldest first)
        sorted_logs = sorted(habit_logs, key=lambda x: x.date_logged)
        
        for log in sorted_logs:
            log_date = log.date_logged.astimezone(tz).date() if log.date_logged.tzinfo else log.date_logged.date()
            
            if last_date is None:
                current_streak = 1
            elif log_date == last_date + timedelta(days=1):
                current_streak += 1
            else:
                # Streak broken
                best_streak = max(best_streak, current_streak)
                current_streak = 1
            
            last_date = log_date
        
        # Don't forget the last streak
        best_streak = max(best_streak, current_streak)
        
        return best_streak
    
    @staticmethod
    def is_streak_active(habit_logs: list, user) -> bool:
        """
        Check if habit has an active streak (logged today or yesterday).
        
        Args:
            habit_logs: List of HabitLog objects
            user: User object for timezone
            
        Returns:
            True if streak is active
        """
        if not habit_logs:
            return False
        
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        today = TimezoneService.utc_now().astimezone(tz).date()
        yesterday = today - timedelta(days=1)
        
        latest_log = habit_logs[0]  # Assuming sorted by newest first
        log_date = latest_log.date_logged.astimezone(tz).date() if latest_log.date_logged.tzinfo else latest_log.date_logged.date()
        
        return log_date in [today, yesterday]
    
    @staticmethod
    def days_until_streak_breaks(habit_logs: list, user) -> int:
        """
        Calculate days until streak breaks if not logged.
        
        Args:
            habit_logs: List of HabitLog objects
            user: User object for timezone
            
        Returns:
            Days until streak breaks (0 if today, 1 if tomorrow, etc.)
        """
        if not habit_logs:
            return 0
        
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        today = TimezoneService.utc_now().astimezone(tz).date()
        
        latest_log = habit_logs[0]
        log_date = latest_log.date_logged.astimezone(tz).date() if latest_log.date_logged.tzinfo else latest_log.date_logged.date()
        
        if log_date == today:
            return 1  # Must log tomorrow
        elif log_date == today - timedelta(days=1):
            return 0  # Must log today
        else:
            return -1  # Streak already broken
    
    @staticmethod
    def get_streak_status(habit_logs: list, user) -> dict:
        """
        Get comprehensive streak information.
        
        Returns:
            {
                'current': int,
                'best': int,
                'is_active': bool,
                'days_until_break': int
            }
        """
        return {
            'current': StreakCalculator.calculate_current_streak(habit_logs, user),
            'best': StreakCalculator.calculate_best_streak(habit_logs, user),
            'is_active': StreakCalculator.is_streak_active(habit_logs, user),
            'days_until_break': StreakCalculator.days_until_streak_breaks(habit_logs, user)
        }
    
    @staticmethod
    def get_missing_days(habit_logs: list, user, days_back: int = 30) -> list:
        """
        Get list of days in the past N days that were missed.
        
        Args:
            habit_logs: List of HabitLog objects
            user: User object for timezone
            days_back: How many days back to check
            
        Returns:
            List of dates that were missed
        """
        tz = pytz.timezone(TimezoneService.get_user_timezone(user))
        today = TimezoneService.utc_now().astimezone(tz).date()
        
        # Get all logged dates
        logged_dates = set()
        for log in habit_logs:
            log_date = log.date_logged.astimezone(tz).date() if log.date_logged.tzinfo else log.date_logged.date()
            if (today - log_date).days <= days_back:
                logged_dates.add(log_date)
        
        # Find missing dates
        missing = []
        for i in range(days_back):
            check_date = today - timedelta(days=i)
            if check_date not in logged_dates:
                missing.append(check_date)
        
        return sorted(missing)
