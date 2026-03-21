"""API routes for handling Time Bucket data."""

from datetime import date, timedelta
from flask import Blueprint, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from personalhq.extensions import db
from personalhq.models.experiences import Experience
from personalhq.models.coretheme import CoreTheme
from personalhq.models.emotionalvalue import EmotionalValue
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.bucket_experience import BucketExperience

time_buckets_api_bp = Blueprint('time_buckets_api', __name__, url_prefix='/api/v1/life')

@time_buckets_api_bp.route('/experiences/create', methods=['POST'])
@login_required
def create_experience():
    """Creates a new Experience and links it to a Time Bucket."""
    name = request.form.get('name')
    bucket_id = request.form.get('bucket_id')
    details = request.form.get('details')
    theme_id = request.form.get('theme_id', type=int)
    emotion_id = request.form.get('emotional_value_id', type=int)

    if not name or not bucket_id:
        return redirect(url_for('time_buckets_view.manage'))

    # 1. Create the base Experience using the foreign keys
    new_exp = Experience(
        name=name.strip(),
        details=details.strip() if details else None,
        theme_id=theme_id,
        emotional_value_id=emotion_id
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
    """Creates a new Time Bucket on the timeline."""
    name = request.form.get('name')
    theme = request.form.get('theme')
    start_age = request.form.get('start_age')
    end_age = request.form.get('end_age')

    if not name or not start_age or not end_age or not current_user.date_of_birth:
        return redirect(url_for('time_buckets_view.manage'))

    start_date, end_date = get_bucket_dates_from_age(start_age, end_age, current_user)

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

@time_buckets_api_bp.route('/buckets/<int:bucket_id>/edit', methods=['POST'])
@login_required
def edit_bucket(bucket_id):
    """Updates an existing Time Bucket."""
    bucket = db.session.get(TimeBucket, bucket_id)
    if not bucket or bucket.user_id != current_user.id:
        return redirect(url_for('time_buckets_view.manage'))

    name = request.form.get('name')
    theme = request.form.get('theme')
    start_age = request.form.get('start_age')
    end_age = request.form.get('end_age')

    if name and start_age and end_age:
        bucket.name = name.strip()
        bucket.theme = theme.strip() if theme else None
        
        start_date, end_date = get_bucket_dates_from_age(start_age, end_age, current_user)
        bucket.start_date = start_date
        bucket.end_date = end_date
        db.session.commit()

    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/experiences/<int:exp_id>/edit', methods=['POST'])
@login_required
def edit_experience(exp_id):
    """Updates an existing Experience and its bucket assignment."""
    exp = db.session.get(Experience, exp_id)
    if not exp:
        return redirect(url_for('time_buckets_view.manage'))

    # Security: Ensure the user owns the bucket this experience is currently in
    bucket_link = BucketExperience.query.filter_by(experience_id=exp.id).first()
    if not bucket_link:
         return redirect(url_for('time_buckets_view.manage'))
    
    current_bucket = db.session.get(TimeBucket, bucket_link.bucket_id)
    if not current_bucket or current_bucket.user_id != current_user.id:
         return redirect(url_for('time_buckets_view.manage'))

    name = request.form.get('name')
    details = request.form.get('details')
    new_bucket_id = request.form.get('bucket_id', type=int)
    theme_id = request.form.get('theme_id', type=int)
    emotion_id = request.form.get('emotional_value_id', type=int)

    if name and new_bucket_id:
        exp.name = name.strip()
        exp.details = details.strip() if details else None
        
        # Update the relational fields
        exp.theme_id = theme_id
        exp.emotional_value_id = emotion_id
        
        # Move it to a new time bucket if they changed the dropdown
        if bucket_link.bucket_id != new_bucket_id:
            bucket_link.bucket_id = new_bucket_id
            
        db.session.commit()

    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/buckets/<int:bucket_id>/delete', methods=['POST'])
@login_required
def delete_bucket(bucket_id):
    """Deletes an entire Time Bucket and its associated experiences."""
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

def get_bucket_dates_from_age(start_age, end_age, user):
    """Calculates exact bucket dates based on the user's biological age."""
    dob = user.date_of_birth
    if not dob:
        raise ValueError("User Date of Birth is required.")

    # Start Date: Their birthday on the year they turn start_age
    start_year = dob.year + int(start_age)
    try:
        start_date = date(start_year, dob.month, dob.day)
    except ValueError:
        start_date = date(start_year, 2, 28) # Leap year baby catch!

    # End Date: The day before they turn (end_age + 1)
    end_year = dob.year + int(end_age) + 1
    try:
        next_bday = date(end_year, dob.month, dob.day)
    except ValueError:
        next_bday = date(end_year, 2, 28)

    end_date = next_bday - timedelta(days=1)

    return start_date, end_date

@time_buckets_api_bp.route('/themes/create', methods=['POST'])
@login_required
def create_theme():
    name = request.form.get('name')
    color = request.form.get('color', 'stone')
    if name:
        new_theme = CoreTheme(user_id=current_user.id, name=name.strip(), color=color)
        db.session.add(new_theme)
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/emotions/create', methods=['POST'])
@login_required
def create_emotion():
    name = request.form.get('name')
    color = request.form.get('color', 'rose')
    if name:
        new_emotion = EmotionalValue(user_id=current_user.id, name=name.strip(), color=color)
        db.session.add(new_emotion)
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/themes/<int:id>/edit', methods=['POST'])
@login_required
def edit_theme(id):
    theme = db.session.get(CoreTheme, id)
    if theme and theme.user_id == current_user.id:
        theme.name = request.form.get('name', theme.name).strip()
        theme.color = request.form.get('color', theme.color)
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/themes/<int:id>/delete', methods=['POST'])
@login_required
def delete_theme(id):
    theme = db.session.get(CoreTheme, id)
    if theme and theme.user_id == current_user.id:
        db.session.delete(theme)
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/emotions/<int:id>/edit', methods=['POST'])
@login_required
def edit_emotion(id):
    emotion = db.session.get(EmotionalValue, id)
    if emotion and emotion.user_id == current_user.id:
        emotion.name = request.form.get('name', emotion.name).strip()
        emotion.color = request.form.get('color', emotion.color)
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))

@time_buckets_api_bp.route('/emotions/<int:id>/delete', methods=['POST'])
@login_required
def delete_emotion(id):
    emotion = db.session.get(EmotionalValue, id)
    if emotion and emotion.user_id == current_user.id:
        db.session.delete(emotion)
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))
