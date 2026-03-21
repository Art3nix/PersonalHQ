# PersonalHQ Services Documentation

This document describes all the new services added to PersonalHQ for production readiness.

## Core Services

### TimezoneService (`personalhq/services/timezone_service.py`)

Handles all timezone conversions and date/time operations.

**Key Methods:**
- `get_user_timezone(user)` - Get user's timezone preference
- `set_user_timezone(user, timezone)` - Set user's timezone
- `utc_now()` - Get current UTC time
- `user_now(user)` - Get current time in user's timezone
- `to_utc(dt, user_timezone)` - Convert datetime to UTC
- `to_user_timezone(dt, user_timezone)` - Convert UTC to user timezone
- `get_today_start_end(user)` - Get start/end of today in user's timezone
- `is_today(dt, user)` - Check if datetime is today
- `format_for_user(dt, user, format_str)` - Format datetime for user

**Usage:**
```python
from personalhq.services.timezone_service import TimezoneService

# Get current time in user's timezone
user_now = TimezoneService.user_now(user)

# Get today's date range
today_start, today_end = TimezoneService.get_today_start_end(user)
```

---

### StreakCalculator (`personalhq/services/streak_calculator.py`)

Calculates habit streaks and tracking information.

**Key Methods:**
- `calculate_current_streak(habit_logs, user)` - Get current consecutive day streak
- `calculate_best_streak(habit_logs, user)` - Get best streak ever
- `is_streak_active(habit_logs, user)` - Check if streak is active
- `days_until_streak_breaks(habit_logs, user)` - Days until streak breaks
- `get_streak_status(habit_logs, user)` - Comprehensive streak info
- `get_missing_days(habit_logs, user, days_back)` - Get missed days

**Usage:**
```python
from personalhq.services.streak_calculator import StreakCalculator

# Get all streak info
streak_info = StreakCalculator.get_streak_status(habit_logs, user)
print(f"Current: {streak_info['current']}, Best: {streak_info['best']}")
```

---

### ValidationService (`personalhq/services/validation_service.py`)

Validates all user input across the application.

**Key Methods:**
- `validate_habit(data)` - Validate habit creation/update
- `validate_identity(data)` - Validate identity data
- `validate_deep_work_session(data)` - Validate session data
- `validate_brain_dump(data)` - Validate inbox entry
- `validate_journal_entry(data)` - Validate journal entry
- `validate_email(email)` - Validate email format
- `validate_password(password)` - Validate password strength
- `sanitize_input(text, max_length)` - Sanitize user input

**Usage:**
```python
from personalhq.services.validation_service import ValidationService

is_valid, error = ValidationService.validate_habit({
    'name': 'Morning Run',
    'frequency': 'daily'
})

if not is_valid:
    print(f"Validation error: {error}")
```

---

### ResponseService (`personalhq/services/response_service.py`)

Provides consistent API response formatting.

**Key Methods:**
- `success(data, message, status_code)` - Return success response
- `created(data, message)` - Return 201 Created
- `error(message, status_code, errors)` - Return error response
- `validation_error(errors, message)` - Return 422 validation error
- `not_found(message)` - Return 404
- `unauthorized(message)` - Return 401
- `paginated(items, page, per_page, total, message)` - Return paginated response

**Usage:**
```python
from personalhq.services.response_service import ResponseService

# Success response
return ResponseService.success({'habit_id': 123}, "Habit created", 201)

# Error response
return ResponseService.validation_error({'name': 'Name is required'})
```

---

### LoggingService (`personalhq/services/logging_service.py`)

Structured logging for all operations.

**Key Methods:**
- `log_crud(operation, model, user_id, resource_id, details)` - Log CRUD operations
- `log_auth(event, user_id, email, success, reason)` - Log auth events
- `log_error(error, context, user_id)` - Log errors with context
- `log_request(endpoint, method, status_code, duration_ms, user_id)` - Log HTTP requests
- `log_security_event(event, severity, user_id, details)` - Log security events
- `log_performance(operation, duration_ms, threshold_ms)` - Log slow operations

