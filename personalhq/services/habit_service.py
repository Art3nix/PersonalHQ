"""Module handling the business logic and streak calculations for Habits."""

from datetime import datetime, timedelta
from collections import Counter
from personalhq.extensions import db
from personalhq.models.habits import HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.services.time_service import get_local_today

def recalculate_habit_streaks(habit):
    """Scans all logs and strictly enforces target_count for streaks."""
    logs = db.session.query(HabitLog.completed_date).filter_by(habit_id=habit.id).all()
    log_dates_raw = [log[0] for log in logs]
    
    if not log_dates_raw:
        habit.streak = 0
        habit.last_completed = None
        return

    today = get_local_today()
    current_streak = 0
    valid_dates = []

    if habit.frequency == HabitFrequency.DAILY:
        # Count logs per day. Only keep days where count >= target_count
        date_counts = Counter(log_dates_raw)
        valid_dates = sorted([d for d, c in date_counts.items() if c >= habit.target_count], reverse=True)
        
        if not valid_dates:
            habit.streak = 0
            habit.last_completed = None
            return

        # Check if most recent valid date is today or yesterday
        if (today - valid_dates[0]).days <= 1:
            current_streak = 1
            for i in range(len(valid_dates) - 1):
                if (valid_dates[i] - valid_dates[i+1]).days == 1:
                    current_streak += 1
                else: break

    else: # WEEKLY
        # Group logs by the Monday of their respective week
        week_counts = Counter([d - timedelta(days=d.weekday()) for d in log_dates_raw])
        valid_dates = sorted([w for w, c in week_counts.items() if c >= habit.target_count], reverse=True)
        
        if not valid_dates:
            habit.streak = 0
            habit.last_completed = None
            return
            
        monday_this = today - timedelta(days=today.weekday())
        if (monday_this - valid_dates[0]).days <= 7:
            current_streak = 1
            for i in range(len(valid_dates) - 1):
                if (valid_dates[i] - valid_dates[i+1]).days == 7:
                    current_streak += 1
                else: break

    # Calculate Best Streak based only on valid periods
    best_streak = habit.best_streak or 0
    temp_streak = 1
    
    for i in range(len(valid_dates) - 1):
        diff = (valid_dates[i] - valid_dates[i+1]).days
        if (habit.frequency == HabitFrequency.DAILY and diff == 1) or \
           (habit.frequency == HabitFrequency.WEEKLY and diff == 7):
            temp_streak += 1
        else:
            best_streak = max(best_streak, temp_streak)
            temp_streak = 1

    habit.streak = current_streak
    habit.best_streak = max(best_streak, temp_streak, current_streak)
    habit.last_completed = datetime.combine(valid_dates[0], datetime.min.time())


def get_habit_status_and_sync(habit) -> str:
    """Evaluates current state for the UI styling (COMPLETED, PENDING, EXPIRING, BROKEN)."""
    recalculate_habit_streaks(habit)

    today = get_local_today()
    current_hour = datetime.now().hour

    if habit.frequency == HabitFrequency.DAILY:
        count_today = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).count()
        if count_today >= habit.target_count: return "COMPLETED"

        yesterday = today - timedelta(days=1)
        count_yesterday = HabitLog.query.filter_by(habit_id=habit.id, completed_date=yesterday).count()
        if count_yesterday >= habit.target_count:
            # Streak is alive. Only trigger the visual warning after 8:00 PM.
            if current_hour >= 20: 
                return "EXPIRING"
            return "PENDING"

        return "BROKEN"
    else:
        start_of_week = today - timedelta(days=today.weekday())
        count_this_week = HabitLog.query.filter(
            HabitLog.habit_id == habit.id, HabitLog.completed_date >= start_of_week
        ).count()
        if count_this_week >= habit.target_count: return "COMPLETED"

        start_of_last_week = start_of_week - timedelta(days=7)
        count_last_week = HabitLog.query.filter(
            HabitLog.habit_id == habit.id, 
            HabitLog.completed_date >= start_of_last_week, 
            HabitLog.completed_date < start_of_week
        ).count()
        if count_last_week >= habit.target_count:
            # Streak is alive. Warn only on Sunday after 8:00 PM.
            if today.weekday() == 6 and current_hour >= 20:
                return "EXPIRING"
            return "PENDING"

        return "BROKEN"

def get_habit_current_count(habit) -> int:
    """Fetches the exact progress count for today or this week."""
    today = get_local_today()
    if habit.frequency == HabitFrequency.DAILY:
        return HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).count()
    else:
        start_of_week = today - timedelta(days=today.weekday())
        return HabitLog.query.filter(HabitLog.habit_id == habit.id, HabitLog.completed_date >= start_of_week).count()
