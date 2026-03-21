# PersonalHQ API Integration Guide

## Overview

This guide explains how to integrate the new refactored API routes (v2) with the frontend templates. All new routes follow RESTful principles and use consistent response formatting.

---

## API Endpoints Summary

### Habits API (`/api/v2/habits`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v2/habits` | List all habits |
| POST | `/api/v2/habits` | Create new habit |
| GET | `/api/v2/habits/<id>` | Get single habit |
| PUT | `/api/v2/habits/<id>` | Update habit |
| DELETE | `/api/v2/habits/<id>` | Delete habit |
| POST | `/api/v2/habits/<id>/log` | Log habit completion |
| POST | `/api/v2/habits/<id>/unlog` | Remove habit log |
| GET | `/api/v2/habits/<id>/streak` | Get streak info |
| POST | `/api/v2/habits/<id>/toggle-active` | Enable/disable habit |

### Identities API (`/api/v2/identities`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v2/identities` | List all identities |
| POST | `/api/v2/identities` | Create new identity |
| GET | `/api/v2/identities/<id>` | Get single identity |
| PUT | `/api/v2/identities/<id>` | Update identity |
| DELETE | `/api/v2/identities/<id>` | Delete identity |
| GET | `/api/v2/identities/<id>/habits` | Get linked habits |
| GET | `/api/v2/identities/<id>/stats` | Get statistics |

### Deep Work / Focus Sessions API (`/api/v2/focus-sessions`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v2/focus-sessions` | List all sessions |
| POST | `/api/v2/focus-sessions` | Create new session |
| GET | `/api/v2/focus-sessions/<id>` | Get single session |
| POST | `/api/v2/focus-sessions/<id>/start` | Start timer |
| POST | `/api/v2/focus-sessions/<id>/pause` | Pause timer |
| POST | `/api/v2/focus-sessions/<id>/resume` | Resume timer |
| POST | `/api/v2/focus-sessions/<id>/end` | End session |
| POST | `/api/v2/focus-sessions/<id>/discard` | Discard session |
| POST | `/api/v2/focus-sessions/<id>/extend` | Extend by minutes |
| GET | `/api/v2/focus-sessions/today` | Get today's sessions |
| GET | `/api/v2/focus-sessions/active` | Get active session |
| GET | `/api/v2/focus-sessions/stats` | Get statistics |

### Brain Dump / Inbox API (`/api/v2/inbox`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v2/inbox` | List inbox entries |
| POST | `/api/v2/inbox` | Create entry |
| GET | `/api/v2/inbox/<id>` | Get single entry |
| PUT | `/api/v2/inbox/<id>` | Update entry |
| DELETE | `/api/v2/inbox/<id>` | Delete entry |
| POST | `/api/v2/inbox/<id>/mark-done` | Mark as done |
| POST | `/api/v2/inbox/<id>/mark-processing` | Mark as processing |
| GET | `/api/v2/inbox/stats` | Get statistics |
| GET | `/api/v2/inbox/by-tag/<tag>` | Filter by tag |
| GET | `/api/v2/inbox/recent` | Get recent entries |

### Journals API (`/api/v2/journals`)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/api/v2/journals` | List all journals |
| POST | `/api/v2/journals` | Create new journal |
| GET | `/api/v2/journals/<id>` | Get single journal |
| PUT | `/api/v2/journals/<id>` | Update journal |
| DELETE | `/api/v2/journals/<id>` | Delete journal |
| GET | `/api/v2/journals/<id>/entries` | List entries |
| POST | `/api/v2/journals/<id>/entries` | Create entry |
| GET | `/api/v2/journals/entries/<id>` | Get single entry |
| PUT | `/api/v2/journals/entries/<id>` | Update entry |
| DELETE | `/api/v2/journals/entries/<id>` | Delete entry |
| GET | `/api/v2/journals/<id>/stats` | Get statistics |
| GET | `/api/v2/journals/<id>/recent` | Get recent entries |

---

## Response Format

All API endpoints return JSON in this format:

### Success Response
```json
{
    "status": "success",
    "message": "Operation completed",
    "data": { /* response data */ },
    "timestamp": "2026-03-21T10:30:00Z"
}
```

### Error Response
```json
{
    "status": "error",
    "message": "Error description",
    "error_code": "VALIDATION_ERROR",
    "timestamp": "2026-03-21T10:30:00Z"
}
```

### Paginated Response
```json
{
    "status": "success",
    "message": "Items retrieved",
    "data": [ /* items */ ],
    "pagination": {
        "total": 100,
        "limit": 50,
        "offset": 0,
        "pages": 2
    },
    "timestamp": "2026-03-21T10:30:00Z"
}
```

---

## Frontend Integration Examples

### 1. Fetch All Habits

```javascript
async function getHabits() {
    try {
        const response = await fetch('/api/v2/habits');
        const result = await response.json();
        
        if (result.status === 'success') {
            console.log('Habits:', result.data);
            notificationSystem.success('Habits loaded');
        } else {
            notificationSystem.error(result.message);
        }
    } catch (error) {
        notificationSystem.error('Failed to load habits');
    }
}
```

### 2. Create New Habit

