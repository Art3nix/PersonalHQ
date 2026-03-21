"""Service for validating user input across all models."""

import re
from datetime import datetime


class ValidationService:
    """Validates user input for all features."""
    
    @staticmethod
    def validate_habit(data: dict) -> tuple[bool, str]:
        """
        Validate habit creation/update data.
        
        Returns:
            (is_valid, error_message)
        """
        if not data.get('name') or not isinstance(data['name'], str):
            return False, "Habit name is required and must be text"
        
        if len(data['name'].strip()) < 2:
            return False, "Habit name must be at least 2 characters"
        
        if len(data['name']) > 255:
            return False, "Habit name must be less than 255 characters"
        
        if 'description' in data and data['description']:
            if len(data['description']) > 1000:
                return False, "Habit description must be less than 1000 characters"
        
        if 'frequency' in data and data['frequency'] not in ['daily', 'weekly', 'custom']:
            return False, "Invalid frequency"
        
        if 'check_ins_required' in data:
            try:
                check_ins = int(data['check_ins_required'])
                if check_ins < 1 or check_ins > 100:
                    return False, "Check-ins must be between 1 and 100"
            except (ValueError, TypeError):
                return False, "Check-ins must be a number"
        
        return True, ""
    
    @staticmethod
    def validate_identity(data: dict) -> tuple[bool, str]:
        """Validate identity creation/update data."""
        if not data.get('name') or not isinstance(data['name'], str):
            return False, "Identity name is required and must be text"
        
        if len(data['name'].strip()) < 2:
            return False, "Identity name must be at least 2 characters"
        
        if len(data['name']) > 255:
            return False, "Identity name must be less than 255 characters"
        
        if 'reinforcing_sentence' in data and data['reinforcing_sentence']:
            if len(data['reinforcing_sentence']) > 500:
                return False, "Reinforcing sentence must be less than 500 characters"
        
        if 'color' in data and data['color']:
            if not ValidationService._is_valid_hex_color(data['color']):
                return False, "Invalid color format"
        
        return True, ""
    
    @staticmethod
    def validate_deep_work_session(data: dict) -> tuple[bool, str]:
        """Validate deep work session creation/update data."""
        if not data.get('task_name') or not isinstance(data['task_name'], str):
            return False, "Task name is required"
        
        if len(data['task_name'].strip()) < 2:
            return False, "Task name must be at least 2 characters"
        
        if len(data['task_name']) > 255:
            return False, "Task name must be less than 255 characters"
        
        if 'duration_minutes' in data:
            try:
                duration = int(data['duration_minutes'])
                if duration < 5 or duration > 480:
                    return False, "Duration must be between 5 and 480 minutes"
            except (ValueError, TypeError):
                return False, "Duration must be a number"
        
        return True, ""
    
    @staticmethod
    def validate_brain_dump(data: dict) -> tuple[bool, str]:
        """Validate brain dump/inbox entry."""
        if not data.get('content') or not isinstance(data['content'], str):
            return False, "Content is required"
        
        content = data['content'].strip()
        if len(content) < 1:
            return False, "Content cannot be empty"
        
        if len(content) > 5000:
            return False, "Content must be less than 5000 characters"
        
        return True, ""
    
    @staticmethod
    def validate_journal_entry(data: dict) -> tuple[bool, str]:
        """Validate journal entry."""
        if not data.get('content') or not isinstance(data['content'], str):
            return False, "Content is required"
        
        content = data['content'].strip()
        if len(content) < 1:
            return False, "Content cannot be empty"
        
        if len(content) > 10000:
            return False, "Content must be less than 10000 characters"
        
        if 'title' in data and data['title']:
            if len(data['title']) > 255:
                return False, "Title must be less than 255 characters"
        
        return True, ""
    
    @staticmethod
    def validate_time_bucket(data: dict) -> tuple[bool, str]:
        """Validate time bucket/decade."""
        if not data.get('name') or not isinstance(data['name'], str):
            return False, "Time bucket name is required"
        
        if len(data['name'].strip()) < 2:
            return False, "Time bucket name must be at least 2 characters"
        
        if len(data['name']) > 255:
            return False, "Time bucket name must be less than 255 characters"
        
        if 'start_age' in data and 'end_age' in data:
            try:
                start = int(data['start_age'])
                end = int(data['end_age'])
                if start < 0 or end < 0:
                    return False, "Ages must be positive"
                if start >= end:
                    return False, "Start age must be less than end age"
                if end > 120:
                    return False, "End age must be realistic"
            except (ValueError, TypeError):
                return False, "Ages must be numbers"
        
        return True, ""
    
    @staticmethod
    def validate_experience(data: dict) -> tuple[bool, str]:
        """Validate experience."""
        if not data.get('title') or not isinstance(data['title'], str):
            return False, "Experience title is required"
        
        if len(data['title'].strip()) < 2:
            return False, "Experience title must be at least 2 characters"
        
        if len(data['title']) > 255:
            return False, "Experience title must be less than 255 characters"
        
        if 'description' in data and data['description']:
            if len(data['description']) > 1000:
                return False, "Description must be less than 1000 characters"
        
        return True, ""
    
    @staticmethod
    def validate_email(email: str) -> tuple[bool, str]:
        """Validate email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(pattern, email):
            return False, "Invalid email format"
        return True, ""
    
    @staticmethod
    def validate_password(password: str) -> tuple[bool, str]:
        """Validate password strength."""
        if len(password) < 8:
            return False, "Password must be at least 8 characters"
        
        if len(password) > 128:
            return False, "Password must be less than 128 characters"
        
        if not any(c.isupper() for c in password):
            return False, "Password must contain at least one uppercase letter"
        
        if not any(c.islower() for c in password):
            return False, "Password must contain at least one lowercase letter"
        
        if not any(c.isdigit() for c in password):
            return False, "Password must contain at least one digit"
        
        return True, ""
    
    @staticmethod
    def sanitize_input(text: str, max_length: int = 5000) -> str:
        """
        Sanitize user input to prevent XSS.
        
        Args:
            text: Input text
            max_length: Maximum length after sanitization
            
        Returns:
            Sanitized text
        """
        if not isinstance(text, str):
            return ""
        
        # Remove dangerous characters but keep markdown-safe ones
        dangerous_chars = ['<', '>', '&', '"', "'"]
        for char in dangerous_chars:
            text = text.replace(char, '')
        
        # Truncate if too long
        if len(text) > max_length:
            text = text[:max_length]
        
        return text.strip()
    
    @staticmethod
    def _is_valid_hex_color(color: str) -> bool:
        """Check if color is valid hex format."""
        pattern = r'^#([A-Fa-f0-9]{6}|[A-Fa-f0-9]{3})$'
        return bool(re.match(pattern, color))
    
    @staticmethod
    def validate_date_range(start_date: datetime, end_date: datetime) -> tuple[bool, str]:
        """Validate date range."""
        if start_date >= end_date:
            return False, "Start date must be before end date"
        return True, ""
