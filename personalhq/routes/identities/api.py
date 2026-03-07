"""API routes for Identity Matrix actions."""

from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.identities import Identity
from personalhq.models.habits import Habit

identities_api_bp = Blueprint('identities_api', __name__, url_prefix='/actions/identities')

@identities_api_bp.route('/create', methods=['POST'])
@login_required
def create_identity():
    """Creates a new Identity and optionally links existing unassigned habits."""
    name = request.form.get('name')
    description = request.form.get('description')
    
    # getlist() captures all checked checkboxes sharing the 'habit_ids' name
    habit_ids = request.form.getlist('habit_ids') 

    if not name:
        flash('Identity name is required.', 'error')
        return redirect(url_for('identities_view.matrix'))

    new_identity = Identity(
        user_id=current_user.id,
        name=name.strip(),
        description=description.strip() if description else None
    )
    
    db.session.add(new_identity)
    db.session.flush() # Flush to generate the new_identity.id without committing yet

    # If the user checked any unassigned habits in the modal, update their foreign keys
    if habit_ids:
        habits_to_update = Habit.query.filter(
            Habit.id.in_(habit_ids), 
            Habit.user_id == current_user.id
        ).all()
        
        for habit in habits_to_update:
            habit.identity_id = new_identity.id

    db.session.commit()
    flash(f'Identity "{new_identity.name}" established.', 'success')

    return redirect(url_for('identities_view.matrix'))

@identities_api_bp.route('/<int:identity_id>/delete', methods=['POST'])
@login_required
def delete_identity(identity_id):
    """Deletes an Identity and safely unassigns its associated habits and focus sessions."""
    identity = db.session.get(Identity, identity_id)

    if identity and identity.user_id == current_user.id:
        # Unassign habits so they don't get deleted or cause foreign key errors
        for habit in identity.habits:
            habit.identity_id = None

        # Unassign focus sessions
        for session in identity.focus_sessions:
            session.identity_id = None

        db.session.delete(identity)
        db.session.commit()

    return redirect(url_for('identities_view.matrix'))
