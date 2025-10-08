"""
Authentication module for GiljoAI MCP.

This module provides authentication components for LAN/WAN deployment modes:
- JWT token management for web dashboard sessions
- Auth dependencies for FastAPI endpoints
- Legacy AuthManager for file-based auth (backwards compatibility)

Components:
    - JWTManager: Create and verify JWT tokens
    - get_current_user: FastAPI dependency for authentication
    - require_admin: FastAPI dependency for admin-only endpoints
    - AuthManager: Legacy file-based auth (imported from sibling module)
"""

# Import from the auth/ subdirectory modules
from .jwt_manager import JWTManager
from .dependencies import (
    get_current_user,
    get_current_active_user,
    get_current_user_optional,
    require_admin,
    get_db_session
)

# Import AuthManager from the legacy auth module (renamed from auth.py to auth_legacy.py)
from giljo_mcp.auth_legacy import AuthManager

__all__ = [
    "AuthManager",  # Legacy
    "JWTManager",
    "get_current_user",
    "get_current_active_user",
    "get_current_user_optional",
    "require_admin",
    "get_db_session"
]
