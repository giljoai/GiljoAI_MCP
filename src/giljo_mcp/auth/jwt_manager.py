"""
JWT token generation and validation for web dashboard sessions.

This module provides JWT token management for LAN/WAN authentication:
- Creates access tokens for authenticated web users
- Verifies and decodes JWT tokens from httpOnly cookies
- Manages token expiration (24 hours default)
- Uses HS256 algorithm with secret from environment

Security Notes:
- Tokens are signed with secret key (not encrypted - JWTs are self-contained)
- Tokens include user_id, username, role, tenant_key in payload
- Token expiration is enforced (24 hours)
- Secret key must be kept secure (use environment variables)

Usage Example:
    from giljo_mcp.auth.jwt_manager import JWTManager

    # Create token after login
    token = JWTManager.create_access_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        tenant_key=user.tenant_key
    )

    # Verify token from cookie
    try:
        payload = JWTManager.verify_token(token)
        user_id = payload["sub"]
    except HTTPException:
        # Invalid or expired token
        pass
"""

import os
from datetime import datetime, timedelta, timezone
from typing import Dict
from uuid import UUID

import jwt
from fastapi import HTTPException, status


class JWTManager:
    """Manage JWT tokens for user sessions"""

    # Get secret from environment or use the one from AuthManager
    SECRET_KEY = os.getenv("JWT_SECRET") or os.getenv("GILJO_MCP_SECRET_KEY")
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 24

    @classmethod
    def create_access_token(cls, user_id: UUID, username: str, role: str, tenant_key: str = "default") -> str:
        """
        Create JWT access token for authenticated user.

        Args:
            user_id: User's UUID
            username: User's username
            role: User's role (admin, developer, viewer)
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Encoded JWT token string

        Example:
            >>> token = JWTManager.create_access_token(
            ...     user_id=UUID("123e4567-e89b-12d3-a456-426614174000"),
            ...     username="admin",
            ...     role="admin",
            ...     tenant_key="default"
            ... )
            >>> token.startswith("eyJ")  # JWT format
            True
        """
        if not cls.SECRET_KEY:
            raise RuntimeError(
                "JWT_SECRET or GILJO_MCP_SECRET_KEY environment variable not set. "
                "Cannot create access tokens without secret key."
            )

        expire = datetime.now(timezone.utc) + timedelta(hours=cls.ACCESS_TOKEN_EXPIRE_HOURS)
        payload = {
            "sub": str(user_id),  # Subject (user ID)
            "username": username,
            "role": role,
            "tenant_key": tenant_key,
            "exp": expire,  # Expiration time
            "iat": datetime.now(timezone.utc),  # Issued at
            "type": "access",  # Token type
        }
        return jwt.encode(payload, cls.SECRET_KEY, algorithm=cls.ALGORITHM)

    @classmethod
    def verify_token(cls, token: str) -> Dict:
        """
        Verify and decode JWT token.

        Args:
            token: JWT token string to verify

        Returns:
            Decoded token payload containing:
                - sub: User ID (as string UUID)
                - username: User's username
                - role: User's role
                - tenant_key: Tenant key
                - exp: Expiration timestamp
                - iat: Issued at timestamp

        Raises:
            HTTPException: If token is invalid or expired

        Example:
            >>> token = JWTManager.create_access_token(...)
            >>> payload = JWTManager.verify_token(token)
            >>> payload["username"]
            'admin'
        """
        if not cls.SECRET_KEY:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="JWT secret key not configured on server"
            )

        try:
            payload = jwt.decode(token, cls.SECRET_KEY, algorithms=[cls.ALGORITHM])

            # Verify token type (if present)
            if payload.get("type") != "access":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired. Please login again."
            )
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {e!s}"
            )

    @classmethod
    def decode_token_no_verify(cls, token: str) -> Dict:
        """
        Decode JWT token without verification (for debugging only).

        WARNING: Do NOT use for authentication - this does not verify signature!

        Args:
            token: JWT token string to decode

        Returns:
            Decoded payload (unverified)
        """
        return jwt.decode(token, options={"verify_signature": False})

    @classmethod
    def get_token_expiry(cls, token: str) -> datetime:
        """
        Get expiration time from token.

        Args:
            token: JWT token string

        Returns:
            Expiration datetime (UTC)

        Raises:
            HTTPException: If token is invalid
        """
        payload = cls.verify_token(token)
        exp_timestamp = payload.get("exp")
        if not exp_timestamp:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing expiration claim")
        return datetime.fromtimestamp(exp_timestamp, tz=timezone.utc)

    @classmethod
    def is_token_expired(cls, token: str) -> bool:
        """
        Check if token is expired without raising exception.

        Args:
            token: JWT token string

        Returns:
            True if expired, False if still valid
        """
        try:
            cls.verify_token(token)
            return False
        except HTTPException as e:
            return "expired" in str(e.detail).lower()
