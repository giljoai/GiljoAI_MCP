# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
SEC-0002 Property — per-IP rate-limit verification.

This test verifies the behavior documented in
``docs/security/SEC-0002_passive_server_audit.md`` Deliverable D:

- ``api/middleware/rate_limiter.py`` is a sliding-window per-IP limiter.
- Keying is extracted by ``_get_client_ip(request)`` in this priority:
  ``X-Forwarded-For`` first element, then ``X-Real-IP``, then
  ``request.client.host``, then the literal ``"unknown"``.
- Over-limit requests raise HTTP 429 with ``Retry-After``,
  ``X-RateLimit-Limit``, ``X-RateLimit-Remaining``, ``X-RateLimit-Reset``
  headers.
- Static-file and configured exempt paths bypass the limiter entirely.

**Out of scope — what this test does NOT verify:**

This test verifies PER-IP behavior only. It does NOT verify per-tenant quotas
(that is SAAS-018, a separate anti-abuse project). A tenant operating from
many IPs can exceed any intended per-tenant budget under the current
middleware; the Trust Model surfaces this explicitly. Do not mistake a green
run here for a cross-IP anti-abuse guarantee.

Test style: direct-call / unit-style against ``RateLimiter`` and
``RateLimitMiddleware``, following the SEC-0005c pattern in
``tests/security/test_tenant_required.py`` (which uses direct handler calls
with hand-built request-like objects rather than spinning up a full
FastAPI TestClient). A TestClient-based test would add app-state
dependencies that are not needed to verify the three contracts above.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from starlette.responses import Response

from api.middleware.rate_limiter import RateLimiter, RateLimitMiddleware


# ---------------------------------------------------------------------------
# Helpers: minimal Request-shaped objects for _get_client_ip / dispatch
# ---------------------------------------------------------------------------


def _make_request(
    *,
    path: str = "/api/v1/projects",
    method: str = "GET",
    forwarded_for: str | None = None,
    real_ip: str | None = None,
    client_host: str | None = "127.0.0.1",
) -> SimpleNamespace:
    """
    Build a duck-typed Request that exposes only what ``RateLimitMiddleware``
    touches: ``url.path``, ``method``, ``headers.get``, and ``client.host``.

    Starlette's real Request has much more surface, but the rate-limit
    middleware is self-contained enough that a SimpleNamespace stub is
    sufficient and avoids having to build a full ASGI scope.
    """
    headers: dict[str, str] = {}
    if forwarded_for is not None:
        headers["X-Forwarded-For"] = forwarded_for
    if real_ip is not None:
        headers["X-Real-IP"] = real_ip

    return SimpleNamespace(
        url=SimpleNamespace(path=path),
        method=method,
        headers=SimpleNamespace(get=headers.get),
        client=SimpleNamespace(host=client_host) if client_host is not None else None,
    )


def _ok_call_next():
    """Async stand-in for ``call_next`` that returns a plain 200 Response."""

    async def _call_next(_request):
        # A real Response so the middleware can attach X-RateLimit-* headers.
        return Response(content=b"", status_code=200)

    return AsyncMock(side_effect=_call_next)


# ---------------------------------------------------------------------------
# RateLimiter: per-key bucket invariants
# ---------------------------------------------------------------------------


@pytest.mark.security
def test_rate_limiter_same_key_shares_bucket():
    """Two calls with the same key count toward one bucket (per-IP keying)."""
    limiter = RateLimiter(requests_per_minute=2)

    assert limiter.is_allowed("1.1.1.1") is True
    assert limiter.is_allowed("1.1.1.1") is True
    # Third call for the same key must be blocked — bucket is full.
    assert limiter.is_allowed("1.1.1.1") is False


@pytest.mark.security
def test_rate_limiter_distinct_keys_have_independent_buckets():
    """
    Different keys have independent quotas — exhausting one IP's bucket must
    not affect another IP. This is the core per-IP contract.
    """
    limiter = RateLimiter(requests_per_minute=2)

    # Exhaust IP A.
    assert limiter.is_allowed("1.1.1.1") is True
    assert limiter.is_allowed("1.1.1.1") is True
    assert limiter.is_allowed("1.1.1.1") is False

    # IP B still has a full budget — distinct bucket.
    assert limiter.is_allowed("2.2.2.2") is True
    assert limiter.is_allowed("2.2.2.2") is True
    assert limiter.is_allowed("2.2.2.2") is False


