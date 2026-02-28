"""HTML View routes for the Inbox/BrainDumps."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.braindumps import BrainDump
from personalhq.models.timebuckets import TimeBucket

braindumps_view_bp = Blueprint('braindumps_view', __name__, url_prefix='/inbox')

@braindumps_view_bp.route('/')
@login_required
def index():
    """Renders the Inbox triage page."""
    braindumps = BrainDump.query.filter_by(user_id=current_user.id).order_by(BrainDump.created_at.asc()).all()
    buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.start_date.asc()).all()

    return render_template(
        'inbox.html',
        braindumps=braindumps,
        dump_count=len(braindumps),
        buckets=buckets
    )
