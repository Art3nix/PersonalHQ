"""Refactored Deep Work / Focus Sessions API routes using service layer."""

from flask import Blueprint, request
from flask_login import login_required, current_user
from personalhq.models.focussessions import FocusSession
from personalhq.services.deepwork_service import DeepWorkService
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

focus_api_v2_bp = Blueprint('focus_api_v2', __name__, url_prefix='/api/v2/focus-sessions')


@focus_api_v2_bp.route('', methods=['GET'])
@login_required
@api_rate_limit()
def get_sessions():
    """Get all focus sessions for current user."""
    try:
        sessions = FocusSession.query.filter_by(user_id=current_user.id).order_by(
            FocusSession.created_at.desc()
        ).all()
        
        sessions_data = [{
            'id': s.id,
            'task_name': s.task_name,
            'duration_minutes': s.duration_minutes,
            'status': s.status,
            'created_at': s.created_at.isoformat() if s.created_at else None
        } for s in sessions]
        
        return ResponseService.success(sessions_data, "Sessions retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get sessions", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_session():
    """Create a new focus session."""
    try:
        data = request.get_json() or {}
        
        session, error = DeepWorkService.create_session(
            current_user,
            data.get('task_name'),
            data.get('duration_minutes', 25),
            data.get('identity_id')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'FocusSession', current_user.id, session.id, 
                               {'task_name': session.task_name})
        
        return ResponseService.created({
            'id': session.id,
            'task_name': session.task_name,
            'duration_minutes': session.duration_minutes,
            'status': session.status
        }, "Focus session created successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to create session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_session(session_id):
    """Get a specific focus session."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        time_remaining = DeepWorkService.get_session_time_remaining(session)
        
        return ResponseService.success({
            'id': session.id,
            'task_name': session.task_name,
            'duration_minutes': session.duration_minutes,
            'status': session.status,
            'time_remaining_seconds': time_remaining,
            'created_at': session.created_at.isoformat() if session.created_at else None
        }, "Session retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>/start', methods=['POST'])
@login_required
@api_rate_limit()
def start_session(session_id):
    """Start a focus session timer."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        success, error = DeepWorkService.start_session(session)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('START', 'FocusSession', current_user.id, session.id)
        
        return ResponseService.success({
            'id': session.id,
            'status': session.status,
            'started_at': session.started_at.isoformat() if session.started_at else None
        }, "Session started")
    except Exception as e:
        LoggingService.log_error(e, "Failed to start session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>/pause', methods=['POST'])
@login_required
@api_rate_limit()
def pause_session(session_id):
    """Pause a focus session timer."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        success, error = DeepWorkService.pause_session(session)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('PAUSE', 'FocusSession', current_user.id, session.id)
        
        return ResponseService.success({
            'id': session.id,
            'status': session.status
        }, "Session paused")
    except Exception as e:
        LoggingService.log_error(e, "Failed to pause session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>/resume', methods=['POST'])
@login_required
@api_rate_limit()
def resume_session(session_id):
    """Resume a paused focus session timer."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        success, error = DeepWorkService.resume_session(session)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('RESUME', 'FocusSession', current_user.id, session.id)
        
        return ResponseService.success({
            'id': session.id,
            'status': session.status
        }, "Session resumed")
    except Exception as e:
        LoggingService.log_error(e, "Failed to resume session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>/end', methods=['POST'])
@login_required
@api_rate_limit()
def end_session(session_id):
    """End a focus session (with confirmation)."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        data = request.get_json() or {}
        early = data.get('early', False)
        
        success, error = DeepWorkService.end_session(session, early)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('END', 'FocusSession', current_user.id, session.id, {'early': early})
        
        return ResponseService.success({
            'id': session.id,
            'status': session.status,
            'completed_at': session.completed_at.isoformat() if session.completed_at else None
        }, "Session ended successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to end session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>/discard', methods=['POST'])
@login_required
@api_rate_limit()
def discard_session(session_id):
    """Discard a focus session (requires confirmation)."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        success, error = DeepWorkService.discard_session(session)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('DISCARD', 'FocusSession', current_user.id, session.id)
        
        return ResponseService.success({}, "Session discarded")
    except Exception as e:
        LoggingService.log_error(e, "Failed to discard session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/<int:session_id>/extend', methods=['POST'])
@login_required
@api_rate_limit()
def extend_session(session_id):
    """Extend a focus session by additional minutes."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        
        if not session:
            return ResponseService.not_found("Session not found")
        
        data = request.get_json() or {}
        additional_minutes = data.get('additional_minutes', 5)
        
        success, error = DeepWorkService.extend_session(session, additional_minutes)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('EXTEND', 'FocusSession', current_user.id, session.id, 
                               {'additional_minutes': additional_minutes})
        
        return ResponseService.success({
            'id': session.id,
            'duration_minutes': session.duration_minutes,
            'time_remaining_seconds': DeepWorkService.get_session_time_remaining(session)
        }, "Session extended successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to extend session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/today', methods=['GET'])
@login_required
@api_rate_limit()
def get_today_sessions():
    """Get all focus sessions for today."""
    try:
        sessions = DeepWorkService.get_today_sessions(current_user)
        
        sessions_data = [{
            'id': s.id,
            'task_name': s.task_name,
            'duration_minutes': s.duration_minutes,
            'status': s.status,
            'time_remaining_seconds': DeepWorkService.get_session_time_remaining(s)
        } for s in sessions]
        
        return ResponseService.success(sessions_data, "Today's sessions retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get today's sessions", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/active', methods=['GET'])
@login_required
@api_rate_limit()
def get_active_session():
    """Get the currently active focus session."""
    try:
        session = DeepWorkService.get_active_session(current_user)
        
        if not session:
            return ResponseService.success(None, "No active session")
        
        time_remaining = DeepWorkService.get_session_time_remaining(session)
        
        return ResponseService.success({
            'id': session.id,
            'task_name': session.task_name,
            'duration_minutes': session.duration_minutes,
            'status': session.status,
            'time_remaining_seconds': time_remaining
        }, "Active session retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get active session", current_user.id)
        return ResponseService.server_error()


@focus_api_v2_bp.route('/stats', methods=['GET'])
@login_required
@api_rate_limit()
def get_session_stats():
    """Get focus session statistics."""
    try:
        days_back = request.args.get('days_back', 30, type=int)
        stats = DeepWorkService.get_session_stats(current_user, days_back)
        
        return ResponseService.success(stats, "Session statistics retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get session stats", current_user.id)
        return ResponseService.server_error()
