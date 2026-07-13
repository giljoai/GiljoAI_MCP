# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""One auth validator for all four transports (SEC-3004).

Authentication was implemented FOUR independent times — HTTP middleware, the
FastAPI dependency, the WebSocket handshake, and the MCP middleware — with three
near-identical API-key bcrypt loops, and it had DRIFTED: the SEC-6001 jti
revocation fix landed in only 2 of 4 copies, and is_active deactivation in only
2 of 4. This module is the single home for the credential-validation pipeline:

    decode → revocation → is_active

:func:`validate_principal` performs that pipeline once and returns a
:class:`Principal`, or raises :class:`PrincipalValidationError` carrying a
machine-readable :class:`AuthErrorReason`. Each transport keeps ONLY credential
extraction and maps the reason to its own wire response (REST 401, WS close
1008, MCP ASGI 401). Transport-specific concerns that are NOT part of the shared
pipeline stay in the transport:

- Resource-server audience binding (MCP only) — passed in as ``expected_audience``.
- OAuth scope gating (MCP only) — the parsed scopes are returned; the transport
  applies its own default for claim-less tokens.
- MCP session (jti/session-id) lifecycle — layered AROUND this validator, not a
  fork of the pipeline.
- The legacy file-based API-key store used by the HTTP ``AuthManager`` — a
  distinct credential source, NOT one of the three DB bcrypt loops, preserved
  in that transport.

In-process caches (the api-key verdict cache in ``api_key_utils`` and the jti
revocation cache in ``oauth_revocation_service``) sit IN FRONT of the DB reads
this validator performs — the validator slots behind them, it does not replace
them. The HTTP middleware additionally pre-fetches the ``User`` once per request
and hands it back via ``prefetched_user`` so the request-scoped dependency does
not issue a second identical SELECT (BE-6063a).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import TYPE_CHECKING

from fastapi import HTTPException
from sqlalchemy import func, or_, select

from giljo_mcp.api_key_utils import get_key_prefix, verify_api_key_cached
from giljo_mcp.auth.jwt_manager import JWTAudienceMismatchError, JWTManager
from giljo_mcp.database import tenant_isolation_bypass
from giljo_mcp.models import APIKey, User
from giljo_mcp.services.oauth_revocation_service import is_access_token_jti_revoked


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


class AuthErrorReason(StrEnum):
    """Why credential validation failed. Transports map these to wire responses.

    The distinction between :attr:`INVALID_TOKEN` / :attr:`EXPIRED` /
    :attr:`NO_TENANT` (a Bearer value that is simply *not a usable JWT*) and the
    hard rejects (:attr:`REVOKED`, :attr:`INACTIVE`, :attr:`INVALID_AUDIENCE`)
    is load-bearing for the MCP transport: a not-a-JWT result falls back to the
    API-key path, whereas a hard reject is final (a valid JWT that must NOT
    authenticate must never silently retry as an API key).
    """

    INVALID_TOKEN = "invalid_token"
    EXPIRED = "expired"
    NO_TENANT = "no_tenant"
    INVALID_AUDIENCE = "invalid_audience"
    REVOKED = "revoked"
    INACTIVE = "inactive"
    INVALID_CREDENTIALS = "invalid_credentials"


# Reasons that mean "this Bearer value is not a usable JWT" — the MCP transport
# may retry the same value as an API key. Everything else is a final verdict on
# a token that WAS a valid JWT (or on an API key).
JWT_FALLBACK_REASONS = frozenset({AuthErrorReason.INVALID_TOKEN, AuthErrorReason.EXPIRED, AuthErrorReason.NO_TENANT})


class PrincipalValidationError(Exception):
    """Credential validation failed. Carries a machine-readable reason."""

    def __init__(self, reason: AuthErrorReason, detail: str = "") -> None:
        self.reason = reason
        self.detail = detail or reason.value
        super().__init__(self.detail)


@dataclass(frozen=True)
class Principal:
    """The authenticated identity produced by :func:`validate_principal`.

    ``user`` is the resolved, attached ORM ``User`` (always present — the
    pipeline never returns a principal without confirming an active user row).
    ``user_id`` is the stable user UUID (JWT ``sub`` / ``api_keys.user_id``),
    distinct from ``username`` (the free-text display/login name). Transports
    that historically keyed off the username (e.g. the SaaS per-user rate
    limiter, BE-6022) must read ``username``, not ``user_id``.
    """

    user_id: str
    tenant_key: str
    auth_method: str  # "jwt" | "api_key"
    user: User
    username: str | None = None
    role: str | None = None
    scopes: list[str] | None = None
    api_key_id: str | None = None
    exp: int | None = None
    jti: str | None = None


