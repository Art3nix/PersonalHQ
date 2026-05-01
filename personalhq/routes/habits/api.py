"""Module defining the API and view routes for Habits."""

from datetime import datetime, timedelta
from flask import Blueprint, request, redirect, url_for, jsonify, flash
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.extensions import db
from personalhq.services.time_service import get_logical_today
from personalhq.services.habit_service import get_habit_status_and_sync, recalculate_habit_streaks

habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/actions/habits')

def _get_date_from_request(data: dict):
    """Safely parse a date from request data, defaulting to today."""
    target_date_str = data.get('date')
    if target_date_str:
        try:
            return datetime.strptime(target_date_str, '%Y-%m-%d').date()
        except ValueError:
            pass
    return get_logical_today(current_user)

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return jsonify({"status": "error"}), 404

    data = request.get_json() or {}
    target_date = _get_date_from_request(data)

    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()

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

    return jsonify({
        "status": "success",
        "streak": habit.streak,
        "best": habit.best_streak,
        "habit_status": status_str,
        "progress": log.progress,
        "target": habit.target_count,
        "ai_insight": habit.ai_celebration if log.progress >= habit.target_count else habit.ai_insight
    })

@habits_api_bp.route('/create', methods=['POST'])
@login_required
def create_habit():
    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')
    description = request.form.get('description')
    trigger = request.form.get('trigger')
    target_count = request.form.get('target_count', 1, type=int)
    target_count = request.form.get('target_count', 1, type=int)
    
    # SECURITY PATCH: Cap the streak at 10,000 (roughly 27 years)
    raw_streak = request.form.get('initial_streak', 0, type=int)
    initial_streak = min(raw_streak, 10000) 

    if not name or not frequency_str or not icon:
        return redirect(url_for('habits_view.manage'))

    frequency = HabitFrequency.DAILY if frequency_str == 'DAILY' else HabitFrequency.WEEKLY
    identity_id = request.form.get('identity_id', type=int)

    craving = request.form.get('craving', '').strip()
    reward = request.form.get('reward', '').strip()

    new_habit = Habit(
        user_id=current_user.id,
        name=name.strip(),
        icon=icon.strip(),
        frequency=frequency,
        identity_id=identity_id,
        streak=initial_streak,
        best_streak=initial_streak,
        target_count=target_count,
        description=description.strip() if description else None,
        trigger=trigger.strip() if trigger else None,
        craving=craving if craving else None,
        reward=reward if reward else None,
    )

    db.session.add(new_habit)
    db.session.flush() # Get the new_habit.id without closing the transaction!

    # Generate historical logs so the streak engine finds them naturally
    if initial_streak > 0:
        today = get_logical_today(current_user)
        
        for i in range(1, initial_streak + 1):
            # Step backward by Days or Weeks depending on the frequency
            delta = timedelta(days=i) if frequency == HabitFrequency.DAILY else timedelta(weeks=i)
            past_date = today - delta
            
            backfill_log = HabitLog(
                habit_id=new_habit.id,
                completed_date=past_date,
                progress=target_count,      # Instantly mark as 100% complete
                target_at_time=target_count
            )
            db.session.add(backfill_log)

    # Save the habit AND the backfilled logs to the database all at once
    db.session.commit()
    flash(f'Habit "{new_habit.name}" created successfully.', 'success')
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
        craving = request.form.get('craving', '').strip()
        reward = request.form.get('reward', '').strip()
        habit.craving = craving if craving else None
        habit.reward = reward if reward else None
        db.session.commit()
        flash(f'"{habit.name}" updated.', 'success')

    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/<int:habit_id>/delete', methods=['POST'])
@login_required
def delete_habit(habit_id):
    habit = db.session.get(Habit, habit_id)
    if habit and habit.user_id == current_user.id:
        name = habit.name
        db.session.delete(habit)
        db.session.commit()
        flash(f'"{name}" deleted.', 'success')
    return redirect(url_for('habits_view.manage'))

@habits_api_bp.route('/<int:habit_id>/log', methods=['POST'])
@login_required
def log_habit_progress(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return jsonify({"status": "error"}), 404

    data = request.get_json() or {}
    target_date = _get_date_from_request(data)

    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()

    if not log:
        log = HabitLog(habit_id=habit.id, completed_date=target_date, progress=0, target_at_time=habit.target_count)
        db.session.add(log)

    log.progress += 1
    db.session.commit()

    recalculate_habit_streaks(habit)
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "streak": habit.streak,
        "best": habit.best_streak,
        "habit_status": status_str,
        "progress": log.progress,
        "target": habit.target_count,
        "ai_insight": habit.ai_celebration if log.progress >= habit.target_count else habit.ai_insight
    })

@habits_api_bp.route('/<int:habit_id>/unlog', methods=['POST'])
@login_required
def unlog_habit_progress(habit_id):
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return jsonify({"status": "error"}), 404

    data = request.get_json() or {}
    target_date = _get_date_from_request(data)

    log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=target_date).first()

    if not log:
        log = HabitLog(habit_id=habit.id, completed_date=target_date, progress=0, target_at_time=habit.target_count)
        db.session.add(log)

    log.progress = max(0, log.progress - 1)
    db.session.commit()

    recalculate_habit_streaks(habit)
    status_str = get_habit_status_and_sync(habit)
    db.session.commit()

    return jsonify({
        "status": "success",
        "streak": habit.streak,
        "best": habit.best_streak,
        "habit_status": status_str,
        "progress": log.progress,
        "target": habit.target_count,
        "ai_insight": habit.ai_celebration if log.progress >= habit.target_count else habit.ai_insight
    })

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
