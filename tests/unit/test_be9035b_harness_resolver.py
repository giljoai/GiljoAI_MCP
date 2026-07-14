# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9035b -- runtime harness detection resolver + the effective_harness precedence seam.

Locks the pure, table-driven ``harness_from_client_info`` resolver (the three-case
harvest design: recognized name -> table; absent/empty -> generic; unrecognized
non-empty -> generic + INFO log so the seed table self-improves) and the ONE
precedence helper ``effective_harness`` (DETECTED beats declared-CLI-hint beats
generic). Detection drives RENDERING only, never auth.

The seed table grew from live captures: ``claude-code`` (step-(a) production harvest),
then ``codex-mcp-client`` and ``opencode``, then ``gemini-cli-mcp-client`` and
``antigravity-client`` (TSK-9088 capture sweep). Hosted OpenAI/Anthropic chat-connector
surfaces and connection probes are RECOGNIZED-as-generic (explicit rows, silent). A
spoofed-lookalike name (exact-match only) must never resolve to a real harness.

Edition Scope: Both. Pure functions -- no DB, no module-level mutable state;
parallel-safe under pytest-xdist.
"""

from __future__ import annotations

import logging

import pytest

from giljo_mcp.platform_registry import (
    GENERIC_HARNESS,
    HARNESS_ANTIGRAVITY,
    HARNESS_CLAUDE_CODE,
    HARNESS_CODEX,
    HARNESS_GEMINI,
    HARNESS_OPENCODE,
    effective_harness,
    harness_from_client_info,
)


# ---------------------------------------------------------------------------
# harness_from_client_info -- the three-case resolver
# ---------------------------------------------------------------------------


def test_confirmed_claude_code_row_resolves_exact():
    """The one CONFIRMED harvest row: name=='claude-code' (exact) -> claude-code."""
    assert harness_from_client_info("claude-code", "2.1.199") == HARNESS_CLAUDE_CODE
    # version is irrelevant to today's resolution (accepted for the future tie-break).
    assert harness_from_client_info("claude-code", None) == HARNESS_CLAUDE_CODE


def test_confirmed_codex_mcp_client_row_resolves_exact_and_silent(caplog):
    """BE-9070: local Codex CLI identifies as codex-mcp-client, exact -> codex."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info("codex-mcp-client", "0.42.0") == HARNESS_CODEX
        assert harness_from_client_info("codex-mcp-client", None) == HARNESS_CODEX
    assert "[harness-detect]" not in caplog.text


def test_confirmed_opencode_row_resolves_exact_and_silent(caplog):
    """BE-9035c: opencode now self-identifies via clientInfo (name=='opencode', from the
    BE-9035 harvest) so it is a RECOGNIZED first-class harness -> resolves to opencode,
    with NO unrecognized-observation log (it is a known row, not table-growth traffic)."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info("opencode", "9.9.9") == HARNESS_OPENCODE
        assert harness_from_client_info("opencode", None) == HARNESS_OPENCODE
    assert "[harness-detect]" not in caplog.text


def test_tsk9088_gemini_cli_row_resolves_exact_and_silent(caplog):
    """TSK-9088: Gemini CLI identifies as gemini-cli-mcp-client (live-captured) -> gemini,
    a RECOGNIZED harness with NO self-improve log."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info("gemini-cli-mcp-client", "0.49.0") == HARNESS_GEMINI
        assert harness_from_client_info("gemini-cli-mcp-client", None) == HARNESS_GEMINI
    assert "[harness-detect]" not in caplog.text


def test_tsk9088_antigravity_row_resolves_exact_and_silent(caplog):
    """TSK-9088: the Antigravity desktop app AND CLI both send antigravity-client
    (live-captured; version literal 'v1.0.0') -> antigravity, RECOGNIZED, NO log."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info("antigravity-client", "v1.0.0") == HARNESS_ANTIGRAVITY
        assert harness_from_client_info("antigravity-client", None) == HARNESS_ANTIGRAVITY
    assert "[harness-detect]" not in caplog.text


@pytest.mark.parametrize(
    "name",
    [
        "Anthropic/ClaudeAI",  # Claude Desktop AND claude.ai web (identical string)
        "Anthropic/Toolbox",  # Anthropic connector-validation probe
        "openai-mcp",  # chatgpt.com steady-state (hosted, no terminal)
        "openai-mcp (ChatGPT)",  # chatgpt.com connector validation/tool-discovery
        "openai-mcp (Codex)",  # Codex hosted-connector surface (!= codex-mcp-client)
        "opencode-check",  # opencode's connection-test probe (!= real 'opencode')
    ],
)
def test_tsk9088_known_generic_surfaces_resolve_generic_and_silent(name, caplog):
    """TSK-9088: hosted chat/connector surfaces + probes map to generic EXPLICITLY, so the
    self-improve INFO log stays quiet for known-benign, high-frequency traffic. These are
    RECOGNIZED-as-generic (case a), distinct from the unrecognized+log path (case c)."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info(name, "1.0.0") == GENERIC_HARNESS
    assert "[harness-detect]" not in caplog.text


