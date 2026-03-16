"""Module defining the API and view routes for Habits."""

from datetime import datetime
from flask import Blueprint, request, redirect, url_for
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.extensions import db
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import get_habit_status_and_sync, recalculate_habit_streaks

# We use the /actions/ namespace for the interactive JSON routes
habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/actions/habits')

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error"}, 404

    # Get target date from JSON (allows historical logging)
    data = request.get_json() or {}
    target_date_str = data.get('date')
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        target_date = get_local_today()

    # 1. Add or Remove the log for that specific day
    existing_log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()
    if existing_log:
        db.session.delete(existing_log)
    else:
        db.session.add(HabitLog(habit_id=habit.id, completed_date=target_date))

    db.session.commit()

    recalculate_habit_streaks(habit)

    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {
        "status": "success", 
        "streak": habit.streak, 
        "best": habit.best_streak, 
        "habit_status": status_str
    }

@habits_api_bp.route('/create', methods=['POST'])
@login_required
def create_habit():
    """Receives form data to create a new habit and redirects back to the management page."""
    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')
    description = request.form.get('description')
    trigger = request.form.get('trigger')

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
        streak=0,
        description=description.strip() if description else None,
        trigger=trigger.strip() if trigger else None
    )

    db.session.add(new_habit)
    db.session.commit()

    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/<int:habit_id>/edit', methods=['POST'])
@login_required
def edit_habit(habit_id):
    """Updates an existing habit's details."""
    habit = db.session.get(Habit, habit_id)
    
    if not habit or habit.user_id != current_user.id:
        return redirect(url_for('habits_view.manage'))

    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')
    identity_id = request.form.get('identity_id', type=int)
    description = request.form.get('description')
    trigger = request.form.get('trigger')

    if name and frequency_str and icon:
        habit.name = name.strip()
        habit.icon = icon.strip()
        habit.frequency = HabitFrequency.DAILY if frequency_str == 'DAILY' else HabitFrequency.WEEKLY
        # If identity_id is 0 or empty, it sets it to None (Unassigned)
        habit.identity_id = identity_id or None,
        description=description.strip() if description else None,
        trigger=trigger.strip() if trigger else None
        
        db.session.commit()

    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    """Deletes a habit and all associated logs via cascade."""
    habit = db.session.get(Habit, habit_id)
    
    # Security check to ensure users can only delete their own habits
    if habit and habit.user_id == current_user.id:
        db.session.delete(habit)
        db.session.commit()
        
    return redirect(url_for('habits_view.manage'))
