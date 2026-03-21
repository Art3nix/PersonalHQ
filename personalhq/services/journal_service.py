"""Module handling the business logic for Journals."""

import random
from datetime import datetime, timedelta
from personalhq.models.journals import JournalFrequency, Journal, JournalEntry
from personalhq.services.time_service import get_local_today
from personalhq.extensions import db
from personalhq.services.timezone_service import TimezoneService
from personalhq.services.validation_service import ValidationService

def get_active_prompt(journal):
    """
    Determines which JournalPrompt to display based on the journal's 
    rotation frequency and the current date.
    """
    if not journal.prompts: #
        return None

    count = len(journal.prompts)
    today = get_local_today()

    # Calculate a deterministic index based on the frequency
    if journal.frequency == JournalFrequency.DAILY:
        # toordinal() returns an integer representing the day since Jan 1, 1 AD
        index = today.toordinal() % count

    elif journal.frequency == JournalFrequency.WEEKLY:
        # isocalendar()[1] returns the current week number of the year
        index = today.isocalendar()[1] % count

    elif journal.frequency == JournalFrequency.MONTHLY:
        # Create an absolute month integer to ensure smooth year-over-year rollover
        absolute_month = (today.year * 12) + today.month
        index = absolute_month % count

    elif journal.frequency == JournalFrequency.YEARLY:
        index = today.year % count

    elif journal.frequency == JournalFrequency.ON_DEMAND:
        # Pick a new random prompt every single time the page loads
        index = random.randint(0, count - 1)

    else:
        index = 0

    # Return the specific JournalPrompt model
    return journal.prompts[index]


class JournalServiceV2:
    """Enhanced journal service with CRUD operations."""
    
    @staticmethod
    def create_journal(user, name: str, description: str = None,
                      prompt: str = None) -> tuple[Journal, str]:
        """
        Create a new journal.
        
        Returns:
            (journal, error_message)
        """
        if not name or len(name.strip()) < 2:
            return None, "Journal name must be at least 2 characters"
        
        try:
            journal = Journal(
                user_id=user.id,
                name=name.strip(),
                description=description.strip() if description else None,
                prompt=prompt.strip() if prompt else None,
                created_at=TimezoneService.utc_now()
            )
            db.session.add(journal)
            db.session.commit()
            return journal, ""
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to create journal: {str(e)}"
    
    @staticmethod
    def update_journal(journal: Journal, **kwargs) -> tuple[bool, str]:
        """
        Update journal properties.
        
        Returns:
            (success, error_message)
        """
        allowed_fields = ['name', 'description', 'prompt']
        
        try:
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                
                if key == 'name' and value:
                    if len(value.strip()) < 2:
                        return False, "Journal name must be at least 2 characters"
                    journal.name = value.strip()
                elif key == 'description' and value:
                    journal.description = value.strip()
                elif key == 'prompt' and value:
                    journal.prompt = value.strip()
            
            journal.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update journal: {str(e)}"
    
    @staticmethod
    def delete_journal(journal: Journal) -> tuple[bool, str]:
        """
        Delete a journal and all its entries.
        
        Returns:
            (success, error_message)
        """
        try:
            # Delete all entries
            JournalEntry.query.filter_by(journal_id=journal.id).delete()
            db.session.delete(journal)
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete journal: {str(e)}"
    
    @staticmethod
    def create_entry(journal: Journal, content: str, title: str = None,
                    date_written: datetime = None) -> tuple[JournalEntry, str]:
        """
        Create a new journal entry.
        
        Returns:
            (entry, error_message)
        """
        is_valid, error = ValidationService.validate_journal_entry({
            'content': content,
            'title': title
        })
        if not is_valid:
            return None, error
        
        try:
            if date_written is None:
                date_written = TimezoneService.utc_now()
            
            entry = JournalEntry(
                journal_id=journal.id,
                title=title.strip() if title else None,
                content=content.strip(),
                date_written=date_written,
                created_at=TimezoneService.utc_now()
            )
            db.session.add(entry)
            db.session.commit()
            return entry, ""
        except Exception as e:
            db.session.rollback()
            return None, f"Failed to create entry: {str(e)}"
    
    @staticmethod
    def update_entry(entry: JournalEntry, **kwargs) -> tuple[bool, str]:
        """
        Update journal entry.
        
        Returns:
            (success, error_message)
        """
        allowed_fields = ['title', 'content']
        
        try:
            for key, value in kwargs.items():
                if key not in allowed_fields:
                    continue
                
                if key == 'title' and value:
                    entry.title = value.strip()
                elif key == 'content' and value:
                    is_valid, error = ValidationService.validate_journal_entry({'content': value})
                    if not is_valid:
                        return False, error
                    entry.content = value.strip()
            
            entry.updated_at = TimezoneService.utc_now()
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to update entry: {str(e)}"
    
    @staticmethod
    def delete_entry(entry: JournalEntry) -> tuple[bool, str]:
        """
        Delete a journal entry.
        
        Returns:
            (success, error_message)
        """
        try:
            db.session.delete(entry)
            db.session.commit()
            return True, ""
        except Exception as e:
            db.session.rollback()
            return False, f"Failed to delete entry: {str(e)}"
    
    @staticmethod
    def get_journal_entries(journal: Journal, limit: int = 50, offset: int = 0) -> list:
        """Get entries for a journal, paginated."""
        return JournalEntry.query.filter_by(journal_id=journal.id).order_by(
            JournalEntry.date_written.desc()
        ).limit(limit).offset(offset).all()
    
    @staticmethod
    def get_recent_entries(journal: Journal, days_back: int = 30) -> list:
        """Get recent entries from the past N days."""
        cutoff_date = TimezoneService.utc_now() - timedelta(days=days_back)
        return JournalEntry.query.filter(
            JournalEntry.journal_id == journal.id,
            JournalEntry.date_written >= cutoff_date
        ).order_by(JournalEntry.date_written.desc()).all()
    
    @staticmethod
    def get_user_journals(user) -> list:
        """Get all journals for a user."""
        return Journal.query.filter_by(user_id=user.id).all()
    
    @staticmethod
    def get_journal_stats(journal: Journal, days_back: int = 30) -> dict:
        """Get statistics for a journal."""
        cutoff_date = TimezoneService.utc_now() - timedelta(days=days_back)
        
        entries = JournalEntry.query.filter(
            JournalEntry.journal_id == journal.id,
            JournalEntry.date_written >= cutoff_date
        ).all()
        
        total_entries = len(entries)
        total_words = sum(len(e.content.split()) for e in entries)
        average_words = total_words // total_entries if total_entries > 0 else 0
        
        return {
            'total_entries': total_entries,
            'total_words': total_words,
            'average_words_per_entry': average_words,
            'entries': entries
        }
