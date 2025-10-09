"""
Authentication module for GiljoAI MCP.

This module provides authentication components for LAN/WAN deployment modes:
- JWT token management for web dashboard sessions
- Auth dependencies for FastAPI endpoints
- Auto-login for localhost clients (127.0.0.1, ::1)
- Localhost user management
- Legacy AuthManager for file-based auth (backwards compatibility)

Components:
    - JWTManager: Create and verify JWT tokens
    - AutoLoginMiddleware: Auto-authenticate localhost clients
    - ensure_localhost_user: Create/retrieve system localhost user
    - get_localhost_user: Retrieve localhost user
    - get_current_user: FastAPI dependency for authentication
    - require_admin: FastAPI dependency for admin-only endpoints
    - AuthManager: Legacy file-based auth (imported from sibling module)
"""

# Import from the auth/ subdirectory modules
# Import AuthManager from the legacy auth module (renamed from auth.py to auth_legacy.py)
from giljo_mcp.auth_legacy import AuthManager

from .auto_login import AutoLoginMiddleware, LOCALHOST_IPS
from .dependencies import (
    get_current_active_user,
    get_current_user,
    get_current_user_optional,
    get_db_session,
    require_admin,
)
from .jwt_manager import JWTManager
from .localhost_user import ensure_localhost_user, get_localhost_user


__all__ = [
    # Legacy
    "AuthManager",
    # JWT
    "JWTManager",
    # Auto-login
    "AutoLoginMiddleware",
    "LOCALHOST_IPS",
    "ensure_localhost_user",
    "get_localhost_user",
    # Dependencies
    "get_current_active_user",
    "get_current_user",
    "get_current_user_optional",
    "get_db_session",
    "require_admin",
]
