"""Module defining SQLAlchemy model for Daily Notes (AI Coach State)."""

from datetime import date
from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from personalhq.extensions import db

class DailyNote(db.Model):
    """Class representing the pre-generated AI coaching state for a specific logical day."""
    __tablename__ = 'daily_notes'

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id'), nullable=False)
    logical_date: Mapped[date] = mapped_column(nullable=False)

    # --- 1. Dashboard (The Command Center) ---
    ai_daily_briefing: Mapped[str | None]
    ai_focus_empty_state: Mapped[str | None]
    ai_habit_empty_state: Mapped[str | None]
    ai_chapter_empty_state: Mapped[str | None]

    # --- 2. Braindumps (Inbox) ---
    ai_inbox_subtitle: Mapped[str | None]
    ai_inbox_overload: Mapped[str | None]
    ai_braindump_empty_state: Mapped[str | None]

    # --- 3. Deep Work (Planner & Analysis) ---
    ai_planner_subtitle: Mapped[str | None]
    ai_planner_empty_state: Mapped[str | None]
    ai_focus_analysis: Mapped[str | None] # Analyzes recent focus trends

    # --- 4. Habits (Analytics) ---
    ai_habits_subtitle: Mapped[str | None]
    ai_habits_empty_state: Mapped[str | None]
    ai_heatmap_analysis: Mapped[str | None]
    ai_dow_analysis: Mapped[str | None]
    ai_momentum_analysis: Mapped[str | None]

    # --- 5. Identity Matrix ---
    ai_identity_empty_state: Mapped[str | None]

    # --- 6. Journals ---
    ai_journals_subtitle: Mapped[str | None]
    ai_journals_empty_state: Mapped[str | None]
    ai_writing_coach: Mapped[str | None] # Encouragement shown on the /write page
    ai_prompt_suggestion: Mapped[str | None] # Dynamic daily prompt
    ai_archive_insight: Mapped[str | None]
    ai_archive_empty_state: Mapped[str | None]

    # --- 7. Time Buckets (Life Map) ---
    ai_map_subtitle: Mapped[str | None]
    ai_lifemap_empty_state: Mapped[str | None]

    # Relationships
    user = relationship("User", back_populates="daily_notes")

    __table_args__ = (UniqueConstraint('user_id', 'logical_date', name='_user_logical_date_uc'),)


    # dashboard
#    ai_daily_briefing = None
#    ai_focus_empty_state = None
#    ai_habit_empty_state = None
#    ai_chapter_empty_state = None
#    session.ai_intention
#    habit.ai_insight

    # braindump
#    ai_inbox_overload = None
#    ai_inbox_subtitle = None
#    ai_empty_state = None
#    dump.ai_insight

    # deep work
#    ai_planner_subtitle = None
#    ai_empty_state = None
#    ai_analysis = None
#    session.ai_insight

    # habits
#    ai_habits_subtitle = None
#    ai_habits_empty_state = None
#    ai_heatmap_analysis = None
#    ai_dow_analysis = None
#    ai_momentum_analysis = None
#    habit.ai_insight

    # identity
#    ai_empty_state = None
#    stat['model'].ai_insight

    # journals
#    ai_journals_subtitle = None
#    ai_journals_empty_state = None
#    journal.ai_insight
#    ai_writing_coach = None
#    ai_prompt_suggestion = None
#    ai_archive_insight = None
#    ai_archive_empty_state = None
#    entry.ai_insight

    # time buckets
#    ai_map_subtitle = None
#    ai_lifemap_empty_state = None
#    bucket.ai_empty_state
#    bucket.ai_insight
#    exp.ai_insight
