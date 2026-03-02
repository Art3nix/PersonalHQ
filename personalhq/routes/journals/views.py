"""Module defining the HTML View routes for Journals."""

from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.journals import Journal, JournalFrequency
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

@journals_view_bp.route('/<int:journal_id>')
@login_required
def view_journal(journal_id):
    """Renders a specific journal, its prompts, and its past entries."""
    journal = db.session.get(Journal, journal_id)

    if not journal or journal.user_id != current_user.id:
        return redirect(url_for('journal_view.index'))

    # Get the calculated prompt for the UI
    active_prompt = journal_service.get_active_prompt(journal)

    return render_template(
        'journals/view.html',
        journal=journal,
        entries=journal.entries, 
        active_prompt=active_prompt, # Pass the single prompt instead of the full list
        prompts=journal.prompts
    )
