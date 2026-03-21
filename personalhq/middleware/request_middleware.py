"""Request/response middleware for logging and metrics."""

from datetime import datetime
from flask import request, g
from personalhq.services.logging_service import LoggingService


def register_request_middleware(app):
    """Register request/response middleware."""
    
    @app.before_request
    def before_request():
        """Called before each request."""
        g.start_time = datetime.utcnow()
        g.user_id = None
        
        # Try to get user from session or auth header
        if hasattr(g, 'current_user') and g.current_user:
            g.user_id = g.current_user.id
    
    @app.after_request
    def after_request(response):
        """Called after each request."""
        if hasattr(g, 'start_time'):
            duration = (datetime.utcnow() - g.start_time).total_seconds() * 1000
            
            # Log the request
            LoggingService.log_request(
                endpoint=request.endpoint or 'unknown',
                method=request.method,
                status_code=response.status_code,
                duration_ms=duration,
                user_id=g.get('user_id')
            )
            
            # Log slow requests
            if duration > 1000:  # More than 1 second
                LoggingService.log_performance(
                    operation=f"{request.method} {request.endpoint}",
                    duration_ms=duration,
                    threshold_ms=1000
                )
        
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    @app.teardown_request
    def teardown_request(exception=None):
        """Called at the end of each request."""
        if exception:
            LoggingService.log_error(
                exception,
                f"Request error: {request.method} {request.endpoint}",
                user_id=g.get('user_id')
            )
