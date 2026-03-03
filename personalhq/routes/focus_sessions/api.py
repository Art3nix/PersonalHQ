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
    """Updates the queue_order of focus sessions after a drag-and-drop."""
    data = request.get_json()
    session_ids = data.get('session_ids', [])

    if not session_ids:
        return jsonify({"status": "error", "message": "No session IDs provided"}), 400

    # Loop through the new order and update the database
    for index, session_id in enumerate(session_ids):
        # Enumerate starts at 0, but we want queue_order to start at 1
        new_queue_order = index + 1 
        
        # Only update if the session exists and belongs to the current user
        session_record = db.session.get(FocusSession, session_id)
        if session_record and session_record.user_id == current_user.id:
            session_record.queue_order = new_queue_order

    db.session.commit()
    
    return jsonify({"status": "success"})