"""HTML View routes for the Time Buckets roadmap."""

from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, current_app
from flask_login import login_required, current_user
from personalhq.models.timebuckets import TimeBucket
from personalhq.models.coretheme import CoreTheme
from personalhq.models.emotionalvalue import EmotionalValue
from personalhq.models.dailynotes import DailyNote
from personalhq.extensions import db
from personalhq.services.time_service import get_logical_today

time_buckets_view_bp = Blueprint('time_buckets_view', __name__, url_prefix='/life')

@time_buckets_view_bp.route('/')
@login_required
def manage():
    """Renders the Life Map / Time Buckets management page."""
    # Fetch all buckets in chronological order
    buckets = TimeBucket.query.filter_by(user_id=current_user.id).order_by(TimeBucket.start_date.asc()).all()
    core_themes = CoreTheme.query.all()
    emotional_values = EmotionalValue.query.all()

    # ==========================================
    # AI COACH CONTEXT
    # ==========================================
    today = get_logical_today(current_user)
    daily_note = DailyNote.query.filter_by(user_id=current_user.id, logical_date=get_logical_today(current_user)).first()

    # Fetch from DB
    ai_map_subtitle = daily_note.ai_map_subtitle if daily_note else None
    ai_lifemap_empty_state = daily_note.ai_lifemap_empty_state if daily_note else None

    if current_app.config['TEST_AI_NUDGES'] is True and current_user.date_of_birth:
        today = get_logical_today(current_user)
        # Roughly calculate current age
        current_age = today.year - current_user.date_of_birth.year - ((today.month, today.day) < (current_user.date_of_birth.month, current_user.date_of_birth.day))

        if not buckets:
            ai_lifemap_empty_state = f"You are currently {current_age} years old. Time is passing. Define the bucket for your {current_age}s right now to start anchoring your experiences."
        else:
            # 1. Global Subtitle Logic
            active_buckets = [b for b in buckets if b.start_date.year - current_user.date_of_birth.year <= current_age <= b.end_date.year - current_user.date_of_birth.year]
            if active_buckets:
                ai_map_subtitle = f"You are currently in the '{active_buckets[0].name}' chapter of your life. Prioritize experiences meant for this window."
            else:
                ai_map_subtitle = "You have unmapped years ahead of you. Fill in the gaps."

            # 2. Bucket-Level Coaching
            for bucket in buckets:
                start_age = bucket.start_date.year - current_user.date_of_birth.year
                end_age = bucket.end_date.year - current_user.date_of_birth.year
                
                # Check for empty buckets
                if not bucket.experiences:
                    bucket.ai_empty_state = f"What do you want to accomplish between the ages of {start_age} and {end_age}? Plot an experience here before time fills the void for you."
                
                # Check relation to current age
                if current_age > end_age:
                    bucket.ai_insight = "This chapter has closed. Any uncompleted experiences here must be moved to the future or permanently discarded."
                elif start_age <= current_age <= end_age:
                    years_left = end_age - current_age
                    if years_left <= 2:
                        bucket.ai_insight = f"Urgent: You only have {years_left} years left in this chapter. It is time to aggressively fund and execute these experiences."
                    else:
                        bucket.ai_insight = f"This is your active chapter. You have {years_left} years left to accomplish these goals."
                else:
                    bucket.ai_insight = "This chapter is in the future. Keep funding your life so you can afford these when the time comes."

                # 3. Experience-Level Coaching
                for link in bucket.experiences:
                    exp = link.experience
                    if exp.is_completed:
                        exp.ai_insight = "Memory secured. This dividend will pay out for the rest of your life."
                    elif exp.core_theme and "Adventure" in exp.core_theme.name:
                        exp.ai_insight = "High-adventure experiences require peak physical health. Ensure your daily habits are supporting your ability to do this."
                    elif exp.emotional_value and "Connection" in exp.emotional_value.name:
                        exp.ai_insight = "Relationships compound. Prioritizing this will deepen your bonds for decades to come."
                    else:
                        exp.ai_insight = None
    # ==========================================

    return render_template('time_buckets/manage.html',
                        buckets=buckets,
                        core_themes=core_themes,
                        emotional_values=emotional_values,
                        ai_map_subtitle=ai_map_subtitle,
                        ai_lifemap_empty_state=ai_lifemap_empty_state
    )

@time_buckets_view_bp.route('/set_dob', methods=['POST'])
@login_required
def set_dob():
    """Saves the user's Date of Birth so the timeline can function."""
    dob_str = request.form.get('date_of_birth')
    if dob_str:
        current_user.date_of_birth = datetime.strptime(dob_str, '%Y-%m-%d').date()
        db.session.commit()
    return redirect(url_for('time_buckets_view.manage'))
