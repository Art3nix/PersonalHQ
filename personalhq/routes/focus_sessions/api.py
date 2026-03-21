"""Module defining the API routes for Focus Sessions."""

from datetime import datetime
from sqlalchemy import func
from flask import Blueprint, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services import focus_service

focus_api_bp = Blueprint('focus_api', __name__, url_prefix='/actions/focus')

@focus_api_bp.route('/start', methods=['POST'])
@login_required
def start():
    """Starts a new focus session."""
    data = request.get_json() or {}
    name = data.get('name', 'Deep Work Block')

    session = focus_service.start_session(current_user.id, name)
    return jsonify({"status": "success", "session_id": session.id}), 201

@focus_api_bp.route('/<int:session_id>/pause', methods=['POST'])
@login_required
def pause(session_id):
    """Pauses the active timer."""
    if focus_service.pause_session(session_id):
        return jsonify({"status": "success", "message": "Timer paused."}), 200
    return jsonify({"status": "error", "message": "Could not pause session."}), 400

@focus_api_bp.route('/<int:session_id>/resume', methods=['POST'])
@login_required
def resume(session_id):
    """Resumes a paused timer."""
    if focus_service.resume_session(session_id):
        return jsonify({"status": "success", "message": "Timer resumed."}), 200
    return jsonify({"status": "error", "message": "Could not resume session."}), 400

@focus_api_bp.route('/<int:session_id>/end', methods=['POST'])
@login_required
def end(session_id):
    """Ends a paused session and marks the associated task as completed."""
    if focus_service.end_session(session_id):
        return jsonify({"status": "success", "message": "Session completed."}), 200
    return jsonify({"status": "error", "message": "Cannot end session. Must be paused first."}), 400

@focus_api_bp.route('/<int:session_id>/status', methods=['GET'])
@login_required
def status(session_id):
    """Fetches the true server-side time and state for the UI clock."""
    data = focus_service.get_session_time_data(session_id)
    if data:
        return jsonify({"status": "success", "data": data}), 200
    return jsonify({"status": "error", "message": "Session not found."}), 404

@focus_api_bp.route('/log', methods=['POST'])
@login_required
def log_session():
    """Receives a completed timer session from the frontend and logs it."""
    data = request.get_json()
    duration = data.get('duration_minutes')
    intention = data.get('intention')

    if not duration:
        return jsonify({"status": "error", "message": "Duration required"}), 400

    session = FocusSession(
        user_id=current_user.id,
        duration_minutes=int(duration),
        intention=intention.strip() if intention else None
    )

    db.session.add(session)
    db.session.commit()

    return jsonify({"status": "success", "session_id": session.id})

@focus_api_bp.route('/schedule', methods=['POST'])
@login_required
def schedule_session():
    """Schedules a future Focus Session."""
    name = request.form.get('name')
    target_date_str = request.form.get('target_date')
    duration = request.form.get('target_duration_minutes', type=int)

    if not name or not target_date_str:
        return redirect(url_for('focus_view.planner'))

    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()

    # Automatically calculate the next queue_order for this specific date
    max_order = db.session.query(func.max(FocusSession.queue_order)).filter_by(
        user_id=current_user.id, target_date=target_date
    ).scalar() or 0

    identity_id = request.form.get('identity_id', type=int)

    new_session = FocusSession(
        user_id=current_user.id,
        name=name.strip(),
        target_date=target_date,
        target_duration_minutes=duration or 60,
        status=SessionStatus.NOT_STARTED,
        queue_order=max_order + 1,
        total_paused_seconds=0,
        identity_id=identity_id
    )

    db.session.add(new_session)
    db.session.commit()

    return redirect(url_for('focus_view.planner'))

@focus_api_bp.route('/<int:session_id>/toggle', methods=['POST'])
@login_required
def toggle_session(session_id):
    """Toggles a scheduled focus session between NOT_STARTED and FINISHED."""
    session_record = db.session.get(FocusSession, session_id)
    if not session_record or session_record.user_id != current_user.id:
        return jsonify({"status": "error"}), 404

    # Flip the Enum status
    if session_record.status == SessionStatus.FINISHED:
        session_record.status = SessionStatus.NOT_STARTED
        session_record.start_time = None
        session_record.end_time = None
        session_record.total_paused_seconds = 0
        session_record.last_paused_tick = None
    else:
        session_record.status = SessionStatus.FINISHED
        
    db.session.commit()
    
    return jsonify({
        "status": "success", 
        "is_finished": session_record.status == SessionStatus.FINISHED
    })

@focus_api_bp.route('/reorder', methods=['POST'])
@login_required
def reorder_sessions():
    """Updates the queue_order and target_date of focus sessions after a drag-and-drop."""
    data = request.get_json()
    session_ids = data.get('session_ids', [])
    new_date_str = data.get('target_date') # Capture the new date

    if not session_ids:
        return jsonify({"status": "error", "message": "No session IDs provided"}), 400

    # Parse the new date if it was provided
    new_date = None
    if new_date_str:
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()

    # Loop through the new order and update the database
    for index, session_id in enumerate(session_ids):
        # Enumerate starts at 0, but we want queue_order to start at 1
        new_queue_order = index + 1 
        
        # Only update if the session exists and belongs to the current user
        session_record = db.session.get(FocusSession, session_id)
        if session_record and session_record.user_id == current_user.id:
            session_record.queue_order = new_queue_order
            
            # If the session was dragged to a new day, update the date!
            if new_date:
                session_record.target_date = new_date

    db.session.commit()

    return jsonify({"status": "success"})

@focus_api_bp.route('/<int:session_id>/edit', methods=['POST'])
@login_required
def edit_session(session_id):
    """Updates an existing focus session's details."""
    session = db.session.get(FocusSession, session_id)
    
    if not session or session.user_id != current_user.id:
        return redirect(url_for('focus_view.planner'))

    name = request.form.get('name')
    target_date_str = request.form.get('target_date')
    duration = request.form.get('target_duration_minutes', type=int)
    identity_id = request.form.get('identity_id', type=int)

    if name and target_date_str:
        session.name = name.strip()
        # Convert HTML date string back to Python date object
        session.target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
        
        if duration:
            session.target_duration_minutes = duration
            
        session.identity_id = identity_id or None
        db.session.commit()

    return redirect(url_for('focus_view.planner'))

@focus_api_bp.route('/<int:session_id>/delete', methods=['POST'])
@login_required
def delete_session(session_id):
    """Deletes a scheduled focus session."""
    session = db.session.get(FocusSession, session_id)
    
    # Ensure users can only delete their own sessions
    if session and session.user_id == current_user.id:
        db.session.delete(session)
        db.session.commit()
        
    return redirect(url_for('focus_view.planner'))
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
