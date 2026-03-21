"""Refactored Identities API routes using service layer."""

from flask import Blueprint, request
from flask_login import login_required, current_user
from personalhq.models.identities import Identity
from personalhq.services.identity_service import IdentityService
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

identities_api_v2_bp = Blueprint('identities_api_v2', __name__, url_prefix='/api/v2/identities')


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
            'reinforcing_sentence': i.reinforcing_sentence,
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
def create_identity():
    """Create a new identity."""
    try:
        data = request.get_json() or {}
        
        identity, error = IdentityService.create_identity(
            current_user,
            data.get('name'),
            data.get('reinforcing_sentence'),
            data.get('color', '#3B82F6')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'Identity', current_user.id, identity.id, {'name': identity.name})
        
        return ResponseService.created({
            'id': identity.id,
            'name': identity.name,
            'color': identity.color if hasattr(identity, 'color') else None
        }, "Identity created successfully")
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
            'reinforcing_sentence': identity.reinforcing_sentence,
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
def delete_identity(identity_id):
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
