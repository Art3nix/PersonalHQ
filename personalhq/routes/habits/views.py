"""Module defining the HTML View routes for Habit Management."""

from flask import Blueprint, render_template
from flask_login import login_required, current_user
from personalhq.models.habits import Habit, HabitFrequency

habits_view_bp = Blueprint('habits_view', __name__, url_prefix='/habits')

@habits_view_bp.route('/')
@login_required
def manage():
    """Renders the detailed habit analytics and management page."""
    all_habits = Habit.query.filter_by(user_id=current_user.id).all()

    total_habits = len(all_habits)
    best_streak = max([(h.streak if h.streak else 0) for h in all_habits], default=0)
    daily_count = sum(1 for h in all_habits if h.frequency == HabitFrequency.DAILY)
    weekly_count = total_habits - daily_count

    return render_template(
        'habits/manage.html',
        habits=all_habits,
        stats={
            "total": total_habits,
            "best_streak": best_streak,
            "daily": daily_count,
            "weekly": weekly_count
        },
        HabitFrequency=HabitFrequency
    )
