# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""OAuth 2.1 refresh-token grant — rotation + family reuse detection (API-0021e Phase 2).

Split out of ``oauth_service`` to keep that file under the 800-line guardrail
while still expressing the OAuth flow as a coherent ``OAuthService`` API.
The helpers here operate on the same ``AsyncSession`` the OAuthService caller
holds; they don't open new connections. The owning service (``OAuthService``)
delegates to these for the refresh-token-specific surface.

Security contract (RFC 6749 §6 + §10.4 + OAuth 2.1 Security BCP):
  - The raw refresh token is NEVER persisted; only the sha256 hex digest.
  - ``family_id`` groups every token derived from the same initial
    authorization-code grant. Reusing a revoked or already-rotated token
    revokes the entire family + logs a security event.
  - Tenant_key on the row is the SERVER-AUTHORITATIVE source. A request body
    NEVER produces the tenant — the token's row does.
  - Public PKCE clients ARE supported here (BE-6161). They hold no secret, so
    possession of the one-time-use rotating refresh token is the proof-of-
    possession (RFC 8252 / OAuth 2.1 §4.3.1); rotation + family reuse detection
    is what bounds the risk, exactly as for confidential clients. Confidential
    clients additionally bcrypt-verify their secret.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from uuid import UUID, uuid4

from sqlalchemy import select, update

from giljo_mcp.auth.jwt_manager import JWTManager
from giljo_mcp.database import tenant_isolation_bypass, tenant_session_context
from giljo_mcp.models.auth import User
from giljo_mcp.models.oauth import OAuthRefreshToken
from giljo_mcp.services.cache_backends import OAUTH_REFRESH_BACKEND_NAME, get_cache_backend


if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from giljo_mcp.services.oauth_service import OAuthService


logger = logging.getLogger(__name__)

# API-0021l: 5-second idempotency window for /refresh retries. Same shape as
# the /token primitive in oauth_token_idempotency. The cache hit suppresses
# the existing reuse-detection alarm INSIDE the window — that's the whole
# point: concurrent retries from the same client are not malicious replays.
#
# State is held in the `oauth_refresh` `CacheBackend` (INF-5074). CE: dict.
# SaaS: Redis. The swap is transparent to this module.
OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS = int(os.environ.get("OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS", "5"))
_REFRESH_IDEMPOTENCY_FIELD_SEP = b"\x1f"


@dataclass(frozen=True)
class _RefreshIdempotencyEntry:
    response_body: dict
    body_signature: str


def _serialize_refresh_entry(entry: _RefreshIdempotencyEntry) -> str:
    return json.dumps(
        {
            "response_body": entry.response_body,
            "body_signature": entry.body_signature,
        }
    )


def _deserialize_refresh_entry(raw: str) -> _RefreshIdempotencyEntry:
    payload = json.loads(raw)
    return _RefreshIdempotencyEntry(
        response_body=dict(payload["response_body"]),
        body_signature=str(payload["body_signature"]),
    )


async def _refresh_idempotency_cache_get(tenant_key: str, token_hash: str) -> _RefreshIdempotencyEntry | None:
    backend = get_cache_backend(OAUTH_REFRESH_BACKEND_NAME)
    raw = await backend.get(tenant_key, token_hash)
    if raw is None:
        return None
    return _deserialize_refresh_entry(raw)


async def _refresh_idempotency_cache_put(tenant_key: str, token_hash: str, entry: _RefreshIdempotencyEntry) -> None:
    backend = get_cache_backend(OAUTH_REFRESH_BACKEND_NAME)
    await backend.set(
        tenant_key,
        token_hash,
        _serialize_refresh_entry(entry),
        ttl_seconds=OAUTH_REFRESH_IDEMPOTENCY_WINDOW_SECONDS,
    )


def _compute_refresh_body_signature(
    *,
    client_id: str,
    client_secret_hash: str | None,
    refresh_token_hash: str,
) -> str:
    """Canonical body-signature for the /refresh idempotency check.

    Uses the stored ``client_secret_hash`` rather than the plaintext secret
    so the signature stays deterministic across retries even though the
    same caller might present its plaintext secret with cosmetic
    whitespace differences (it doesn't, but the hash is the canonical
    server-side identity anyway).

    BE-6161: public PKCE clients have no ``client_secret_hash`` (``None``);
    the empty-string substitution keeps the digest well-defined. The
    ``refresh_token_hash`` already uniquely identifies the in-window retry,
    so the secret-hash component is corroborating, not load-bearing, here.
    """
    h = hashlib.sha256()
    h.update(client_id.encode("utf-8"))
    h.update(_REFRESH_IDEMPOTENCY_FIELD_SEP)
    h.update((client_secret_hash or "").encode("utf-8"))
    h.update(_REFRESH_IDEMPOTENCY_FIELD_SEP)
    h.update(refresh_token_hash.encode("utf-8"))
    return h.hexdigest()


