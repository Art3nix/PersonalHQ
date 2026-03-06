"""Module defining the API and view routes for Habits."""

from datetime import datetime
from flask import Blueprint, request, redirect, url_for
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.extensions import db
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import get_habit_status_and_sync

# We use the /actions/ namespace for the interactive JSON routes
habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/actions/habits')

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    """Toggles a habit's completion status for today and logs the event."""
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error", "message": "Habit not found"}, 404

    today = get_local_today()

    # Check if a log already exists for today
    existing_log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()

    if existing_log:
        # UN-CHECKING THE HABIT
        db.session.delete(existing_log)

        # Revert the streak and last_completed date
        habit.streak = max(0, (habit.streak or 0) - 1)

        # Find the previous log to reset last_completed
        previous_log = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed_date < today
        ).order_by(HabitLog.completed_date.desc()).first()

        if previous_log:
            # Revert last_completed to the previous log's date
            habit.last_completed = datetime.combine(previous_log.completed_date, datetime.min.time())
        else:
            habit.last_completed = None

        is_done = False
    else:
        # CHECKING THE HABIT
        new_log = HabitLog(habit_id=habit.id, completed_date=today)
        db.session.add(new_log)

        # STREAK LOGIC
        if habit.frequency == HabitFrequency.DAILY:
            # If completed exactly yesterday, increment. Otherwise, reset to 1.
            if habit.last_completed and (today - habit.last_completed.date()).days == 1:
                habit.streak = (habit.streak or 0) + 1
            else:
                habit.streak = 1
        else:
            # WEEKLY LOGIC
            if habit.last_completed:
                last_week = habit.last_completed.date().isocalendar()[:2]
                this_week = today.isocalendar()[:2]
                
                if last_week == this_week:
                    # They checked a weekly habit twice in the same week. Maintain streak.
                    pass 
                elif (today - habit.last_completed.date()).days <= 14:
                    # Completed last week, so increment streak.
                    habit.streak = (habit.streak or 0) + 1
                else:
                    # Streak broken
                    habit.streak = 1
            else:
                habit.streak = 1

        habit.last_completed = today
        is_done = True

    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {"status": "success", "streak": habit.streak, "habit_status": status_str}

@habits_api_bp.route('/create', methods=['POST'])
@login_required
def create_habit():
    """Receives form data to create a new habit and redirects back to the management page."""
    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')

    # Validation check
    if not name or not frequency_str or not icon:
        return redirect(url_for('habits_view.manage'))

    frequency = HabitFrequency.DAILY if frequency_str == 'DAILY' else HabitFrequency.WEEKLY

    identity_id = request.form.get('identity_id', type=int)

    new_habit = Habit(
        user_id=current_user.id,
        name=name.strip(),
        icon=icon.strip(),
        frequency=frequency,
        identity_id=identity_id,
        streak=0
    )

    db.session.add(new_habit)
    db.session.commit()

    return redirect(url_for('habits_view.manage'))
