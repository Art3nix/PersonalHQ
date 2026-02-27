"""HTML View routes for the Time Buckets roadmap."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.timebuckets import TimeBucket

time_buckets_view_bp = Blueprint('time_buckets_view', __name__, url_prefix='/life')

@time_buckets_view_bp.route('/')
@login_required
def manage():
    """Renders the Life Map / Time Buckets management page."""
    # Fetch all buckets in chronological order
    buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.start_date.asc()).all()
    
    return render_template(
        'time_buckets/manage.html',
        buckets=buckets
    )