# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-3006a single-writer rule — the shared async password helper.

All user password / recovery-PIN hashing and verification now route through the
ONE helper (``async_hash_password`` / ``async_verify_password``), which offloads
bcrypt's ~250-400ms CPU off the event loop via ``asyncio.to_thread`` (the
BE-6068 pattern). These tests prove the roundtrip is correct AND that each call
is genuinely dispatched through ``to_thread`` (not run inline on the loop).
"""

import asyncio

import bcrypt
import pytest

from giljo_mcp.utils.password_helper import async_hash_password, async_verify_password


@pytest.mark.asyncio
async def test_hash_then_verify_roundtrip():
    """A hashed password verifies true; a wrong password verifies false."""
    hashed = await async_hash_password("S3cret-pass!")
    assert isinstance(hashed, str)
    assert hashed.startswith("$2")  # bcrypt prefix
    assert await async_verify_password("S3cret-pass!", hashed) is True
    assert await async_verify_password("wrong-pass", hashed) is False


@pytest.mark.asyncio
async def test_helper_offloads_bcrypt_via_to_thread(monkeypatch):
    """Both helper calls must dispatch bcrypt through asyncio.to_thread."""
    seen: list[str] = []
    real_to_thread = asyncio.to_thread

    async def _spy(fn, *args, **kwargs):
        if fn is bcrypt.hashpw:
            seen.append("hash")
        elif fn is bcrypt.checkpw:
            seen.append("verify")
        return await real_to_thread(fn, *args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", _spy)

    hashed = await async_hash_password("offload-me")
    assert await async_verify_password("offload-me", hashed) is True

    assert "hash" in seen, "async_hash_password did not offload bcrypt.hashpw via to_thread"
    assert "verify" in seen, "async_verify_password did not offload bcrypt.checkpw via to_thread"


@pytest.mark.asyncio
async def test_helper_interops_with_externally_hashed_value():
    """A hash produced by raw bcrypt (e.g. a test fixture / legacy row) verifies."""
    legacy = bcrypt.hashpw(b"legacy-pw", bcrypt.gensalt()).decode("utf-8")
    assert await async_verify_password("legacy-pw", legacy) is True


# ---------------------------------------------------------------------------
# SEC-9174 #6 — bcrypt >72-byte fail-close
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_verify_overlong_password_fails_closed():
    """bcrypt >= 4 raises ValueError for a password over 72 UTF-8 bytes. The
    helper must fail CLOSED (return False), never propagate — pre-fix the raise
    surfaced as a 500 at login for a KNOWN account vs a 401 for an unknown one,
    a username-enumeration oracle (SEC-9174 #6)."""
    hashed = await async_hash_password("S3cret-pass!")
    assert await async_verify_password("A" * 100, hashed) is False


@pytest.mark.asyncio
async def test_verify_overlong_multibyte_password_fails_closed():
    """The 72 limit is BYTES, not characters: 40 x 'é' is 40 chars / 80 bytes."""
    hashed = await async_hash_password("S3cret-pass!")
    assert await async_verify_password("é" * 40, hashed) is False


@pytest.mark.asyncio
async def test_verify_at_72_byte_boundary_still_works():
    """Exactly-72-byte passwords stay verifiable — the guard must not over-reject."""
    password = "B" * 72
    hashed = await async_hash_password(password)
    assert await async_verify_password(password, hashed) is True
    assert await async_verify_password("B" * 71 + "x", hashed) is False


@pytest.mark.asyncio
async def test_verify_malformed_stored_hash_fails_closed():
    """A corrupt stored hash makes bcrypt.checkpw raise ValueError ('invalid
    salt'); verification must fail closed (False), not bubble up as a 500."""
    assert await async_verify_password("whatever", "not-a-bcrypt-hash") is False
