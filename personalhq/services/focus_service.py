"""Module handling the business logic for Deep Work focus sessions."""

from personalhq.extensions import db
from personalhq.models.focussessions import FocusSession, SessionStatus
from personalhq.services.time_service import get_local_now, get_local_today

def start_session(user_id: int, name: str) -> FocusSession:
    """Creates a new session and starts the timer."""
    new_session = FocusSession(
        user_id=user_id,
        name=name,
        target_date=get_local_today(),
        start_time=get_local_now(),
        status=SessionStatus.IN_PROGRESS,
        queue_order=1,  # You can dynamically assign this later based on existing queue
        total_paused_seconds=0
    )
    db.session.add(new_session)
    db.session.commit()
    return new_session

def pause_session(session_id: int) -> bool:
    """Transitions session to PAUSED and records the exact tick."""
    session = db.session.get(FocusSession, session_id)
    if session and session.status == SessionStatus.IN_PROGRESS:
        session.status = SessionStatus.PAUSED
        session.last_paused_tick = get_local_now()
        db.session.commit()
        return True
    return False

def resume_session(session_id: int) -> bool:
    """Calculates pause duration, adds to the total, and resumes IN_PROGRESS."""
    session = db.session.get(FocusSession, session_id)
    if not session:
        return False

    # Handle the very first start
    if session.status == SessionStatus.NOT_STARTED:
        session.status = SessionStatus.IN_PROGRESS
        session.start_time = get_local_now()
        db.session.commit()
        return True
    
    # Handle resuming from a pause
    if session and session.status == SessionStatus.PAUSED:
        pause_delta = (get_local_now() - session.last_paused_tick).total_seconds()

        current_total = session.total_paused_seconds or 0
        session.total_paused_seconds = current_total + int(pause_delta)

        session.status = SessionStatus.IN_PROGRESS
        session.last_paused_tick = None
        db.session.commit()
        return True
    return False

def end_session(session_id: int) -> bool:
    """Finalizes the session, strictly requiring it to be paused first per the UI rules."""
    session = db.session.get(FocusSession, session_id)

    # Enforce the rule: You can only end a session if it is currently paused
    if session and session.status == SessionStatus.PAUSED:
        session.status = SessionStatus.FINISHED
        session.end_time = get_local_now()
        db.session.commit()
        return True
    return False

def get_session_time_data(session_id: int) -> dict:
    """Calculates the true server-side elapsed time for the frontend timer."""
    session = db.session.get(FocusSession, session_id)
    if not session:
        return None

    now = get_local_now()
    total_paused = session.total_paused_seconds or 0

    if session.status == SessionStatus.IN_PROGRESS:
        elapsed = (now - session.start_time).total_seconds() - total_paused
        can_end = False
    elif session.status == SessionStatus.PAUSED:
        elapsed = (session.last_paused_tick - session.start_time).total_seconds() - total_paused
        can_end = True
    else:
        elapsed = 0
        can_end = False

    return {
        "elapsed_seconds": max(0, int(elapsed)),
        "status": session.status.value,
        "can_end": can_end
    }
