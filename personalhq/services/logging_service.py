"""Service for structured logging across the application."""

import logging
from datetime import datetime
from flask import request, g
from functools import wraps


class LoggingService:
    """Provides structured logging for the application."""
    
    # Log levels
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR
    CRITICAL = logging.CRITICAL
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get a logger instance."""
        return logging.getLogger(name)
    
    @staticmethod
    def log_crud(operation: str, model: str, user_id: int, resource_id: int = None, details: dict = None):
        """
        Log CRUD operations.
        
        Args:
            operation: 'CREATE', 'READ', 'UPDATE', 'DELETE'
            model: Model name (e.g., 'Habit', 'Identity')
            user_id: User performing the operation
            resource_id: ID of the resource being modified
            details: Additional details
        """
        logger = LoggingService.get_logger('crud')
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'model': model,
            'user_id': user_id,
            'resource_id': resource_id,
            'details': details or {}
        }
        logger.info(f"CRUD: {operation} {model}", extra=log_data)
    
    @staticmethod
    def log_auth(event: str, user_id: int = None, email: str = None, success: bool = True, reason: str = None):
        """
        Log authentication events.
        
        Args:
            event: 'LOGIN', 'LOGOUT', 'REGISTER', 'PASSWORD_RESET', 'PASSWORD_CHANGE'
            user_id: User ID
            email: User email
            success: Whether the operation succeeded
            reason: Reason for failure
        """
        logger = LoggingService.get_logger('auth')
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'user_id': user_id,
            'email': email,
            'success': success,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.user_agent.string if request else None,
            'reason': reason
        }
        level = logging.INFO if success else logging.WARNING
        logger.log(level, f"AUTH: {event}", extra=log_data)
    
    @staticmethod
    def log_error(error: Exception, context: str = None, user_id: int = None):
        """
        Log errors with context.
        
        Args:
            error: Exception object
            context: Additional context
            user_id: User ID if applicable
        """
        logger = LoggingService.get_logger('error')
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'error_type': type(error).__name__,
            'error_message': str(error),
            'context': context,
            'user_id': user_id,
            'ip_address': request.remote_addr if request else None,
            'endpoint': request.endpoint if request else None,
            'method': request.method if request else None
        }
        logger.error(f"ERROR: {context or 'Unhandled exception'}", extra=log_data, exc_info=True)
    
    @staticmethod
    def log_request(endpoint: str, method: str, status_code: int, duration_ms: float, user_id: int = None):
        """
        Log HTTP requests.
        
        Args:
            endpoint: Request endpoint
            method: HTTP method
            status_code: Response status code
            duration_ms: Request duration in milliseconds
            user_id: User ID if authenticated
        """
        logger = LoggingService.get_logger('request')
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'endpoint': endpoint,
            'method': method,
            'status_code': status_code,
            'duration_ms': duration_ms,
            'user_id': user_id,
            'ip_address': request.remote_addr if request else None,
            'user_agent': request.user_agent.string if request else None
        }
        logger.info(f"REQUEST: {method} {endpoint} {status_code}", extra=log_data)
    
    @staticmethod
    def log_security_event(event: str, severity: str, user_id: int = None, details: dict = None):
        """
        Log security events.
        
        Args:
            event: Security event name
            severity: 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
            user_id: User ID if applicable
            details: Additional details
        """
        logger = LoggingService.get_logger('security')
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'event': event,
            'severity': severity,
            'user_id': user_id,
            'ip_address': request.remote_addr if request else None,
            'details': details or {}
        }
        
        level_map = {
            'LOW': logging.INFO,
            'MEDIUM': logging.WARNING,
            'HIGH': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        level = level_map.get(severity, logging.WARNING)
        logger.log(level, f"SECURITY: {event}", extra=log_data)
    
    @staticmethod
    def log_performance(operation: str, duration_ms: float, threshold_ms: float = 1000):
        """
        Log slow operations.
        
        Args:
            operation: Operation name
            duration_ms: Duration in milliseconds
            threshold_ms: Threshold for warning
        """
        logger = LoggingService.get_logger('performance')
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'operation': operation,
            'duration_ms': duration_ms,
            'threshold_ms': threshold_ms
        }
        
        if duration_ms > threshold_ms:
            logger.warning(f"SLOW: {operation} took {duration_ms}ms", extra=log_data)
        else:
            logger.debug(f"PERFORMANCE: {operation} took {duration_ms}ms", extra=log_data)


def log_request_decorator(f):
    """Decorator to log HTTP requests."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        start_time = datetime.utcnow()
        
        try:
            result = f(*args, **kwargs)
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            # Extract status code from response
            status_code = 200
            if isinstance(result, tuple) and len(result) > 1:
                status_code = result[1]
            
            user_id = g.get('user_id') if hasattr(g, 'user_id') else None
            LoggingService.log_request(request.endpoint, request.method, status_code, duration, user_id)
            
            return result
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds() * 1000
            LoggingService.log_error(e, f"Request to {request.endpoint}", g.get('user_id'))
            raise
    
    return decorated_function
