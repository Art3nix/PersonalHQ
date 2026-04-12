"""Settings and account management routes."""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from personalhq.extensions import db, bcrypt

settings_bp = Blueprint('settings', __name__, url_prefix='/settings')

@settings_bp.route('/', methods=['GET', 'POST'])
@login_required
def index():
    """Account settings page."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_profile':
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            timezone = request.form.get('timezone', 'UTC').strip()
            
            # Safely extract and validate the reset hour
            try:
                day_reset_hour = int(request.form.get('day_reset_hour', 0))
                if not 0 <= day_reset_hour <= 23:
                    day_reset_hour = 0
            except ValueError:
                day_reset_hour = 0

            if first_name and last_name:
                current_user.first_name = first_name
                current_user.last_name = last_name
                current_user.timezone = timezone
                current_user.day_reset_hour = day_reset_hour
                db.session.commit()
                flash('Profile updated successfully.', 'success')
            else:
                flash('Name fields are required.', 'error')

        elif action == 'change_password':
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')

            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'error')
            elif len(new_password) < 8:
                flash('New password must be at least 8 characters.', 'error')
            elif new_password != confirm_password:
                flash('New passwords do not match.', 'error')
            else:
                current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
                db.session.commit()
                flash('Password changed successfully.', 'success')

        return redirect(url_for('settings.index'))

    # Common timezones list
    timezones = [
        'UTC', 'Europe/Prague', 'Europe/London', 'Europe/Paris', 'Europe/Berlin',
        'Europe/Warsaw', 'Europe/Vienna', 'Europe/Zurich', 'Europe/Amsterdam',
        'America/New_York', 'America/Chicago', 'America/Denver', 'America/Los_Angeles',
        'America/Toronto', 'America/Vancouver', 'Asia/Tokyo', 'Asia/Shanghai',
        'Asia/Dubai', 'Australia/Sydney', 'Pacific/Auckland'
    ]

    return render_template('settings/index.html', timezones=timezones)
