"""Business logic for the Thought Catcher / Brain Dumps."""

from datetime import datetime
from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump

def save_thought(user_id: int, content: str) -> dict:
    """Saves a new unstructured thought to the database."""
    if not content or not content.strip():
        return {"error": "Thought cannot be empty."}

    new_dump = BrainDump(
        user_id=user_id,
        content=content.strip(),
        created_at=datetime.now()
    )

    db.session.add(new_dump)
    db.session.commit()

    return {"status": "success", "id": new_dump.id}