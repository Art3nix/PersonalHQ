"""Module defining the API routes for Journals."""

from flask import Blueprint, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.journals import Journal, JournalFrequency
from personalhq.models.journalentries import JournalEntry
from personalhq.models.journalprompts import JournalPrompt

journals_api_bp = Blueprint('journals_api', __name__, url_prefix='/api/v1/journals')

@journals_api_bp.route('/<int:journal_id>/entries', methods=['POST'])
@login_required
def add_entry(journal_id):
    """Receives form data to create a new journal entry."""
    journal = db.session.get(Journal, journal_id)

    if not journal or journal.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Journal not found"}), 404

    content = request.form.get('content')

    if content and content.strip():
        new_entry = JournalEntry(
            journal_id=journal.id,
            content=content.strip()
        )
        db.session.add(new_entry)
        db.session.commit()

    # Redirect back to the journal view after saving
    return redirect(url_for('journals_view.entries', journal_id=journal.id))

@journals_api_bp.route('/entries/<int:entry_id>/edit', methods=['POST'])
@login_required
def edit_entry(entry_id):
    """Updates the text of a specific journal entry."""
    entry = db.session.get(JournalEntry, entry_id)
    if not entry:
        return redirect(request.referrer or url_for('journals_view.index'))

    # Security check: Ensure the user owns the journal this entry belongs to
    journal = db.session.get(Journal, entry.journal_id)
    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journals_view.index'))

    content = request.form.get('content')
    if content:
        entry.content = content.strip()
        db.session.commit()

    return redirect(url_for('journals_view.entries', journal_id=journal.id))

@journals_api_bp.route('/entries/<int:entry_id>/delete', methods=['POST'])
@login_required
def delete_entry(entry_id):
    """Deletes a specific journal entry."""
    entry = db.session.get(JournalEntry, entry_id)

    # Check that the entry exists and belongs to a journal owned by the current user
    if entry and entry.journal.user_id == current_user.id:
        journal_id = entry.journal_id
        db.session.delete(entry)
        db.session.commit()
        return redirect(url_for('journals_view.entries', journal_id=journal_id))

    return jsonify({"status": "error"}), 403


@journals_api_bp.route('/create', methods=['POST'])
@login_required
def create_journal():
    """Creates a new journal category."""
    name = request.form.get('name')
    description = request.form.get('description')
    icon = request.form.get('icon', '📓')
    color = request.form.get('color', 'indigo')
    frequency_val = request.form.get('frequency', 'DAILY').upper()

    # Safely convert the string from the form into your Enum
    try:
        frequency = JournalFrequency[frequency_val]
    except KeyError:
        frequency = JournalFrequency.DAILY

    if name and name.strip():
        new_journal = Journal(
            user_id=current_user.id,
            name=name.strip(),
            description=description.strip() if description else None,
            color=color,
            icon=icon.strip(),
            frequency=frequency
        )
        db.session.add(new_journal)
        db.session.commit()

    return redirect(url_for('journals_view.index'))

@journals_api_bp.route('/<int:journal_id>/edit', methods=['POST'])
@login_required
def edit_journal(journal_id):
    """Updates an existing Journal's name, description, and frequency."""
    journal = db.session.get(Journal, journal_id)
    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journals_view.index'))

    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color')
    frequency_val = request.form.get('frequency')

    if name:
        journal.name = name.strip()
        journal.description = description.strip() if description else None
        if color: journal.color = color

        # Safely update the frequency enum
        if frequency_val:
            try:
                journal.frequency = JournalFrequency[frequency_val.upper()]
            except KeyError:
                pass

        db.session.commit()

    # Bounce back to the page they clicked Edit from
    return redirect(request.referrer or url_for('journals_view.index'))

@journals_api_bp.route('/<int:journal_id>/delete', methods=['POST'])
@login_required
def delete_journal(journal_id):
    """Deletes an entire journal, along with its entries and prompts."""
    journal = db.session.get(Journal, journal_id)

    if journal and journal.user_id == current_user.id:
        db.session.delete(journal)
        db.session.commit()

    return redirect(url_for('journals_view.index'))

