"""Unified Habits API routes - handles both legacy and modern endpoints."""

from datetime import datetime
from flask import Blueprint, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.habit_logs import HabitLog
from personalhq.extensions import db
from personalhq.services.time_service import get_local_today
from personalhq.services.habit_service import (
    get_habit_status_and_sync, toggle_habit as toggle_habit_service,
    create_habit, update_habit, delete_habit, log_habit, unlog_habit,
    get_streak_info, get_all_habits, toggle_habit_active
)
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

# Blueprint for legacy /actions/ endpoints
habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/api/v1/habits')

# Blueprint for modern /api/v2/ endpoints
habits_api_v2_bp = Blueprint('habits_api_v2', __name__, url_prefix='/api/v2/habits')


# ============================================================================
# LEGACY ENDPOINTS (BACKWARD COMPATIBILITY)
# ============================================================================

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
    """
    DEPRECATED: Toggles a habit's completion status for today and logs the event.
    Use POST /api/v2/habits/<id>/log instead.
    """
    habit = db.session.get(Habit, habit_id)
    if not habit or habit.user_id != current_user.id:
        return {"status": "error", "message": "Habit not found"}, 404

    today = get_local_today()
    existing_log = HabitLog.query.filter_by(habit_id=habit.id, completed_date=today).first()

    if existing_log:
        db.session.delete(existing_log)
        habit.streak = max(0, (habit.streak or 0) - 1)
        
        previous_log = HabitLog.query.filter(
            HabitLog.habit_id == habit.id,
            HabitLog.completed_date < today
        ).order_by(HabitLog.completed_date.desc()).first()

        if previous_log:
            habit.last_completed = datetime.combine(previous_log.completed_date, datetime.min.time())
        else:
            habit.last_completed = None

        is_done = False
    else:
        new_log = HabitLog(habit_id=habit.id, completed_date=today)
        db.session.add(new_log)

        if habit.frequency == HabitFrequency.DAILY:
            if habit.last_completed and (today - habit.last_completed.date()).days == 1:
                habit.streak = (habit.streak or 0) + 1
            else:
                habit.streak = 1
        else:
            if habit.last_completed:
                last_week = habit.last_completed.date().isocalendar()[:2]
                this_week = today.isocalendar()[:2]
                
                if last_week == this_week:
                    pass 
                elif (today - habit.last_completed.date()).days <= 14:
                    habit.streak = (habit.streak or 0) + 1
                else:
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
    """
    DEPRECATED: Receives form data to create a new habit.
    Use POST /api/v2/habits instead.
    """
    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')

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


@habits_api_bp.route('/<int:habit_id>/edit', methods=['POST'])
@login_required
    """
    DEPRECATED: Updates an existing habit's details.
    Use PUT /api/v2/habits/<id> instead.
    """
    habit = db.session.get(Habit, habit_id)
    
    if not habit or habit.user_id != current_user.id:
        return redirect(url_for('habits_view.manage'))

    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')
    identity_id = request.form.get('identity_id', type=int)

    if name and frequency_str and icon:
        habit.name = name.strip()
        habit.icon = icon.strip()
        habit.frequency = HabitFrequency.DAILY if frequency_str == 'DAILY' else HabitFrequency.WEEKLY
        habit.identity_id = identity_id or None
        
        db.session.commit()

    return redirect(url_for('habits_view.manage'))


@habits_api_bp.route('/<int:habit_id>/delete', methods=['POST'])
@login_required
    """
    DEPRECATED: Deletes a habit and all associated logs.
    Use DELETE /api/v2/habits/<id> instead.
    """
    habit = db.session.get(Habit, habit_id)
    
    if habit and habit.user_id == current_user.id:
        db.session.delete(habit)
        db.session.commit()
        
    return redirect(url_for('habits_view.manage'))


# ============================================================================
# MODERN API ENDPOINTS (v2)
# ============================================================================

