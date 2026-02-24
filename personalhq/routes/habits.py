"""Module defining the API and view routes for Habits."""

from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from personalhq.services import habit_service

# We use the /actions/ namespace for the interactive JSON routes
habits_bp = Blueprint('habits', __name__, url_prefix='/actions/habits')

@habits_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle(habit_id):
    """Toggles the completion status of a habit and calculates the streak."""
    result = habit_service.toggle_habit(habit_id, current_user.id)
    
    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 404
        
    return jsonify(result), 200