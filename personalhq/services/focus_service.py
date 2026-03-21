"""Module handling the business logic for Deep Work focus sessions."""

from datetime import timedelta
from sqlalchemy import func
from personalhq.extensions import db
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.time_service import get_local_now, get_local_today

def start_session(user_id: int, name: str, duration_minutes: int = 60, identity_id: int = None) -> FocusSession:
    """Creates a new session and starts the timer."""
    today = get_local_today()
    max_order = db.session.query(func.max(FocusSession.queue_order)).filter_by(
        user_id=user_id, target_date=today
    ).scalar() or 0

    new_session = FocusSession(
        user_id=user_id,
        name=name,
        target_date=today,
        start_time=get_local_now(),
        status=SessionStatus.IN_PROGRESS,
        queue_order=max_order + 1,
        target_duration_minutes=duration_minutes,
        total_paused_seconds=0,
        identity_id=identity_id
    )
    db.session.add(new_session)
    db.session.commit()
    return new_session

def pause_session(session_id: int) -> bool:
    """Transitions session to PAUSED and records the exact tick."""
    session = db.session.get(FocusSession, session_id)
    if not session:
        return False
    if session.status == SessionStatus.IN_PROGRESS:
        session.status = SessionStatus.PAUSED
        session.last_paused_tick = get_local_now()
        db.session.commit()
        return True
    return False

def resume_session(session_id: int) -> bool:
    """Calculates pause duration, adds to the total, and resumes IN_PROGRESS."""
    session = db.session.get(FocusSession, session_id)

    # FIXED: null check first before accessing .status
    if not session:
        return False

    # Handle the very first start
    if session.status == SessionStatus.NOT_STARTED:
        session.status = SessionStatus.IN_PROGRESS
        session.start_time = get_local_now()
        db.session.commit()
        return True

    # Handle resuming from a pause
    if session.status == SessionStatus.PAUSED:
        pause_delta = (get_local_now() - session.last_paused_tick).total_seconds()
        current_total = session.total_paused_seconds or 0
        session.total_paused_seconds = current_total + int(pause_delta)
        session.status = SessionStatus.IN_PROGRESS
        session.last_paused_tick = None
        db.session.commit()
        return True
    return False

def end_session(session_id: int) -> bool:
    """Finalizes the session. Works from PAUSED or IN_PROGRESS states."""
    session = db.session.get(FocusSession, session_id)

    if not session:
        return False

    # Auto-pause if still running before ending
    if session.status == SessionStatus.IN_PROGRESS:
        session.last_paused_tick = get_local_now()
        session.status = SessionStatus.PAUSED

    if session.status == SessionStatus.PAUSED:
        session.status = SessionStatus.FINISHED
        session.end_time = get_local_now()
        db.session.commit()
        return True
    return False

def discard_session(session_id: int) -> bool:
    """Wipes the progress of a session but keeps it in the planner."""
    session = db.session.get(FocusSession, session_id)
    if not session:
        return False

    session.status = SessionStatus.NOT_STARTED
    session.start_time = None
    session.end_time = None
    session.total_paused_seconds = 0
    session.last_paused_tick = None
    db.session.commit()
    return True

def get_session_time_data(session_id: int) -> dict:
    """Calculates the true server-side elapsed time for the frontend timer."""
    session = db.session.get(FocusSession, session_id)
    if not session:
        return None

    now = get_local_now()
    total_paused = session.total_paused_seconds or 0

    if session.status == SessionStatus.IN_PROGRESS:
        elapsed = (now - session.start_time).total_seconds() - total_paused
        can_end = True
    elif session.status == SessionStatus.PAUSED:
        elapsed = (session.last_paused_tick - session.start_time).total_seconds() - total_paused
        can_end = True
    elif session.status == SessionStatus.FINISHED:
        # Return finished session data
        if session.end_time and session.start_time:
            total_paused = session.total_paused_seconds or 0
            elapsed = (session.end_time - session.start_time).total_seconds() - total_paused
        else:
            elapsed = session.target_duration_minutes * 60
        can_end = False
    else:
        elapsed = 0
        can_end = False

    return {
        "elapsed_seconds": max(0, int(elapsed)),
        "target_seconds": session.target_duration_minutes * 60,
        "status": session.status.value,
        "can_end": can_end
    }

def carry_over_sessions(user_id: int) -> int:
    """Moves all NOT_STARTED sessions from yesterday to today's queue."""
    today = get_local_today()
    yesterday = today - timedelta(days=1)

    missed_sessions = FocusSession.query.filter_by(
        user_id=user_id,
        target_date=yesterday,
        status=SessionStatus.NOT_STARTED
    ).order_by(FocusSession.queue_order).all()

    if not missed_sessions:
        return 0

    # Find next queue_order for today
    max_order = db.session.query(func.max(FocusSession.queue_order)).filter_by(
        user_id=user_id, target_date=today
    ).scalar() or 0

    for i, session in enumerate(missed_sessions):
        session.target_date = today
        session.queue_order = max_order + i + 1

    db.session.commit()
    return len(missed_sessions)
