"""Refactored Brain Dump / Inbox API routes using service layer."""

from flask import Blueprint, request
from flask_login import login_required, current_user
from personalhq.models.braindumps import BrainDump
from personalhq.services.braindump_service import BrainDumpServiceV2
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

braindump_api_v2_bp = Blueprint('braindump_api_v2', __name__, url_prefix='/api/v2/inbox')


@braindump_api_v2_bp.route('', methods=['GET'])
@login_required
@api_rate_limit()
def get_inbox():
    """Get all inbox entries for current user."""
    try:
        status = request.args.get('status', 'inbox')
        limit = request.args.get('limit', 100, type=int)
        
        entries = BrainDumpServiceV2.get_inbox_entries(current_user, status, limit)
        
        entries_data = [{
            'id': e.id,
            'content': e.content,
            'status': e.status,
            'tags': e.tags,
            'priority': e.priority if hasattr(e, 'priority') else 'medium',
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries]
        
        return ResponseService.success(entries_data, "Inbox entries retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get inbox", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_entry():
    """Create a new brain dump entry."""
    try:
        data = request.get_json() or {}
        
        entry, error = BrainDumpServiceV2.create_entry(
            current_user,
            data.get('content'),
            data.get('source', 'manual'),
            data.get('tags')
        ) if hasattr(BrainDumpServiceV2, 'create_entry') else (None, "Not implemented")
        
        if not entry:
            # Fallback to original save_thought
            from personalhq.services.braindump_service import save_thought
            result = save_thought(current_user.id, data.get('content'))
            if 'error' in result:
                return ResponseService.error(result['error'], 400)
            return ResponseService.created({'id': result['id']}, "Entry created successfully")
        
        LoggingService.log_crud('CREATE', 'BrainDump', current_user.id, entry.id)
        
        return ResponseService.created({
            'id': entry.id,
            'content': entry.content,
            'status': entry.status
        }, "Entry created successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to create entry", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/<int:entry_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_entry(entry_id):
    """Get a specific inbox entry."""
    try:
        entry = BrainDump.query.filter_by(id=entry_id, user_id=current_user.id).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        return ResponseService.success({
            'id': entry.id,
            'content': entry.content,
            'status': entry.status,
            'tags': entry.tags,
            'priority': entry.priority if hasattr(entry, 'priority') else 'medium',
            'created_at': entry.created_at.isoformat() if entry.created_at else None
        }, "Entry retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get entry", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/<int:entry_id>', methods=['PUT'])
@login_required
@api_rate_limit()
def update_entry(entry_id):
    """Update an inbox entry."""
    try:
        entry = BrainDump.query.filter_by(id=entry_id, user_id=current_user.id).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        data = request.get_json() or {}
        
        success, error = BrainDumpServiceV2.update_entry(entry, **data)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('UPDATE', 'BrainDump', current_user.id, entry.id, data)
        
        return ResponseService.success({'id': entry.id}, "Entry updated successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to update entry", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/<int:entry_id>', methods=['DELETE'])
@login_required
@api_rate_limit()
def delete_entry(entry_id):
    """Delete an inbox entry (requires confirmation)."""
    try:
        entry = BrainDump.query.filter_by(id=entry_id, user_id=current_user.id).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        success, error = BrainDumpServiceV2.delete_entry(entry)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('DELETE', 'BrainDump', current_user.id, entry.id)
        
        return ResponseService.success({}, "Entry deleted successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to delete entry", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/<int:entry_id>/mark-done', methods=['POST'])
@login_required
@api_rate_limit()
def mark_done(entry_id):
    """Mark an entry as done."""
    try:
        entry = BrainDump.query.filter_by(id=entry_id, user_id=current_user.id).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        success, error = BrainDumpServiceV2.mark_as_done(entry)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('MARK_DONE', 'BrainDump', current_user.id, entry.id)
        
        return ResponseService.success({'id': entry.id, 'status': 'done'}, "Entry marked as done")
    except Exception as e:
        LoggingService.log_error(e, "Failed to mark entry as done", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/<int:entry_id>/mark-processing', methods=['POST'])
@login_required
@api_rate_limit()
def mark_processing(entry_id):
    """Mark an entry as processing."""
    try:
        entry = BrainDump.query.filter_by(id=entry_id, user_id=current_user.id).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        success, error = BrainDumpServiceV2.mark_as_processing(entry)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('MARK_PROCESSING', 'BrainDump', current_user.id, entry.id)
        
        return ResponseService.success({'id': entry.id, 'status': 'processing'}, "Entry marked as processing")
    except Exception as e:
        LoggingService.log_error(e, "Failed to mark entry as processing", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/stats', methods=['GET'])
@login_required
@api_rate_limit()
def get_stats():
    """Get inbox statistics."""
    try:
        stats = BrainDumpServiceV2.get_inbox_stats(current_user)
        
        return ResponseService.success(stats, "Inbox statistics retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get inbox stats", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/by-tag/<tag>', methods=['GET'])
@login_required
@api_rate_limit()
def get_by_tag(tag):
    """Get entries with a specific tag."""
    try:
        entries = BrainDumpServiceV2.get_entries_by_tag(current_user, tag)
        
        entries_data = [{
            'id': e.id,
            'content': e.content,
            'status': e.status,
            'tags': e.tags
        } for e in entries]
        
        return ResponseService.success(entries_data, f"Entries with tag '{tag}' retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get entries by tag", current_user.id)
        return ResponseService.server_error()


@braindump_api_v2_bp.route('/recent', methods=['GET'])
@login_required
@api_rate_limit()
def get_recent():
    """Get recent inbox entries."""
    try:
        days_back = request.args.get('days_back', 30, type=int)
        entries = BrainDumpServiceV2.get_all_entries(current_user, days_back)
        
        entries_data = [{
            'id': e.id,
            'content': e.content,
            'status': e.status,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries]
        
        return ResponseService.success(entries_data, f"Recent entries from last {days_back} days")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get recent entries", current_user.id)
        return ResponseService.server_error()