```javascript
async function createHabit(name, frequency, identityId) {
    try {
        const response = await fetch('/api/v2/habits', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                name: name,
                frequency: frequency,
                identity_id: identityId
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success' || response.status === 201) {
            notificationSystem.success('Habit created successfully');
            return result.data;
        } else {
            notificationSystem.error(result.message);
        }
    } catch (error) {
        notificationSystem.error('Failed to create habit');
    }
}
```

### 3. Delete Habit with Confirmation

```javascript
async function deleteHabit(habitId) {
    showConfirmation(
        'Delete Habit?',
        'This action cannot be undone.',
        async () => {
            try {
                const response = await fetch(`/api/v2/habits/${habitId}`, {
                    method: 'DELETE'
                });
                
                const result = await response.json();
                
                if (result.status === 'success') {
                    notificationSystem.success('Habit deleted');
                    // Refresh habits list
                    getHabits();
                } else {
                    notificationSystem.error(result.message);
                }
            } catch (error) {
                notificationSystem.error('Failed to delete habit');
            }
        },
        'Delete'
    );
}
```

### 4. Start Focus Session

```javascript
async function startFocusSession(taskName, durationMinutes) {
    try {
        // Create session
        const createResponse = await fetch('/api/v2/focus-sessions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                task_name: taskName,
                duration_minutes: durationMinutes
            })
        });
        
        const createResult = await createResponse.json();
        
        if (createResult.status !== 'success') {
            notificationSystem.error(createResult.message);
            return;
        }
        
        const sessionId = createResult.data.id;
        
        // Start timer
        const startResponse = await fetch(`/api/v2/focus-sessions/${sessionId}/start`, {
            method: 'POST'
        });
        
        const startResult = await startResponse.json();
        
        if (startResult.status === 'success') {
            notificationSystem.success('Focus session started');
            timerDisplay.show(taskName, durationMinutes);
        } else {
            notificationSystem.error(startResult.message);
        }
    } catch (error) {
        notificationSystem.error('Failed to start session');
    }
}
```

### 5. Log Habit with Unsaved Progress Warning

```javascript
// Track unsaved changes
trackUnsavedChanges('form');

// Log habit
async function logHabit(habitId) {
    try {
        const response = await fetch(`/api/v2/habits/${habitId}/log`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                date_logged: new Date().toISOString().split('T')[0]
            })
        });
        
        const result = await response.json();
        
        if (result.status === 'success') {
            notificationSystem.success('Habit logged successfully');
            // Mark as saved
            document.querySelector('form').dispatchEvent(new Event('submit'));
        } else {
            notificationSystem.error(result.message);
        }
    } catch (error) {
        notificationSystem.error('Failed to log habit');
    }
}
```

---

## Error Handling

All endpoints return appropriate HTTP status codes:

- **200 OK** - Successful GET request
- **201 Created** - Successful POST request
- **204 No Content** - Successful DELETE request
- **400 Bad Request** - Invalid input or validation error
- **401 Unauthorized** - Authentication required
- **403 Forbidden** - Permission denied
- **404 Not Found** - Resource not found
- **429 Too Many Requests** - Rate limit exceeded
- **500 Internal Server Error** - Server error

---

## Rate Limiting

All endpoints are rate-limited to prevent abuse:

- **Auth endpoints**: 5 requests per minute
- **Read endpoints**: 100 requests per minute
- **Write endpoints**: 30 requests per minute

Rate limit headers are included in responses:
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1645000000
```

---

## Authentication

All endpoints require user authentication. Include the session cookie with requests:

```javascript
// Cookies are automatically sent with fetch() if credentials are included
fetch('/api/v2/habits', {
    credentials: 'include'
});
```

---

## Component Usage

### Confirmation Modal

```javascript
showConfirmation(
    'Delete Item?',
    'Are you sure you want to delete this item?',
    () => {
        // Confirmation callback
        deleteItem();
    },
    'Delete'
);
```

### Unsaved Progress Warning

```javascript
trackUnsavedChanges('form'); // Tracks all form changes
```

### Notifications

```javascript
notificationSystem.success('Operation successful');
notificationSystem.error('An error occurred');
notificationSystem.warning('Warning message');
notificationSystem.info('Info message');
```

### Timer Display

```javascript
timerDisplay.show('Focus Session', 25); // 25 minutes
```

---

## Migration from Old Routes

The old routes (v1) are still available but deprecated. Gradually migrate to v2:

| Old Route | New Route | Status |
|-----------|-----------|--------|
| `/actions/habits/<id>/toggle` | `/api/v2/habits/<id>/log` | Deprecated |
| `/habits/create` | `POST /api/v2/habits` | Deprecated |
| `/focus/start` | `POST /api/v2/focus-sessions/<id>/start` | Deprecated |

---

## Best Practices

1. **Always check response status** - Don't assume success
2. **Handle errors gracefully** - Show user-friendly messages
3. **Use notifications** - Provide feedback for all operations
4. **Prevent accidental data loss** - Use confirmations for delete
5. **Track unsaved changes** - Warn before navigation
6. **Respect rate limits** - Don't make excessive requests
7. **Use consistent error handling** - Centralize error logic

---

## Support

For issues or questions about the API, refer to:
- `SERVICES_DOCUMENTATION.md` - Service layer documentation
- `PRODUCTION_READY.md` - Production deployment guide
- `COMPLETION_GUIDE.md` - Pre-launch checklist