def hash_refresh_token(raw_token: str) -> str:
    """Return the sha256 hex digest of ``raw_token`` for DB lookup.

    Refresh tokens are 64-byte url-safe random strings; the raw value is
    returned to the client ONCE in the response and never persisted.
    Lookups go ``hash(presented) -> WHERE token_hash =``. sha256 is
    sufficient here because the input already has 64 bytes of entropy —
    bcrypt would add no real-world security and a lot of latency on every
    refresh call.
    """
    return hashlib.sha256(raw_token.encode("ascii")).hexdigest()


def new_family_id() -> str:
    """Mint a fresh ``family_id`` (UUIDv4) for a brand-new refresh-token chain."""
    return str(uuid4())


async def issue_refresh_token(
    session: AsyncSession,
    *,
    family_id: str,
    client_id: str,
    tenant_key: str,
    user_id: str,
    scope: str | None,
    aud: str,
    lifetime_seconds: int,
) -> str:
    """Mint + persist a refresh-token row, return the raw token string.

    The raw value is what's handed back to the client; the DB stores only
    its sha256 hex hash. ``family_id`` groups every token derived from the
    same initial authorization-code grant; reusing a revoked token revokes
    the entire family (RFC 6749 §10.4 + OAuth 2.1 Security BCP).
    """
    raw_token = secrets.token_urlsafe(64)
    token_hash = hash_refresh_token(raw_token)
    expires_at = datetime.now(UTC) + timedelta(seconds=lifetime_seconds)

    row = OAuthRefreshToken(
        token_hash=token_hash,
        family_id=family_id,
        client_id=client_id,
        tenant_key=tenant_key,
        user_id=user_id,
        scope=scope,
        aud=aud,
        expires_at=expires_at,
        revoked=False,
    )
    session.add(row)
    await session.flush()
    return raw_token


async def revoke_family(
    session: AsyncSession,
    *,
    family_id: str,
    tenant_key: str,
) -> int:
    """Mark every token in the family as revoked (idempotent).

    Tenant filter is mandatory (CLAUDE.md tenant-isolation rule); a
    family_id collision across tenants is astronomically unlikely with
    UUIDv4 but the WHERE clause is part of the contract.
    Returns the number of rows updated for observability/logging.
    """
    result = await session.execute(
        update(OAuthRefreshToken)
        .where(
            OAuthRefreshToken.family_id == family_id,
            OAuthRefreshToken.tenant_key == tenant_key,
            OAuthRefreshToken.revoked.is_(False),
        )
        .values(revoked=True)
    )
    await session.flush()
    return int(result.rowcount or 0)


async def revoke_all_for_user(
    session: AsyncSession,
    *,
    user_id: str,
    tenant_key: str,
) -> int:
    """Revoke EVERY outstanding refresh token the user holds, across all families.

    SEC-9047: called from the password change/reset paths so a credential
    change cuts off refresh-token minting everywhere, not just for one
    family. Idempotent; tenant filter is mandatory (CLAUDE.md tenant-isolation
    rule). Returns the number of rows updated for observability/logging.
    """
    result = await session.execute(
        update(OAuthRefreshToken)
        .where(
            OAuthRefreshToken.user_id == user_id,
            OAuthRefreshToken.tenant_key == tenant_key,
            OAuthRefreshToken.revoked.is_(False),
        )
        .values(revoked=True)
    )
    await session.flush()
    return int(result.rowcount or 0)


