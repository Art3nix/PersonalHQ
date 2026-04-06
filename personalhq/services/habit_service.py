"""Module handling the business logic and streak calculations for Habits."""

from datetime import datetime, timedelta, timezone
from collections import defaultdict
from zoneinfo import ZoneInfo
from personalhq.extensions import db
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.users import User
from personalhq.models.habit_logs import HabitLog
from personalhq.services.time_service import get_logical_today, get_local_now


# ---------------------------------------------------------------------------
# STREAK RECALCULATION  (write path only — called after a log toggle)
# ---------------------------------------------------------------------------

def recalculate_habit_streaks(habit, logs=None):
    """
    Recomputes streak from log history.  Only call this after a write.
    Optionally pass pre-fetched logs to avoid an extra query.
    """
    if logs is None:
        logs = HabitLog.query.filter_by(habit_id=habit.id).all()

    if not logs:
        habit.streak = 0
        habit.last_completed = None
        return

    today = get_logical_today(habit.user)
    valid_dates = []

    if habit.frequency == HabitFrequency.DAILY:
        valid_dates = sorted(
            [l.completed_date for l in logs if l.progress >= l.target_at_time],
            reverse=True
        )
        if not valid_dates:
            habit.streak = 0
            habit.last_completed = None
            return

        current_streak = 0
        if (today - valid_dates[0]).days <= 1:
            current_streak = 1
            for i in range(len(valid_dates) - 1):
                if (valid_dates[i] - valid_dates[i + 1]).days == 1:
                    current_streak += 1
                else:
                    break

    else:  # WEEKLY
        week_progress = defaultdict(int)
        week_targets = {}
        for l in logs:
            monday = l.completed_date - timedelta(days=l.completed_date.weekday())
            week_progress[monday] += l.progress
            week_targets[monday] = l.target_at_time

        valid_dates = sorted(
            [w for w, prog in week_progress.items()
             if prog >= week_targets.get(w, habit.target_count)],
            reverse=True
        )
        if not valid_dates:
            habit.streak = 0
            habit.last_completed = None
            return

        monday_this = today - timedelta(days=today.weekday())
        current_streak = 0
        if (monday_this - valid_dates[0]).days <= 7:
            current_streak = 1
            for i in range(len(valid_dates) - 1):
                if (valid_dates[i] - valid_dates[i + 1]).days == 7:
                    current_streak += 1
                else:
                    break

    # Best streak - MUST start at 0 to allow downgrades when unlogging!
    best_streak = 0
    temp_streak = 1

    if valid_dates:
        for i in range(len(valid_dates) - 1):
            diff = (valid_dates[i] - valid_dates[i + 1]).days
            expected = 1 if habit.frequency == HabitFrequency.DAILY else 7
            if diff == expected:
                temp_streak += 1
            else:
                best_streak = max(best_streak, temp_streak)
                temp_streak = 1

    habit.streak = current_streak
    habit.best_streak = max(best_streak, temp_streak, current_streak)
    if valid_dates:
        habit.last_completed = datetime.combine(valid_dates[0], datetime.min.time())
    else:
        habit.last_completed = None


# ---------------------------------------------------------------------------
# STATUS — read path, uses pre-fetched log dict, NO streak recalc
# ---------------------------------------------------------------------------

def get_habit_status(habit, logs_by_date: dict) -> str:
    """
    Returns COMPLETED / PENDING / EXPIRING / BROKEN.
    logs_by_date: {date: HabitLog} — pre-fetched for this habit, no DB calls.
    Streak is read directly from the model (written by recalculate_habit_streaks).
    """
    today = get_logical_today(habit.user)
    current_hour = get_local_now().hour

    if habit.frequency == HabitFrequency.DAILY:
        log_today = logs_by_date.get(today)
        if log_today and log_today.progress >= habit.target_count:
            return "COMPLETED"
        yesterday = today - timedelta(days=1)
        log_yesterday = logs_by_date.get(yesterday)
        if log_yesterday and log_yesterday.progress >= habit.target_count:
            return "EXPIRING" if current_hour >= 20 else "PENDING"
        return "BROKEN"
    else:
        start_of_week = today - timedelta(days=today.weekday())
        week_logs = [l for d, l in logs_by_date.items() if d >= start_of_week]
        if sum(l.progress for l in week_logs) >= habit.target_count:
            return "COMPLETED"
        start_of_last_week = start_of_week - timedelta(days=7)
        last_week_logs = [l for d, l in logs_by_date.items()
                          if start_of_last_week <= d < start_of_week]
        if sum(l.progress for l in last_week_logs) >= habit.target_count:
            return "EXPIRING" if (today.weekday() == 6 and current_hour >= 20) else "PENDING"
        return "BROKEN"


