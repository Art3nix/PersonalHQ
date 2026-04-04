"""Module defining the HTML View routes for Journals."""

from flask import Blueprint, render_template, redirect, url_for, request
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.journals import Journal, JournalFrequency
from personalhq.models.journalentries import JournalEntry
from personalhq.models.journalprompts import JournalPrompt
from personalhq.services import journal_service
from personalhq.services.time_service import get_local_today

journals_view_bp = Blueprint('journals_view', __name__, url_prefix='/journals')

@journals_view_bp.route('/')
@login_required
def index():
    """Renders the main Journals overview and the creation modal."""
    journals = Journal.query.filter_by(user_id=current_user.id).all()

    # Fetch 2 most recent entries per journal for preview
    recent_entries = {}
    for journal in journals:
        journal_entries = JournalEntry.query.filter_by(journal_id=journal.id).order_by(
            JournalEntry.created_at.desc()
        ).limit(2).all()
        recent_entries[journal.id] = journal_entries

    # ==========================================
    # START JOURNALS AI MOCK DATA
    # ==========================================
    TEST_AI_NUDGES = True
    ai_journals_subtitle = None
    ai_journals_empty_state = None

    if TEST_AI_NUDGES:
        if not journals:
            ai_journals_empty_state = "A clear mind executes better. Create a 'Daily Brain Dump' or a 'Gratitude' journal to start processing your thoughts."
        else:
            # 1. Global Subtitle
            # Check if they have written anything today across all journals
            today = get_local_today()
            wrote_today = any(
                entry.created_at.date() == today
                for entries in recent_entries.values()
                for entry in entries
            )

            if wrote_today:
                ai_journals_subtitle = "Your mind is decluttered. You have successfully processed your thoughts today."
            else:
                ai_journals_subtitle = "You haven't written today. Take 2 minutes to document what is on your mind."

            # 2. Individual Journal Insights
            for journal in journals:
                all_entries = recent_entries.get(journal.id, [])

                if not all_entries:
                    journal.ai_insight = "This space is completely empty. What is holding you back from writing your first entry here?"
                else:
                    last_entry_date = all_entries[0].created_at.date()
                    days_since_last = (today - last_entry_date).days

                    if days_since_last == 0:
                        journal.ai_insight = "Entry logged today. Momentum is building."
                    elif days_since_last <= 3:
                        journal.ai_insight = f"Last updated {days_since_last} days ago. Keep the habit alive."
                    else:
                        journal.ai_insight = f"It has been {days_since_last} days since you last wrote here. Is there a lingering thought you need to get out?"
    # ==========================================
    # END JOURNALS AI MOCK DATA
    # ==========================================

    return render_template(
        'journals/index.html',
        journals=journals,
        recent_entries=recent_entries,
        JournalFrequency=JournalFrequency,
        ai_journals_subtitle=ai_journals_subtitle,
        ai_journals_empty_state=ai_journals_empty_state
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

    active_prompt = None
    # If we just added a new prompt (via ?new_id=XXX)
    new_prompt_id = request.args.get('new_id', type=int)
    
    if new_prompt_id:
        active_prompt = JournalPrompt.query.filter_by(id=new_prompt_id, journal_id=journal.id).first()
    
    # If we are editing an entry, use its original prompt
    if not active_prompt and entry_to_edit and entry_to_edit.prompt_id:
        active_prompt = db.session.get(JournalPrompt, entry_to_edit.prompt_id)
    
    # Get the standard rotation prompt
    if not active_prompt and journal.prompts:
        active_prompt = journal_service.get_active_prompt(journal)
        
        # Absolute bulletproof fallback just in case the service returns None
        if not active_prompt:
            active_prompt = journal.prompts[0]

    # ==========================================
    # START WRITING AI MOCK DATA
    # ==========================================
    TEST_AI_NUDGES = True
    ai_writing_coach = None
    ai_prompt_suggestion = None

    if TEST_AI_NUDGES:
        # 1. Warm-Up Coach
        if entry_to_edit:
            ai_writing_coach = "You are editing a past entry. Be careful not to rewrite history; just clarify the thoughts you had in that specific moment."
        else:
            # Here you could check time of day, streak length, etc.
            ai_writing_coach = "Drop your mental filters. The blank page isn't judging you. Write whatever comes to mind first, even if it's just 'I don't know what to write today'."

        # 2. Sidebar Prompt Engineer
        # In production, an LLM would read their past 5 entries and generate a prompt they haven't answered yet.
        ai_prompt_suggestion = "What is one difficult decision I am currently avoiding?"
    # ==========================================
    # END WRITING AI MOCK DATA
    # ==========================================

    return render_template(
        'journals/write.html',
        journal=journal,
        entries=journal.entries, 
        active_prompt=active_prompt,
        prompts=journal.prompts,
        entry_to_edit=entry_to_edit,
        ai_writing_coach=ai_writing_coach,
        ai_prompt_suggestion=ai_prompt_suggestion
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

    # ==========================================
    # START ARCHIVE AI MOCK DATA
    # ==========================================
    TEST_AI_NUDGES = True
    ai_archive_insight = None
    ai_archive_empty_state = None

    if TEST_AI_NUDGES:
        if not journal_entries:
            ai_archive_empty_state = f"This '{journal.name}' journal is a blank slate. Use the Prompts menu to find a starting point and write your first entry."
        else:
            # 1. Macro Archive Insight (Summarizing the journal)
            if len(journal_entries) >= 5:
                ai_archive_insight = "Pattern detected: You consistently write longer entries on weekends. Your stress levels appear lower when you document them."
            else:
                ai_archive_insight = "You've established a baseline. Keep adding entries to unlock deeper pattern recognition."

            # 2. Micro Entry Insights (Attached to individual past entries)
            for i, entry in enumerate(journal_entries):
                # We only want to put insights on SOME entries, not every single one, 
                # to prevent the UI from feeling cluttered.
                content_lower = entry.content.lower()
                
                if i == 0: # Most recent entry
                    entry.ai_insight = "Your latest entry. Notice how your perspective here compares to your older entries below."
                elif "anxious" in content_lower or "worried" in content_lower:
                    entry.ai_insight = "Reflection: Looking back at this now, did the thing you were worried about actually happen?"
                elif "goal" in content_lower or "excited" in content_lower:
                    entry.ai_insight = "Momentum check: Have you taken the next physical step toward this since you wrote it?"
                elif len(entry.content.split()) > 100 and i % 3 == 0:
                    # Randomly tagging long, deep entries
                    entry.ai_insight = "Deep dive. This entry contains significant emotional processing."
                else:
                    entry.ai_insight = None
    # ==========================================
    # END ARCHIVE AI MOCK DATA
    # ==========================================

    return render_template(
        'journals/entries.html',
        journal=journal,
        entries=journal_entries,
        prompts=journal.prompts,
        JournalFrequency=JournalFrequency,
        ai_archive_insight=ai_archive_insight,
        ai_archive_empty_state=ai_archive_empty_state
    )
