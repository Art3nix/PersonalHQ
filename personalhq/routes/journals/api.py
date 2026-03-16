"""Module defining the API routes for Journals."""

from flask import Blueprint, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.journals import Journal, JournalFrequency
from personalhq.models.journalentries import JournalEntry
from personalhq.models.journalprompts import JournalPrompt

journals_api_bp = Blueprint('journals_api', __name__, url_prefix='/actions/journals')

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
    """Updates an existing Journal's name, description, icon, and frequency."""
    journal = db.session.get(Journal, journal_id)
    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journals_view.index'))

    name = request.form.get('name')
    description = request.form.get('description')
    color = request.form.get('color')
    icon = request.form.get('icon') # Now we grab the icon!
    frequency_val = request.form.get('frequency')

    if name:
        journal.name = name.strip()
        journal.description = description.strip() if description else None
        
        if color: 
            journal.color = color
            
        if icon: 
            journal.icon = icon.strip() # Now we save it!

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
