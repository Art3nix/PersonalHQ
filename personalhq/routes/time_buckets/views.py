"""HTML View routes for the Time Buckets roadmap."""

from flask import Blueprint, render_template, request, redirect, url_for
from flask_login import login_required, current_user
from datetime import datetime
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.coretheme import CoreTheme
from personalhq.models.emotionalvalue import EmotionalValue
from personalhq.extensions import db

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

@time_buckets_view_bp.route('/set_dob', methods=['POST'])
@login_required
def set_dob():
    """Saves the user's Date of Birth so the timeline can function."""
    dob_str = request.form.get('date_of_birth')
    if dob_str:
        current_user.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))
