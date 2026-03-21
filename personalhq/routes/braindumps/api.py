"""API routes for handling BrainDump data actions."""

from datetime import datetime
from flask import Blueprint, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from personalhq.extensions import db
from personalhq.services import braindump_service
from personalhq.models.braindumps import BrainDump
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.experiences import Experience
from personalhq.models.bucket_experience import BucketExperience
from personalhq.models.journalentries import JournalEntry

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

@braindumps_api_bp.route('/<int:dump_id>/edit', methods=['POST'])
@login_required
def edit_dump(dump_id):
    """Updates the raw text of a thought in the Inbox."""
    dump = db.session.get(BrainDump, dump_id)
    if not dump or dump.user_id != current_user.id:
        return redirect(url_for('braindumps_view.index'))

    content = request.form.get('content')
    if content:
        dump.content = content.strip()
        db.session.commit()

    return redirect(url_for('braindumps_view.index'))

@braindumps_api_bp.route('/<int:dump_id>/delete', methods=['POST'])
@login_required
def delete_dump(dump_id):
    """Deletes a processed thought from the Inbox."""
    dump = db.session.get(BrainDump, dump_id)
    if dump and dump.user_id == current_user.id:
        db.session.delete(dump)
        db.session.commit()

    return redirect(url_for('braindumps_view.index'))

@braindumps_api_bp.route('/<int:dump_id>/convert', methods=['POST'])
@login_required
def convert_dump(dump_id):
    """Converts a BrainDump into a Focus Session or an Experience, then deletes the dump."""
    dump = db.session.get(BrainDump, dump_id)
    if not dump or dump.user_id != current_user.id:
        return redirect(url_for('braindumps_view.index'))

    convert_type = request.form.get('convert_type') # 'focus' or 'experience'
    name = request.form.get('name')

    if convert_type == 'focus':
        target_date_str = request.form.get('target_date')
        duration = request.form.get('target_duration_minutes', type=int)

        # Default to today if no date provided
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else datetime.today().date()

        # Calculate queue order
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

    elif convert_type == 'experience':
        bucket_id = request.form.get('bucket_id')
        details = request.form.get('details')

        if not bucket_id:
            return redirect(url_for('braindumps_view.index'))

        # Experience does not use user_id
        new_exp = Experience(
            name=name.strip(),
            details=details.strip() if details else None
        )
        db.session.add(new_exp)
        db.session.flush()

        link = BucketExperience(
            bucket_id=int(bucket_id),
            experience_id=new_exp.id
        )
        db.session.add(link)

    elif convert_type == 'journal':
        journal_id = request.form.get('journal_id')
        content = request.form.get('journal_content')
        
        if journal_id and content:
            new_entry = JournalEntry(
                journal_id=int(journal_id),
                content=content.strip()
            )
            db.session.add(new_entry)

    # Clear it from the Inbox
    db.session.delete(dump)
    db.session.commit()

    return redirect(url_for('braindumps_view.index'))
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
