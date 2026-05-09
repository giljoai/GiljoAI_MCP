# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

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

API-0021c: client lookup is performed through a pluggable
``ClientResolver`` (Callable). CE ships a built-in single-client resolver
that preserves identical pre-0021c behavior. SaaS replaces it at startup
via ``set_client_resolver()`` to look up clients in the ``oauth_clients``
table populated by RFC 7591 Dynamic Client Registration.
"""

import base64
import hashlib
import inspect
import logging
import re
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import delete, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.models.auth import User
from giljo_mcp.models.oauth import OAuthAuthorizationCode


logger = logging.getLogger(__name__)

BUILTIN_CLIENT_ID = "giljo-mcp-default"
AUTHORIZATION_CODE_LIFETIME_MINUTES = 10
ACCESS_TOKEN_LIFETIME_SECONDS = 86400  # 24 hours
ALLOWED_REDIRECT_URI_PATTERNS = [
    r"^http://localhost(:\d+)?/",
    r"^http://127\.0\.0\.1(:\d+)?/",
    r"^http://\[::1\](:\d+)?/",
]

# OAuth-grantable scopes for the MCP resource server (API-0021b).
# `mcp:agent` is intentionally NOT grantable through /authorize — orchestration
# tools (spawn_job, complete_job, send_message, …) must never be reachable by
# OAuth clients. API keys remain the only path to mcp:agent surface.
OAUTH_GRANTABLE_SCOPES: frozenset[str] = frozenset({"mcp:read", "mcp:write"})
DEFAULT_OAUTH_SCOPE: str = "mcp:read mcp:write"


# ---------------------------------------------------------------------------
# Client resolver seam (API-0021c)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedClient:
    """OAuth client metadata returned by a ``ClientResolver``.

    ``redirect_uris`` semantics:
      - ``None`` → the validator falls back to :data:`ALLOWED_REDIRECT_URI_PATTERNS`
        (used by the CE built-in single-client default; preserves localhost
        regex matching for unchanged behavior).
      - ``list[str]`` → exact-match validation against the registered URIs
        (used by SaaS DCR clients per RFC 7591 §2).

    ``client_secret_hash`` is None for PKCE-only public clients (built-in
    case). DCR-registered confidential clients store a bcrypt hash; matching
    plaintext-secret verification at /token is out of scope for API-0021c
    (PKCE remains the proof-of-possession mechanism).
    """

    client_id: str
    client_name: str
    redirect_uris: list[str] | None
    client_secret_hash: str | None


# Resolver contract (post-API-0021c): positional ``(client_id, tenant_key)``.
# Tenant-scoping the lookup is a hard rule (CLAUDE.md: every DB query filters
# by tenant_key). The CE built-in is global and ignores ``tenant_key``; SaaS
# DB-backed resolvers MUST apply it as a SQL ``WHERE`` clause.
#
# A resolver may return either ``ResolvedClient | None`` directly (sync) or
# an awaitable yielding the same (async). ``validate_authorize_request`` is
# async and awaits whichever shape the active resolver returns — this lets
# CE keep its sync built-in default while SaaS does a true cache-miss DB
# round-trip via :func:`giljo_mcp.saas.auth.oauth_client.lookup_client`.
ClientResolver = Callable[
    [str, str],
    "ResolvedClient | None | Awaitable[ResolvedClient | None]",
]


def _builtin_single_client_resolver(client_id: str, tenant_key: str) -> ResolvedClient | None:
    """CE default: only the built-in MCP client is recognized.

    The built-in client is global (CE has no multi-tenant DB lookup); the
    ``tenant_key`` argument is part of the ``ClientResolver`` contract so
    SaaS resolvers can scope by tenant without changing the signature, but
    CE ignores it. Returns ``None`` for any other ``client_id``, producing
    the same ``ValueError("Invalid client_id")`` that the previous hardcoded
    constant comparison raised.
    """
    _ = tenant_key  # contract-required positional arg; CE built-in is global
    if client_id != BUILTIN_CLIENT_ID:
        return None
    return ResolvedClient(
        client_id=BUILTIN_CLIENT_ID,
        client_name="GiljoAI MCP (built-in)",
        redirect_uris=None,
        client_secret_hash=None,
    )


_resolver: ClientResolver = _builtin_single_client_resolver


def set_client_resolver(resolver: ClientResolver) -> None:
    """Install a process-wide ``ClientResolver``.

    SaaS bootstrap calls this once at startup with a DB-backed resolver that
    queries the ``oauth_clients`` table and falls back to the built-in
    resolver when no row matches. CE leaves the default in place.
    """
    if not callable(resolver):
        raise TypeError(f"ClientResolver must be callable, got {type(resolver).__name__}")
    global _resolver  # noqa: PLW0603 — the seam IS the process-wide state
    _resolver = resolver


def get_client_resolver() -> ClientResolver:
    """Return the currently active ``ClientResolver``."""
    return _resolver


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

    async def validate_authorize_request(
        self,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        code_challenge_method: str,
        response_type: str,
        scope: str,
        *,
        tenant_key: str,
    ) -> None:
        """Validate an OAuth authorization request.

        Checks all parameters against expected values and patterns.
        This is a synchronous validation step before any DB interaction.

        Args:
            client_id: Resolved through the active ``ClientResolver``.
                CE default: only ``BUILTIN_CLIENT_ID`` is recognized. SaaS:
                any client registered through DCR (RFC 7591) under the
                authenticated user's ``tenant_key``, with the built-in
                client preserved as a global fallback.
            redirect_uri: Validated against the resolved client's registered
                URIs (exact match) when ``ResolvedClient.redirect_uris`` is
                a list, or against ``ALLOWED_REDIRECT_URI_PATTERNS`` when
                None (built-in client localhost fallback).
            code_challenge: Base64url-encoded S256 challenge (non-empty).
            code_challenge_method: Must be "S256".
            response_type: Must be "code".
            scope: Requested scope. Must be a subset of OAUTH_GRANTABLE_SCOPES.
                Any token outside that set (notably `mcp:agent`) is rejected
                outright — orchestration scope is never grantable via OAuth.
            tenant_key: Tenant scope of the authenticated user. The router
                MUST plumb this from ``current_user.tenant_key``; the
                resolver applies it as the DB lookup's tenant filter so a
                client registered under tenant A cannot be discovered from
                tenant B (CLAUDE.md tenant-isolation rule).

        Raises:
            ValueError: If any parameter fails validation.
        """
        if not tenant_key:
            raise ValueError("tenant_key is required for authorize-request validation")
        resolver_result = _resolver(client_id, tenant_key)
        if inspect.isawaitable(resolver_result):
            resolved = await resolver_result
        else:
            resolved = resolver_result
        if resolved is None:
            raise ValueError(f"Invalid client_id: no client registered for '{client_id}'")

        if response_type != "code":
            raise ValueError(f"Invalid response_type: expected 'code', got '{response_type}'")

        if code_challenge_method != "S256":
            raise ValueError(f"Invalid code_challenge_method: expected 'S256', got '{code_challenge_method}'")

        if not code_challenge:
            raise ValueError("code_challenge is required and must be non-empty")

        if not self._redirect_uri_matches(resolved, redirect_uri):
            raise ValueError(f"Invalid redirect_uri: '{redirect_uri}' is not registered for this client")

        self._validate_scope_string(scope)

    @staticmethod
    def _redirect_uri_matches(resolved: ResolvedClient, redirect_uri: str) -> bool:
        """Apply the right redirect_uri policy for the resolved client.

        DCR clients (``redirect_uris`` is a concrete list) require exact match
        per RFC 7591 §3 / §3.2. The built-in single client (``redirect_uris``
        is None) keeps the legacy localhost-pattern behavior for backwards
        compatibility with existing CE OAuth flows.
        """
        if resolved.redirect_uris is None:
            return OAuthService.validate_redirect_uri(redirect_uri)
        if not redirect_uri:
            return False
        return redirect_uri in resolved.redirect_uris

    @staticmethod
    def _validate_scope_string(scope: str) -> None:
        """Reject any scope token outside OAUTH_GRANTABLE_SCOPES.

        Empty / whitespace-only `scope` is treated as the default grant
        (caller's choice — the route layer supplies DEFAULT_OAUTH_SCOPE as the
        Pydantic default). Non-empty values must contain only `mcp:read` and
        `mcp:write`. `mcp:agent` is the canonical privilege-escalation token
        and is never grantable through /authorize.

        Args:
            scope: Space-separated scope string from the OAuth client.

        Raises:
            ValueError: If any token in `scope` is not in OAUTH_GRANTABLE_SCOPES.
        """
        if not scope or not scope.strip():
            return
        requested = {token for token in scope.split() if token}
        forbidden = requested - OAUTH_GRANTABLE_SCOPES
        if forbidden:
            raise ValueError(
                f"Scope contains non-grantable token(s): {sorted(forbidden)}. Allowed: {sorted(OAUTH_GRANTABLE_SCOPES)}"
            )

    async def generate_authorization_code(
        self,
        user_id: str,
        tenant_key: str,
        client_id: str,
        redirect_uri: str,
        code_challenge: str,
        scope: str = DEFAULT_OAUTH_SCOPE,
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
            scope: Requested scope (default DEFAULT_OAUTH_SCOPE = "mcp:read mcp:write").

        Returns:
            The generated authorization code string.
        """
        code = secrets.token_urlsafe(64)
        expires_at = datetime.now(UTC) + timedelta(minutes=AUTHORIZATION_CODE_LIFETIME_MINUTES)

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
        audience: str | None = None,
    ) -> dict:
        """Exchange an authorization code for a JWT access token.

        Validates the code, verifies PKCE, marks the code as used,
        and issues a JWT via JWTManager.

        Args:
            code: The authorization code to exchange.
            client_id: Client ID (must match the code's client_id).
            code_verifier: PKCE code verifier to prove possession.
            redirect_uri: Must match the URI used during authorization.
            audience: Canonical MCP resource URI to bake into the JWT `aud`
                claim. The router computes this from the incoming request via
                :func:`giljo_mcp.http.url_resolver.get_canonical_mcp_resource_uri`.
                Omit only for tests that want a legacy aud-less token.

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

        if auth_code.expires_at < datetime.now(UTC):
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
            audience=audience,
            scope=auth_code.scope,
        )

        logger.info(
            "Exchanged authorization code for token: user_id=%s tenant_key=%s",
            user.id,
            user.tenant_key,
        )

        return {
            "access_token": access_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_LIFETIME_SECONDS,
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
        now = datetime.now(UTC)
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