**Usage:**
```python
from personalhq.services.logging_service import LoggingService

# Log a habit creation
LoggingService.log_crud('CREATE', 'Habit', user.id, habit.id, {'name': 'Morning Run'})

# Log an auth event
LoggingService.log_auth('LOGIN', user.id, user.email, True)
```

---

## Feature Services

### HabitServiceV2 (`personalhq/services/habit_service_v2.py`)

Complete habit management with CRUD operations.

**Key Methods:**
- `create_habit(user, name, description, frequency, identity_id, check_ins_required, trigger)` - Create habit
- `update_habit(habit, **kwargs)` - Update habit properties
- `delete_habit(habit)` - Delete habit and logs
- `log_habit(habit, user, date_logged, check_ins)` - Log habit completion
- `unlog_habit(habit, user, date)` - Remove habit log
- `get_habit_logs(habit, days_back)` - Get habit logs
- `get_streak_info(habit, user)` - Get streak information
- `import_habit_streak(user, name, existing_streak, frequency)` - Import with existing streak
- `get_habits_by_frequency(user, frequency)` - Get habits by frequency
- `toggle_habit_active(habit, is_active)` - Enable/disable habit

---

### IdentityService (`personalhq/services/identity_service.py`)

Identity management with color support.

**Key Methods:**
- `create_identity(user, name, reinforcing_sentence, color)` - Create identity
- `update_identity(identity, **kwargs)` - Update identity
- `delete_identity(identity)` - Delete identity
- `get_identities(user)` - Get all identities
- `get_identity_habits(identity)` - Get linked habits
- `get_identity_stats(identity, user)` - Get statistics

---

### DeepWorkService (`personalhq/services/deepwork_service.py`)

Deep work session management with timer.

**Key Methods:**
- `create_session(user, task_name, duration_minutes, identity_id)` - Create session
- `start_session(session)` - Start timer
- `pause_session(session)` - Pause timer
- `resume_session(session)` - Resume timer
- `end_session(session, early)` - End session
- `discard_session(session)` - Abandon session
- `get_session_time_remaining(session)` - Get remaining time
- `extend_session(session, additional_minutes)` - Extend session
- `get_today_sessions(user)` - Get today's sessions
- `get_active_session(user)` - Get currently active session
- `get_session_stats(user, days_back)` - Get statistics

---

### JournalServiceV2 (`personalhq/services/journal_service.py`)

Journal management with entry CRUD.

**Key Methods:**
- `create_journal(user, name, description, prompt)` - Create journal
- `update_journal(journal, **kwargs)` - Update journal
- `delete_journal(journal)` - Delete journal
- `create_entry(journal, content, title, date_written)` - Create entry
- `update_entry(entry, **kwargs)` - Update entry
- `delete_entry(entry)` - Delete entry
- `get_journal_entries(journal, limit, offset)` - Get entries paginated
- `get_recent_entries(journal, days_back)` - Get recent entries
- `get_user_journals(user)` - Get all journals
- `get_journal_stats(journal, days_back)` - Get statistics

---

### BrainDumpServiceV2 (`personalhq/services/braindump_service.py`)

Brain dump (GTD inbox) management.

**Key Methods:**
- `update_entry(entry, **kwargs)` - Update entry
- `delete_entry(entry)` - Delete entry
- `get_inbox_entries(user, status, limit)` - Get entries by status
- `get_all_entries(user, days_back)` - Get all entries
- `get_inbox_stats(user)` - Get statistics
- `mark_as_done(entry)` - Mark entry as done
- `mark_as_processing(entry)` - Mark entry as processing

---

## Middleware

### ErrorHandler (`personalhq/middleware/error_handler.py`)

Global error handling for all exceptions.

**Features:**
- Handles all HTTP exceptions
- Logs errors with context
- Hides internal errors in production
- Returns consistent error responses

**Usage:**
```python
from personalhq.middleware.error_handler import register_error_handlers

register_error_handlers(app)
```

---

### RequestMiddleware (`personalhq/middleware/request_middleware.py`)

Request/response logging and security headers.