@habits_api_v2_bp.route('', methods=['GET'])
@login_required
@api_rate_limit()
def get_habits():
    """Get all habits for current user."""
    try:
        habits = get_all_habits(current_user.id, include_inactive=False)
        
        habits_data = [{
            'id': h.id,
            'name': h.name,
            'description': h.description,
            'frequency': str(h.frequency),
            'streak': h.streak or 0,
            'identity_id': h.identity_id,
            'icon': h.icon,
            'is_active': h.is_active if hasattr(h, 'is_active') else True,
            'created_at': h.created_at.isoformat() if h.created_at else None
        } for h in habits]
        
        return ResponseService.success(habits_data, "Habits retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get habits", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_habit_api():
    """Create a new habit."""
    try:
        data = request.get_json() or {}
        
        habit, error = create_habit(
            user_id=current_user.id,
            name=data.get('name'),
            description=data.get('description'),
            frequency=data.get('frequency', 'daily'),
            identity_id=data.get('identity_id'),
            check_ins_required=data.get('check_ins_required', 1),
            trigger=data.get('trigger'),
            icon=data.get('icon', '⭐')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'Habit', current_user.id, habit.id, {'name': habit.name})
        
        return ResponseService.created({
            'id': habit.id,
            'name': habit.name,
            'streak': habit.streak or 0
        }, "Habit created successfully", 201)
    except Exception as e:
        LoggingService.log_error(e, "Failed to create habit", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_habit(habit_id):
    """Get a specific habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        return ResponseService.success({
            'id': habit.id,
            'name': habit.name,
            'description': habit.description,
            'frequency': str(habit.frequency),
            'streak': habit.streak or 0,
            'identity_id': habit.identity_id,
            'icon': habit.icon,
            'is_active': habit.is_active if hasattr(habit, 'is_active') else True,
            'created_at': habit.created_at.isoformat() if habit.created_at else None
        }, "Habit retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get habit", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>', methods=['PUT'])
@login_required
@api_rate_limit()
def update_habit_api(habit_id):
    """Update a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        data = request.get_json() or {}
        
        success, error = update_habit(habit=habit, **data)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('UPDATE', 'Habit', current_user.id, habit.id, data)
        
        return ResponseService.success({'id': habit.id}, "Habit updated successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to update habit", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>', methods=['DELETE'])
@login_required
@api_rate_limit()
def delete_habit_api(habit_id):
    """Delete a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        success, error = delete_habit(habit=habit)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('DELETE', 'Habit', current_user.id, habit.id)
        
        return ResponseService.success({}, "Habit deleted successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to delete habit", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>/log', methods=['POST'])
@login_required
@api_rate_limit()
def log_habit_api(habit_id):
    """Log a habit completion."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        data = request.get_json() or {}
        
        log_entry, error = log_habit(
            habit=habit,
            user=current_user,
            date_logged=data.get('date_logged'),
            check_ins=data.get('check_ins', 1)
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('LOG', 'Habit', current_user.id, habit.id)
        
        return ResponseService.success({
            'id': habit.id,
            'streak': habit.streak or 0
        }, "Habit logged successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to log habit", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>/unlog', methods=['POST'])
@login_required
@api_rate_limit()
def unlog_habit_api(habit_id):
    """Remove a habit log."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        data = request.get_json() or {}
        
        success, error = unlog_habit(habit=habit, user=current_user, date=data.get('date'))
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('UNLOG', 'Habit', current_user.id, habit.id)
        
        return ResponseService.success({
            'id': habit.id,
            'streak': habit.streak or 0
        }, "Habit log removed successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to remove habit log", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>/streak', methods=['GET'])
@login_required
@api_rate_limit()
def get_habit_streak(habit_id):
    """Get streak information for a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        streak_info = get_streak_info(habit, user=current_user)
        
        return ResponseService.success(streak_info, "Streak information retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get streak info", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>/toggle-active', methods=['POST'])
@login_required
@api_rate_limit()
def toggle_habit_active_api(habit_id):
    """Enable/disable a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        is_active = not (habit.is_active if hasattr(habit, 'is_active') else True)
        success, error = toggle_habit_active(habit, is_active)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('TOGGLE', 'Habit', current_user.id, habit.id, {'is_active': is_active})
        
        return ResponseService.success({'id': habit.id, 'is_active': is_active}, "Habit status updated")
    except Exception as e:
        LoggingService.log_error(e, "Failed to toggle habit", current_user.id)
        return ResponseService.server_error()
