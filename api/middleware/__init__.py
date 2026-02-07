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
from .auth_rate_limiter import RateLimiter as AuthRateLimiter
from .auth_rate_limiter import get_rate_limiter
from .csrf import CSRFProtectionMiddleware, CSRFProtectionOptional, get_csrf_token
from .input_validator import InputValidationMiddleware, RequestSanitizer, sanitize
from .logging_middleware import LoggingMiddleware
from .metrics import APIMetricsMiddleware
from .rate_limiter import EndpointRateLimiter, RateLimiter, RateLimitMiddleware

# New security middleware (Handover 0129c)
from .security import CORSSecurityMiddleware, SecurityHeadersMiddleware


__all__ = [
    "APIMetricsMiddleware",
    # Existing middleware
    "AuthMiddleware",
    "AuthRateLimiter",
    "CORSSecurityMiddleware",
    "CSRFProtectionMiddleware",
    "CSRFProtectionOptional",
    "EndpointRateLimiter",
    "InputValidationMiddleware",
    "LoggingMiddleware",
    "RateLimitMiddleware",
    "RateLimiter",
    "RequestSanitizer",
    # New security middleware
    "SecurityHeadersMiddleware",
    "get_csrf_token",
    # Auth-specific rate limiting
    "get_rate_limiter",
    "sanitize",
]
