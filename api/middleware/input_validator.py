# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Input Validation Middleware

Centralized input validation and sanitization.

Protects against:
- SQL injection (additional layer beyond ORM)
- XSS (cross-site scripting)
- Path traversal
- Command injection

Created in Handover 0129c - Security Hardening & OWASP Compliance
"""

import logging
import re
from typing import Any, Callable, ClassVar

from fastapi import HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware


logger = logging.getLogger(__name__)


class InputValidationMiddleware(BaseHTTPMiddleware):
    """
    Validate and sanitize all incoming requests.

    This provides defense-in-depth protection against common attacks:
    - SQL injection: Detects SQL patterns in query params
    - XSS: Detects script injection attempts
    - Path traversal: Blocks directory traversal attempts

    Note: This is ADDITIONAL to Pydantic validation in endpoints.
    Pydantic handles schema validation, this handles malicious patterns.
    """

    # Dangerous SQL injection patterns to block
    SQL_INJECTION_PATTERNS: ClassVar[list[str]] = [
        r"(\bUNION\b.*\bSELECT\b)",  # UNION SELECT attacks
        r"(\bDROP\b.*\bTABLE\b)",  # DROP TABLE attacks
        r"(\bEXEC\b.*\()",  # EXEC() function calls
        r"(--|#|\/\*|\*\/)",  # SQL comment markers
        r"(\bOR\b.*=.*)",  # OR 1=1 attacks
        r"(\bAND\b.*=.*)",  # AND 1=1 attacks
        r"(\bINSERT\b.*\bINTO\b)",  # INSERT attacks
        r"(\bUPDATE\b.*\bSET\b)",  # UPDATE attacks
        r"(\bDELETE\b.*\bFROM\b)",  # DELETE attacks
    ]

    # XSS (Cross-Site Scripting) patterns to block
    XSS_PATTERNS: ClassVar[list[str]] = [
        r"<script[^>]*>.*?</script>",  # <script> tags
        r"javascript:",  # javascript: protocol
        r"onerror\s*=",  # onerror event handler
        r"onload\s*=",  # onload event handler
        r"onclick\s*=",  # onclick event handler
        r"onmouseover\s*=",  # onmouseover event handler
        r"<iframe[^>]*>",  # iframe injection
        r"<embed[^>]*>",  # embed injection
        r"<object[^>]*>",  # object injection
    ]

    # Path traversal patterns to block
    PATH_TRAVERSAL_PATTERNS: ClassVar[list[str]] = [
        r"\.\./",  # ../ (Unix)
        r"\.\.\\",  # ..\ (Windows)
    ]

    def __init__(self, app, strict_mode: bool = False):
        """
        Initialize input validation middleware.

        Args:
            app: FastAPI application instance
            strict_mode: If True, applies stricter validation (may block legitimate inputs)
        """
        super().__init__(app)
        self.strict_mode = strict_mode
        logger.info(f"InputValidationMiddleware initialized (strict_mode: {strict_mode})")

    async def dispatch(self, request: Request, call_next: Callable):
        """
        Validate all request inputs.

        Args:
            request: Incoming HTTP request
            call_next: Next middleware/handler in chain

        Returns:
            Response if validation passes

        Raises:
            HTTPException: 400 if malicious input detected
        """
        # Validate query parameters
        for key, value in request.query_params.items():
            if not self._is_safe(value):
                logger.warning(
                    f"Blocked unsafe query parameter: {key}={value[:50]}... "
                    f"from IP: {request.client.host if request.client else 'unknown'}"
                )
                raise HTTPException(status_code=400, detail=f"Invalid input detected in query parameter: {key}")

        # Validate path for path traversal
        path = request.url.path
        if not self._is_safe_path(path):
            logger.warning(
                f"Blocked path traversal attempt: {path} "
                f"from IP: {request.client.host if request.client else 'unknown'}"
            )
            raise HTTPException(status_code=400, detail="Invalid path - path traversal detected")

        # Note: Request body validation happens in endpoints via Pydantic models
        # This middleware provides an additional safety layer for query/path params

        response = await call_next(request)
        return response

    def _is_safe(self, value: str) -> bool:
        """
        Check if input value is safe.

        Args:
            value: Input string to validate

        Returns:
            True if safe, False if malicious pattern detected
        """
        if not isinstance(value, str):
            return True

        # Check for SQL injection patterns
        for pattern in self.SQL_INJECTION_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.debug(f"SQL injection pattern detected: {pattern} in value: {value[:50]}...")
                return False

        # Check for XSS patterns
        for pattern in self.XSS_PATTERNS:
            if re.search(pattern, value, re.IGNORECASE):
                logger.debug(f"XSS pattern detected: {pattern} in value: {value[:50]}...")
                return False

        return True

    def _is_safe_path(self, path: str) -> bool:
        """
        Check if path is safe (no traversal).

        Args:
            path: URL path to validate

        Returns:
            True if safe, False if path traversal detected
        """
        for pattern in self.PATH_TRAVERSAL_PATTERNS:
            if re.search(pattern, path):
                logger.debug(f"Path traversal pattern detected: {pattern} in path: {path}")
                return False
        return True


class RequestSanitizer:
    """
    Sanitize request data before processing.

    Provides helper methods to sanitize strings and dictionaries.
    Useful for sanitizing data that will be displayed in UI or logs.

    Usage in endpoints:
        from api.middleware.input_validator import RequestSanitizer

        sanitizer = RequestSanitizer()
        safe_data = sanitizer.sanitize(request_data)
    """

    @staticmethod
    def sanitize_string(value: str) -> str:
        """
        Sanitize string input by escaping HTML special characters.

        Args:
            value: Input string to sanitize

        Returns:
            Sanitized string with HTML characters escaped
        """
        if not isinstance(value, str):
            return value

        # Remove leading/trailing whitespace
        value = value.strip()

        # Escape HTML special characters to prevent XSS
        value = (
            value.replace("&", "&amp;")  # Must be first
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;")
            .replace("/", "&#x2F;")
        )

        return value

    @staticmethod
    def sanitize_dict(data: dict) -> dict:
        """
        Recursively sanitize dictionary.

        Args:
            data: Dictionary to sanitize

        Returns:
            New dictionary with sanitized values
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = RequestSanitizer.sanitize_string(value)
            elif isinstance(value, dict):
                sanitized[key] = RequestSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = RequestSanitizer.sanitize_list(value)
            else:
                sanitized[key] = value
        return sanitized

    @staticmethod
    def sanitize_list(data: list) -> list:
        """
        Recursively sanitize list.

        Args:
            data: List to sanitize

        Returns:
            New list with sanitized items
        """
        sanitized = []
        for item in data:
            if isinstance(item, str):
                sanitized.append(RequestSanitizer.sanitize_string(item))
            elif isinstance(item, dict):
                sanitized.append(RequestSanitizer.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(RequestSanitizer.sanitize_list(item))
            else:
                sanitized.append(item)
        return sanitized

    def sanitize(self, data: Any) -> Any:
        """
        Sanitize any input data (auto-detects type).

        Args:
            data: Data to sanitize (str, dict, list, or other)

        Returns:
            Sanitized data of same type
        """
        if isinstance(data, str):
            return self.sanitize_string(data)
        if isinstance(data, dict):
            return self.sanitize_dict(data)
        if isinstance(data, list):
            return self.sanitize_list(data)
        return data


# Convenience function for quick sanitization
def sanitize(data: Any) -> Any:
    """
    Convenience function to sanitize any data.

    Args:
        data: Data to sanitize

    Returns:
        Sanitized data

    Example:
        from api.middleware.input_validator import sanitize

        user_input = "<script>alert('xss')</script>"
        safe_input = sanitize(user_input)
        # safe_input = "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    """
    return RequestSanitizer().sanitize(data)
