"""API routes for handling BrainDump data actions."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.services import braindump_service
from personalhq.models.braindumps import BrainDump

braindumps_api_bp = Blueprint('braindumps_api', __name__, url_prefix='/actions/braindumps')

@braindumps_api_bp.route('/catch', methods=['POST'])
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

@braindumps_api_bp.route('/<int:dump_id>/delete', methods=['POST'])
@login_required
def delete_dump(dump_id):
    """Deletes a processed thought from the Inbox."""
    dump = db.session.get(BrainDump, dump_id)
    if dump and dump.user_id == current_user.id:
        db.session.delete(dump)
        db.session.commit()
        return jsonify({"status": "success"})
    return jsonify({"status": "error"}), 404
