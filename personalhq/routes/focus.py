"""Module defining the API routes for Focus Sessions."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from personalhq.services import focus_service

focus_bp = Blueprint('focus', __name__, url_prefix='/actions/focus')

@focus_bp.route('/start', methods=['POST'])
@login_required
def start():
    """Starts a new focus session."""
    data = request.get_json() or {}
    name = data.get('name', 'Deep Work Block')

    session = focus_service.start_session(current_user.id, name)
    return jsonify({"status": "success", "session_id": session.id}), 201

@focus_bp.route('/<int:session_id>/pause', methods=['POST'])
@login_required
def pause(session_id):
    """Pauses the active timer."""
    if focus_service.pause_session(session_id):
        return jsonify({"status": "success", "message": "Timer paused."}), 200
    return jsonify({"status": "error", "message": "Could not pause session."}), 400

@focus_bp.route('/<int:session_id>/resume', methods=['POST'])
@login_required
def resume(session_id):
    """Resumes a paused timer."""
    if focus_service.resume_session(session_id):
        return jsonify({"status": "success", "message": "Timer resumed."}), 200
    return jsonify({"status": "error", "message": "Could not resume session."}), 400

@focus_bp.route('/<int:session_id>/end', methods=['POST'])
@login_required
def end(session_id):
    """Ends a paused session and marks the associated task as completed."""
    if focus_service.end_session(session_id):
        return jsonify({"status": "success", "message": "Session completed."}), 200
    return jsonify({"status": "error", "message": "Cannot end session. Must be paused first."}), 400

@focus_bp.route('/<int:session_id>/status', methods=['GET'])
@login_required
def status(session_id):
    """Fetches the true server-side time and state for the UI clock."""
    data = focus_service.get_session_time_data(session_id)
    if data:
        return jsonify({"status": "success", "data": data}), 200
    return jsonify({"status": "error", "message": "Session not found."}), 404