@pytest.mark.security
def test_rate_limiter_get_remaining_tracks_usage():
    """``get_remaining`` reports the unused slots for the key's bucket."""
    limiter = RateLimiter(requests_per_minute=3)

    assert limiter.get_remaining("1.1.1.1") == 3
    limiter.is_allowed("1.1.1.1")
    assert limiter.get_remaining("1.1.1.1") == 2
    limiter.is_allowed("1.1.1.1")
    assert limiter.get_remaining("1.1.1.1") == 1
    limiter.is_allowed("1.1.1.1")
    assert limiter.get_remaining("1.1.1.1") == 0


# ---------------------------------------------------------------------------
# _get_client_ip: header-priority contract
# ---------------------------------------------------------------------------


@pytest.mark.security
def test_get_client_ip_prefers_x_forwarded_for_first_hop():
    """X-Forwarded-For takes priority; first comma-separated element wins."""
    middleware = RateLimitMiddleware(app=None, requests_per_minute=300)

    req = _make_request(
        forwarded_for="203.0.113.7, 10.0.0.1, 10.0.0.2",
        real_ip="198.51.100.9",
        client_host="127.0.0.1",
    )
    assert middleware._get_client_ip(req) == "203.0.113.7"


@pytest.mark.security
def test_get_client_ip_falls_back_to_x_real_ip_then_client_host():
    """X-Real-IP used when XFF absent; client.host used when both absent."""
    middleware = RateLimitMiddleware(app=None, requests_per_minute=300)

    req_real = _make_request(real_ip="198.51.100.9", client_host="127.0.0.1")
    assert middleware._get_client_ip(req_real) == "198.51.100.9"

    req_host = _make_request(client_host="127.0.0.1")
    assert middleware._get_client_ip(req_host) == "127.0.0.1"

    req_none = _make_request(client_host=None)
    assert middleware._get_client_ip(req_none) == "unknown"


# ---------------------------------------------------------------------------
# RateLimitMiddleware.dispatch: 429 shape + exempt-path bypass
# ---------------------------------------------------------------------------


@pytest.mark.security
@pytest.mark.asyncio
async def test_middleware_allows_under_limit_and_sets_headers():
    """Requests under the limit pass through with X-RateLimit-* headers set."""
    middleware = RateLimitMiddleware(app=None, requests_per_minute=3)
    call_next = _ok_call_next()

    req = _make_request(forwarded_for="203.0.113.10")
    resp = await middleware.dispatch(req, call_next)

    assert resp.status_code == 200
    assert resp.headers["X-RateLimit-Limit"] == "3"
    assert resp.headers["X-RateLimit-Remaining"] == "2"
    assert "X-RateLimit-Reset" in resp.headers
    call_next.assert_awaited_once()


@pytest.mark.security
@pytest.mark.asyncio
async def test_middleware_429_on_limit_exceeded_with_retry_after():
    """
    Over-limit requests raise HTTP 429 with Retry-After, X-RateLimit-Limit,
    X-RateLimit-Remaining=0, and X-RateLimit-Reset headers.
    """
    middleware = RateLimitMiddleware(app=None, requests_per_minute=2)
    call_next = _ok_call_next()

    # Burn the bucket for one IP.
    req = _make_request(forwarded_for="203.0.113.20")
    await middleware.dispatch(req, call_next)
    await middleware.dispatch(req, call_next)

    # Third request from the same IP trips the limit.
    with pytest.raises(HTTPException) as exc:
        await middleware.dispatch(req, call_next)

    assert exc.value.status_code == 429
    headers = exc.value.headers or {}
    assert "Retry-After" in headers
    assert int(headers["Retry-After"]) >= 1
    assert headers["X-RateLimit-Limit"] == "2"
    assert headers["X-RateLimit-Remaining"] == "0"
    assert "X-RateLimit-Reset" in headers
    # call_next must not have been awaited a third time — the limiter rejected
    # before forwarding.
    assert call_next.await_count == 2


