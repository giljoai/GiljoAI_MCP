"""
Middleware for GiljoAI MCP

This module provides both existing and new security middleware:

Existing middleware (migrated from api/middleware.py):
- AuthMiddleware: Authentication for all API requests
- LoggingMiddleware: Request/response logging
- APIMetricsMiddleware: API and MCP call tracking

New security middleware (Handover 0129c):
- SecurityHeadersMiddleware: Security headers (HSTS, CSP, X-Frame-Options, etc.)
- CORSSecurityMiddleware: Enhanced CORS with security controls
- RateLimitMiddleware: Per-IP rate limiting (100 req/min default)
- InputValidationMiddleware: Input validation and sanitization
- CSRFProtectionMiddleware: CSRF protection

Created/Updated in Handover 0129c - Security Hardening & OWASP Compliance
"""

# Existing middleware (migrated)
from .auth import AuthMiddleware
from .logging_middleware import LoggingMiddleware
from .metrics import APIMetricsMiddleware

# New security middleware (Handover 0129c)
from .security import SecurityHeadersMiddleware, CORSSecurityMiddleware
from .rate_limiter import RateLimitMiddleware, EndpointRateLimiter, RateLimiter
from .auth_rate_limiter import get_rate_limiter, RateLimiter as AuthRateLimiter
from .input_validator import InputValidationMiddleware, RequestSanitizer, sanitize
from .csrf import CSRFProtectionMiddleware, CSRFProtectionOptional, get_csrf_token

__all__ = [
    # Existing middleware
    "AuthMiddleware",
    "LoggingMiddleware",
    "APIMetricsMiddleware",
    # New security middleware
    "SecurityHeadersMiddleware",
    "CORSSecurityMiddleware",
    "RateLimitMiddleware",
    "EndpointRateLimiter",
    "RateLimiter",
    "InputValidationMiddleware",
    "RequestSanitizer",
    "sanitize",
    "CSRFProtectionMiddleware",
    "CSRFProtectionOptional",
    "get_csrf_token",
    # Auth-specific rate limiting
    "get_rate_limiter",
    "AuthRateLimiter",
]