@pytest.mark.parametrize("name", [None, "", "   ", "\t\n"])
def test_absent_or_empty_name_resolves_generic_silently(name, caplog):
    """Case (b): absent / {} / whitespace-only name -> generic, and NO observation log
    (an empty connect is the common, expected case, not something to grow the table from)."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info(name, None) == GENERIC_HARNESS
    assert "[harness-detect]" not in caplog.text


@pytest.mark.parametrize(
    "name",
    [
        "codex",  # a real harness, but NOT confirmed in the harvest -> must not be guessed
        "codex-mcp",  # lookalike: local Codex CLI sends codex-mcp-client, exact only
        "gemini-cli",
        "antigravity",
        # NOTE (BE-9035c): "opencode" is now a RECOGNIZED harness and is asserted
        # positively in test_confirmed_opencode_row_resolves_exact_and_silent; it must
        # NOT appear here.
        "totally-made-up-client",
    ],
)
def test_unrecognized_nonempty_name_resolves_generic_and_logs(name, caplog):
    """Case (c): an unrecognized NON-EMPTY name -> generic AND an INFO observation log
    (raw name), so the seed table self-improves from real traffic, never from guesses."""
    with caplog.at_level(logging.INFO):
        assert harness_from_client_info(name, "9.9.9") == GENERIC_HARNESS
    assert "[harness-detect]" in caplog.text
    assert name in caplog.text


def test_openai_mcp_hosted_surface_stays_generic():
    """BE-9070/TSK-9088: openai-mcp is hosted, not a terminal CLI; it stays generic.
    (As of TSK-9088 it is now a RECOGNIZED-as-generic row, asserted silent in
    test_tsk9088_known_generic_surfaces_resolve_generic_and_silent — here we only pin
    that it never borrows a real harness's render.)"""
    assert harness_from_client_info("openai-mcp", "9.9.9") == GENERIC_HARNESS


@pytest.mark.parametrize(
    "spoof",
    [
        "claude-code-proxy",  # substring superset
        "claudecode",  # punctuation-stripped lookalike
        "claude_code",  # underscore variant
        "Claude-Code",  # case variant
        "x-claude-code",  # prefix injection
        " claude-code-x ",
    ],
)
def test_spoofed_lookalikes_never_resolve_to_claude(spoof):
    """Matching is EXACT (never substring/prefix/case-fold): a lookalike degrades to
    generic. Detection is not a security boundary, but a conservative table keeps a
    hostile/mistaken clientInfo from borrowing the wrong harness's render."""
    assert harness_from_client_info(spoof, None) == GENERIC_HARNESS


def test_surrounding_whitespace_on_confirmed_name_is_tolerated():
    """A confirmed name padded with whitespace still resolves (strip, not fuzzy-match)."""
    assert harness_from_client_info("  claude-code  ", None) == HARNESS_CLAUDE_CODE


# ---------------------------------------------------------------------------
# effective_harness -- the ONE precedence helper (DETECTED > declared-hint > generic)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "declared_mode,expected",
    [
        ("claude_code_cli", HARNESS_CLAUDE_CODE),
        ("codex_cli", "codex"),
        ("gemini_cli", "gemini"),
        ("antigravity_cli", "antigravity"),
        ("generic_mcp", GENERIC_HARNESS),  # no CLI harness -> floor (render key stays generic_mcp)
        ("multi_terminal", GENERIC_HARNESS),  # human-driven; not a harness
        ("", GENERIC_HARNESS),
        (None, GENERIC_HARNESS),
        ("some_unknown_future_mode", GENERIC_HARNESS),
    ],
)
def test_declared_hint_when_no_detection_is_byte_safe(declared_mode, expected):
    """session=None -> detection absent -> the declared-CLI-hint path. This is the
    byte-safety floor: every value matches what tool_for_mode-based keying produced
    before the seam existed (the untouched golden is the transport-level proof)."""
    assert effective_harness(declared_mode, None) == expected


@pytest.mark.parametrize("session_shape", [{"harness": "claude-code"}, {"resolved_harness": "claude-code"}])
def test_detected_concrete_harness_beats_declared(session_shape):
    """A CONCRETE detected harness wins over the declared mode (the DESIGN precedence
    flip). A generic_mcp project connected from claude-code renders claude-code."""
    assert effective_harness("generic_mcp", session_shape) == HARNESS_CLAUDE_CODE
    # ...and even overrides a DIFFERENT declared CLI (detected codex beats declared claude).
    assert effective_harness("claude_code_cli", {"harness": "codex"}) == "codex"


@pytest.mark.parametrize("detected", [None, "", "generic"])
def test_generic_or_absent_detection_falls_through_to_declared(detected):
    """empty/absent/'generic' detection is NOT concrete and must NOT override the
    declared hint -- otherwise a claude project would lose its render. (BE-9035c:
    'opencode' is no longer generic; a concrete detected opencode WOULD win, which is
    why it is excluded from this generic-only parametrize.)"""
    assert effective_harness("claude_code_cli", {"harness": detected}) == HARNESS_CLAUDE_CODE


def test_reads_mcpsession_like_row_via_session_data():
    """effective_harness tolerates an MCPSession-like row (reads .session_data)."""

    class _Row:
        session_data = {"resolved_harness": "gemini", "client_info": {"name": "gemini-cli"}}

    assert effective_harness("multi_terminal", _Row()) == "gemini"


def test_no_declared_and_no_detection_is_generic_floor():
    assert effective_harness(None, None) == GENERIC_HARNESS
    assert effective_harness("", {"harness": "generic"}) == GENERIC_HARNESS
