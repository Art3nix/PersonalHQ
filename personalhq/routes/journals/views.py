"""Module defining the HTML View routes for Journals."""

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.journals import Journal, JournalFrequency
from personalhq.models.journalentries import JournalEntry
from personalhq.services import journal_service

journals_view_bp = Blueprint('journals_view', __name__, url_prefix='/journals')

@journals_view_bp.route('/')
@login_required
def index():
    """Renders the main Journals overview and the creation modal."""
    journals = Journal.query.filter_by(user_id=current_user.id).all()

    return render_template(
        'journals/index.html',
        journals=journals,
        JournalFrequency=JournalFrequency # Pass this to the template
    )

@journals_view_bp.route('/<int:journal_id>/write')
@login_required
def write(journal_id):
    """The Zen Mode Editor for writing or editing an entry."""
    journal = db.session.get(Journal, journal_id)
    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journals_view.index'))

    # Check if we are trying to edit an existing entry
    edit_id = request.args.get('edit_id', type=int)
    entry_to_edit = None
    if edit_id:
        entry_to_edit = db.session.get(JournalEntry, edit_id)
        # Security check
        if not entry_to_edit or entry_to_edit.journal_id != journal.id:
            entry_to_edit = None

    active_prompt = journal_service.get_active_prompt(journal)

    return render_template(
        'journals/write.html',
        journal=journal,
        entries=journal.entries, 
        active_prompt=active_prompt,
        prompts=journal.prompts,
        entry_to_edit=entry_to_edit # Pass the entry to the template
    )

@journals_view_bp.route('/<int:journal_id>')
@login_required
def entries(journal_id):
    """Renders a beautiful masonry grid of all past journal entries."""
    journal = db.session.get(Journal, journal_id)
    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journals_view.index'))

    # Grab all entries, newest first
    journal_entries = JournalEntry.query.filter_by(journal_id=journal.id).order_by(JournalEntry.created_at.desc()).all()

    return render_template(
        'journals/entries.html',
        journal=journal,
        entries=journal_entries, 
        JournalFrequency=JournalFrequency
    )
