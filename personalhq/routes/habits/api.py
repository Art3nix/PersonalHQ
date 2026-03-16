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
    target_count = request.form.get('target_count', 1, type=int)

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
        target_count=target_count,
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
    description = request.form.get('description', '').strip()
    trigger = request.form.get('trigger', '').strip()
    target_count = request.form.get('target_count', 1, type=int)

    if name and frequency_str and icon:
        habit.name = name.strip()
        habit.icon = icon.strip()
        habit.frequency = HabitFrequency.DAILY if frequency_str == 'DAILY' else HabitFrequency.WEEKLY
        habit.identity_id = identity_id or None
        habit.description = description if description else None
        habit.trigger = trigger if trigger else None
        habit.target_count = target_count

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

@habits_api_bp.route('/<int:habit_id>/log', methods=['POST'])
@login_required
def log_habit_progress(habit_id):
    """Adds a single progress log for a habit on a specific date."""
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error"}, 404

    data = request.get_json() or {}
    target_date_str = data.get('date')
    if target_date_str:
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    else:
        target_date = get_local_today()

    # Simply add a new row every time they click the button
    new_log = HabitLog(habit_id=habit.id, completed_date=target_date)
    db.session.add(new_log)
    db.session.commit()

    recalculate_habit_streaks(habit)
    
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {
        "status": "success", 
        "habit_status": status_str
    }

@habits_api_bp.route('/<int:habit_id>/unlog', methods=['POST'])
@login_required
def unlog_habit_progress(habit_id):
    """Removes the most recent log for a specific date (Undo for target > 1)."""
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error"}, 404

    data = request.get_json() or {}
    target_date_str = data.get('date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else get_local_today()

    # Find the most recently clicked log for this date and delete it
    latest_log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date)\
                               .order_by(HabitLog.logged_at.desc()).first()
    
    if latest_log:
        db.session.delete(latest_log)
        db.session.commit()

    recalculate_habit_streaks(habit)
    
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {"status": "success", "habit_status": status_str}
