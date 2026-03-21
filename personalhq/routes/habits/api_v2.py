"""Refactored Habits API routes using service layer."""

from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from personalhq.models.habits import Habit
from personalhq.services.habit_service_v2 import HabitServiceV2
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

habits_api_v2_bp = Blueprint('habits_api_v2', __name__, url_prefix='/api/v2/habits')


@habits_api_v2_bp.route('', methods=['GET'])
@login_required
@api_rate_limit()
def get_habits():
    """Get all habits for current user."""
    try:
        habits = Habit.query.filter_by(user_id=current_user.id).all()
        
        habits_data = [{
            'id': h.id,
            'name': h.name,
            'description': h.description,
            'frequency': h.frequency,
            'streak': h.streak or 0,
            'identity_id': h.identity_id,
            'created_at': h.created_at.isoformat() if h.created_at else None
        } for h in habits]
        
        return ResponseService.success(habits_data, "Habits retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get habits", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_habit():
    """Create a new habit."""
    try:
        data = request.get_json() or {}
        
        habit, error = HabitServiceV2.create_habit(
            current_user,
            data.get('name'),
            data.get('description'),
            data.get('frequency', 'daily'),
            data.get('identity_id'),
            data.get('check_ins_required', 1),
            data.get('trigger')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'Habit', current_user.id, habit.id, {'name': habit.name})
        
        return ResponseService.created({
            'id': habit.id,
            'name': habit.name,
            'streak': habit.streak or 0
        }, "Habit created successfully")
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
            'frequency': habit.frequency,
            'streak': habit.streak or 0,
            'identity_id': habit.identity_id,
            'created_at': habit.created_at.isoformat() if habit.created_at else None
        }, "Habit retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get habit", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>', methods=['PUT'])
@login_required
@api_rate_limit()
def update_habit(habit_id):
    """Update a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        data = request.get_json() or {}
        
        success, error = HabitServiceV2.update_habit(habit, **data)
        
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
def delete_habit(habit_id):
    """Delete a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        success, error = HabitServiceV2.delete_habit(habit)
        
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
def log_habit(habit_id):
    """Log a habit completion."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        data = request.get_json() or {}
        
        success, error = HabitServiceV2.log_habit(
            habit,
            current_user,
            data.get('date_logged'),
            data.get('check_ins', 1)
        )
        
        if not success:
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
def unlog_habit(habit_id):
    """Remove a habit log."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        data = request.get_json() or {}
        
        success, error = HabitServiceV2.unlog_habit(habit, current_user, data.get('date'))
        
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
        
        logs = habit.habit_logs
        streak_info = HabitServiceV2.get_streak_info(habit, current_user)
        
        return ResponseService.success(streak_info, "Streak information retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get streak info", current_user.id)
        return ResponseService.server_error()


@habits_api_v2_bp.route('/<int:habit_id>/toggle-active', methods=['POST'])
@login_required
@api_rate_limit()
def toggle_habit_active(habit_id):
    """Enable/disable a habit."""
    try:
        habit = Habit.query.filter_by(id=habit_id, user_id=current_user.id).first()
        
        if not habit:
            return ResponseService.not_found("Habit not found")
        
        is_active = not (habit.is_active if hasattr(habit, 'is_active') else True)
        success, error = HabitServiceV2.toggle_habit_active(habit, is_active)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('TOGGLE', 'Habit', current_user.id, habit.id, {'is_active': is_active})
        
        return ResponseService.success({'id': habit.id, 'is_active': is_active}, "Habit status updated")
    except Exception as e:
        LoggingService.log_error(e, "Failed to toggle habit", current_user.id)
        return ResponseService.server_error()
