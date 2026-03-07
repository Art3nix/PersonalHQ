"""API routes for handling Time Bucket data."""

from datetime import datetime
from flask import Blueprint, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.experiences import Experience
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.bucket_experience import BucketExperience

time_buckets_api_bp = Blueprint('time_buckets_api', __name__, url_prefix='/actions/life')

@time_buckets_api_bp.route('/experiences/create', methods=['POST'])
@login_required
def create_experience():
    """Creates a new Experience and links it to a Time Bucket."""
    name = request.form.get('name')
    bucket_id = request.form.get('bucket_id')
    details = request.form.get('details')

    if not name or not bucket_id:
        return redirect(url_for('time_buckets_view.manage'))

    # 1. Create the base Experience
    new_exp = Experience(
        name=name.strip(),
        details=details.strip() if details else None
    )
    db.session.add(new_exp)
    db.session.flush()

    # 2. Link it to the selected Time Bucket
    link = BucketExperience(
        bucket_id=int(bucket_id),
        experience_id=new_exp.id
    )
    db.session.add(link)
    db.session.commit()

    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/experiences/<int:exp_id>/toggle', methods=['POST'])
@login_required
def toggle_experience(exp_id):
    """Toggles the completion status of an experience."""
    exp = db.session.get(Experience, exp_id)

    if not exp:
        return jsonify({"status": "error"}), 404

    # Flip the boolean
    exp.is_completed = not exp.is_completed
    db.session.commit()

    return jsonify({"status": "success", "is_completed": exp.is_completed})

@time_buckets_api_bp.route('/buckets/create', methods=['POST'])
@login_required
def create_bucket():
    """Creates a new Time Bucket (Decade) on the timeline."""
    name = request.form.get('name')
    theme = request.form.get('theme')
    start_date_str = request.form.get('start_date')
    end_date_str = request.form.get('end_date')

    if not name or not start_date_str or not end_date_str:
        return redirect(url_for('time_buckets_view.manage'))

    # Convert the HTML 'YYYY-MM-DD' strings to Python date objects
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()

    new_bucket = TimeBucket(
        user_id=current_user.id,
        name=name.strip(),
        theme=theme.strip() if theme else None,
        start_date=start_date,
        end_date=end_date
    )

    db.session.add(new_bucket)
    db.session.commit()

    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/buckets/<int:bucket_id>/delete', methods=['POST'])
@login_required
def delete_bucket(bucket_id):
    """Deletes an entire Time Bucket (Decade) and its associated experiences."""
    bucket = db.session.get(TimeBucket, bucket_id)

    if bucket and bucket.user_id == current_user.id:
        db.session.delete(bucket)
        db.session.commit()

    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/experiences/<int:exp_id>/delete', methods=['POST'])
@login_required
def delete_experience(exp_id):
    """Deletes a specific experience from a Time Bucket."""
    exp = db.session.get(Experience, exp_id)

    if exp:
        # Security check: Ensure the user owns the bucket this experience is in
        bucket_link = BucketExperience.query.filter_by(experience_id=exp.id).first()
        if bucket_link:
            bucket = db.session.get(TimeBucket, bucket_link.bucket_id)
            if bucket and bucket.user_id == current_user.id:
                db.session.delete(exp)
                db.session.commit()
                
    return redirect(url_for('time_buckets_view.manage'))