async def refresh_token_grant(
    service: OAuthService,
    *,
    refresh_token: str,
    client_id: str,
    client_secret: str | None,
    access_token_lifetime_seconds: int,
    refresh_token_lifetime_seconds: int,
) -> dict:
    """Exchange a refresh token for a new access+refresh pair.

    Steps (see module docstring for the security contract):
      1. Hash the presented token → unique global lookup. Either the row
         exists or it doesn't.
      2. Cross-tenant + cross-client guard: ``row.client_id`` MUST match
         the body-supplied ``client_id``. The row's ``tenant_key`` is the
         server-authoritative tenant for everything that follows.
      3. Verify client through the active ``ClientResolver`` under the
         row's tenant_key. Confidential clients bcrypt-verify their
         client_secret; public PKCE clients (BE-6161) present no secret and
         are authenticated by possession of the rotating refresh token.
      4. Reuse detection: a revoked row triggers ``revoke_family()`` and an
         EXPLICIT commit BEFORE raising; otherwise the router's
         HTTPException would surface as GeneratorExit through the session
         context manager and roll back the revocation.
      5. Otherwise: revoke prior row, mint a fresh access+refresh pair in
         the same ``family_id``.

    Args:
        service: ``OAuthService`` instance — used for its DB session
            handle and its ``_verify_client_authentication`` static.
        refresh_token: Plaintext refresh token from the client body.
        client_id: Client identifier from the request body. Used to
            corroborate (not produce) the row's tenant_key.
        client_secret: Confidential client's plaintext secret.
        access_token_lifetime_seconds: Lifetime to bake into the new JWT
            (``exp`` claim). Mirrors what /token issues.
        refresh_token_lifetime_seconds: Lifetime to bake into the new
            refresh row (``expires_at``). Mirrors what /token issues.

    Returns:
        Dict with ``access_token``, ``token_type``, ``expires_in``,
        ``refresh_token``, ``refresh_expires_in``.

    Raises:
        ValueError: With one of these prefixes (router maps to status):
            - ``invalid_client``  (401, RFC 6749 §5.2)
            - ``invalid_grant``   (401, RFC 6749 §5.2)
            - ``invalid_request`` (400)
    """
    if not refresh_token:
        raise ValueError("invalid_request: refresh_token is required")

    db = service._db
    token_hash = hash_refresh_token(refresh_token)
    # API-0022 (folds API-0024): defense-in-depth. Bind the lookup itself to
    # the body-supplied client_id so a stolen token_hash presented under a
    # different client never even resolves a row. ``oauth_clients.client_id``
    # is a UUIDv4 primary key (globally unique), so this is equivalent to
    # binding to tenant_key without a second round-trip. The existing
    # explicit client_id guard below stays as the second layer.
    # BE6004C-5: public, pre-auth /refresh call -- no tenant context exists;
    # the refresh row carries the server-authoritative tenant_key. Scope the
    # resolve-from-row lookup with an audited bypass; everything AFTER the row
    # is resolved runs tenant-scoped under _refresh_grant_after_lookup().
    with tenant_isolation_bypass(
        db,
        reason="oauth /refresh: resolve refresh token before tenant is known",
        models=(OAuthRefreshToken,),
    ):
        row_result = await db.execute(
            select(OAuthRefreshToken).where(
                OAuthRefreshToken.token_hash == token_hash,
                OAuthRefreshToken.client_id == client_id,
            )
        )
        row = row_result.scalar_one_or_none()

    if row is None:
        # Unknown token. Don't leak whether it's the wrong client/tenant
        # vs. a never-issued value — invalid_grant for both.
        raise ValueError("invalid_grant: refresh_token not found")

    if row.client_id != client_id:
        raise ValueError("invalid_grant: refresh_token does not belong to this client")

    # The row's tenant_key is now authoritative; the remainder (client verify,
    # reuse-detection family revoke, User read, rotation INSERT) runs scoped.
    with tenant_session_context(db, row.tenant_key):
        return await _refresh_grant_after_lookup(
            service=service,
            db=db,
            row=row,
            token_hash=token_hash,
            client_id=client_id,
            client_secret=client_secret,
            access_token_lifetime_seconds=access_token_lifetime_seconds,
            refresh_token_lifetime_seconds=refresh_token_lifetime_seconds,
        )


