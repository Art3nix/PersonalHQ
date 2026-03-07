"""API routes for handling BrainDump data actions."""

from datetime import datetime
from flask import Blueprint, redirect, url_for, jsonify, request
from flask_login import login_required, current_user
from sqlalchemy import func
from personalhq.extensions import db
from personalhq.services import braindump_service
from personalhq.models.braindumps import BrainDump
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.models.experiences import Experience
from personalhq.models.bucket_experience import BucketExperience
from personalhq.models.journalentries import JournalEntry

braindumps_api_bp = Blueprint('braindumps_api', __name__, url_prefix='/actions/braindumps')

@braindumps_api_bp.route('/catch', methods=['POST'])
@login_required
def catch_thought():
    """Endpoint to receive and save a thought from the dashboard."""
    data = request.get_json() or {}
    content = data.get('content')

    if not content:
        return jsonify({"status": "error", "message": "No content provided."}), 400

    result = braindump_service.save_thought(current_user.id, content)

    if "error" in result:
        return jsonify({"status": "error", "message": result["error"]}), 400

    return jsonify(result), 201

@braindumps_api_bp.route('/<int:dump_id>/delete', methods=['POST'])
@login_required
def delete_dump(dump_id):
    """Deletes a processed thought from the Inbox."""
    dump = db.session.get(BrainDump, dump_id)
    if dump and dump.user_id == current_user.id:
        db.session.delete(dump)
        db.session.commit()

    return redirect(url_for('braindumps_view.index'))

@braindumps_api_bp.route('/<int:dump_id>/convert', methods=['POST'])
@login_required
def convert_dump(dump_id):
    """Converts a BrainDump into a Focus Session or an Experience, then deletes the dump."""
    dump = db.session.get(BrainDump, dump_id)
    if not dump or dump.user_id != current_user.id:
        return redirect(url_for('braindumps_view.index'))

    convert_type = request.form.get('convert_type') # 'focus' or 'experience'
    name = request.form.get('name')

    if convert_type == 'focus':
        target_date_str = request.form.get('target_date')
        duration = request.form.get('target_duration_minutes', type=int)

        # Default to today if no date provided
        target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date() if target_date_str else datetime.today().date()

        # Calculate queue order
        max_order = db.session.query(func.max(FocusSession.queue_order)).filter_by(
            user_id=current_user.id, target_date=target_date
        ).scalar() or 0

        identity_id = request.form.get('identity_id', type=int)

        new_session = FocusSession(
            user_id=current_user.id,
            name=name.strip(),
            target_date=target_date,
            target_duration_minutes=duration or 60,
            status=SessionStatus.NOT_STARTED,
            queue_order=max_order + 1,
            total_paused_seconds=0,
            identity_id=identity_id
        )
        db.session.add(new_session)

    elif convert_type == 'experience':
        bucket_id = request.form.get('bucket_id')
        details = request.form.get('details')

        if not bucket_id:
            return redirect(url_for('braindumps_view.index'))

        # Experience does not use user_id
        new_exp = Experience(
            name=name.strip(),
            details=details.strip() if details else None
        )
        db.session.add(new_exp)
        db.session.flush()

        link = BucketExperience(
            bucket_id=int(bucket_id),
            experience_id=new_exp.id
        )
        db.session.add(link)

    elif convert_type == 'journal':
        journal_id = request.form.get('journal_id')
        content = request.form.get('journal_content')
        
        if journal_id and content:
            new_entry = JournalEntry(
                journal_id=int(journal_id),
                content=content.strip()
            )
            db.session.add(new_entry)

    # Clear it from the Inbox
    db.session.delete(dump)
    db.session.commit()

    return redirect(url_for('braindumps_view.index'))
