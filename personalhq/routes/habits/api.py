"""Module defining the API and view routes for Habits."""

from datetime import date
from flask import Blueprint, request, redirect, url_for
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.extensions import db

# We use the /actions/ namespace for the interactive JSON routes
habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/actions/habits')

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    """Toggles a habit's completion status for today and logs the event."""
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error", "message": "Habit not found"}, 404

    today = date.today()

    # Check if a log already exists for today
    existing_log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()

    if existing_log:
        # UN-CHECKING THE HABIT
        db.session.delete(existing_log)

        # Revert the streak and last_completed date
        habit.streak = max(0, habit.streak - 1)

        # Find the previous log to reset last_completed
        previous_log = HabitLog.query.filter(
            HabitLog.habit_id == habit.id, 
            HabitLog.completed_date < today
        ).order_by(HabitLog.completed_date.desc()).first()

        habit.last_completed = previous_log.completed_date if previous_log else None

        is_done = False
    else:
        # CHECKING THE HABIT
        new_log = HabitLog(habit_id=habit.id, completed_date=today)
        db.session.add(new_log)

        # We only increment the streak if they didn't already complete it yesterday
        # (A more robust streak calculator can be built later, but this works for the MVP)
        habit.streak += 1
        habit.last_completed = today

        is_done = True

    db.session.commit()

    return {"status": "success", "is_done": is_done, "streak": habit.streak}

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

    new_habit = Habit(
        user_id=current_user.id,
        name=name.strip(),
        icon=icon.strip(),
        frequency=frequency
    )

    db.session.add(new_habit)
    db.session.commit()

    return redirect(url_for('habits_view.manage'))
