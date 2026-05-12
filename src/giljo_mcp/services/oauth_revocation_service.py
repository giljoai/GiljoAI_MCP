# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""RFC 7009 OAuth Token Revocation (API-0022).

Split out of ``oauth_service`` to keep that file under the 800-line
guardrail. The revocation surface has two seams:

1. Write side -- :func:`revoke_token` is called from the /oauth/revoke
   endpoint. It accepts the presented token (access or refresh), extracts
   the lookup key (``jti`` for access JWTs, sha256 hex for refresh tokens),
   and persists a row in ``oauth_revoked_tokens``. For refresh tokens it
   additionally flips ``revoked=true`` on the entire family in
   ``oauth_refresh_tokens`` (RFC 6749 §10.4).

2. Read side -- :func:`is_access_token_jti_revoked` is called from
   :class:`MCPAuthMiddleware` on every Bearer JWT. A short-lived in-process
   TTL cache (default 60s) sits in front of the DB lookup to keep the
   hot path cheap. Cache misses fall through to the DB and populate the
   cache. Tenant isolation: the cache key is ``(tenant_key, jti)`` so a
   revoked jti in tenant A cannot poison tenant B.

The endpoint is idempotent per RFC 7009 §2.2 -- garbage in, 200 OK out.
This module surfaces ValueError only for genuine internal contract
violations (e.g. missing tenant_key on a verified JWT, which would be a
JWTManager bug). Endpoint-layer callers should treat ValueError as a 500.
"""

from __future__ import annotations

import hashlib
import logging
import time
from typing import TYPE_CHECKING

from sqlalchemy import select, update

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.models.oauth import OAuthRefreshToken, OAuthRevokedToken


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


logger = logging.getLogger(__name__)


TOKEN_TYPE_ACCESS = "access_token"
TOKEN_TYPE_REFRESH = "refresh_token"

# Hot-path cache: positive entries (jti IS revoked) live REVOCATION_CACHE_TTL
# seconds before the next DB confirmation. Negative entries (jti NOT
# revoked) live a much shorter window so a freshly-revoked token surfaces
# at the resource server quickly. The mission cites <60s; we keep
# positives at 60s and negatives at 5s.
REVOCATION_CACHE_TTL_POSITIVE = 60.0
REVOCATION_CACHE_TTL_NEGATIVE = 5.0
_REVOCATION_CACHE_MAX_ENTRIES = 4096

# Cache: (tenant_key, jti) -> (is_revoked: bool, expires_at_monotonic: float)
_revocation_cache: dict[tuple[str, str], tuple[bool, float]] = {}


def _cache_get(tenant_key: str, jti: str) -> bool | None:
    entry = _revocation_cache.get((tenant_key, jti))
    if entry is None:
        return None
    is_revoked, expires_at = entry
    if time.monotonic() >= expires_at:
        _revocation_cache.pop((tenant_key, jti), None)
        return None
    return is_revoked


def _cache_put(tenant_key: str, jti: str, *, is_revoked: bool) -> None:
    if len(_revocation_cache) >= _REVOCATION_CACHE_MAX_ENTRIES:
        # Cheap FIFO-ish eviction: drop the oldest insertion.
        try:
            oldest_key = next(iter(_revocation_cache))
            _revocation_cache.pop(oldest_key, None)
        except StopIteration:
            pass
    ttl = REVOCATION_CACHE_TTL_POSITIVE if is_revoked else REVOCATION_CACHE_TTL_NEGATIVE
    _revocation_cache[(tenant_key, jti)] = (is_revoked, time.monotonic() + ttl)


def clear_revocation_cache() -> None:
    """Test helper: wipe the in-process revocation cache."""
    _revocation_cache.clear()


async def is_access_token_jti_revoked(
    db_session: AsyncSession,
    *,
    tenant_key: str,
    jti: str,
) -> bool:
    """Return True iff the access-token jti has been revoked in this tenant.

    Hot path: in-process TTL cache in front of a DB lookup. Tenant-scoped
    cache key prevents cross-tenant poisoning.
    """
    cached = _cache_get(tenant_key, jti)
    if cached is not None:
        return cached

    result = await db_session.execute(
        select(OAuthRevokedToken.jti).where(
            OAuthRevokedToken.jti == jti,
            OAuthRevokedToken.tenant_key == tenant_key,
        )
    )
    is_revoked = result.first() is not None
    _cache_put(tenant_key, jti, is_revoked=is_revoked)
    return is_revoked


def _sha256_hex(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


async def _revoke_access_jwt(
    db_session: AsyncSession,
    *,
    token: str,
) -> bool:
    """Attempt to revoke ``token`` as a signed access JWT. Returns True on success."""
    try:
        # No expected_audience: revocation is identity by signature + jti, not by aud.
        payload = JWTManager.verify_token(token)
    except Exception:  # noqa: BLE001 -- RFC 7009: never leak token validity
        return False

    jti = payload.get("jti")
    tenant_key = payload.get("tenant_key")
    if not jti or not tenant_key:
        # Pre-API-0022 tokens lacked jti. Best-effort: nothing to revoke server-side;
        # token will roll off when it expires. Returning False keeps the endpoint
        # idempotent at the HTTP layer (still 200 OK) without persisting a row we
        # could never match against.
        return False

    existing = await db_session.execute(select(OAuthRevokedToken.jti).where(OAuthRevokedToken.jti == jti))
    if existing.first() is not None:
        return True

    db_session.add(
        OAuthRevokedToken(
            jti=jti,
            token_type=TOKEN_TYPE_ACCESS,
            tenant_key=tenant_key,
        )
    )
    await db_session.flush()
    _cache_put(tenant_key, jti, is_revoked=True)
    return True


async def _revoke_refresh_token_family(
    db_session: AsyncSession,
    *,
    token: str,
) -> bool:
    """Revoke ``token`` as a raw refresh token; flips the whole family.

    Per RFC 6749 §10.4 and OAuth 2.1 Security BCP, revoking any refresh
    token revokes the entire family derived from the same initial grant.
    """
    token_hash = _sha256_hex(token)
    row = await db_session.execute(
        select(OAuthRefreshToken.family_id, OAuthRefreshToken.tenant_key).where(
            OAuthRefreshToken.token_hash == token_hash
        )
    )
    found = row.first()
    if found is None:
        return False

    family_id, tenant_key = found.family_id, found.tenant_key
    await db_session.execute(
        update(OAuthRefreshToken).where(OAuthRefreshToken.family_id == family_id).values(revoked=True)
    )
    await db_session.flush()
    logger.info(
        "Revoked refresh-token family: family_id=%s tenant_key=%s",
        family_id,
        tenant_key,
    )
    return True


async def revoke_token(
    db_session: AsyncSession,
    *,
    token: str,
    token_type_hint: str | None = None,
) -> None:
    """RFC 7009 token revocation entry point.

    Idempotent: ALWAYS returns None. Garbage input, already-revoked tokens,
    foreign tokens, and unknown formats all complete without raising. The
    only outward signal of success is "no exception."

    Behavior:
      - ``token_type_hint == 'refresh_token'`` -- try refresh first, then access.
      - ``token_type_hint == 'access_token'`` (or unset) -- try access first,
        then refresh.
      - Either way, the first match wins; a token can only be one type.
    """
    if not token:
        # Empty body still 200 OK per spec; nothing to do.
        return

    order: tuple[str, ...]
    if token_type_hint == TOKEN_TYPE_REFRESH:
        order = (TOKEN_TYPE_REFRESH, TOKEN_TYPE_ACCESS)
    else:
        order = (TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH)

    for token_type in order:
        if token_type == TOKEN_TYPE_ACCESS:
            if await _revoke_access_jwt(db_session, token=token):
                return
        elif await _revoke_refresh_token_family(db_session, token=token):
            return

    # No match in either type. RFC 7009 §2.2: still 200 OK; do not leak.
    logger.debug("Revoke request for unknown/foreign token (idempotent 200)")
