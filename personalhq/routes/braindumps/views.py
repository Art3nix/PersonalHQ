"""HTML View routes for the Inbox/BrainDumps."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.braindumps import BrainDump
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.identities import Identity
from personalhq.models.journals import Journal

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
    # START INBOX AI MOCK DATA
    # ==========================================
    TEST_AI_NUDGES = True
    
    ai_inbox_overload = None
    ai_inbox_subtitle = None
    ai_empty_state = None

    if TEST_AI_NUDGES:
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
    # END INBOX AI MOCK DATA
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