**Features:**
- Logs all requests with duration
- Adds security headers
- Tracks slow requests
- Handles request teardown

**Usage:**
```python
from personalhq.middleware.request_middleware import register_request_middleware

register_request_middleware(app)
```

---

### RateLimiter (`personalhq/middleware/rate_limiter.py`)

Rate limiting for API protection.

**Decorators:**
- `@rate_limit(limit, window_seconds)` - Custom rate limit
- `@auth_rate_limit()` - Strict auth endpoint limit (5 req/5 min)
- `@api_rate_limit()` - Standard API limit (1000 req/hour)

**Usage:**
```python
from personalhq.middleware.rate_limiter import rate_limit, auth_rate_limit

@app.route('/api/login', methods=['POST'])
@auth_rate_limit()
def login():
    # Login logic
    pass

@app.route('/api/habits', methods=['GET'])
@api_rate_limit()
def get_habits():
    # Get habits logic
    pass
```

---

## Integration Guide

### In App Initialization

```python
from flask import Flask
from personalhq.middleware.error_handler import register_error_handlers
from personalhq.middleware.request_middleware import register_request_middleware

app = Flask(__name__)

# Register middleware
register_error_handlers(app)
register_request_middleware(app)
```

### In API Routes

```python
from personalhq.services.habit_service_v2 import HabitServiceV2
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService
from personalhq.middleware.rate_limiter import api_rate_limit

@app.route('/api/habits', methods=['POST'])
@api_rate_limit()
def create_habit():
    data = request.get_json()
    
    # Create habit using service
    habit, error = HabitServiceV2.create_habit(
        current_user,
        data.get('name'),
        data.get('description'),
        data.get('frequency')
    )
    
    if error:
        return ResponseService.error(error, 400)
    
    # Log the operation
    LoggingService.log_crud('CREATE', 'Habit', current_user.id, habit.id)
    
    return ResponseService.created({'habit_id': habit.id}, "Habit created")
```

---

## Best Practices

1. **Always validate input** using ValidationService before processing
2. **Always log CRUD operations** for audit trail
3. **Always use ResponseService** for consistent API responses
4. **Always handle timezone** using TimezoneService for user-specific dates
5. **Always use services** instead of direct database queries
6. **Always catch exceptions** and log them with context
7. **Always rate limit** sensitive endpoints
8. **Always add security headers** via middleware

---

## Testing Services

```python
from personalhq.services.habit_service_v2 import HabitServiceV2
from personalhq.services.streak_calculator import StreakCalculator
from personalhq.services.timezone_service import TimezoneService

# Test habit creation
habit, error = HabitServiceV2.create_habit(user, "Morning Run", frequency="daily")
assert error == ""
assert habit.name == "Morning Run"

# Test streak calculation
logs = HabitLog.query.filter_by(habit_id=habit.id).all()
streak_info = StreakCalculator.get_streak_status(logs, user)
assert streak_info['current'] >= 0

# Test timezone
user_now = TimezoneService.user_now(user)
assert user_now is not None
```

---

## Performance Considerations

1. **Caching**: Use cache for frequently accessed data (user preferences, timezone)
2. **Database Indexes**: Add indexes on user_id, created_at, status fields
3. **Query Optimization**: Use eager loading for relationships
4. **Pagination**: Always paginate large result sets
5. **Rate Limiting**: Protect endpoints from abuse

---

## Security Considerations

1. **Input Validation**: All user input is validated and sanitized
2. **SQL Injection**: Use ORM (SQLAlchemy) exclusively
3. **XSS Prevention**: Sanitize all user input
4. **CSRF Protection**: Use Flask-WTF CSRF tokens
5. **Rate Limiting**: Protect auth endpoints with strict limits
6. **Error Handling**: Don't expose internal errors to users
7. **Logging**: Log all security events

---

## Future Enhancements

1. Add caching layer for frequently accessed data
2. Add database query optimization and indexing
3. Add API versioning support
4. Add webhook support for integrations
5. Add export functionality (CSV, JSON, PDF)
6. Add bulk operations support
7. Add advanced filtering and search
8. Add analytics and reporting