@journals_api_bp.route('/<int:journal_id>/prompts/create', methods=['POST'])
@login_required
def add_prompt(journal_id):
    """Adds a new rotating prompt to a specific journal."""
    journal = db.session.get(Journal, journal_id)

    if not journal or journal.user_id != current_user.id:
        return jsonify({"status": "error", "message": "Unauthorized"}), 403

    text = request.form.get('text')

    if text and text.strip():
        new_prompt = JournalPrompt(
            journal_id=journal.id,
            text=text.strip()
        )
        db.session.add(new_prompt)
        db.session.commit()

    return redirect(request.referrer or url_for('journals_view.write', journal_id=journal.id))

@journals_api_bp.route('/prompts/<int:prompt_id>/edit', methods=['POST'])
@login_required
def edit_prompt(prompt_id):
    """Updates the text of a specific journal prompt."""
    prompt = db.session.get(JournalPrompt, prompt_id)
    if not prompt:
        return redirect(request.referrer or url_for('journals_view.index'))

    # Security check: Ensure the user owns the journal this prompt belongs to
    journal = db.session.get(Journal, prompt.journal_id)
    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journals_view.index'))

    text = request.form.get('text')
    if text:
        prompt.text = text.strip()
        db.session.commit()

    return redirect(request.referrer or url_for('journals_view.index'))

@journals_api_bp.route('/prompts/<int:prompt_id>/delete', methods=['POST'])
@login_required
def delete_prompt(prompt_id):
    """Deletes a specific prompt."""
    prompt = db.session.get(JournalPrompt, prompt_id)

    # Security check using the relationship to the parent journal
    if prompt and prompt.journal.user_id == current_user.id:
        journal_id = prompt.journal_id
        db.session.delete(prompt)
        db.session.commit()
        return redirect(request.referrer or url_for('journals_view.write', journal_id=journal_id))

    return jsonify({"status": "error", "message": "Unauthorized"}), 403
"""Refactored Journals API routes using service layer."""

from flask import Blueprint, request
from flask_login import login_required, current_user
from personalhq.models.journals import Journal, JournalEntry
from personalhq.services.journal_service import JournalServiceV2
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

journals_api_v2_bp = Blueprint('journals_api_v2', __name__, url_prefix='/api/v2/journals')


