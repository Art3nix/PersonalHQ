"""HTML View routes for the Inbox/BrainDumps."""

from flask import Blueprint, render_template, current_app
from flask_login import login_required, current_user
from personalhq.models.braindumps import BrainDump
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.identities import Identity
from personalhq.models.journals import Journal
from personalhq.models.dailynotes import DailyNote
from personalhq.services.time_service import get_logical_today

braindumps_view_bp = Blueprint('braindumps_view', __name__, url_prefix='/inbox')

@braindumps_view_bp.route('/')
@login_required
def index():
    """Renders the Inbox triage page."""
    braindumps = BrainDump.query.filter_by(user_id=current_user.id).order_by(BrainDump.created_at.asc()).all()
    buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.start_date.asc()).all()
    identities = Identity.query.filter_by(user_id=current_user.id).all()
    journals = Journal.query.filter_by(user_id=current_user.id).all()

    # ==========================================
    # AI COACH CONTEXT
    # ==========================================

    daily_note = DailyNote.query.filter_by(user_id=current_user.id, logical_date=get_logical_today(current_user)).first()

    # Fetch from DB (Note: we mapped this to ai_braindump_empty_state in the model)
    ai_inbox_overload = daily_note.ai_inbox_overload if daily_note else None
    ai_inbox_subtitle = daily_note.ai_inbox_subtitle if daily_note else None
    ai_empty_state = daily_note.ai_braindump_empty_state if daily_note else None

    if current_app.config['TEST_AI_NUDGES'] is True:
        # 1. Overload Warning (Triggers if > 30 dumps, or force it for testing)
        if len(braindumps) > 30:
            ai_inbox_overload = f"Your inbox is getting heavy ({len(braindumps)} items). Spend 5 minutes deleting ideas you no longer care about."
        else:
            ai_inbox_subtitle = "Your brain is built for creating ideas, not holding them. What needs to be processed?"
            
        # 2. Empty State
        ai_empty_state = "A clear inbox means a present mind. Go execute today's deep work."

        # 3. Item-Specific Notes
        for dump in braindumps:
            word_count = len(dump.content.split())
            if word_count < 4:
                dump.ai_insight = "This is a bit vague. Is this a project, a task, or just a passing thought?"
            elif "?" in dump.content:
                dump.ai_insight = "Sounds like an open loop. Convert this to a Deep Work session to research it, or discard it if it doesn't matter."
            else:
                dump.ai_insight = None
    # ==========================================

    return render_template(
        'braindumps/inbox.html',
        braindumps=braindumps,
        dump_count=len(braindumps),
        buckets=buckets,
        identities=identities,
        journals=journals,
        ai_inbox_overload=ai_inbox_overload,
        ai_inbox_subtitle=ai_inbox_subtitle,
        ai_empty_state=ai_empty_state
    )
