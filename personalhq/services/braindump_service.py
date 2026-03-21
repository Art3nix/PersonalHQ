"""Business logic for the Thought Catcher / Brain Dumps."""

from datetime import timedelta
from personalhq.extensions import db
from personalhq.models.braindumps import BrainDump
from personalhq.services.time_service import get_local_now
from personalhq.services.timezone_service import TimezoneService
from personalhq.services.validation_service import ValidationService

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


class BrainDumpServiceV2:
    """Enhanced brain dump service with CRUD operations."""
    
    @staticmethod
    def update_entry(entry: BrainDump, **kwargs) -> tuple[bool, str]:
        """Update brain dump entry."""
        allowed_fields = ['content', 'status', 'tags', 'priority']
        
        try:
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                
                if key == 'content' and value:
                    is_valid, error = ValidationService.validate_brain_dump({'content': value})
                    if not is_valid:
                        return False, error
                    entry.content = value.strip()
                elif key == 'status' and value in ['inbox', 'processing', 'done']:
                    entry.status = value
                elif key == 'tags' and value:
                    entry.tags = value.strip()
                elif key == 'priority' and value in ['low', 'medium', 'high']:
                    entry.priority = value
            
            entry.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update entry: {str(e)}"
    
    @staticmethod
    def delete_entry(entry: BrainDump) -> tuple[bool, str]:
        """Delete a brain dump entry."""
        try:
            db.session.delete(entry)
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete entry: {str(e)}"
    
    @staticmethod
    def get_inbox_entries(user, status: str = 'inbox', limit: int = 100) -> list:
        """Get brain dump entries by status."""
        return BrainDump.query.filter_by(
            user_id=user.id,
            status=status
        ).order_by(BrainDump.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_all_entries(user, days_back: int = 90) -> list:
        """Get all brain dump entries from the past N days."""
        cutoff_date = TimezoneService.utc_now() - timedelta(days=days_back)
        return BrainDump.query.filter(
            BrainDump.user_id == user.id,
            BrainDump.created_at >= cutoff_date
        ).order_by(BrainDump.created_at.desc()).all()
    
    @staticmethod
    def get_inbox_stats(user) -> dict:
        """Get statistics for the inbox."""
        inbox_entries = BrainDump.query.filter_by(user_id=user.id, status='inbox').all()
        processing_entries = BrainDump.query.filter_by(user_id=user.id, status='processing').all()
        done_entries = BrainDump.query.filter_by(user_id=user.id, status='done').all()
        
        return {
            'inbox_count': len(inbox_entries),
            'processing_count': len(processing_entries),
            'done_count': len(done_entries),
            'total_count': len(inbox_entries) + len(processing_entries) + len(done_entries)
        }
    
    @staticmethod
    def mark_as_done(entry: BrainDump) -> tuple[bool, str]:
        """Mark entry as done."""
        try:
            entry.status = 'done'
            entry.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to mark as done: {str(e)}"
    
    @staticmethod
    def mark_as_processing(entry: BrainDump) -> tuple[bool, str]:
        """Mark entry as processing."""
        try:
            entry.status = 'processing'
            entry.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to mark as processing: {str(e)}"