@journals_api_v2_bp.route('', methods=['GET'])
@login_required
@api_rate_limit()
def get_journals():
    """Get all journals for current user."""
    try:
        journals = JournalServiceV2.get_user_journals(current_user)
        
        journals_data = [{
            'id': j.id,
            'name': j.name,
            'description': j.description,
            'prompt': j.prompt,
            'created_at': j.created_at.isoformat() if j.created_at else None
        } for j in journals]
        
        return ResponseService.success(journals_data, "Journals retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get journals", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('', methods=['POST'])
@login_required
@api_rate_limit()
def create_journal():
    """Create a new journal."""
    try:
        data = request.get_json() or {}
        
        journal, error = JournalServiceV2.create_journal(
            current_user,
            data.get('name'),
            data.get('description'),
            data.get('prompt')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'Journal', current_user.id, journal.id, {'name': journal.name})
        
        return ResponseService.created({
            'id': journal.id,
            'name': journal.name
        }, "Journal created successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to create journal", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_journal(journal_id):
    """Get a specific journal."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        return ResponseService.success({
            'id': journal.id,
            'name': journal.name,
            'description': journal.description,
            'prompt': journal.prompt,
            'created_at': journal.created_at.isoformat() if journal.created_at else None
        }, "Journal retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get journal", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>', methods=['PUT'])
@login_required
@api_rate_limit()
def update_journal(journal_id):
    """Update a journal."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        data = request.get_json() or {}
        
        success, error = JournalServiceV2.update_journal(journal, **data)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('UPDATE', 'Journal', current_user.id, journal.id, data)
        
        return ResponseService.success({'id': journal.id}, "Journal updated successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to update journal", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>', methods=['DELETE'])
@login_required
@api_rate_limit()
def delete_journal(journal_id):
    """Delete a journal (requires confirmation)."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        success, error = JournalServiceV2.delete_journal(journal)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('DELETE', 'Journal', current_user.id, journal.id)
        
        return ResponseService.success({}, "Journal deleted successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to delete journal", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>/entries', methods=['GET'])
@login_required
@api_rate_limit()
def get_entries(journal_id):
    """Get all entries for a journal."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        entries = JournalServiceV2.get_journal_entries(journal, limit, offset)
        
        entries_data = [{
            'id': e.id,
            'title': e.title,
            'content': e.content[:100] + '...' if len(e.content) > 100 else e.content,
            'date_written': e.date_written.isoformat() if e.date_written else None,
            'created_at': e.created_at.isoformat() if e.created_at else None
        } for e in entries]
        
        return ResponseService.success(entries_data, "Journal entries retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get journal entries", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>/entries', methods=['POST'])
@login_required
@api_rate_limit()
def create_entry(journal_id):
    """Create a new journal entry."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        data = request.get_json() or {}
        
        entry, error = JournalServiceV2.create_entry(
            journal,
            data.get('content'),
            data.get('title'),
            data.get('date_written')
        )
        
        if error:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('CREATE', 'JournalEntry', current_user.id, entry.id)
        
        return ResponseService.created({
            'id': entry.id,
            'title': entry.title,
            'date_written': entry.date_written.isoformat() if entry.date_written else None
        }, "Journal entry created successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to create journal entry", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/entries/<int:entry_id>', methods=['GET'])
@login_required
@api_rate_limit()
def get_entry(entry_id):
    """Get a specific journal entry."""
    try:
        entry = JournalEntry.query.join(Journal).filter(
            JournalEntry.id == entry_id,
            Journal.user_id == current_user.id
        ).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        return ResponseService.success({
            'id': entry.id,
            'title': entry.title,
            'content': entry.content,
            'date_written': entry.date_written.isoformat() if entry.date_written else None,
            'created_at': entry.created_at.isoformat() if entry.created_at else None
        }, "Journal entry retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get journal entry", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/entries/<int:entry_id>', methods=['PUT'])
@login_required
@api_rate_limit()
def update_entry(entry_id):
    """Update a journal entry."""
    try:
        entry = JournalEntry.query.join(Journal).filter(
            JournalEntry.id == entry_id,
            Journal.user_id == current_user.id
        ).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        data = request.get_json() or {}
        
        success, error = JournalServiceV2.update_entry(entry, **data)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('UPDATE', 'JournalEntry', current_user.id, entry.id, data)
        
        return ResponseService.success({'id': entry.id}, "Journal entry updated successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to update journal entry", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/entries/<int:entry_id>', methods=['DELETE'])
@login_required
@api_rate_limit()
def delete_entry(entry_id):
    """Delete a journal entry (requires confirmation)."""
    try:
        entry = JournalEntry.query.join(Journal).filter(
            JournalEntry.id == entry_id,
            Journal.user_id == current_user.id
        ).first()
        
        if not entry:
            return ResponseService.not_found("Entry not found")
        
        success, error = JournalServiceV2.delete_entry(entry)
        
        if not success:
            return ResponseService.error(error, 400)
        
        LoggingService.log_crud('DELETE', 'JournalEntry', current_user.id, entry.id)
        
        return ResponseService.success({}, "Journal entry deleted successfully")
    except Exception as e:
        LoggingService.log_error(e, "Failed to delete journal entry", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>/stats', methods=['GET'])
@login_required
@api_rate_limit()
def get_stats(journal_id):
    """Get statistics for a journal."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        days_back = request.args.get('days_back', 30, type=int)
        stats = JournalServiceV2.get_journal_stats(journal, days_back)
        
        return ResponseService.success(stats, "Journal statistics retrieved")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get journal stats", current_user.id)
        return ResponseService.server_error()


@journals_api_v2_bp.route('/<int:journal_id>/recent', methods=['GET'])
@login_required
@api_rate_limit()
def get_recent(journal_id):
    """Get recent entries for a journal."""
    try:
        journal = Journal.query.filter_by(id=journal_id, user_id=current_user.id).first()
        
        if not journal:
            return ResponseService.not_found("Journal not found")
        
        days_back = request.args.get('days_back', 30, type=int)
        entries = JournalServiceV2.get_recent_entries(journal, days_back)
        
        entries_data = [{
            'id': e.id,
            'title': e.title,
            'content': e.content[:100] + '...' if len(e.content) > 100 else e.content,
            'date_written': e.date_written.isoformat() if e.date_written else None
        } for e in entries]
        
        return ResponseService.success(entries_data, f"Recent entries from last {days_back} days")
    except Exception as e:
        LoggingService.log_error(e, "Failed to get recent entries", current_user.id)
        return ResponseService.server_error()
