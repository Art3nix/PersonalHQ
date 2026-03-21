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
    duration = data.get('duration_minutes', 60)
    identity_id = data.get('identity_id')

    session = focus_service.start_session(current_user.id, name, duration, identity_id)
    return jsonify({"status": "success", "session_id": session.id}), 201

@focus_api_bp.route('/<int:session_id>/pause', methods=['POST'])
@login_required
def pause(session_id):
    """Pauses the active timer."""
    session = db.session.get(FocusSession, session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not found."}), 404
    if focus_service.pause_session(session_id):
        return jsonify({"status": "success", "message": "Timer paused."}), 200
    return jsonify({"status": "error", "message": "Could not pause session."}), 400

@focus_api_bp.route('/<int:session_id>/resume', methods=['POST'])
@login_required
def resume(session_id):
    """Resumes a paused timer."""
    session = db.session.get(FocusSession, session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not found."}), 404
    if focus_service.resume_session(session_id):
        return jsonify({"status": "success", "message": "Timer resumed."}), 200
    return jsonify({"status": "error", "message": "Could not resume session."}), 400

@focus_api_bp.route('/<int:session_id>/end', methods=['POST'])
@login_required
def end(session_id):
    """Ends a session."""
    session = db.session.get(FocusSession, session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not found."}), 404
    if focus_service.end_session(session_id):
        return jsonify({"status": "success", "message": "Session completed."}), 200
    return jsonify({"status": "error", "message": "Cannot end session."}), 400

@focus_api_bp.route('/<int:session_id>/status', methods=['GET'])
@login_required
def status(session_id):
    """Fetches the true server-side time and state for the UI clock."""
    session = db.session.get(FocusSession, session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Not found."}), 404
    data = focus_service.get_session_time_data(session_id)
    if data:
        return jsonify({"status": "success", "data": data}), 200
    return jsonify({"status": "error", "message": "Session not found."}), 404

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
    """Updates the queue_order and target_date of focus sessions."""
    data = request.get_json()
    session_ids = data.get('session_ids', [])
    new_date_str = data.get('target_date')

    if not session_ids:
        return jsonify({"status": "error", "message": "No session IDs provided"}), 400

    new_date = None
    if new_date_str:
        new_date = datetime.strptime(new_date_str, '%Y-%m-%d').date()

    for index, session_id in enumerate(session_ids):
        session_record = db.session.get(FocusSession, session_id)
        if session_record and session_record.user_id == current_user.id:
            session_record.queue_order = index + 1
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

    if session and session.user_id == current_user.id:
        name = session.name
        db.session.delete(session)
        db.session.commit()
        from flask import flash
        flash(f'"{name}" removed from queue.', 'success')

    return redirect(url_for('focus_view.planner'))

@focus_api_bp.route('/<int:session_id>/reset', methods=['POST'])
@login_required
def reset_session(session_id):
    """Wipes the progress of a session but keeps it in the planner."""
    session = db.session.get(FocusSession, session_id)
    if not session or session.user_id != current_user.id:
        return jsonify({"status": "error"}), 404

    focus_service.discard_session(session_id)
    return jsonify({"status": "success"})

@focus_api_bp.route('/carry-over', methods=['POST'])
@login_required
def carry_over():
    """Moves all missed sessions from yesterday to today."""
    count = focus_service.carry_over_sessions(current_user.id)
    return jsonify({
        "status": "success",
        "carried_over": count,
        "message": f"Moved {count} session{'s' if count != 1 else ''} from yesterday to today."
    })
