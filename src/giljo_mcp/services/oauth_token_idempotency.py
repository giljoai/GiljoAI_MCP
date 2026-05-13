# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""OAuth /token idempotency-window primitive (API-0021l).

Split out of ``oauth_service`` to keep that file under the 800-line guardrail
while still expressing the OAuth /token flow as a coherent ``OAuthService``
API. The helpers here are stateful at module scope (the cache dict) — there
is intentionally no class wrapper because the bug we're solving is a
short-window concurrency race and an ``IdempotencyManager`` class spanning
both /token and /refresh would be premature abstraction (post-0962 write
discipline). /refresh has its own equivalent primitive in
``oauth_refresh_service`` for the same reason.

Why this exists (live evidence):
ChatGPT's connector backend issues concurrent POST /token from different
Azure egress IPs (verified on demo.giljo.ai 2026-05-10 15:41:48 EDT) using
the same auth-code. Spec-strict single-use enforcement returned 200 for
the first and 400 "Authorization code has already been used" for the
second; the connector UI flashed "Something went wrong" before reading the
first response. Auth0/Okta/AWS Cognito all implement a short idempotency
window for confidential clients to absorb honest retries — this is parity.

TODO(INF-5074): replace with Redis/DB-backed cache when SaaS goes multi-worker —
the current single-worker assumption breaks under uvicorn --workers > 1.
"""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from datetime import datetime


OAUTH_TOKEN_IDEMPOTENCY_WINDOW_SECONDS = int(os.environ.get("OAUTH_TOKEN_IDEMPOTENCY_WINDOW_SECONDS", "5"))
_TOKEN_IDEMPOTENCY_CACHE_MAX_ENTRIES = 1000
_TOKEN_IDEMPOTENCY_FIELD_SEP = b"\x1f"


@dataclass(frozen=True)
class IdempotencyEntry:
    """One cached /token response keyed by (tenant_key, code)."""

    response_body: dict
    body_signature: str
    expires_at: datetime


_token_idempotency_cache: dict[tuple[str, str], IdempotencyEntry] = {}


def cache_get(key: tuple[str, str], *, now: datetime) -> IdempotencyEntry | None:
    """Return the cached entry for ``key``, lazy-evicting on TTL lapse."""
    entry = _token_idempotency_cache.get(key)
    if entry is None:
        return None
    if entry.expires_at <= now:
        _token_idempotency_cache.pop(key, None)
        return None
    return entry


def cache_put(key: tuple[str, str], entry: IdempotencyEntry) -> None:
    """Insert ``entry`` under ``key``, LRU-by-expiry evicting on soft cap."""
    cache = _token_idempotency_cache
    if len(cache) >= _TOKEN_IDEMPOTENCY_CACHE_MAX_ENTRIES and key not in cache:
        oldest_key = min(cache, key=lambda k: cache[k].expires_at)
        cache.pop(oldest_key, None)
    cache[key] = entry


def compute_body_signature(
    *,
    client_id: str,
    proof: str,
    redirect_uri: str,
) -> str:
    """Canonical body-signature for the /token idempotency check.

    ``proof`` is the client's proof-of-possession token: code_verifier for
    public PKCE clients, the plaintext client_secret for confidential
    clients. The signature only needs to match across retries from the
    same caller — using whichever value the caller sends keeps the
    comparison deterministic without an extra resolver round-trip.

    The unit-separator byte (\\x1f) prevents ambiguous concatenation when
    adjacent fields would otherwise blend (e.g., ``"abcdef" + "1234"`` vs.
    ``"abc" + "def1234"``).
    """
    h = hashlib.sha256()
    h.update(client_id.encode("utf-8"))
    h.update(_TOKEN_IDEMPOTENCY_FIELD_SEP)
    h.update(proof.encode("utf-8"))
    h.update(_TOKEN_IDEMPOTENCY_FIELD_SEP)
    h.update(redirect_uri.encode("utf-8"))
    return h.hexdigest()
