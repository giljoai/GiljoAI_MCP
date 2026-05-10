# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Unit tests for ``giljo_mcp.services.oauth_token_idempotency``.

The module is a thin set of stateful helpers (cache get/put, signature).
End-to-end behavior is covered by
``tests/api/test_oauth_endpoints.py::TestTokenIdempotency`` at the FastAPI
boundary — these unit tests just lock the building blocks: TTL eviction,
soft-cap LRU eviction, and signature determinism / discrimination.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from giljo_mcp.services import oauth_token_idempotency as idem


@pytest.fixture
def fresh_cache(monkeypatch):
    """Each test runs against a fresh module-scope cache dict."""
    fresh: dict = {}
    monkeypatch.setattr(idem, "_token_idempotency_cache", fresh)
    return fresh


def _make_entry(*, expires_in_seconds: int = 5, signature: str = "sig") -> idem.IdempotencyEntry:
    return idem.IdempotencyEntry(
        response_body={"access_token": "tok"},
        body_signature=signature,
        expires_at=datetime.now(UTC) + timedelta(seconds=expires_in_seconds),
    )


class TestComputeBodySignature:
    def test_identical_inputs_yield_identical_signatures(self):
        sig1 = idem.compute_body_signature(client_id="cid", proof="proof", redirect_uri="https://x/cb")
        sig2 = idem.compute_body_signature(client_id="cid", proof="proof", redirect_uri="https://x/cb")
        assert sig1 == sig2
        assert len(sig1) == 64  # sha256 hex

    def test_field_separator_prevents_concatenation_collision(self):
        # Without a unit separator, ("ab", "c", "d") and ("a", "bc", "d") would
        # both hash sha256("abcd"). The 0x1F separator MUST disambiguate.
        sig_a = idem.compute_body_signature(client_id="ab", proof="c", redirect_uri="d")
        sig_b = idem.compute_body_signature(client_id="a", proof="bc", redirect_uri="d")
        assert sig_a != sig_b

    def test_signature_changes_with_each_field(self):
        base = idem.compute_body_signature(client_id="cid", proof="proof", redirect_uri="https://x/cb")
        diff_client = idem.compute_body_signature(client_id="cid2", proof="proof", redirect_uri="https://x/cb")
        diff_proof = idem.compute_body_signature(client_id="cid", proof="proof2", redirect_uri="https://x/cb")
        diff_redir = idem.compute_body_signature(client_id="cid", proof="proof", redirect_uri="https://x/cb2")
        assert {base, diff_client, diff_proof, diff_redir}.__len__() == 4


class TestCacheGetPut:
    def test_put_then_get_returns_entry(self, fresh_cache):
        key = ("tk_x", "code-1")
        entry = _make_entry()
        idem.cache_put(key, entry)
        got = idem.cache_get(key, now=datetime.now(UTC))
        assert got is entry

    @pytest.mark.usefixtures("fresh_cache")
    def test_miss_returns_none(self):
        assert idem.cache_get(("tk_x", "missing"), now=datetime.now(UTC)) is None

    def test_lazy_evict_on_expired_entry(self, fresh_cache):
        key = ("tk_x", "code-1")
        idem.cache_put(key, _make_entry(expires_in_seconds=-1))
        # Past expiry → cache_get returns None AND removes the entry.
        assert idem.cache_get(key, now=datetime.now(UTC)) is None
        assert key not in fresh_cache

    def test_soft_cap_evicts_oldest_entry(self, fresh_cache, monkeypatch):
        # Shrink the cap so the test is fast and deterministic.
        monkeypatch.setattr(idem, "_TOKEN_IDEMPOTENCY_CACHE_MAX_ENTRIES", 3)

        # Fill the cache with three entries with strictly increasing expiry.
        now = datetime.now(UTC)
        for i in range(3):
            idem.cache_put(
                ("tk_x", f"code-{i}"),
                idem.IdempotencyEntry(
                    response_body={"i": i},
                    body_signature="sig",
                    expires_at=now + timedelta(seconds=10 + i),
                ),
            )
        assert len(fresh_cache) == 3

        # Inserting a fourth entry with the latest expiry must evict the oldest.
        idem.cache_put(
            ("tk_x", "code-3"),
            idem.IdempotencyEntry(
                response_body={"i": 3},
                body_signature="sig",
                expires_at=now + timedelta(seconds=20),
            ),
        )
        assert len(fresh_cache) == 3
        assert ("tk_x", "code-0") not in fresh_cache  # oldest evicted
        assert ("tk_x", "code-3") in fresh_cache

    def test_overwrite_existing_key_does_not_count_toward_cap(self, fresh_cache, monkeypatch):
        monkeypatch.setattr(idem, "_TOKEN_IDEMPOTENCY_CACHE_MAX_ENTRIES", 1)
        key = ("tk_x", "code-1")
        idem.cache_put(key, _make_entry(signature="old"))
        idem.cache_put(key, _make_entry(signature="new"))
        # Same key replaced in place; no eviction needed.
        assert len(fresh_cache) == 1
        got = idem.cache_get(key, now=datetime.now(UTC))
        assert got is not None
        assert got.body_signature == "new"
