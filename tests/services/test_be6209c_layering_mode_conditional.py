# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-6209c (Q1) — layering fix: orchestrator protocol BODY fragments are now
mode-conditional.

A handful of body fragments were hardcoded with multi-terminal-only prose ("copy
agent prompts from the dashboard", "tell user to paste in a NEW terminal", "waiting
for user to start agents") that rendered in EVERY mode — contradicting the
subagent-mode wake block ("your subagents are Task()/spawn_agent() processes you
spawn autonomously"). These render mode-conditionally now.

Invariant preserved: the multi_terminal render stays byte-identical (the exact
today strings are still emitted); only CLI subagent-mode branches change.

Pure-string assertions (no DB, no module-level mutable state) — parallel-safe.
Edition Scope: CE.
"""

from __future__ import annotations

from giljo_mcp.services.protocol_sections.agent_lifecycle import _generate_orchestrator_protocol


# The exact strings that may render ONLY in multi_terminal mode. They assume a human
# who copies prompts into terminals — false for a CLI subagent orchestrator.
_MULTI_TERMINAL_ONLY = (
    '   - "Copy agent prompts from the dashboard to start them."',
    # BE-9012d: softened "paste... in a NEW terminal" to a harness-neutral "start...
    # in a new agent session (terminal, desktop, or web tab)".
    "  → Tell user to start the new prompt in a new agent session (terminal, desktop, or web tab)",
    "**If waiting for user to start agents (multi-terminal):**",
)


def _proto(*, execution_mode: str, tool: str) -> str:
    return _generate_orchestrator_protocol(
        job_id="job-6209c",
        tenant_key="tk_6209c",
        executor_id="exec-6209c",
        execution_mode=execution_mode,
        tool=tool,
        is_chain_conductor=False,
    )


def test_multi_terminal_render_keeps_today_strings_byte_identical() -> None:
    """No-regression lock: multi_terminal still emits the EXACT multi-terminal-only
    fragments (byte-identical to pre-BE-6209c)."""
    multi = _proto(execution_mode="multi_terminal", tool="multi_terminal")
    for s in _MULTI_TERMINAL_ONLY:
        assert s in multi, f"multi_terminal render must keep verbatim: {s!r}"


def test_subagent_render_drops_multi_terminal_only_fragments() -> None:
    """In a CLI subagent mode the contradictory multi-terminal-only fragments are gone."""
    sub = _proto(execution_mode="claude-code", tool="claude-code")
    for s in _MULTI_TERMINAL_ONLY:
        assert s not in sub, f"subagent render must NOT carry multi-terminal-only fragment: {s!r}"


def test_subagent_render_uses_self_spawn_phrasing() -> None:
    """The subagent body gets self-spawn phrasing keyed off the tool, so it agrees with
    the wake block instead of contradicting it."""
    sub = _proto(execution_mode="claude-code", tool="claude-code")
    assert "I will spawn each agent directly via Task(subagent_type=...)" in sub
    assert "no dashboard copy/paste needed" in sub
    assert "Launch the replacement directly via Task(subagent_type=...)" in sub
    assert "**If your spawned subagents are running (nothing actionable right now):**" in sub


def test_subagent_self_spawn_syntax_is_tool_aware() -> None:
    """The self-spawn syntax mirrors _FORBIDDEN_BY_TOOL per CLI; unknown tools fall back."""
    codex = _proto(execution_mode="codex", tool="codex")
    assert "spawn_agent(name=...)" in codex
    assert "Task(subagent_type=...)" not in codex

    gemini = _proto(execution_mode="gemini", tool="gemini")
    assert "@agent-name" in gemini

    # Unknown subagent tool → generic phrasing, never a crash or a multi-terminal leak.
    generic = _proto(execution_mode="some_future_cli", tool="some_future_cli")
    assert "your CLI's in-process subagent syntax" in generic
    for s in _MULTI_TERMINAL_ONLY:
        assert s not in generic
