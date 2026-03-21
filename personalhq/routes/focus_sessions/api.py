"""Modern API routes for Focus Sessions (Deep Work)."""

from datetime import datetime
from sqlalchemy import func
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.deepwork_service import DeepWorkService
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

# Modern API endpoints only (no legacy /actions/)
focus_api_bp = Blueprint('focus_api', __name__, url_prefix='/api/v1/focus-sessions')

@focus_api_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_session():
    """Create a new focus session."""
    try:
        data = request.get_json() or {}
        name = data.get('name', 'Deep Work Block')
        duration_minutes = data.get('duration_minutes', 25)
        target_date = data.get('target_date')
        identity_id = data.get('identity_id')
        
        session = DeepWorkService.create_session(
            current_user.id, name, duration_minutes, target_date, identity_id
        )
        
        LoggingService.log_crud('CREATE', 'FocusSession', current_user.id, session.id, {'name': name})
        
        return ResponseService.created({
            'id': session.id,
            'name': session.name,
            'duration_minutes': session.duration_minutes,
            'status': session.status
        }, "Focus session created", 201)
    except Exception as e:
        LoggingService.log_error(e, "Failed to create focus session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/start', methods=['POST'])
@login_required
@api_rate_limit()
def start_session(session_id):
    """Start a focus session timer."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        success = DeepWorkService.start_session(session)
        if success:
            LoggingService.log_crud('UPDATE', 'FocusSession', current_user.id, session.id, {'status': 'ACTIVE'})
            return ResponseService.success({'status': session.status}, "Session started")
        
        return ResponseService.error("Cannot start session", 400)
    except Exception as e:
        LoggingService.log_error(e, "Failed to start session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/pause', methods=['POST'])
@login_required
@api_rate_limit()
def pause_session(session_id):
    """Pause a focus session timer."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        success = DeepWorkService.pause_session(session)
        if success:
            LoggingService.log_crud('UPDATE', 'FocusSession', current_user.id, session.id, {'status': 'PAUSED'})
            return ResponseService.success({'status': session.status}, "Session paused")
        
        return ResponseService.error("Cannot pause session", 400)
    except Exception as e:
        LoggingService.log_error(e, "Failed to pause session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/resume', methods=['POST'])
@login_required
@api_rate_limit()
def resume_session(session_id):
    """Resume a paused focus session timer."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        success = DeepWorkService.resume_session(session)
        if success:
            LoggingService.log_crud('UPDATE', 'FocusSession', current_user.id, session.id, {'status': 'ACTIVE'})
            return ResponseService.success({'status': session.status}, "Session resumed")
        
        return ResponseService.error("Cannot resume session", 400)
    except Exception as e:
        LoggingService.log_error(e, "Failed to resume session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/end', methods=['POST'])
@login_required
@api_rate_limit()
def end_session(session_id):
    """End a focus session (mark as completed)."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        success = DeepWorkService.end_session(session)
        if success:
            LoggingService.log_crud('UPDATE', 'FocusSession', current_user.id, session.id, {'status': 'COMPLETED'})
            return ResponseService.success({'status': session.status}, "Session completed")
        
        return ResponseService.error("Cannot end session", 400)
    except Exception as e:
        LoggingService.log_error(e, "Failed to end session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/discard', methods=['POST'])
@login_required
@api_rate_limit()
def discard_session(session_id):
    """Discard a focus session (cancel without saving)."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        success = DeepWorkService.discard_session(session)
        if success:
            LoggingService.log_crud('DELETE', 'FocusSession', current_user.id, session.id)
            return ResponseService.success({}, "Session discarded")
        
        return ResponseService.error("Cannot discard session", 400)
    except Exception as e:
        LoggingService.log_error(e, "Failed to discard session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/extend', methods=['POST'])
@login_required
@api_rate_limit()
def extend_session(session_id):
    """Extend a focus session by additional minutes."""
    try:
        data = request.get_json() or {}
        additional_minutes = data.get('additional_minutes', 5)
        
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        success = DeepWorkService.extend_session(session, additional_minutes)
        if success:
            LoggingService.log_crud('UPDATE', 'FocusSession', current_user.id, session.id, {'extended_by': additional_minutes})
            return ResponseService.success({'duration_minutes': session.duration_minutes}, "Session extended")
        
        return ResponseService.error("Cannot extend session", 400)
    except Exception as e:
        LoggingService.log_error(e, "Failed to extend session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>/status', methods=['GET'])
@login_required
@api_rate_limit()
def get_session_status(session_id):
    """Get current session status and time remaining."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        status_data = DeepWorkService.get_session_status(session)
        return ResponseService.success(status_data, "Session status retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get session status", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_session(session_id):
    """Get a specific focus session."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        return ResponseService.success({
            'id': session.id,
            'name': session.name,
            'duration_minutes': session.duration_minutes,
            'status': session.status,
            'target_date': session.target_date.isoformat() if session.target_date else None,
            'created_at': session.created_at.isoformat() if session.created_at else None
        }, "Session retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/<int:session_id>', methods=['DELETE'])
@login_required
@api_rate_limit()
def delete_session(session_id):
    """Delete a focus session."""
    try:
        session = FocusSession.query.filter_by(id=session_id, user_id=current_user.id).first()
        if not session:
            return ResponseService.not_found("Session not found")
        
        db.session.delete(session)
        db.session.commit()
        
        LoggingService.log_crud('DELETE', 'FocusSession', current_user.id, session.id)
        return ResponseService.success({}, "Session deleted")
    except Exception as e:
        LoggingService.log_error(e, "Failed to delete session", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/today', methods=['GET'])
@login_required
@api_rate_limit()
def get_today_sessions():
    """Get all focus sessions scheduled for today."""
    try:
        from datetime import date
        today = date.today()
        
        sessions = FocusSession.query.filter_by(
            user_id=current_user.id,
            target_date=today
        ).order_by(FocusSession.queue_order).all()
        
        sessions_data = [{
            'id': s.id,
            'name': s.name,
            'duration_minutes': s.duration_minutes,
            'status': s.status,
            'queue_order': s.queue_order
        } for s in sessions]
        
        return ResponseService.success(sessions_data, "Today's sessions retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get today's sessions", current_user.id)
        return ResponseService.server_error()

@focus_api_bp.route('/active', methods=['GET'])
@login_required
@api_rate_limit()
def get_active_session():
    """Get the currently active focus session."""
    try:
        session = FocusSession.query.filter_by(
            user_id=current_user.id,
            status=SessionStatus.ACTIVE
        ).first()
        
        if not session:
            return ResponseService.not_found("No active session")
        
        status_data = DeepWorkService.get_session_status(session)
        return ResponseService.success(status_data, "Active session retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get active session", current_user.id)
        return ResponseService.server_error()