async def _refresh_grant_after_lookup(
    *,
    service: OAuthService,
    db: AsyncSession,
    row: OAuthRefreshToken,
    token_hash: str,
    client_id: str,
    client_secret: str | None,
    access_token_lifetime_seconds: int,
    refresh_token_lifetime_seconds: int,
) -> dict:
    """Post-lookup refresh-grant flow, run under the row's tenant context.

    Split out of :func:`refresh_token_grant` so the resolve-from-row lookup can
    run under a scoped ``tenant_isolation_bypass`` while everything that follows
    (which touches tenant-scoped ``OAuthRefreshToken``/``User`` rows) runs
    tenant-SCOPED via ``tenant_session_context(row.tenant_key)`` (BE6004C-5).
    """
    resolved = await service._verify_client_authentication(
        client_id=client_id,
        tenant_key=row.tenant_key,
        client_secret=client_secret,
    )

    # BE-6161: public PKCE clients are now first-class at /refresh. They hold no
    # secret — possession of the one-time-use rotating refresh token IS the
    # proof-of-possession (RFC 8252 / OAuth 2.1 §4.3.1), and the rotation +
    # family reuse-detection below is what bounds the risk. _verify_client_
    # authentication has already enforced the matching auth shape: a public
    # client (client_secret_hash is None) MUST NOT present a secret, a
    # confidential client MUST present a verifying one. Either way the resolved
    # client is the legitimate holder, so the grant proceeds for both.
    now = datetime.now(UTC)

    # API-0021l: idempotency-window cache check. Concurrent retries of the
    # SAME refresh_token from the SAME confidential client must yield the
    # SAME rotated pair, otherwise the second call would either rotate
    # twice (issuing two access_tokens, leaving one orphaned) or trip the
    # reuse-detection alarm and revoke the entire family. The cache hit
    # path SUPPRESSES the reuse-detection alarm by short-circuiting before
    # the ``row.revoked`` branch — that's intentional: in-window retries
    # are not malicious replays. Mismatched signature falls through to
    # existing reuse-detection unchanged.
    refresh_idem_signature = _compute_refresh_body_signature(
        client_id=client_id,
        client_secret_hash=resolved.client_secret_hash,
        refresh_token_hash=token_hash,
    )
    cached = await _refresh_idempotency_cache_get(row.tenant_key, token_hash)
    if cached is not None and cached.body_signature == refresh_idem_signature:
        logger.info(
            "oauth_refresh_idempotency_hit family_id=%s tenant=%s",
            row.family_id,
            row.tenant_key[:12] if row.tenant_key else "",
        )
        return dict(cached.response_body)

    if row.revoked:
        revoked_count = await revoke_family(db, family_id=row.family_id, tenant_key=row.tenant_key)
        # Commit BEFORE raising. The router maps ValueError to an
        # HTTPException, which FastAPI surfaces as GeneratorExit through
        # the session context manager — that path rolls back. Without
        # this explicit commit the family revocation would be lost and a
        # sibling token in the family could keep refreshing. RFC 6749
        # §10.4 reuse detection MUST be durable.
        await db.commit()
        logger.warning(
            "oauth_refresh_token_reuse_detected family_id=%s tenant=%s revoked_rows=%d",
            row.family_id,
            row.tenant_key[:12] if row.tenant_key else "",
            revoked_count,
        )
        raise ValueError("invalid_grant: refresh_token reuse detected; family revoked")

    if row.expires_at < now:
        raise ValueError("invalid_grant: refresh_token has expired")

    # SEC-3001a item 1 (deactivation propagation): the refresh grant must enforce
    # is_active, not merely existence. An offboarded user keeps a live refresh
    # token; without this filter they would rotate it into fresh access+refresh
    # pairs until the row's expiry. Mirrors the dashboard /api/auth/refresh gate
    # (api/endpoints/auth/session.py) and the REST dependency is_active check.
    user_result = await db.execute(
        select(User).where(
            User.id == row.user_id,
            User.tenant_key == row.tenant_key,
            User.is_active,
        )
    )
    user = user_result.scalar_one_or_none()
    if user is None:
        raise ValueError("invalid_grant: user no longer active")

    # Rotation: revoke the prior token, mint a new pair in the same family.
    row.revoked = True
    await db.flush()

    new_access = JWTManager.create_access_token(
        user_id=UUID(user.id),
        username=user.username,
        role=user.role,
        tenant_key=user.tenant_key,
        audience=row.aud or None,
        scope=row.scope,
        revocation_epoch=user.token_revocation_epoch or 0,
    )
    new_refresh = await issue_refresh_token(
        db,
        family_id=row.family_id,
        client_id=row.client_id,
        tenant_key=row.tenant_key,
        user_id=row.user_id,
        scope=row.scope,
        aud=row.aud,
        lifetime_seconds=refresh_token_lifetime_seconds,
    )

    logger.info(
        "oauth_refresh_token_rotated family_id=%s tenant=%s user_id=%s",
        row.family_id,
        row.tenant_key[:12] if row.tenant_key else "",
        row.user_id,
    )

    response: dict = {
        "access_token": new_access,
        "token_type": "bearer",
        "expires_in": access_token_lifetime_seconds,
        "refresh_token": new_refresh,
        "refresh_expires_in": refresh_token_lifetime_seconds,
    }

    # API-0021l: cache the rotated pair so a concurrent retry inside the
    # window receives the SAME pair instead of triggering a second rotation
    # (which would either orphan an access_token or trip reuse-detection
    # and revoke the family).
    await _refresh_idempotency_cache_put(
        row.tenant_key,
        token_hash,
        _RefreshIdempotencyEntry(
            response_body=dict(response),
            body_signature=refresh_idem_signature,
        ),
    )

    return response