@pytest.mark.security
@pytest.mark.asyncio
async def test_middleware_distinct_ips_do_not_share_bucket_at_dispatch_level():
    """
    End-to-end per-IP check: IP A exhausting its budget does not block IP B.
    This is the contract-level complement of
    ``test_rate_limiter_distinct_keys_have_independent_buckets`` — it runs
    through the same ``dispatch`` path that production traffic takes.
    """
    middleware = RateLimitMiddleware(app=None, requests_per_minute=1)
    call_next = _ok_call_next()

    req_a = _make_request(forwarded_for="203.0.113.30")
    req_b = _make_request(forwarded_for="203.0.113.31")

    # IP A: first call OK, second call 429.
    await middleware.dispatch(req_a, call_next)
    with pytest.raises(HTTPException) as exc_a:
        await middleware.dispatch(req_a, call_next)
    assert exc_a.value.status_code == 429

    # IP B: still has its full budget — not affected by IP A's rejection.
    resp_b = await middleware.dispatch(req_b, call_next)
    assert resp_b.status_code == 200


# ---------------------------------------------------------------------------
# Exempt-path bypass
# ---------------------------------------------------------------------------


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize("exempt_path", ["/api/health", "/api/metrics"])
async def test_middleware_exempt_paths_bypass_rate_limiter(exempt_path):
    """
    Configured exempt paths (``/api/health``, ``/api/metrics``) bypass the
    limiter even when the bucket is already full for the caller's IP.
    """
    middleware = RateLimitMiddleware(app=None, requests_per_minute=1)
    call_next = _ok_call_next()

    # Exhaust the normal bucket so the IP would otherwise be rejected.
    req_normal = _make_request(path="/api/v1/projects", forwarded_for="203.0.113.40")
    await middleware.dispatch(req_normal, call_next)
    with pytest.raises(HTTPException):
        await middleware.dispatch(req_normal, call_next)

    # Same IP hitting an exempt path MUST NOT 429 — bypass is path-based,
    # not IP-based, so an exhausted IP can still hit /api/health.
    req_exempt = _make_request(path=exempt_path, forwarded_for="203.0.113.40")
    resp = await middleware.dispatch(req_exempt, call_next)
    assert resp.status_code == 200


@pytest.mark.security
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "static_path",
    ["/", "/index.html", "/favicon.ico", "/assets/main.js", "/assets/nested/deep/chunk.css"],
)
async def test_middleware_static_paths_bypass_rate_limiter(static_path):
    """
    Frontend static-file paths (``/``, ``/index.html``, ``/favicon.ico``,
    ``/assets/*``) bypass the limiter. Production serves the compiled
    frontend from the same process, and the sliding window must not
    interfere with asset delivery.
    """
    middleware = RateLimitMiddleware(app=None, requests_per_minute=1)
    call_next = _ok_call_next()

    # Exhaust the API bucket for this IP.
    req_normal = _make_request(path="/api/v1/projects", forwarded_for="203.0.113.50")
    await middleware.dispatch(req_normal, call_next)
    with pytest.raises(HTTPException):
        await middleware.dispatch(req_normal, call_next)

    # Static path for the same IP still passes.
    req_static = _make_request(path=static_path, forwarded_for="203.0.113.50")
    resp = await middleware.dispatch(req_static, call_next)
    assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Documentation anchor
# ---------------------------------------------------------------------------


@pytest.mark.security
def test_sec_0002_audit_artifact_exists():
    """
    The SEC-0002 audit artifact this test corroborates must exist. If someone
    removes the audit doc, this test screams so the documentation / guard
    cannot silently drift apart.
    """
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[2]
    audit = repo_root / "docs" / "security" / "SEC-0002_passive_server_audit.md"
    assert audit.is_file(), (
        f"Missing SEC-0002 audit artifact at {audit}. The rate-limit "
        "verification test is the behavioral complement to that document; "
        "removing the document without updating this test breaks the "
        "passive-server trust model."
    )
