"""
OAuthService - OAuth 2.1 Authorization Code flow with PKCE.

Implements the server-side logic for OAuth 2.1 with S256 PKCE:
- Authorization request validation
- Authorization code generation and storage
- Code-to-token exchange with PKCE verification
- Redirect URI validation (localhost-only for CE)
- Expired/used code cleanup

Design Principles:
- Single Responsibility: Only OAuth authorization logic
- Exception-based errors: Raises ValueError on validation failures
- Stateless: Each method operates on the provided DB session
- PKCE-only: No client_secret, S256 challenge method required
"""

import base64
import hashlib
import logging
import re
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.auth.jwt_manager import JWTManager
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.oauth import OAuthAuthorizationCode


logger = logging.getLogger(__name__)

BUILTIN_CLIENT_ID = "giljo-mcp-default"
AUTHORIZATION_CODE_LIFETIME_MINUTES = 10
ALLOWED_REDIRECT_URI_PATTERNS = [
    r"^http://localhost(:\d+)?/",
    r"^http://127\.0\.0\.1(:\d+)?/",
    r"^http://\[::1\](:\d+)?/",
]


class OAuthService:
    """OAuth 2.1 Authorization Code flow with PKCE support.

    Manages the full authorization code lifecycle: validation, generation,
    exchange, and cleanup. Designed for the built-in MCP client only
    (single client_id, localhost redirect URIs).

    Args:
        db_session: SQLAlchemy async session for database operations.
    """

    def __init__(self, db_session: AsyncSession) -> None:
        self._db = db_session

    def validate_authorize_request(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        response_type: str,
        scope: str,
    ) -> None:
        """Validate an OAuth authorization request.

        Checks all parameters against expected values and patterns.
        This is a synchronous validation step before any DB interaction.

        Args:
            client_id: Must match BUILTIN_CLIENT_ID.
            redirect_uri: Must match an allowed localhost pattern.
            code_challenge: Base64url-encoded S256 challenge (non-empty).
            code_challenge_method: Must be "S256".
            response_type: Must be "code".
            scope: Requested scope (informational, not enforced here).

        Raises:
            ValueError: If any parameter fails validation.
        """
        if client_id != BUILTIN_CLIENT_ID:
            raise ValueError(f"Invalid client_id: expected '{BUILTIN_CLIENT_ID}', got '{client_id}'")

        if response_type != "code":
            raise ValueError(f"Invalid response_type: expected 'code', got '{response_type}'")

        if code_challenge_method != "S256":
            raise ValueError(f"Invalid code_challenge_method: expected 'S256', got '{code_challenge_method}'")

        if not code_challenge:
            raise ValueError("code_challenge is required and must be non-empty")

        if not self.validate_redirect_uri(redirect_uri):
            raise ValueError(f"Invalid redirect_uri: '{redirect_uri}' does not match allowed patterns")

    async def generate_authorization_code(
        self,
        user_id: str,
        tenant_key: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        scope: str = "mcp",
    ) -> str:
        """Generate and store a cryptographically random authorization code.

        Creates a single-use authorization code bound to the user, tenant,
        and PKCE challenge. The code expires after AUTHORIZATION_CODE_LIFETIME_MINUTES.

        Args:
            user_id: ID of the authenticated user.
            tenant_key: Tenant key for multi-tenant isolation.
            client_id: Client identifier (must be validated before calling).
            redirect_uri: Redirect URI registered for this request.
            code_challenge: Base64url-encoded S256 PKCE challenge.
            scope: Requested scope (default "mcp").

        Returns:
            The generated authorization code string.
        """
        code = secrets.token_urlsafe(64)
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=AUTHORIZATION_CODE_LIFETIME_MINUTES)

        auth_code = OAuthAuthorizationCode(
            code=code,
            client_id=client_id,
            user_id=user_id,
            tenant_key=tenant_key,
            redirect_uri=redirect_uri,
            code_challenge=code_challenge,
            code_challenge_method="S256",
            scope=scope,
            expires_at=expires_at,
            used=False,
        )

        self._db.add(auth_code)
        await self._db.flush()

        logger.info(
            "Generated authorization code for user_id=%s tenant_key=%s",
            user_id,
            tenant_key,
        )
        return code

    async def exchange_code_for_token(
        self,
        code: str,
        client_id: str,
        code_verifier: str,
        redirect_uri: str,
    ) -> dict:
        """Exchange an authorization code for a JWT access token.

        Validates the code, verifies PKCE, marks the code as used,
        and issues a JWT via JWTManager.

        Args:
            code: The authorization code to exchange.
            client_id: Client ID (must match the code's client_id).
            code_verifier: PKCE code verifier to prove possession.
            redirect_uri: Must match the URI used during authorization.

        Returns:
            Dict with access_token, token_type, and expires_in.

        Raises:
            ValueError: If the code is invalid, expired, used, or PKCE fails.
        """
        result = await self._db.execute(select(OAuthAuthorizationCode).where(OAuthAuthorizationCode.code == code))
        auth_code = result.scalar_one_or_none()

        if auth_code is None:
            raise ValueError("Authorization code not found")

        if auth_code.used:
            raise ValueError("Authorization code has already been used")

        if auth_code.expires_at < datetime.now(timezone.utc):
            raise ValueError("Authorization code has expired")

        if auth_code.client_id != client_id:
            raise ValueError(f"client_id mismatch: expected '{auth_code.client_id}', got '{client_id}'")

        if auth_code.redirect_uri != redirect_uri:
            raise ValueError(f"redirect_uri mismatch: expected '{auth_code.redirect_uri}', got '{redirect_uri}'")

        if not self.verify_pkce(code_verifier, auth_code.code_challenge):
            raise ValueError("PKCE verification failed: code_verifier does not match challenge")

        auth_code.used = True
        await self._db.flush()

        user_result = await self._db.execute(
            select(User).where(
                User.id == auth_code.user_id,
                User.tenant_key == auth_code.tenant_key,
            )
        )
        user = user_result.scalar_one_or_none()

        if user is None:
            raise ValueError("User associated with authorization code not found")

        access_token = JWTManager.create_access_token(
            user_id=UUID(user.id),
            username=user.username,
            role=user.role,
            tenant_key=user.tenant_key,
        )

        logger.info(
            "Exchanged authorization code for token: user_id=%s tenant_key=%s",
            user.id,
            user.tenant_key,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": 86400,
        }

    @staticmethod
    def verify_pkce(code_verifier: str, stored_challenge: str) -> bool:
        """Verify a PKCE code_verifier against a stored S256 challenge.

        Computes base64url(SHA256(code_verifier)) and compares it to the
        stored challenge value. Comparison uses constant-time equality
        via hmac.compare_digest for security.

        Args:
            code_verifier: The plaintext verifier from the token request.
            stored_challenge: The base64url-encoded S256 challenge from authorization.

        Returns:
            True if the verifier matches, False otherwise.
        """
        import hmac

        if not code_verifier:
            return False

        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        computed_challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
        return hmac.compare_digest(computed_challenge, stored_challenge)

    async def cleanup_expired_codes(self) -> int:
        """Delete all expired or used authorization codes.

        Returns:
            Number of deleted records.
        """
        now = datetime.now(timezone.utc)
        result = await self._db.execute(
            delete(OAuthAuthorizationCode).where(
                or_(
                    OAuthAuthorizationCode.expires_at < now,
                    OAuthAuthorizationCode.used == True,  # noqa: E712
                )
            )
        )
        await self._db.flush()

        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info("Cleaned up %d expired/used authorization codes", deleted_count)
        return deleted_count

    @staticmethod
    def validate_redirect_uri(redirect_uri: str) -> bool:
        """Check if a redirect URI matches allowed localhost patterns.

        Args:
            redirect_uri: The URI to validate.

        Returns:
            True if the URI matches any allowed pattern, False otherwise.
        """
        if not redirect_uri:
            return False

        return any(re.match(pattern, redirect_uri) for pattern in ALLOWED_REDIRECT_URI_PATTERNS)
