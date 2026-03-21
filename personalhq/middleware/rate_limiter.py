"""Rate limiting middleware for API protection."""

from flask import request, g
from functools import wraps
from datetime import datetime, timedelta
from personalhq.extensions import db, cache
from personalhq.services.response_service import ResponseService


class RateLimiter:
    \"\"\"Rate limiting for API endpoints.\"\"\"
    
    @staticmethod
    def get_client_id():
        \"\"\"Get unique client identifier.\"\"\"
        if hasattr(g, 'user_id') and g.user_id:
            return f\"user:{g.user_id}\"
        return f\"ip:{request.remote_addr}\"\n    \n    @staticmethod\n    def is_rate_limited(limit: int, window_seconds: int) -> bool:\n        \"\"\"Check if client has exceeded rate limit.\"\"\"\n        client_id = RateLimiter.get_client_id()\n        key = f\"rate_limit:{client_id}:{request.endpoint}\"\n        \n        try:\n            current = cache.get(key) or 0\n            if current >= limit:\n                return True\n            \n            # Increment counter\n            cache.set(key, current + 1, window_seconds)\n            return False\n        except:\n            # If cache fails, don't rate limit\n            return False\n\n\ndef rate_limit(limit: int = 100, window_seconds: int = 3600):\n    \"\"\"Decorator for rate limiting endpoints.\"\"\"\n    def decorator(f):\n        @wraps(f)\n        def decorated_function(*args, **kwargs):\n            if RateLimiter.is_rate_limited(limit, window_seconds):\n                return ResponseService.error(\n                    f\"Rate limit exceeded: {limit} requests per {window_seconds} seconds\",\n                    429\n                )\n            return f(*args, **kwargs)\n        return decorated_function\n    return decorator\n\n\ndef auth_rate_limit(limit: int = 5, window_seconds: int = 300):\n    \"\"\"Stricter rate limiting for auth endpoints.\"\"\"\n    return rate_limit(limit, window_seconds)\n\n\ndef api_rate_limit(limit: int = 1000, window_seconds: int = 3600):\n    \"\"\"Standard rate limiting for API endpoints.\"\"\"\n    return rate_limit(limit, window_seconds)\n"
