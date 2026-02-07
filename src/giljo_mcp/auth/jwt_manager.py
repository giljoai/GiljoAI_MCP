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
from uuid import UUID

import jwt
from fastapi import HTTPException, status


class JWTManager:
    """Manage JWT tokens for user sessions"""

    # Default algorithm and token expiration
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 24

    @classmethod
    def _get_secret_key(cls) -> str:
        """
        Get JWT secret key from environment variables.

        Loads dynamically to ensure .env file has been processed.

        Returns:
            Secret key string

        Raises:
            RuntimeError: If no secret key is found
        """
        # Try multiple environment variable names
        secret_key = os.getenv("JWT_SECRET") or os.getenv("GILJO_MCP_SECRET_KEY") or os.getenv("SECRET_KEY")

        if not secret_key:
            # Try to load .env file if not already loaded
            try:
                from dotenv import load_dotenv

                load_dotenv(override=False)  # Don't override existing values

                # Try again after loading .env
                secret_key = os.getenv("JWT_SECRET") or os.getenv("GILJO_MCP_SECRET_KEY") or os.getenv("SECRET_KEY")
            except ImportError:
                pass  # dotenv not available

        if not secret_key:
            raise RuntimeError(
                "JWT secret key not found in environment variables. "
                "Please ensure JWT_SECRET, GILJO_MCP_SECRET_KEY, or SECRET_KEY is set in .env file. "
                "Run 'python install.py' to regenerate configuration if needed."
            )

        return secret_key

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
        secret_key = cls._get_secret_key()

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
        return jwt.encode(payload, secret_key, algorithm=cls.ALGORITHM)

    @classmethod
    def verify_token(cls, token: str) -> dict:
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
        try:
            secret_key = cls._get_secret_key()
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"JWT configuration error: {e}"
            ) from e

        try:
            payload = jwt.decode(token, secret_key, algorithms=[cls.ALGORITHM])

            # Verify token type (if present)
            if payload.get("type") != "access":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

            return payload

        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired. Please login again."
            ) from e
        except jwt.InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Could not validate credentials: {e!s}"
            ) from e

    @classmethod
    def decode_token_no_verify(cls, token: str) -> dict:
        """
        Decode JWT token without verification (for debugging/testing only).

        WARNING: Do NOT use for authentication - this does not verify signature!
        Use verify_token() for production authentication.

        Args:
            token: JWT token string to decode

        Returns:
            Decoded payload (unverified)

        Example:
            >>> token = JWTManager.create_access_token(...)
            >>> payload = JWTManager.decode_token_no_verify(token)
            >>> payload["exp"]  # Check expiration claim in tests
        """
        return jwt.decode(token, options={"verify_signature": False})
