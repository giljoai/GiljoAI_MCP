"""
Authentication Middleware for GiljoAI MCP
Supports LOCAL (no auth), LAN (API key), and WAN (JWT) modes
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
from fastmcp import FastMCP

from .config_manager import DeploymentMode, get_config
from .database import DatabaseManager
from .models import Configuration


logger = logging.getLogger(__name__)


class AuthManager:
    """Manages authentication across different deployment modes"""

    def __init__(self, config=None):
        """Initialize authentication manager"""
        self.config = config or get_config()
        self.mode = self.config.server.mode
        self.jwt_secret = self._get_or_create_jwt_secret()
        self.api_keys: dict[str, dict[str, Any]] = {}
        self.encryption_key = self._get_or_create_encryption_key()
        self.cipher = Fernet(self.encryption_key)

    def is_enabled(self) -> bool:
        """Check if authentication is enabled based on deployment mode"""
        # Authentication is disabled in LOCAL mode, enabled in LAN and WAN modes
        return self.mode != DeploymentMode.LOCAL

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

    async def authenticate_request(
        self, authorization: Optional[str] = None, api_key: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Authenticate a request based on deployment mode

        Args:
            authorization: Authorization header value
            api_key: API key from header or query parameter

        Returns:
            Authentication result with user info and permissions
        """
        # LOCAL mode - no authentication required
        if self.mode == DeploymentMode.LOCAL:
            return {
                "authenticated": True,
                "mode": "LOCAL",
                "user": "local",
                "permissions": ["*"],
            }

        # LAN mode - API key authentication
        if self.mode == DeploymentMode.LAN:
            if not api_key:
                return {
                    "authenticated": False,
                    "error": "API key required for LAN mode",
                }

            key_info = self.validate_api_key(api_key)
            if key_info:
                return {
                    "authenticated": True,
                    "mode": "LAN",
                    "user": key_info["name"],
                    "permissions": key_info.get("permissions", ["*"]),
                }
            return {"authenticated": False, "error": "Invalid API key"}

        # WAN mode - JWT authentication
        if self.mode == DeploymentMode.WAN:
            if not authorization or not authorization.startswith("Bearer "):
                return {
                    "authenticated": False,
                    "error": "Bearer token required for WAN mode",
                }

            token = authorization.replace("Bearer ", "")
            token_info = self.validate_jwt_token(token)

            if token_info:
                return {
                    "authenticated": True,
                    "mode": "WAN",
                    "user": token_info["user_id"],
                    "tenant_key": token_info.get("tenant_key"),
                    "permissions": ["*"],  # Could be extended with role-based permissions
                }
            return {"authenticated": False, "error": "Invalid or expired token"}

        return {"authenticated": False, "error": "Unknown deployment mode"}


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


def register_auth_tools(mcp: FastMCP, db_manager: DatabaseManager, auth_manager: AuthManager):
    """Register authentication management tools"""

    @mcp.tool()
    async def generate_api_key(name: str) -> dict[str, Any]:
        """
        Generate a new API key for LAN mode access

        Args:
            name: Name/description for the API key

        Returns:
            Generated API key
        """
        if auth_manager.mode != DeploymentMode.LAN:
            return {
                "success": False,
                "error": f"API keys are only used in LAN mode (current: {auth_manager.mode.value})",
            }

        try:
            api_key = auth_manager.generate_api_key(name)

            # Store in database for persistence
            async with db_manager.get_session() as session:
                config = Configuration(
                    key=f"api_key_{name}",
                    value=api_key,
                    category="auth",
                    created_at=datetime.now(timezone.utc),
                )
                session.add(config)
                await session.commit()

            return {
                "success": True,
                "api_key": api_key,
                "name": name,
                "message": "Store this key securely - it won't be shown again",
            }

        except Exception as e:
            logger.exception(f"Failed to generate API key: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def revoke_api_key(api_key: str) -> dict[str, Any]:
        """
        Revoke an API key

        Args:
            api_key: The API key to revoke

        Returns:
            Revocation confirmation
        """
        try:
            # Load and update API keys
            api_keys_file = Path.home() / ".giljo-mcp" / "api_keys.json"

            if not api_keys_file.exists():
                return {"success": False, "error": "No API keys found"}

            # Decrypt existing keys
            try:
                encrypted_data = api_keys_file.read_bytes()
                decrypted_data = auth_manager.cipher.decrypt(encrypted_data)
                api_keys = json.loads(decrypted_data.decode())
            except Exception:
                # Try plaintext for migration
                api_keys = json.loads(api_keys_file.read_text())

            if api_key not in api_keys:
                return {"success": False, "error": "API key not found"}

            # Mark as inactive
            api_keys[api_key]["active"] = False
            api_keys[api_key]["revoked_at"] = datetime.now(timezone.utc).isoformat()

            # Encrypt and save updated keys
            plaintext_data = json.dumps(api_keys, indent=2).encode()
            encrypted_data = auth_manager.cipher.encrypt(plaintext_data)
            api_keys_file.write_bytes(encrypted_data)

            # Update in memory
            auth_manager.api_keys = api_keys

            return {"success": True, "api_key": api_key, "status": "revoked"}

        except Exception as e:
            logger.exception(f"Failed to revoke API key: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def generate_jwt_token(
        user_id: str, tenant_key: Optional[str] = None, expires_in: int = 3600
    ) -> dict[str, Any]:
        """
        Generate JWT token for WAN mode

        Args:
            user_id: User identifier
            tenant_key: Optional tenant key to include in token
            expires_in: Token expiration time in seconds

        Returns:
            Generated JWT token
        """
        if auth_manager.mode != DeploymentMode.WAN:
            return {
                "success": False,
                "error": f"JWT tokens are only used in WAN mode (current: {auth_manager.mode.value})",
            }

        try:
            token = auth_manager.generate_jwt_token(user_id, tenant_key, expires_in)

            return {
                "success": True,
                "token": token,
                "user_id": user_id,
                "expires_in": expires_in,
            }

        except Exception as e:
            logger.exception(f"Failed to generate JWT token: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Authentication tools registered")
