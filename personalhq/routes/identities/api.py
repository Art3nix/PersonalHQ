"""Unified Identities API routes - handles both legacy and modern endpoints."""

from flask import Blueprint, request, redirect, url_for, flash
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.identities import Identity
from personalhq.models.habits import Habit
from personalhq.services.identity_service import IdentityService
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

# Blueprint for legacy /actions/ endpoints
identities_api_bp = Blueprint('identities_api', __name__, url_prefix='/api/v1/identities')

# Blueprint for modern /api/v2/ endpoints
identities_api_v2_bp = Blueprint('identities_api_v2', __name__, url_prefix='/api/v2/identities')


# ============================================================================
# LEGACY ENDPOINTS (BACKWARD COMPATIBILITY)
# ============================================================================

@identities_api_bp.route('/create', methods=['POST'])
@login_required
    """
    DEPRECATED: Creates a new Identity and optionally links existing unassigned habits.
    Use POST /api/v2/identities instead.
    """
    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color', 'stone')
    habit_ids = request.form.getlist('habit_ids')

    if not name:
        flash('Identity name is required.', 'error')
        return redirect(url_for('identities_view.matrix'))

    new_identity = Identity(
        user_id=current_user.id,
        name=name.strip(),
        description=description.strip() if description else None,
        color=color
    )

    db.session.add(new_identity)
    db.session.flush()

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


@identities_api_bp.route('/<int:identity_id>/edit', methods=['POST'])
@login_required
    """
    DEPRECATED: Updates an existing Identity's core details.
    Use PUT /api/v2/identities/<id> instead.
    """
    identity = db.session.get(Identity, identity_id)
    
    if not identity or identity.user_id != current_user.id:
        return redirect(url_for('identities_view.matrix'))

    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color', 'stone')

    if name:
        identity.name = name.strip()
        identity.description = description.strip() if description else None
        identity.color = color
        db.session.commit()

    return redirect(url_for('identities_view.matrix'))


@identities_api_bp.route('/<int:identity_id>/delete', methods=['POST'])
@login_required
    """
    DEPRECATED: Deletes an Identity and safely unassigns its associated habits and focus sessions.
    Use DELETE /api/v2/identities/<id> instead.
    """
    identity = db.session.get(Identity, identity_id)

    if identity and identity.user_id == current_user.id:
        for habit in identity.habits:
            habit.identity_id = None

        for session in identity.focus_sessions:
            session.identity_id = None

        db.session.delete(identity)
        db.session.commit()

    return redirect(url_for('identities_view.matrix'))


# ============================================================================
# MODERN API ENDPOINTS (v2)
# ============================================================================

@identities_api_v2_bp.route('', methods=['GET'])
@login_required
@api_rate_limit()
def get_identities():
    """Get all identities for current user."""
    try:
        identities = IdentityService.get_identities(current_user)
        
        identities_data = [{
            'id': i.id,
            'name': i.name,
            'description': i.description if hasattr(i, 'description') else None,
            'reinforcing_sentence': i.reinforcing_sentence if hasattr(i, 'reinforcing_sentence') else None,
            'color': i.color if hasattr(i, 'color') else None,
            'created_at': i.created_at.isoformat() if i.created_at else None
        } for i in identities]
        
        return ResponseService.success(identities_data, "Identities retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get identities", current_user.id)
        return ResponseService.server_error()


@identities_api_v2_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_identity_api():
    """Create a new identity."""
    try:
        data = request.get_json() or {}
        
        identity, error = IdentityService.create_identity(
            current_user,
            data.get('name'),
            data.get('reinforcing_sentence'),
            data.get('color', '#3B82F6'),
            data.get('description')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'Identity', current_user.id, identity.id, {'name': identity.name})
        
        return ResponseService.created({
            'id': identity.id,
            'name': identity.name,
            'color': identity.color if hasattr(identity, 'color') else None
        }, "Identity created successfully", 201)
    except Exception as e:
        LoggingService.log_error(e, "Failed to create identity", current_user.id)
        return ResponseService.server_error()


@identities_api_v2_bp.route('/<int:identity_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_identity(identity_id):
    """Get a specific identity."""
    try:
        identity = Identity.query.filter_by(id=identity_id, user_id=current_user.id).first()
        
        if not identity:
            return ResponseService.not_found("Identity not found")
        
        return ResponseService.success({
            'id': identity.id,
            'name': identity.name,
            'description': identity.description if hasattr(identity, 'description') else None,
            'reinforcing_sentence': identity.reinforcing_sentence if hasattr(identity, 'reinforcing_sentence') else None,
            'color': identity.color if hasattr(identity, 'color') else None,
            'created_at': identity.created_at.isoformat() if identity.created_at else None
        }, "Identity retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get identity", current_user.id)
        return ResponseService.server_error()


@identities_api_v2_bp.route('/<int:identity_id>', methods=['PUT'])
@login_required
@api_rate_limit()
def update_identity(identity_id):
    """Update an identity."""
    try:
        identity = Identity.query.filter_by(id=identity_id, user_id=current_user.id).first()
        
        if not identity:
            return ResponseService.not_found("Identity not found")
        
        data = request.get_json() or {}
        
        success, error = IdentityService.update_identity(identity, **data)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('UPDATE', 'Identity', current_user.id, identity.id, data)
        
        return ResponseService.success({'id': identity.id}, "Identity updated successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to update identity", current_user.id)
        return ResponseService.server_error()


@identities_api_v2_bp.route('/<int:identity_id>', methods=['DELETE'])
@login_required
@api_rate_limit()
def delete_identity_api(identity_id):
    """Delete an identity."""
    try:
        identity = Identity.query.filter_by(id=identity_id, user_id=current_user.id).first()
        
        if not identity:
            return ResponseService.not_found("Identity not found")
        
        success, error = IdentityService.delete_identity(identity)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('DELETE', 'Identity', current_user.id, identity.id)
        
        return ResponseService.success({}, "Identity deleted successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to delete identity", current_user.id)
        return ResponseService.server_error()


@identities_api_v2_bp.route('/<int:identity_id>/habits', methods=['GET'])
@login_required
@api_rate_limit()
def get_identity_habits(identity_id):
    """Get all habits linked to an identity."""
    try:
        identity = Identity.query.filter_by(id=identity_id, user_id=current_user.id).first()
        
        if not identity:
            return ResponseService.not_found("Identity not found")
        
        habits = IdentityService.get_identity_habits(identity)
        
        habits_data = [{
            'id': h.id,
            'name': h.name,
            'streak': h.streak or 0
        } for h in habits]
        
        return ResponseService.success(habits_data, "Identity habits retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get identity habits", current_user.id)
        return ResponseService.server_error()


@identities_api_v2_bp.route('/<int:identity_id>/stats', methods=['GET'])
@login_required
@api_rate_limit()
def get_identity_stats(identity_id):
    """Get statistics for an identity."""
    try:
        identity = Identity.query.filter_by(id=identity_id, user_id=current_user.id).first()
        
        if not identity:
            return ResponseService.not_found("Identity not found")
        
        stats = IdentityService.get_identity_stats(identity, current_user)
        
        return ResponseService.success(stats, "Identity statistics retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get identity stats", current_user.id)
        return ResponseService.server_error()
