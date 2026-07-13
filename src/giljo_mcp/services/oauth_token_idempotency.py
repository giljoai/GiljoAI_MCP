# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""OAuth /token idempotency-window primitive (API-0021l, INF-5074).

Routes idempotency-window state through the `CacheBackend` registry
(`giljo_mcp.services.cache_backends`). CE installs see the default
`InProcessDictBackend` (single-worker correct). SaaS installs see the
Redis-backed adapter from `giljo_mcp.saas.services.redis_cache_backend`,
which keeps state coherent across uvicorn workers — that swap is the
INF-5074 fix.

Why this exists (live evidence):
ChatGPT's connector backend issues concurrent POST /token from different
Azure egress IPs (verified on mcp.example.com 2026-05-10 15:41:48 EDT) using
the same auth-code. Spec-strict single-use enforcement returned 200 for
the first and 400 "Authorization code has already been used" for the
second; the connector UI flashed "Something went wrong" before reading the
first response. Auth0/Okta/AWS Cognito all implement a short idempotency
window for confidential clients to absorb honest retries — this is parity.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from dataclasses import dataclass

from giljo_mcp.services.cache_backends import OAUTH_IDEMPOTENCY_BACKEND_NAME, get_cache_backend


logger = logging.getLogger(__name__)

OAUTH_TOKEN_IDEMPOTENCY_WINDOW_SECONDS = int(os.environ.get("OAUTH_TOKEN_IDEMPOTENCY_WINDOW_SECONDS", "5"))
_TOKEN_IDEMPOTENCY_FIELD_SEP = b"\x1f"


@dataclass(frozen=True)
class IdempotencyEntry:
    """One cached /token response keyed by (tenant_key, code)."""

    response_body: dict
    body_signature: str


def _serialize(entry: IdempotencyEntry) -> str:
    return json.dumps(
        {
            "response_body": entry.response_body,
            "body_signature": entry.body_signature,
        }
    )


def _deserialize(raw: str) -> dict[str, object]:
    return json.loads(raw)


async def cache_get(tenant_key: str, code: str) -> IdempotencyEntry | None:
    """Return the cached entry for `(tenant_key, code)` from the registered backend.

    The backend's TTL drives expiry; a miss is indistinguishable from a
    lapsed entry, which is the desired semantic.
    """
    backend = get_cache_backend(OAUTH_IDEMPOTENCY_BACKEND_NAME)
    raw = await backend.get(tenant_key, code)
    if raw is None:
        return None
    payload = _deserialize(raw)
    return IdempotencyEntry(
        response_body=dict(payload["response_body"]),  # type: ignore[arg-type]
        body_signature=str(payload["body_signature"]),
    )


async def cache_put(tenant_key: str, code: str, entry: IdempotencyEntry) -> None:
    """Insert `entry` under `(tenant_key, code)` with the configured TTL."""
    backend = get_cache_backend(OAUTH_IDEMPOTENCY_BACKEND_NAME)
    await backend.set(
        tenant_key,
        code,
        _serialize(entry),
        ttl_seconds=OAUTH_TOKEN_IDEMPOTENCY_WINDOW_SECONDS,
    )


def compute_body_signature(
    *,
    client_id: str,
    proof: str,
    redirect_uri: str,
) -> str:
    """Canonical body-signature for the /token idempotency check.

    `proof` is the client's proof-of-possession token: code_verifier for
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
