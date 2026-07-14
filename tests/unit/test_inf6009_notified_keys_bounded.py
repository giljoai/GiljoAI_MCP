# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6009 #7 — MCPAuthMiddleware._notified_keys must stay bounded.

The setup:tool_connected de-dup memo previously grew without bound (one entry
per distinct ``tenant:principal``), a slow memory leak for long-lived SaaS
workers. It is now a bounded, insertion-ordered ordered-set: over the cap it
evicts the oldest-inserted key while still suppressing repeat notifications for
any key still resident. These tests pin both properties at the middleware layer.
"""

from api.endpoints.mcp_sdk_server import MCPAuthMiddleware


def _middleware() -> MCPAuthMiddleware:
    # _mark_notified does not touch the wrapped app, so a sentinel is fine.
    return MCPAuthMiddleware(app=object())


def test_set_does_not_exceed_cap_under_many_distinct_keys():
    """Inserting far more than the cap leaves the memo capped, not unbounded."""
    mw = _middleware()
    mw._NOTIFIED_KEYS_MAX = 100  # instance override keeps the test fast

    for i in range(10 * mw._NOTIFIED_KEYS_MAX):
        mw._mark_notified(f"tenant-{i}:principal-{i}")

    assert len(mw._notified_keys) <= mw._NOTIFIED_KEYS_MAX


def test_first_sight_returns_true_repeat_returns_false():
    """De-dup behavior intact: first sight emits, an immediate repeat suppresses."""
    mw = _middleware()

    assert mw._mark_notified("t1:p1") is True  # first sight -> emit
    assert mw._mark_notified("t1:p1") is False  # repeat -> suppress
    assert mw._mark_notified("t2:p2") is True  # different key -> emit


def test_eviction_is_oldest_first():
    """Over the cap, the oldest-inserted key is evicted; newest is retained."""
    mw = _middleware()
    mw._NOTIFIED_KEYS_MAX = 3

    mw._mark_notified("k1")
    mw._mark_notified("k2")
    mw._mark_notified("k3")
    assert set(mw._notified_keys) == {"k1", "k2", "k3"}

    mw._mark_notified("k4")  # over cap -> evict oldest (k1)
    assert "k1" not in mw._notified_keys
    assert set(mw._notified_keys) == {"k2", "k3", "k4"}
    # An evicted key is treated as first-sight again (acceptable: it re-emits).
    assert mw._mark_notified("k1") is True
