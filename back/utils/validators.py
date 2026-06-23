"""
Input validation utilities.
"""
from typing import Any, Dict, List, Optional


class ValidationError(Exception):
    """Validation error exception."""
    
    def __init__(self, errors: Dict[str, List[str]]):
        self.errors = errors
        super().__init__("Validation failed")


def validate_required_fields(
    data: Dict[str, Any],
    required_fields: List[str]
) -> Optional[Dict[str, List[str]]]:
    """Validate that required fields are present.
    
    Args:
        data: Data dictionary to validate
        required_fields: List of required field names
        
    Returns:
        Dictionary of errors or None if valid
    """
    errors = {}
    
    for field in required_fields:
        if field not in data or data[field] is None or data[field] == '':
            errors[field] = [f"{field} is required"]
    
    return errors if errors else None


def validate_file_size(file_size: int, max_size: int = 50 * 1024 * 1024) -> bool:
    """Validate file size.
    
    Args:
        file_size: Size in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if valid, False otherwise
    """
    return 0 < file_size <= max_size


def validate_file_extension(
    filename: str,
    allowed_extensions: List[str]
) -> bool:
    """Validate file extension.
    
    Args:
        filename: File name
        allowed_extensions: List of allowed extensions (e.g., ['.jpg', '.png'])
        
    Returns:
        True if valid, False otherwise
    """
    if not filename:
        return False
    
    ext = filename.lower().rsplit('.', 1)[-1] if '.' in filename else ''
    ext_with_dot = f'.{ext}'
    
    return ext_with_dot in [e.lower() for e in allowed_extensions]


def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal attacks.
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    import re
    # Remove path separators and other dangerous characters
    filename = re.sub(r'[/\\]', '', filename)
    filename = re.sub(r'[^a-zA-Z0-9._-]', '_', filename)
    return filename[:255]  # Limit length
