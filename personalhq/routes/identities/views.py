from datetime import timedelta
from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency
from personalhq.models.identities import Identity
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.time_service import get_local_today

identities_view_bp = Blueprint('identities_view', __name__, url_prefix='/identity')

@identities_view_bp.route('/')
@login_required
def matrix():
    """Renders the Identity Matrix scoreboard."""
    identities = Identity.query.filter_by(user_id=current_user.id).all()
    today = get_local_today()
    start_of_week = today - timedelta(days=today.weekday())

    identity_stats = []
    for identity in identities:
        habit_votes = 0
        week_habit_votes = 0

        # 1. Tally up Habit Votes fairly (1 Vote = 1 Successful Day)
        for habit in identity.habits:
            for log in habit.logs:
                # Check if this specific day was a "Win"
                is_daily_win = habit.frequency == HabitFrequency.DAILY and log.progress >= log.target_at_time
                is_weekly_action = habit.frequency == HabitFrequency.WEEKLY and log.progress > 0
                
                if is_daily_win or is_weekly_action:
                    habit_votes += 1
                    if log.completed_date >= start_of_week:
                        week_habit_votes += 1

        # 2. Tally up Focus Session Votes
        focus_votes = FocusSession.query.filter_by(
            identity_id=identity.id, 
            status=SessionStatus.FINISHED
        ).count()

        week_focus_votes = FocusSession.query.filter(
            FocusSession.identity_id == identity.id,
            FocusSession.status == SessionStatus.FINISHED,
            FocusSession.target_date >= start_of_week
        ).count()

        total_evidence = habit_votes + focus_votes

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

    # ==========================================
    # START IDENTITY AI MOCK DATA
    # ==========================================
    TEST_AI_NUDGES = True
    ai_empty_state = None

    if TEST_AI_NUDGES:
        if not identity_stats:
            ai_empty_state = "Who do you want to be? Don't worry about outcomes yet. Focus on creating one identity (e.g., 'The Writer') and we will build the systems to support it."
        else:
            for stat in identity_stats:
                # 1. Disconnected (No habits linked)
                if not stat['habit_count'] and not stat['focus_count']:
                    stat['model'].ai_insight = "An identity without actions is just a wish. Attach one small daily habit to start building evidence."
                
                # 2. Slipping Alignment (Calculated from your existing logic)
                elif stat['total_evidence'] == 0:
                    stat['model'].ai_insight = f"Your '{stat['model'].name}' identity has been quiet lately. Do we need to schedule a small win today to get it back?"
                
                # 3. Strong Alignment
                elif stat['total_evidence'] > 0:
                    stat['model'].ai_insight = f"The evidence is stacking up. You are consistently proving to yourself that you are {stat['model'].name}."
                
                else:
                    stat['model'].ai_insight = None
    # ==========================================
    # END IDENTITY AI MOCK DATA
    # ==========================================

    return render_template(
        'identities/matrix.html', 
        identity_stats=identity_stats,
        unassigned_habits=unassigned_habits,
        ai_empty_state=ai_empty_state
    )
