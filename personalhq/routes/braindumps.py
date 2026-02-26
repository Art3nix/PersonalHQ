"""Module defining the API routes for Brain Dumps."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from personalhq.services import braindump_service

braindumps_bp = Blueprint('braindumps', __name__, url_prefix='/actions/braindumps')

@braindumps_bp.route('/catch', methods=['POST'])
@login_required
def catch_thought():
    """Endpoint to receive and save a thought from the dashboard."""
    data = request.get_json() or {}
    content = data.get('content')

    if not content:
        return jsonify({"status": "error", "message": "No content provided."}), 400

    result = braindump_service.save_thought(current_user.id, content)

    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 400

    return jsonify(result), 201
