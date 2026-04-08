# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Authentication Middleware for GiljoAI MCP
Supports auto-login for localhost and JWT/API key for network clients
"""

import json
import logging
import os
import secrets
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

import jwt
from cryptography.fernet import Fernet, InvalidToken
from fastapi import Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from .config_manager import get_config


logger = logging.getLogger(__name__)


class AuthManager:
    """
    Manages authentication with unified logic (production parity).

    All clients (localhost and network) require JWT Bearer token or API key.
    No special treatment for localhost - ensures consistent auth testing.
    """

    def __init__(self, config=None, db: Optional[AsyncSession] = None):
        """
        Initialize authentication manager.

        Args:
            config: Optional configuration object
            db: Optional async database session for auto-login user management
        """
        self.config = config or get_config()
        self.db = db
        self.jwt_secret = self._get_or_create_jwt_secret()
        self.api_keys: dict[str, dict[str, Any]] = {}
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

    def _get_or_create_jwt_secret(self) -> str:
        """Get or create JWT secret for token signing"""
        # First check environment variables
        env_secret = os.getenv("JWT_SECRET") or os.getenv("GILJO_MCP_SECRET_KEY")
        if env_secret:
            logger.info("Using JWT secret from environment variable")
            return env_secret

        # Fall back to file-based secret
        secret_file = Path.home() / ".giljo-mcp" / "jwt_secret"
        secret_file.parent.mkdir(parents=True, exist_ok=True)

        if secret_file.exists():
            return secret_file.read_text().strip()
        secret = secrets.token_urlsafe(32)
        secret_file.write_text(secret)
        return secret

    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create Fernet encryption key for API key storage"""
        # Check environment variable first
        env_key = os.getenv("GILJO_MCP_ENCRYPTION_KEY")
        if env_key:
            logger.info("Using encryption key from environment variable")
            return env_key.encode()

        # Fall back to file-based key
        key_file = Path.home() / ".giljo-mcp" / "encryption_key"
        key_file.parent.mkdir(parents=True, exist_ok=True)

        if key_file.exists():
            return key_file.read_bytes()

        # Generate new Fernet key
        key = Fernet.generate_key()
        key_file.write_bytes(key)
        logger.info(f"Generated new encryption key stored at: {key_file}")
        return key

    def generate_api_key(self, name: str, permissions: Optional[list[str]] = None) -> str:
        """Generate a new API key for LAN mode"""
        api_key = f"gk_{secrets.token_urlsafe(32)}"

        self.api_keys[api_key] = {
            "name": name,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "permissions": permissions or ["*"],
            "active": True,
        }

        # Store API key in encrypted file for persistence
        api_keys_file = Path.home() / ".giljo-mcp" / "api_keys.json"
        api_keys_file.parent.mkdir(parents=True, exist_ok=True)

        existing_keys = {}
        if api_keys_file.exists():
            try:
                # Decrypt existing keys
                encrypted_data = api_keys_file.read_bytes()
                decrypted_data = self.cipher.decrypt(encrypted_data)
                existing_keys = json.loads(decrypted_data.decode())
            except (InvalidToken, OSError, json.JSONDecodeError, ValueError) as e:
                logger.warning(f"Could not decrypt existing keys (might be unencrypted): {e}")
                # Try reading as plaintext for migration
                try:
                    existing_keys = json.loads(api_keys_file.read_text())
                    logger.info("Migrating plaintext API keys to encrypted storage")
                except (OSError, json.JSONDecodeError, ValueError):
                    existing_keys = {}

        existing_keys[api_key] = self.api_keys[api_key]

        # Encrypt and save
        plaintext_data = json.dumps(existing_keys, indent=2).encode()
        encrypted_data = self.cipher.encrypt(plaintext_data)
        api_keys_file.write_bytes(encrypted_data)

        logger.info(f"Generated and encrypted API key for '{name}'")
        return api_key

    def validate_api_key(self, api_key: str) -> Optional[dict[str, Any]]:
        """Validate an API key for LAN mode"""
        # Load API keys from encrypted file if not in memory
        if not self.api_keys:
            api_keys_file = Path.home() / ".giljo-mcp" / "api_keys.json"
            if api_keys_file.exists():
                try:
                    # Decrypt and load keys
                    encrypted_data = api_keys_file.read_bytes()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    self.api_keys = json.loads(decrypted_data.decode())
                except (InvalidToken, OSError, json.JSONDecodeError, ValueError) as e:
                    logger.warning(f"Could not decrypt API keys (might be unencrypted): {e}")
                    # Try reading as plaintext for migration
                    try:
                        self.api_keys = json.loads(api_keys_file.read_text())
                        logger.info("Loaded plaintext API keys - will encrypt on next save")
                    except (OSError, json.JSONDecodeError, ValueError):
                        logger.exception("Could not load API keys from file")
                        self.api_keys = {}

        if api_key in self.api_keys:
            key_info = self.api_keys[api_key]
            if key_info.get("active", True):
                return key_info

        return None

    def validate_jwt_token(self, token: str) -> Optional[dict[str, Any]]:
        """Validate JWT token for WAN mode"""
        try:
            payload = jwt.decode(token, self.jwt_secret, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid JWT token: {e}")
            return None

    async def authenticate_request(self, request: Request) -> dict[str, Any]:
        """
        Authenticate incoming request.

        Unified authentication for all clients (localhost and network):
        - Requires JWT Bearer token or API key for ALL connections
        - No special treatment for localhost (production parity)

        Args:
            request: FastAPI Request object

        Returns:
            dict: Authentication result with keys:
                - authenticated: bool
                - user: str (username)
                - user_id: str (username for consistency)
                - tenant_key: str (tenant key)
                - error: str (if authentication failed)
                - user_obj: User (if authenticated via database)

        Example:
            >>> result = await auth_manager.authenticate_request(request)
            >>> if result["authenticated"]:
            ...     print(f"User: {result['user']}")
        """
        # All clients require credentials (unified auth)
        return await self._validate_network_credentials(request)

    async def _validate_network_credentials(self, request: Request) -> dict[str, Any]:
        """
        Validate JWT token or API key for network clients.

        Priority:
        1. JWT token from httpOnly cookie (access_token)
        2. JWT Bearer token (Authorization: Bearer <token>)
        3. API key (X-API-Key header)
        4. Unauthenticated (return error)

        Args:
            request: FastAPI Request object

        Returns:
            dict: Authentication result with consistent user_id and user_obj
        """
        from sqlalchemy import select

        from .models import User

        # Try httpOnly cookie FIRST (PRIMARY AUTH METHOD for web dashboard)
        token = None
        cookie_header = request.headers.get("cookie", "")
        if cookie_header:
            # Parse cookies from Cookie header
            cookies = {}
            for cookie_str in cookie_header.split(";"):
                cookie_clean = cookie_str.strip()
                if "=" in cookie_clean:
                    key, value = cookie_clean.split("=", 1)
                    cookies[key.strip()] = value.strip()

            # Get access_token from cookies
            token = cookies.get("access_token")
            if token:
                logger.debug("REST API: Found JWT token in httpOnly cookie")

        # Try Authorization header if no cookie token found
        if not token:
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]  # Remove "Bearer " prefix

        # Validate JWT token if found
        if token:
            logger.info(f"[Network Auth] Found JWT token (length: {len(token)})")
            # Check if it's a JWT token
            token_info = self.validate_jwt_token(token)
            logger.info(f"[Network Auth] JWT validation result: {bool(token_info)}")
            if token_info:
                jwt_result = {
                    "authenticated": True,
                    "user": token_info.get("username"),
                    "user_id": token_info.get("username"),
                    "tenant_key": token_info.get("tenant_key"),
                    "is_auto_login": False,
                    "permissions": ["*"],
                    "exp": token_info.get("exp"),
                }

                # Get user object from database for consistency
                db_manager = getattr(request.app.state, "db_manager", None)
                if db_manager:
                    try:
                        async with db_manager.get_session_async() as session:
                            result = await session.execute(
                                select(User).where(User.username == token_info.get("username"))
                            )
                            user_obj = result.scalar_one_or_none()

                            if user_obj:
                                jwt_result["user_obj"] = user_obj
                                # Update tenant_key from user object (authoritative source)
                                jwt_result["tenant_key"] = user_obj.tenant_key
                    except SQLAlchemyError as e:
                        logger.warning(f"Failed to load user object for JWT: {e}")

                # Reject if tenant_key is still None after DB lookup attempt
                if not jwt_result.get("tenant_key"):
                    logger.warning("JWT authentication rejected: no tenant_key in token or user record")
                    return {"authenticated": False, "error": "Missing tenant key"}

                return jwt_result

            # If JWT validation failed, try as API key
            key_info = self.validate_api_key(token)
            if key_info:
                return await self._build_api_key_result(key_info, request)

        # Try API key (X-API-Key header)
        api_key = request.headers.get("X-API-Key")
        if api_key:
            key_info = self.validate_api_key(api_key)
            if key_info:
                return await self._build_api_key_result(key_info, request)

        # No valid credentials
        logger.warning("[Network Auth] Authentication failed - no valid credentials found")
        return {"authenticated": False, "error": "Authentication required for network access"}

    async def _build_api_key_result(self, key_info: dict[str, Any], request: Request) -> dict[str, Any]:
        """
        Build authentication result for API key with user object lookup.

        Args:
            key_info: API key information
            request: FastAPI Request object

        Returns:
            dict: Authentication result with user_obj if available
        """
        from sqlalchemy import select

        from .models import User

        result = {
            "authenticated": True,
            "user": key_info["name"],
            "user_id": key_info["name"],
            "tenant_key": key_info.get("tenant_key"),  # Resolved from key or DB lookup below
            "is_auto_login": False,
            "permissions": key_info.get("permissions", ["*"]),
        }

        # Try to get user object from database
        # Note: API keys might not have associated user accounts
        # This is best-effort for consistency
        db_manager = getattr(request.app.state, "db_manager", None)
        if db_manager:
            try:
                async with db_manager.get_session_async() as session:
                    db_result = await session.execute(select(User).where(User.username == key_info["name"]))
                    user_obj = db_result.scalar_one_or_none()

                    if user_obj:
                        result["user_obj"] = user_obj
                        # Update tenant_key from user object (authoritative source)
                        result["tenant_key"] = user_obj.tenant_key
            except SQLAlchemyError as e:
                logger.debug(f"No user object found for API key: {e}")

        # Reject if tenant_key is still None after DB lookup attempt
        if not result.get("tenant_key"):
            logger.warning("API key authentication rejected: no tenant_key resolved")
            return {"authenticated": False, "error": "Missing tenant key"}

        return result
