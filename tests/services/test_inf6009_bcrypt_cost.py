# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""INF-6009 #4 — bcrypt cost factor is pinned at 12 rounds (PASSWORD layer).

``gensalt()`` is now called with an explicit ``rounds=12`` at every PASSWORD
hashing site so the work factor cannot silently regress if a future bcrypt
default changes. A bcrypt hash encodes its cost in the modular-crypt prefix
``$2b$<rounds>$``; this test asserts the produced password hash carries
``$2b$12$``.

BE-6060b note: the API-KEY hashing layer no longer uses bcrypt. ``gk_`` keys are
256-bit machine tokens, so ``hash_api_key`` now emits a fast ``sha256$<hex>``
digest (GitHub/Stripe pattern). The bcrypt-cost pin therefore applies only to
passwords; the API-key cases below assert the new sha256 contract instead.
"""

import pytest

from giljo_mcp.api_key_utils import hash_api_key, verify_api_key
from giljo_mcp.utils.password_helper import async_hash_password


COST_PREFIX = "$2b$12$"
API_KEY_HASH_PREFIX = "sha256$"


@pytest.mark.asyncio
async def test_password_helper_pins_cost_12():
    """async_hash_password produces a $2b$12$ hash."""
    hashed = await async_hash_password("S3cret-pass!")
    assert hashed.startswith(COST_PREFIX), f"expected {COST_PREFIX!r} prefix, got {hashed[:7]!r}"


def test_api_key_hash_uses_sha256_format():
    """BE-6060b: hash_api_key produces a sha256$<hex> hash, NOT bcrypt."""
    hashed = hash_api_key("gk_abc123def456")
    assert hashed.startswith(API_KEY_HASH_PREFIX), f"expected {API_KEY_HASH_PREFIX!r} prefix, got {hashed[:8]!r}"
    assert not hashed.startswith("$2b$"), "API keys must no longer be bcrypt-hashed (BE-6060b)"


def test_api_key_hash_round_trips_through_verify():
    """Sanity: a sha256$ hash still verifies, so the format change did not break auth."""
    hashed = hash_api_key("gk_roundtrip")
    assert hashed.startswith(API_KEY_HASH_PREFIX)
    assert verify_api_key("gk_roundtrip", hashed) is True
    assert verify_api_key("gk_wrong", hashed) is False
