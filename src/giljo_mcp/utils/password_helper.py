# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Shared async password helper (BE-3006a single-writer rule).

The ONE place user passwords / recovery PINs are hashed and verified. bcrypt's
``hashpw``/``checkpw`` are ~250-400ms of pure CPU; run on the event loop they
freeze the single worker (every concurrent MCP call / WS frame stalls). This
helper offloads each call via ``asyncio.to_thread`` (the BE-6068 pattern), so
the loop stays responsive.

Use this for PASSWORD and PIN hashing only. API-key hashing
(``api_key_utils``) and OAuth client-secret hashing are deliberately separate
concerns with their own helpers — do not route them here.
"""

import asyncio

import bcrypt


async def async_hash_password(plaintext: str) -> str:
    """Hash a password / PIN with bcrypt, off the event loop.

    Args:
        plaintext: The clear-text password or PIN to hash.

    Returns:
        The bcrypt hash as a UTF-8 ``str`` (ready for a ``*_hash`` column).
    """
    hashed = await asyncio.to_thread(bcrypt.hashpw, plaintext.encode("utf-8"), bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


async def async_verify_password(plaintext: str, password_hash: str) -> bool:
    """Constant-time-verify a password / PIN against its bcrypt hash, off the loop.

    Args:
        plaintext: The clear-text password or PIN presented by the caller.
        password_hash: The stored bcrypt hash to compare against.

    Returns:
        ``True`` if the plaintext matches the hash, ``False`` otherwise.
    """
    return await asyncio.to_thread(bcrypt.checkpw, plaintext.encode("utf-8"), password_hash.encode("utf-8"))
