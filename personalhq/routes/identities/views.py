from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit
from personalhq.models.habit_logs import HabitLog
from personalhq.models.identities import Identity
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.time_service import get_local_today

identities_view_bp = Blueprint('identities_view', __name__, url_prefix='/identity')

@identities_view_bp.route('/')
@login_required
def matrix():
    """Renders the Identity Matrix scoreboard."""
    identities = Identity.query.filter_by(user_id=current_user.id).all()

    identity_stats = []
    for identity in identities:
        # 1. Tally up Habit Votes (assuming you have a HabitLog table for completions)
        habit_votes = sum(len(habit.logs) for habit in identity.habits) if identity.habits else 0

        # 2. Tally up Focus Session Votes
        focus_votes = FocusSession.query.filter_by(
            identity_id=identity.id, 
            status=SessionStatus.FINISHED
        ).count()

        total_evidence = habit_votes + focus_votes

        # Weekly habit votes
        today = get_local_today()
        start_of_week = today - timedelta(days=today.weekday())
        week_habit_votes = 0
        for habit in identity.habits:
            logs = HabitLog.query.filter(
                HabitLog.habit_id == habit.id,
                HabitLog.completed_date >= start_of_week,
                HabitLog.progress > 0
            ).count()
            week_habit_votes += logs

        week_focus_votes = FocusSession.query.filter(
            FocusSession.identity_id == identity.id,
            FocusSession.status == SessionStatus.FINISHED,
            FocusSession.target_date >= start_of_week
        ).count()

        identity_stats.append({
            'model': identity,
            'total_evidence': total_evidence,
            'habit_count': len(identity.habits),
            'focus_count': FocusSession.query.filter_by(identity_id=identity.id).count(),
            'week_votes': week_habit_votes + week_focus_votes,
        })

    # Sort by the identity with the most evidence
    identity_stats.sort(key=lambda x: x['total_evidence'], reverse=True)

    # Fetch habits that don't belong to an identity yet
    unassigned_habits = Habit.query.filter_by(user_id=current_user.id, identity_id=None, is_active=True).all()

    return render_template(
        'identities/matrix.html', 
        identity_stats=identity_stats,
        unassigned_habits=unassigned_habits # Pass this to the UI
    )
