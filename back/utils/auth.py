"""
Authentication and authorization utilities.
"""
from functools import wraps
from typing import Optional
from flask import request, g
from utils.response import error_response


def extract_token() -> Optional[str]:
    """Extract Bearer token from Authorization header.
    
    Returns:
        Token string or None
    """
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        return auth_header.replace('Bearer ', '', 1).strip()
    return None


def validate_token(token: str) -> bool:
    """Validate authentication token.
    
    Args:
        token: Token to validate
        
    Returns:
        True if valid, False otherwise
        
    Note:
        This is a simplified validation. In production, use JWT or 
        database-backed token validation.
    """
    if not token:
        return False
    
    # TODO: Implement proper JWT validation or database lookup
    # For now, accept any non-empty token (testing only)
    return True


def require_auth(f):
    """Decorator to require authentication for routes.
    
    Usage:
        @app.route('/protected')
        @require_auth
        def protected_route():
            return 'Protected content'
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token()
        
        if not token:
            return error_response(
                message="Authentication required",
                code=401
            )
        
        if not validate_token(token):
            return error_response(
                message="Invalid or expired token",
                code=401
            )
        
        # Store token in Flask g object for use in route
        g.token = token
        
        return f(*args, **kwargs)
    
    return decorated_function


def optional_auth(f):
    """Decorator for optional authentication.
    
    If token is present and valid, stores it in g.token.
    Otherwise, continues without authentication.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = extract_token()
        
        if token and validate_token(token):
            g.token = token
        
        return f(*args, **kwargs)
    
    return decorated_function
