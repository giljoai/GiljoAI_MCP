"""
Authentication module for GiljoAI MCP.

This module provides unified authentication for all deployment contexts:
- JWT token management for web dashboard sessions
- Auth dependencies for FastAPI endpoints
- Production parity: localhost and network clients treated identically
- AuthManager: Main authentication manager

Components:
    - JWTManager: Create and verify JWT tokens
    - AutoLoginMiddleware: Deprecated (kept for backwards compatibility)
    - get_current_user: FastAPI dependency for authentication
    - require_admin: FastAPI dependency for admin-only endpoints
    - AuthManager: Main auth manager with unified logic
"""

# Import from the auth/ subdirectory modules
# Import AuthManager from the auth manager module
from giljo_mcp.auth_manager import AuthManager

from .auto_login import LOCALHOST_IPS, AutoLoginMiddleware
from .dependencies import (
    get_current_active_user,
    get_current_user,
    get_current_user_optional,
    get_db_session,
    require_admin,
)
from .jwt_manager import JWTManager


__all__ = [
    # Legacy
    "AuthManager",
    # JWT
    "JWTManager",
    # Auto-login
    "AutoLoginMiddleware",
    "LOCALHOST_IPS",
    # Dependencies
    "get_current_active_user",
    "get_current_user",
    "get_current_user_optional",
    "get_db_session",
    "require_admin",
]
