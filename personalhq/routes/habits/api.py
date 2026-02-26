"""Module defining the API and view routes for Habits."""

from flask import Blueprint, jsonify, request, redirect, url_for
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.services import habit_service
from personalhq.extensions import db

# We use the /actions/ namespace for the interactive JSON routes
habits_api_bp = Blueprint('habits_api', __name__, url_prefix='/actions/habits')

@habits_api_bp.route('/<int:habit_id>/toggle', methods=['POST'])
@login_required
def toggle(habit_id):
    """Toggles the completion status of a habit and calculates the streak."""
    result = habit_service.toggle_habit(habit_id, current_user.id)

    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 404

    return jsonify(result), 200

@habits_api_bp.route('/create', methods=['POST'])
@login_required
def create_habit():
    """Receives form data to create a new habit and redirects back to the management page."""
    name = request.form.get('name')
    icon = request.form.get('icon')
    frequency_str = request.form.get('frequency')

    # Validation check
    if not name or not frequency_str or not icon:
        return redirect(url_for('habits_view.manage'))

    frequency = HabitFrequency.DAILY if frequency_str == 'DAILY' else HabitFrequency.WEEKLY

    new_habit = Habit(
        user_id=current_user.id,
        name=name.strip(),
        icon=icon.strip(),
        frequency=frequency
    )

    db.session.add(new_habit)
    db.session.commit()

    return redirect(url_for('habits_view.manage'))
