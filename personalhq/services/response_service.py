"""Service for consistent API responses and error handling."""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class ResponseService:
    """Provides consistent response formatting."""
    
    @staticmethod
    def success(data=None, message: str = "Success", status_code: int = 200):
        """
        Return a successful response.
        
        Args:
            data: Response data (dict or list)
            message: Success message
            status_code: HTTP status code
            
        Returns:
            Flask response
        """
        response = {
            'status': 'success',
            'message': message,
            'data': data or {}
        }
        return jsonify(response), status_code
    
    @staticmethod
    def created(data=None, message: str = "Created successfully"):
        """Return a 201 Created response."""
        return ResponseService.success(data, message, 201)
    
    @staticmethod
    def error(message: str, status_code: int = 400, errors: dict = None):
        """
        Return an error response.
        
        Args:
            message: Error message
            status_code: HTTP status code
            errors: Detailed error information (dict)
            
        Returns:
            Flask response
        """
        response = {
            'status': 'error',
            'message': message,
            'errors': errors or {}
        }
        return jsonify(response), status_code
    
    @staticmethod
    def validation_error(errors: dict, message: str = "Validation failed"):
        """Return a validation error response."""
        return ResponseService.error(message, 422, errors)
    
    @staticmethod
    def not_found(message: str = "Resource not found"):
        """Return a 404 Not Found response."""
        return ResponseService.error(message, 404)
    
    @staticmethod
    def unauthorized(message: str = "Unauthorized"):
        """Return a 401 Unauthorized response."""
        return ResponseService.error(message, 401)
    
    @staticmethod
    def forbidden(message: str = "Forbidden"):
        """Return a 403 Forbidden response."""
        return ResponseService.error(message, 403)
    
    @staticmethod
    def server_error(message: str = "Internal server error"):
        """Return a 500 Server Error response."""
        return ResponseService.error(message, 500)
    
    @staticmethod
    def conflict(message: str = "Resource already exists"):
        """Return a 409 Conflict response."""
        return ResponseService.error(message, 409)
    
    @staticmethod
    def paginated(items: list, page: int, per_page: int, total: int, message: str = "Success"):
        """
        Return a paginated response.
        
        Args:
            items: List of items
            page: Current page number
            per_page: Items per page
            total: Total number of items
            message: Success message
            
        Returns:
            Flask response
        """
        response = {
            'status': 'success',
            'message': message,
            'data': items,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }
        return jsonify(response), 200
    
    @staticmethod
    def handle_exception(e: Exception):
        """
        Handle exceptions and return appropriate response.
        
        Args:
            e: Exception to handle
            
        Returns:
            Flask response
        """
        if isinstance(e, HTTPException):
            return ResponseService.error(e.description or str(e), e.code)
        
        # Log the exception (in production, use proper logging)
        print(f"Unhandled exception: {str(e)}")
        
        return ResponseService.server_error("An unexpected error occurred")
