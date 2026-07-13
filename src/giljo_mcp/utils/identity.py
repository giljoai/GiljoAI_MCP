# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Agent-identity token hardening (BE-9037).

A self-declared agent id (``from_agent``) feeds a FUNCTIONAL identity field on the
Agent Message Hub (recipient self-exclusion, baton/get_my_turn matching, read
cursors). A stray control or zero-width character silently forks that identity, so
strip them before the value reaches the DB. Slugs are preserved verbatim — the Hub
keys on the agent slug, not a UUID — so a legitimate id like ``BE-9037`` or
``CI2-orchestrator`` is unchanged.

Edition Scope: CE.
"""

from __future__ import annotations

import re

from giljo_mcp.exceptions import ValidationError


# C0/C1 control chars + zero-width / BOM / line-separator codepoints.
_IDENTITY_STRIP_RE = re.compile("[\x00-\x1f\x7f-\x9f\u200b-\u200f\u2028\u2029\ufeff]")


def sanitize_agent_identity(raw: str) -> str:
    """Strip control + zero-width chars, then surrounding whitespace, from an agent
    identity token. Returns ``''`` when nothing usable survives (the caller turns
    that into a clean 422 rather than writing a blank/garbage addressing key)."""
    return _IDENTITY_STRIP_RE.sub("", raw).strip()


def validate_from_agent(raw: str | None, *, max_len: int = 64) -> str | None:
    """Harden an agent-supplied ``from_agent`` at the write boundary (BE-9037):
    type-check, length-cap, and sanitize. Returns the clean slug, or ``None`` when
    omitted/blank (the user-post path). Raises :class:`ValidationError` (clean 422,
    never a 500) on a non-string, an over-long value, or a value that is only
    control/zero-width chars. The slug is preserved verbatim — the Hub keys on the
    agent slug, never a UUID — and an unknown-but-sane slug is accepted (ad-hoc lane
    ids are legitimate)."""
    if raw is not None and not isinstance(raw, str):
        raise ValidationError(
            "from_agent must be a string.",
            context={"operation": "comm_thread.post", "from_agent_type": type(raw).__name__},
        )
    raw = raw or ""
    if len(raw) > max_len:
        raise ValidationError(
            f"from_agent must be <= {max_len} chars.",
            context={"operation": "comm_thread.post", "from_agent_len": len(raw)},
        )
    cleaned = sanitize_agent_identity(raw)
    if raw and not cleaned:
        raise ValidationError(
            "from_agent contained no usable characters after sanitization.",
            context={"operation": "comm_thread.post"},
        )
    return cleaned or None
