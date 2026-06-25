"""
Standardized API response utilities.
"""
from typing import Any, Dict, Optional
from flask import jsonify


def success_response(
    data: Any = None,
    message: str = "Success",
    code: int = 200
) -> tuple:
    """Create a standardized success response.
    
    Args:
        data: Response data
        message: Success message
        code: HTTP status code
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "success": True,
        "message": message,
        "code": code
    }
    
    if data is not None:
        response["data"] = data
    
    return jsonify(response), code


def error_response(
    message: str = "Error occurred",
    code: int = 400,
    errors: Optional[Dict[str, Any]] = None
) -> tuple:
    """Create a standardized error response.
    
    Args:
        message: Error message
        code: HTTP status code
        errors: Detailed error information
        
    Returns:
        Tuple of (response, status_code)
    """
    response = {
        "success": False,
        "message": message,
        "code": code
    }
    
    if errors:
        response["errors"] = errors
    
    return jsonify(response), code


def validation_error_response(errors: Dict[str, Any]) -> tuple:
    """Create a validation error response.
    
    Args:
        errors: Validation errors dictionary
        
    Returns:
        Tuple of (response, status_code)
    """
    return error_response(
        message="Validation failed",
        code=422,
        errors=errors
    )
