"""
Authentication Middleware for GiljoAI MCP
Supports auto-login for localhost and JWT/API key for network clients
"""

import json
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

import jwt
from cryptography.fernet import Fernet
from fastapi import Request
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
            except Exception as e:
                logger.warning(f"Could not decrypt existing keys (might be unencrypted): {e}")
                # Try reading as plaintext for migration
                try:
                    existing_keys = json.loads(api_keys_file.read_text())
                    logger.info("Migrating plaintext API keys to encrypted storage")
                except Exception:
                    existing_keys = {}

        existing_keys[api_key] = self.api_keys[api_key]

        # Encrypt and save
        plaintext_data = json.dumps(existing_keys, indent=2).encode()
        encrypted_data = self.cipher.encrypt(plaintext_data)
        api_keys_file.write_bytes(encrypted_data)

        logger.info(f"Generated and encrypted API key for '{name}'")
        return api_key

    def get_or_create_api_key(self, name: str, permissions: Optional[list[str]] = None) -> str:
        """
        Get an existing API key by name or create a new one if it doesn't exist.

        This method provides idempotent behavior for API key generation:
        - If an active key with the given name exists, return it
        - If a revoked key with the given name exists, create new key with timestamped name
        - If no key exists, create a new one

        This ensures that re-running the setup wizard doesn't create duplicate keys
        and that the API key modal always appears with a valid key for LAN mode.

        Args:
            name: Name/description for the API key
            permissions: Optional list of permissions (default: ["*"])

        Returns:
            API key string (either existing or newly created)
        """
        # Load API keys from encrypted file if not in memory
        if not self.api_keys:
            api_keys_file = Path.home() / ".giljo-mcp" / "api_keys.json"
            if api_keys_file.exists():
                try:
                    # Decrypt and load keys
                    encrypted_data = api_keys_file.read_bytes()
                    decrypted_data = self.cipher.decrypt(encrypted_data)
                    self.api_keys = json.loads(decrypted_data.decode())
                    logger.debug("Loaded API keys from encrypted storage")
                except Exception as e:
                    logger.warning(f"Could not decrypt API keys (might be unencrypted): {e}")
                    # Try reading as plaintext for migration
                    try:
                        self.api_keys = json.loads(api_keys_file.read_text())
                        logger.info("Loaded plaintext API keys - will encrypt on next save")
                    except Exception:
                        logger.error("Could not load API keys from file")
                        self.api_keys = {}

        # Check if an active key with this name already exists
        for api_key, key_info in self.api_keys.items():
            if key_info.get("name") == name and key_info.get("active", True):
                # Found an active key with matching name - return it (idempotent)
                key_prefix = api_key[:10] + "..."
                logger.info(f"Reusing existing active API key '{name}' (prefix: {key_prefix})")
                return api_key

        # Check if a revoked key with this name exists
        revoked_key_exists = any(
            key_info.get("name") == name and not key_info.get("active", True) for key_info in self.api_keys.values()
        )

        if revoked_key_exists:
            # Create new key with timestamped name to avoid collision
            timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            timestamped_name = f"{name} ({timestamp})"
            logger.info(f"Revoked key exists with name '{name}', creating new key with name '{timestamped_name}'")
            api_key = self.generate_api_key(name=timestamped_name, permissions=permissions)
        else:
            # No key exists - create new one
            logger.info(f"No existing key found for '{name}', creating new API key")
            api_key = self.generate_api_key(name=name, permissions=permissions)

        # Log key prefix for debugging (never log full key)
        key_prefix = api_key[:10] + "..."
        logger.info(f"API key created/retrieved for '{name}' (prefix: {key_prefix})")

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
                except Exception as e:
                    logger.warning(f"Could not decrypt API keys (might be unencrypted): {e}")
                    # Try reading as plaintext for migration
                    try:
                        self.api_keys = json.loads(api_keys_file.read_text())
                        logger.info("Loaded plaintext API keys - will encrypt on next save")
                    except Exception:
                        logger.error("Could not load API keys from file")
                        self.api_keys = {}

        if api_key in self.api_keys:
            key_info = self.api_keys[api_key]
            if key_info.get("active", True):
                return key_info

        return None

    def store_admin_account(self, username: str, password: str, tenant_key: str = "default") -> None:
        """
        Hash password and store admin account in encrypted format.

        Args:
            username: Admin username
            password: Plain text password (will be hashed)
            tenant_key: Tenant key for multi-tenant isolation

        Note:
            Password is hashed using bcrypt before storage.
            Data is encrypted using Fernet cipher before writing to disk.
        """
        from passlib.hash import bcrypt

        # Hash the password using bcrypt
        password_hash = bcrypt.hash(password)

        admin_data = {
            "username": username,
            "password_hash": password_hash,
            "tenant_key": tenant_key,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

        # Store in encrypted file
        admin_file = Path.home() / ".giljo-mcp" / "admin_account.json"
        admin_file.parent.mkdir(parents=True, exist_ok=True)

        # Encrypt and save
        plaintext_data = json.dumps(admin_data, indent=2).encode()
        encrypted_data = self.cipher.encrypt(plaintext_data)
        admin_file.write_bytes(encrypted_data)

        logger.info(f"Stored encrypted admin account for user '{username}'")

    def validate_admin_credentials(self, username: str, password: str) -> bool:
        """
        Validate admin credentials against stored account.

        Args:
            username: Admin username
            password: Plain text password to validate

        Returns:
            True if credentials are valid, False otherwise
        """
        from passlib.hash import bcrypt

        admin_file = Path.home() / ".giljo-mcp" / "admin_account.json"

        if not admin_file.exists():
            logger.warning("No admin account configured")
            return False

        try:
            # Decrypt admin account
            encrypted_data = admin_file.read_bytes()
            decrypted_data = self.cipher.decrypt(encrypted_data)
            admin_data = json.loads(decrypted_data.decode())

            # Check username matches
            if admin_data.get("username") != username:
                return False

            # Verify password hash
            password_hash = admin_data.get("password_hash")
            return bcrypt.verify(password, password_hash)

        except Exception as e:
            logger.error(f"Failed to validate admin credentials: {e}")
            return False

    def generate_jwt_token(self, user_id: str, tenant_key: Optional[str] = None, expires_in: int = 3600) -> str:
        """Generate JWT token for WAN mode"""
        payload = {
            "user_id": user_id,
            "tenant_key": tenant_key,
            "iat": datetime.now(timezone.utc),
            "exp": datetime.now(timezone.utc) + timedelta(seconds=expires_in),
        }

        token = jwt.encode(payload, self.jwt_secret, algorithm="HS256")
        logger.info(f"Generated JWT token for user '{user_id}'")
        return token

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

    def _get_client_ip(self, request: Request) -> str:
        """
        Get client IP from request (handles proxies).

        Args:
            request: FastAPI Request object

        Returns:
            str: Client IP address
        """
        # Check X-Forwarded-For (reverse proxy)
        forwarded_for = request.headers.get("X-Forwarded-For", "").strip()
        if forwarded_for:
            # Take first IP (original client)
            return forwarded_for.split(",")[0].strip()

        # Check X-Real-IP (nginx)
        real_ip = request.headers.get("X-Real-IP", "").strip()
        if real_ip:
            return real_ip

        # Direct connection
        if hasattr(request, "client") and request.client:
            return request.client.host

        return "unknown"

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
            for cookie in cookie_header.split(";"):
                cookie = cookie.strip()
                if "=" in cookie:
                    key, value = cookie.split("=", 1)
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
                    "tenant_key": token_info.get("tenant_key", "default"),
                    "is_auto_login": False,
                    "permissions": ["*"],
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
                    except Exception as e:
                        logger.warning(f"Failed to load user object for JWT: {e}")

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
            "tenant_key": "default",  # API keys use default tenant for now
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
            except Exception as e:
                logger.debug(f"No user object found for API key: {e}")

        return result


def create_auth_middleware(auth_manager: AuthManager):
    """
    Create FastMCP middleware for authentication

    Note: FastMCP middleware integration depends on the framework's support.
    This is a placeholder that shows the authentication logic.
    """

    async def auth_middleware(request, call_next):
        """Middleware to check authentication before processing requests"""

        # Skip auth for health check endpoints
        if request.url.path in ["/health", "/ready"]:
            return await call_next(request)

        # Extract authentication credentials
        authorization = request.headers.get("Authorization")
        api_key = request.headers.get("X-API-Key") or request.query_params.get("api_key")

        # Authenticate the request
        auth_result = await auth_manager.authenticate_request(authorization=authorization, api_key=api_key)

        if not auth_result["authenticated"]:
            # Return authentication error
            return {"error": auth_result["error"], "status": 401}

        # Attach auth info to request for downstream use
        request.state.auth = auth_result

        # Continue processing
        return await call_next(request)

    return auth_middleware
