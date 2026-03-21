"""Module defining the API and view routes for Habits."""

from datetime import datetime
from flask import Blueprint, request, redirect, url_for
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.extensions import db
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import get_habit_status_and_sync, recalculate_habit_streaks

habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/actions/habits')

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error"}, 404

    data = request.get_json() or {}
    target_date_str = data.get('date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else get_local_today()

    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()
    
    # SAFETY NET: Create if missing
    if not log:
        log = HabitLog(habit_id=habit.id, completed_date=target_date, progress=0, target_at_time=habit.target_count)
        db.session.add(log)
    
    if log.progress >= log.target_at_time:
        log.progress = 0
    else:
        log.progress = log.target_at_time
        
    db.session.commit()
    recalculate_habit_streaks(habit)
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {"status": "success", "streak": habit.streak, "best": habit.best_streak, "habit_status": status_str}

@habits_api_bp.route('/create', methods=['POST'])
@login_required
def create_habit():
    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')
    description = request.form.get('description')
    trigger = request.form.get('trigger')
    target_count = request.form.get('target_count', 1, type=int)

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
    habit = db.session.get(Habit, habit_id)
    if habit and habit.user_id == current_user.id:
        db.session.delete(habit)
        db.session.commit()
    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/<int:habit_id>/log', methods=['POST'])
@login_required
def log_habit_progress(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error"}, 404

    data = request.get_json() or {}
    target_date_str = data.get('date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else get_local_today()

    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()
    
    # SAFETY NET: Create if missing
    if not log:
        log = HabitLog(habit_id=habit.id, completed_date=target_date, progress=0, target_at_time=habit.target_count)
        db.session.add(log)
        
    log.progress += 1
    db.session.commit()

    recalculate_habit_streaks(habit)
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {"status": "success", "streak": habit.streak, "best": habit.best_streak, "habit_status": status_str}

@habits_api_bp.route('/<int:habit_id>/unlog', methods=['POST'])
@login_required
def unlog_habit_progress(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error"}, 404

    data = request.get_json() or {}
    target_date_str = data.get('date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else get_local_today()

    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()
    
    # SAFETY NET: Create if missing
    if not log:
        log = HabitLog(habit_id=habit.id, completed_date=target_date, progress=0, target_at_time=habit.target_count)
        db.session.add(log)
        
    log.progress = max(0, log.progress - 1)
    db.session.commit()

    recalculate_habit_streaks(habit)
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return {"status": "success", "streak": habit.streak, "best": habit.best_streak, "habit_status": status_str}

@habits_api_bp.route('/<int:habit_id>/archive', methods=['POST'])
@login_required
def archive_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if habit and habit.user_id == current_user.id:
        habit.is_active = False
        db.session.commit()
    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/<int:habit_id>/unarchive', methods=['POST'])
@login_required
def unarchive_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if habit and habit.user_id == current_user.id:
        habit.is_active = True
        db.session.commit()
    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_habits():
    """Catches the new drag-and-drop order and updates the database."""
    data = request.get_json() or {}
    ordered_ids = data.get('order', [])
    
    if not ordered_ids:
        return {"status": "error", "message": "No order provided"}, 400
        
    # Fetch only the habits belonging to this user that are in the list
    habits = Habit.query.filter(
        Habit.user_id == current_user.id,
        Habit.id.in_(ordered_ids)
    ).all()
    
    # Create a fast lookup map
    habit_map = {h.id: h for h in habits}
    
    # Loop through the array and assign the new index as the sort_order
    for index, h_id_str in enumerate(ordered_ids):
        h_id = int(h_id_str)
        if h_id in habit_map:
            habit_map[h_id].sort_order = index
            
    db.session.commit()
    return {"status": "success"}
