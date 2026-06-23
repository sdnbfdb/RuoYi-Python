"""
Global error handlers for Flask application.
"""
import logging
from flask import Flask
from werkzeug.exceptions import HTTPException
from utils.response import error_response
from utils.validators import ValidationError

logger = logging.getLogger(__name__)


def register_error_handlers(app: Flask):
    """Register global error handlers.
    
    Args:
        app: Flask application instance
    """
    
    @app.errorhandler(ValidationError)
    def handle_validation_error(error: ValidationError):
        """Handle validation errors."""
        return error_response(
            message="Validation failed",
            code=422,
            errors=error.errors
        )
    
    @app.errorhandler(HTTPException)
    def handle_http_exception(error: HTTPException):
        """Handle HTTP exceptions."""
        return error_response(
            message=error.description,
            code=error.code
        )
    
    @app.errorhandler(404)
    def handle_not_found(error):
        """Handle 404 Not Found."""
        return error_response(
            message="Resource not found",
            code=404
        )
    
    @app.errorhandler(500)
    def handle_internal_error(error):
        """Handle 500 Internal Server Error."""
        logger.error(f"Internal server error: {error}", exc_info=True)
        return error_response(
            message="Internal server error occurred",
            code=500
        )
    
    @app.errorhandler(Exception)
    def handle_unexpected_error(error: Exception):
        """Handle unexpected errors."""
        logger.error(f"Unexpected error: {error}", exc_info=True)
        
        # Don't expose internal errors in production
        if app.config.get('DEBUG'):
            message = str(error)
        else:
            message = "An unexpected error occurred"
        
        return error_response(
            message=message,
            code=500
        )
