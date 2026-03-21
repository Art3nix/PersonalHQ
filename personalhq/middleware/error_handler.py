"""Global error handling middleware."""

from flask import jsonify
from werkzeug.exceptions import HTTPException, BadRequest, Unauthorized, Forbidden, NotFound, Conflict
from personalhq.services.response_service import ResponseService
from personalhq.services.logging_service import LoggingService


def register_error_handlers(app):
    """Register all error handlers with the Flask app."""
    
    @app.errorhandler(BadRequest)
    def handle_bad_request(e):
        LoggingService.log_error(e, "Bad Request")
        return ResponseService.error(str(e.description) or "Bad request", 400)
    
    @app.errorhandler(Unauthorized)
    def handle_unauthorized(e):
        LoggingService.log_security_event("Unauthorized Access", "MEDIUM")
        return ResponseService.unauthorized(str(e.description) or "Unauthorized")
    
    @app.errorhandler(Forbidden)
    def handle_forbidden(e):
        LoggingService.log_security_event("Forbidden Access", "MEDIUM")
        return ResponseService.forbidden(str(e.description) or "Forbidden")
    
    @app.errorhandler(NotFound)
    def handle_not_found(e):
        return ResponseService.not_found(str(e.description) or "Resource not found")
    
    @app.errorhandler(Conflict)
    def handle_conflict(e):
        return ResponseService.conflict(str(e.description) or "Resource already exists")
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(e):
        LoggingService.log_error(e, f"HTTP Exception {e.code}")
        return ResponseService.error(str(e.description) or "An error occurred", e.code or 500)
    
    @app.errorhandler(Exception)
    def handle_generic_exception(e):
        LoggingService.log_error(e, "Unhandled Exception", severity="HIGH")
        
        # Don't expose internal error details in production
        import os
        if os.getenv('FLASK_ENV') == 'production':
            return ResponseService.server_error("An unexpected error occurred")
        else:
            return ResponseService.server_error(str(e))
    
    @app.errorhandler(404)
    def handle_404(e):
        return ResponseService.not_found("Endpoint not found")
    
    @app.errorhandler(405)
    def handle_405(e):
        return ResponseService.error("Method not allowed", 405)
    
    @app.errorhandler(500)
    def handle_500(e):
        LoggingService.log_error(e, "Internal Server Error", severity="CRITICAL")
        return ResponseService.server_error("Internal server error")
