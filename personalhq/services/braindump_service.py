"""Business logic for the Thought Catcher / Brain Dumps."""

from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump
from personalhq.services.time_service import get_local_now

def save_thought(user_id: int, content: str) -> dict:
    """Saves a new unstructured thought to the database."""
    if not content or not content.strip():
        return {"error": "Thought cannot be empty."}

    new_dump = BrainDump(
        user_id=user_id,
        content=content.strip(),
        created_at=get_local_now()
    )

    db.session.add(new_dump)
    db.session.commit()

    return {"status": "success", "id": new_dump.id}