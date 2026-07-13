# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from fastapi import HTTPException, status


class JWTAudienceMismatchError(Exception):
    """Raised when a JWT carries an `aud` claim that does not match the expected audience.

    Distinct from jwt.InvalidTokenError so the MCP Bearer middleware can react
    differently: an aud mismatch is a positive auth signal that the token was
    issued for a different resource server. We reject outright (no fallback to
    API-key path) and emit RFC 6750 WWW-Authenticate so the client knows where
    to find the resource metadata.
    """


class JWTManager:
    """Manage JWT tokens for user sessions"""

    # Default algorithm and token expiration
    ALGORITHM = "HS256"
    ACCESS_TOKEN_EXPIRE_HOURS = 24
    REFRESH_GRACE_PERIOD_HOURS = 1

    @classmethod
    def _get_secret_key(cls) -> str:
        """
        Get JWT secret key from environment variables.

        Reads from os.environ only. .env loading is the responsibility of
        the application entry point (api.app lifespan, startup.py, install.py).
        Calling load_dotenv() here was a runtime side effect that mutated
        os.environ during request handling — relocated alongside seq 100 / 97.

        Returns:
            Secret key string

        Raises:
            RuntimeError: If no secret key is found
        """
        secret_key = os.getenv("JWT_SECRET") or os.getenv("GILJO_MCP_SECRET_KEY") or os.getenv("SECRET_KEY")

        if not secret_key:
            raise RuntimeError(
                "JWT secret key not found in environment variables. "
                "Please ensure JWT_SECRET, GILJO_MCP_SECRET_KEY, or SECRET_KEY is set in .env file. "
                "Run 'python install.py' to regenerate configuration if needed."
            )

        return secret_key

    @classmethod
    def get_secret_key(cls) -> str:
        """Public accessor for the shared HMAC secret.

        For a caller that needs its OWN short-lived signed token (a distinct
        purpose/claims/expiry from a session access token -- e.g. SaaS
        social-login's link-pending token, BE-1004) rather than a full
        session. Keeps the secret-resolution logic (env var precedence +
        missing-key error) in exactly one place instead of duplicating it.

        Raises:
            RuntimeError: If no secret key is found (see ``_get_secret_key``).
        """
        return cls._get_secret_key()

    @classmethod
    def create_access_token(
        cls,
        user_id: UUID,
        username: str,
        role: str,
        tenant_key: str,
        audience: str | None = None,
        scope: str | None = None,
        revocation_epoch: int = 0,
    ) -> str:
        """
        Create JWT access token for authenticated user.

        Args:
            user_id: User's UUID
            username: User's username
            role: User's role (admin, developer, viewer)
            tenant_key: Tenant key for multi-tenant isolation (required)
            audience: RFC 7519 `aud` claim value. When set (e.g. canonical MCP
                server URI), the token is bound to that resource server and
                will be rejected at any other resource. Omit to issue a legacy
                aud-less token (transition window only — see API-0021a).
            scope: Space-separated OAuth 2.0 scope string (RFC 6749 §3.3). When
                set, the JWT carries a `scope` claim consumed by the MCP
                transport's tool-gating layer (API-0021b). Omit for cookie/login
                tokens — the MCP middleware then defaults missing-claim JWTs to
                `mcp:read mcp:write` for transport-side gating.
            revocation_epoch: The user's current forced-logout epoch (SEC-6011),
                embedded as the `rev` claim. Validation rejects any token whose
                `rev` is below the user's live epoch, so an admin force-logout
                (which bumps the epoch) invalidates every prior token at once.
                Callers MUST pass the user's live `token_revocation_epoch`, or a
                force-logged-out user could never obtain a valid token again.

        Returns:
            Encoded JWT token string
        """
        secret_key = cls._get_secret_key()

        expire = datetime.now(UTC) + timedelta(hours=cls.ACCESS_TOKEN_EXPIRE_HOURS)
        payload: dict = {
            "sub": str(user_id),
            "username": username,
            "role": role,
            "tenant_key": tenant_key,
            "exp": expire,
            "iat": datetime.now(UTC),
            "type": "access",
            # API-0022: jti enables RFC 7009 token revocation lookup
            # (oauth_revoked_tokens.jti). Every access token carries one;
            # cookie-auth tokens are unaffected since revocation is enforced
            # only at the /mcp resource boundary.
            "jti": uuid4().hex,
            # SEC-6011: forced-logout revocation epoch. Validation rejects a
            # token whose `rev` is below the user's live token_revocation_epoch.
            "rev": int(revocation_epoch or 0),
        }
        if audience is not None:
            payload["aud"] = audience
        if scope is not None:
            payload["scope"] = scope
        return jwt.encode(payload, secret_key, algorithm=cls.ALGORITHM)

    @classmethod
    def verify_token(cls, token: str, expected_audience: str | None = None) -> dict:
        """
        Verify and decode JWT token.

        Audience-binding semantics (RFC 7519 §4.1.3 + RFC 6750 §3) — applies
        only when `expected_audience` is supplied (caller is a specific resource
        server such as the MCP Bearer middleware):

        - Token has no `aud` claim → REJECT (API-0022). The legacy transition
          window opened by API-0021a has closed; aud-less tokens are no longer
          accepted at resource-server boundaries. Raises
          :class:`JWTAudienceMismatchError` so the caller emits 401 +
          `WWW-Authenticate: Bearer` pointing at the resource metadata.
        - Token has `aud == expected_audience` → ACCEPT.
        - Token has `aud != expected_audience` → raise
          :class:`JWTAudienceMismatchError`. Caller must respond 401 with a
          `WWW-Authenticate: Bearer` header pointing at the resource metadata.

        When `expected_audience` is None (e.g. dashboard cookie auth), the
        `aud` claim is ignored entirely.

        Args:
            token: JWT token string to verify.
            expected_audience: When set, treat this validator as a resource
                server and apply the audience-binding semantics above.

        Returns:
            Decoded token payload.

        Raises:
            HTTPException: 401 for invalid/expired/wrong-type tokens, 500 for
                config errors.
            JWTAudienceMismatchError: token's `aud` claim is present but does
                not match `expected_audience`.
        """
        try:
            secret_key = cls._get_secret_key()
        except RuntimeError as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"JWT configuration error: {e}"
            ) from e

        try:
            # Decode without audience verification — we apply our own semantics
            # below (legacy aud-less tokens must still authenticate during the
            # transition window).
            payload = jwt.decode(
                token,
                secret_key,
                algorithms=[cls.ALGORITHM],
                options={"verify_aud": False},
            )

            if payload.get("type") != "access":
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token type")

            if expected_audience is not None:
                token_aud = payload.get("aud")
                if token_aud is None or token_aud == "":
                    raise JWTAudienceMismatchError(
                        f"JWT missing required 'aud' claim for resource '{expected_audience}' "
                        "(API-0022: legacy aud-less tokens no longer accepted)"
                    )
                if token_aud != expected_audience:
                    raise JWTAudienceMismatchError(
                        f"JWT aud '{token_aud}' does not match expected '{expected_audience}'"
                    )

            return payload

        except jwt.ExpiredSignatureError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired. Please login again."
            ) from e
        except jwt.InvalidTokenError as e:
            # Do NOT echo the library exception to the client — it can leak token
            # structure / validation internals. Static generic message only.
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials"
            ) from e

    @classmethod
    def verify_token_allow_expired(cls, token: str, grace_hours: int | None = None) -> dict | None:
        """Verify JWT, accepting tokens expired within the grace period.

        Used by the /api/auth/refresh endpoint for silent token renewal.
        If the token is valid, returns the payload. If expired within the
        grace period, returns the payload (caller must re-validate user in DB).
        If expired beyond the grace period or otherwise invalid, returns None.

        Args:
            token: JWT token string
            grace_hours: Override grace period (default: REFRESH_GRACE_PERIOD_HOURS)

        Returns:
            Decoded payload dict if valid/within grace, None otherwise
        """
        grace = grace_hours if grace_hours is not None else cls.REFRESH_GRACE_PERIOD_HOURS
        try:
            secret_key = cls._get_secret_key()
        except RuntimeError:
            return None

        try:
            payload = jwt.decode(token, secret_key, algorithms=[cls.ALGORITHM])
            if payload.get("type") != "access":
                return None
            return payload
        except jwt.ExpiredSignatureError:
            try:
                payload = jwt.decode(
                    token,
                    secret_key,
                    algorithms=[cls.ALGORITHM],
                    options={"verify_exp": False},
                )
                if payload.get("type") != "access":
                    return None
                exp = datetime.fromtimestamp(payload["exp"], tz=UTC)
                now = datetime.now(UTC)
                if (now - exp) <= timedelta(hours=grace):
                    return payload
                return None
            except jwt.InvalidTokenError:
                return None
        except jwt.InvalidTokenError:
            return None