# Keep the old signature for any call sites we haven't updated yet
def get_habit_status_and_sync(habit) -> str:
    """Legacy wrapper — still works but fires individual queries. Prefer get_habit_status()."""
    recalculate_habit_streaks(habit)

    today = get_logical_today(habit.user)
    current_hour = get_local_now().hour

    if habit.frequency == HabitFrequency.DAILY:
        log_today = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
        if log_today and log_today.progress >= habit.target_count:
            return "COMPLETED"
        yesterday = today - timedelta(days=1)
        log_yesterday = HabitLog.query.filter_by(habit_id=habit.id, completed_date=yesterday).first()
        if log_yesterday and log_yesterday.progress >= habit.target_count:
            return "EXPIRING" if current_hour >= 20 else "PENDING"
        return "BROKEN"
    else:
        start_of_week = today - timedelta(days=today.weekday())
        logs_this_week = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed_date >= start_of_week
        ).all()
        if sum(l.progress for l in logs_this_week) >= habit.target_count:
            return "COMPLETED"
        start_of_last_week = start_of_week - timedelta(days=7)
        logs_last_week = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed_date >= start_of_last_week,
            HabitLog.completed_date < start_of_week
        ).all()
        if sum(l.progress for l in logs_last_week) >= habit.target_count:
            return "EXPIRING" if (today.weekday() == 6 and current_hour >= 20) else "PENDING"
        return "BROKEN"


def get_habit_current_count(habit) -> int:
    today = get_logical_today(habit.user)
    if habit.frequency == HabitFrequency.DAILY:
        log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()
        return log.progress if log else 0
    else:
        start_of_week = today - timedelta(days=today.weekday())
        logs = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed_date >= start_of_week
        ).all()
        return sum(l.progress for l in logs)


# ---------------------------------------------------------------------------
# BULK HELPERS — load all logs for multiple habits in ONE query
# ---------------------------------------------------------------------------

def bulk_load_recent_logs(user, habit_ids: list, days_back: int = 14) -> dict:
    """
    Returns {habit_id: {date: HabitLog}} for the last `days_back` days.
    ONE database query for all habits combined.
    """
    if not habit_ids:
        return {}

    today = get_logical_today(user)
    since = today - timedelta(days=days_back)

    rows = HabitLog.query.filter(
        HabitLog.habit_id.in_(habit_ids),
        HabitLog.completed_date >= since
    ).all()

    result = {hid: {} for hid in habit_ids}
    for log in rows:
        result[log.habit_id][log.completed_date] = log
    return result


# ---------------------------------------------------------------------------
# DAILY LEDGER CATCHUP — gated so it only runs once per day per user
# ---------------------------------------------------------------------------

# In-process cache: {user_id: date_last_run}
_ledger_last_run: dict = {}


def run_daily_ledger_catchup(user_id: int):
    """
    Fills in missing zero-progress log rows for the last 30 days.
    Skipped if already run today for this user (in-process cache).
    On a multi-worker deployment, worst case it runs once per worker per day.
    """
    today = get_logical_today(db.session.get(User, user_id))

    # Skip if already ran today for this user
    if _ledger_last_run.get(user_id) == today:
        return

    _ledger_last_run[user_id] = today

    limit_date = today - timedelta(days=30)
    active_habits = Habit.query.filter_by(user_id=user_id, is_active=True).all()
    if not active_habits:
        return

    habit_ids = [h.id for h in active_habits]

    # ONE query: all existing log dates for all habits
    existing = HabitLog.query.filter(
        HabitLog.habit_id.in_(habit_ids),
        HabitLog.completed_date >= limit_date
    ).with_entities(HabitLog.habit_id, HabitLog.completed_date).all()

    existing_set = set(existing)  # {(habit_id, date), ...}

    new_logs = []
    target_map = {h.id: h.target_count for h in active_habits}
    # Create a helper block to safely translate the creation date
    user = db.session.get(User, user_id)
    created_map = {}

    for h in active_habits:
        if h.created_at:
            # Convert the UTC created_at timestamp into the user's logical date
            user_zone = ZoneInfo(user.timezone or "UTC")
            aware_utc = h.created_at.replace(tzinfo=timezone.utc)
            local_created = aware_utc.astimezone(user_zone)
            
            # Apply the offset midnight logic to the creation timestamp
            if local_created.hour < user.day_reset_hour:
                created_map[h.id] = (local_created - timedelta(days=1)).date()
            else:
                created_map[h.id] = local_created.date()
        else:
            created_map[h.id] = limit_date

    for habit in active_habits:
        start_date = max(limit_date, created_map[habit.id])
        current = start_date
        while current <= today:
            if (habit.id, current) not in existing_set:
                new_logs.append(HabitLog(
                    habit_id=habit.id,
                    completed_date=current,
                    progress=0,
                    target_at_time=target_map[habit.id]
                ))
            current += timedelta(days=1)

    if new_logs:
        db.session.bulk_save_objects(new_logs)
        db.session.commit()