async def _resolve_api_key(db: AsyncSession, api_key: str) -> tuple[APIKey, User] | None:
    """The ONE API-key bcrypt loop (SEC-3004c collapse target).

    Resolves a presented ``gk_`` key to its ``(APIKey, User)`` pair, or ``None``
    when no active, non-expired key matches OR the owning user is missing /
    inactive / in a different tenant. This is the single implementation the REST
    dependency, the WebSocket handshake, and the MCP session manager all call —
    replacing three byte-for-byte-divergent copies.

    Pure resolution: no ``last_used`` / IP / session bookkeeping (those are
    transport-specific write concerns and stay with each caller). The key
    candidate scan runs under an audited tenant-isolation bypass because the
    tenant is derived FROM the matched key (unknown beforehand); the User load
    is then tenant-scoped to that key's tenant_key.
    """
    # Narrow candidates by key_prefix before bcrypt so a caller cannot force a
    # full-table verify of every active key (DoS footgun). The lookup prefix
    # MUST use the same get_key_prefix the key was created with.
    key_prefix = get_key_prefix(api_key)
    stmt = select(APIKey).where(
        APIKey.is_active,
        APIKey.key_prefix == key_prefix,
        # SEC-3001a item 4: exclude expired keys (NULL expires_at = never expires).
        or_(APIKey.expires_at > func.now(), APIKey.expires_at.is_(None)),
    )
    with tenant_isolation_bypass(
        db,
        reason="api key prefix lookup resolves tenant before authentication",
        models=(APIKey,),
    ):
        result = await db.execute(stmt)
    candidates = result.scalars().all()

    for key_record in candidates:
        # bcrypt/sha256 off the event loop + short-lived verdict cache. A
        # revoke/deactivate busts the cache (bust_api_key_cache), so a stale
        # positive can never outlive a revoke.
        if await verify_api_key_cached(
            api_key,
            key_record.key_hash,
            key_id=key_record.id,
            expires_at=key_record.expires_at,
        ):
            db.info["tenant_key"] = key_record.tenant_key
            # tenant_key consistency: the user must be active AND in the key's tenant.
            user = (
                await db.execute(
                    select(User).where(
                        User.id == key_record.user_id,
                        User.is_active,
                        User.tenant_key == key_record.tenant_key,
                    )
                )
            ).scalar_one_or_none()
            if user is not None:
                return key_record, user
            logger.warning("API key valid but user inactive or tenant mismatch: user_id=%s", key_record.user_id)
            # A matched key whose user is gone/inactive is a final negative — do
            # not keep scanning (prefix collisions across distinct users are not
            # an authentication avenue).
            return None

    return None


async def _validate_jwt(
    db: AsyncSession,
    token: str,
    *,
    expected_audience: str | None,
    prefetched_user: User | None,
) -> Principal:
    """decode → revocation → is_active for a JWT credential.

    Raises :class:`PrincipalValidationError`. The decode step applies
    resource-server audience binding only when ``expected_audience`` is set
    (MCP); cookie/dependency callers pass ``None`` and the ``aud`` claim is
    ignored, exactly as before.
    """
    try:
        payload = JWTManager.verify_token(token, expected_audience=expected_audience)
    except JWTAudienceMismatchError as exc:
        raise PrincipalValidationError(AuthErrorReason.INVALID_AUDIENCE, str(exc)) from exc
    except HTTPException as exc:
        # verify_token raises 401 for invalid/expired/wrong-type, 500 for config.
        reason = (
            AuthErrorReason.EXPIRED
            if isinstance(exc.detail, str) and "expired" in exc.detail.lower()
            else AuthErrorReason.INVALID_TOKEN
        )
        raise PrincipalValidationError(reason, str(exc.detail)) from exc

    user_id = payload.get("sub")
    tenant_key = payload.get("tenant_key")
    if not user_id or not tenant_key:
        raise PrincipalValidationError(AuthErrorReason.NO_TENANT, "JWT missing sub/tenant_key")

    # Stamp the session tenant before any tenant-scoped read (the isolation guard
    # requires session.info["tenant_key"], not just an explicit WHERE predicate).
    db.info["tenant_key"] = tenant_key

    # Revocation (SEC-6001 / API-0022). jti-bearing tokens are checked; pre-jti
    # tokens cannot be revoked server-side and roll off at expiry (unchanged).
    jti = payload.get("jti")
    if jti and await is_access_token_jti_revoked(db, tenant_key=tenant_key, jti=jti):
        raise PrincipalValidationError(AuthErrorReason.REVOKED, "Token revoked")

    # is_active. Reuse the request's pre-fetched User when it is the SAME active
    # identity (BE-6063a cache-in-front) — merge(load=False) attaches it without
    # a SELECT. Otherwise load authoritatively, filtering on is_active so a
    # deactivated user holding a live token fails closed.
    user = await _reuse_prefetched_user(db, prefetched_user, user_id=user_id, tenant_key=tenant_key)
    if user is None:
        user = (
            await db.execute(
                select(User).where(
                    User.id == user_id,
                    User.tenant_key == tenant_key,
                    User.is_active,
                )
            )
        ).scalar_one_or_none()
    if user is None:
        raise PrincipalValidationError(AuthErrorReason.INACTIVE, "User not found or inactive")

    # Forced-logout revocation epoch (SEC-6011). An admin force-logout bumps the
    # user's token_revocation_epoch; every JWT minted before that carries a lower
    # `rev` claim and is rejected here. Rides the user load above — no extra
    # query. A missing/legacy `rev` is treated as epoch 0. Hard-reject (same
    # AuthErrorReason as jti revocation) so a forced-out Bearer token does not
    # silently retry as an API key on the /mcp path.
    try:
        token_epoch = int(payload.get("rev", 0) or 0)
    except (TypeError, ValueError):
        token_epoch = 0
    if (user.token_revocation_epoch or 0) > token_epoch:
        raise PrincipalValidationError(AuthErrorReason.REVOKED, "Token revoked (forced logout)")

    raw_scope = payload.get("scope")
    scopes = [s for s in str(raw_scope).split() if s] if raw_scope is not None else None

    return Principal(
        user_id=str(user_id),
        tenant_key=tenant_key,
        auth_method="jwt",
        user=user,
        username=payload.get("username") or user.username,
        role=payload.get("role") or user.role,
        scopes=scopes,
        exp=payload.get("exp"),
        jti=jti,
    )


