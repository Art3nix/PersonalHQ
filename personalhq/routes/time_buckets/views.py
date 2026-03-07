"""HTML View routes for the Time Buckets roadmap."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.coretheme import CoreTheme
from personalhq.models.emotionalvalue import EmotionalValue

time_buckets_view_bp = Blueprint('time_buckets_view', __name__, url_prefix='/life')

@time_buckets_view_bp.route('/')
@login_required
def manage():
    """Renders the Life Map / Time Buckets management page."""
    # Fetch all buckets in chronological order
    buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.start_date.asc()).all()
    core_themes = CoreTheme.query.all()
    emotional_values = EmotionalValue.query.all()

    return render_template('time_buckets/manage.html',
                        buckets=buckets,
                        core_themes=core_themes,
                        emotional_values=emotional_values)
