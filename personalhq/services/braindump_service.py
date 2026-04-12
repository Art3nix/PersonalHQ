"""Business logic for the Brain Dump / Inbox feature."""

from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump
from personalhq.services.time_service import get_utc_now


def save_thought(user_id: int, content: str) -> dict:
    """Saves a new thought to the Brain Dump inbox with correct local timestamp."""
    if not content or not content.strip():
        return {"error": "Content cannot be empty."}

    new_dump = BrainDump(
        user_id=user_id,
        content=content.strip(),
        created_at=get_utc_now(),  # Use user's local time, not UTC
        processed=False
    )
    db.session.add(new_dump)
    db.session.commit()

    return {
        "id": new_dump.id,
        "content": new_dump.content,
        "created_at": new_dump.created_at.strftime('%b %d, %H:%M')
    }