async def _reuse_prefetched_user(
    db: AsyncSession,
    prefetched_user: User | None,
    *,
    user_id: str,
    tenant_key: str,
) -> User | None:
    """Reuse a request-stashed User iff it is the same, still-active identity.

    Mirrors the BE-6063a safety re-assertions: identity (id + tenant_key) AND
    is_active must match the JWT's claim — the middleware's own SELECT does not
    filter on is_active, so this is the gate that stops a deactivated user with
    a live token from riding the stash. Returns the attached instance (merged
    with ``load=False`` so no SELECT runs) or ``None`` to force the DB load.
    """
    if prefetched_user is None:
        return None
    if not getattr(prefetched_user, "is_active", False):
        return None
    if str(getattr(prefetched_user, "id", "")) != str(user_id):
        return None
    if getattr(prefetched_user, "tenant_key", None) != tenant_key:
        return None
    return await db.merge(prefetched_user, load=False)


async def validate_principal(
    db: AsyncSession,
    *,
    jwt_token: str | None = None,
    api_key: str | None = None,
    expected_audience: str | None = None,
    prefetched_user: User | None = None,
) -> Principal:
    """Validate one credential through the single decode→revocation→is_active pipeline.

    Exactly one of ``jwt_token`` / ``api_key`` is the credential to validate.
    When both are supplied the JWT is tried first (transports that accept either
    pass both and rely on this ordering). Returns a :class:`Principal` on
    success; raises :class:`PrincipalValidationError` with an
    :class:`AuthErrorReason` on any failure.

    Args:
        db: Async session. The caller owns its lifecycle and tenant scoping
            posture; this function stamps ``db.info["tenant_key"]`` before
            tenant-scoped reads.
        jwt_token: A JWT (cookie or Bearer) to validate, or ``None``.
        api_key: A ``gk_`` API key to validate, or ``None``.
        expected_audience: Resource-server audience to bind the JWT to (MCP
            only). ``None`` ignores the ``aud`` claim (cookie/dependency/WS).
        prefetched_user: A request-stashed ``User`` to reuse for the JWT
            is_active check without a second SELECT (BE-6063a). Re-asserted
            before use; ignored for the API-key path.
    """
    if jwt_token:
        return await _validate_jwt(db, jwt_token, expected_audience=expected_audience, prefetched_user=prefetched_user)

    if api_key:
        resolved = await _resolve_api_key(db, api_key)
        if resolved is None:
            raise PrincipalValidationError(AuthErrorReason.INVALID_CREDENTIALS, "Invalid API key")
        key_record, user = resolved
        return Principal(
            user_id=str(user.id),
            tenant_key=user.tenant_key,
            auth_method="api_key",
            user=user,
            username=user.username,
            role=user.role,
            api_key_id=str(key_record.id),
        )

    raise PrincipalValidationError(AuthErrorReason.INVALID_CREDENTIALS, "No credentials supplied")
