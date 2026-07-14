# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Banned tokens for agent-facing prose (BE-9058) — the extensible single list.

Rendered protocol chapters, seeded template instructions, the giljo guide, and
MCP tool/parameter descriptions must never teach retired parameter names or
legacy execution-mode tokens: an agent that follows them gets no-op advice
(the server ignores the retired flags) or writes deprecated vocabulary into
the DB (legacy mode tokens on new chain runs).

``tests/unit/test_be9058_agent_prose_tokens.py`` imports this list and greps
both the prose-module sources and the live FastMCP tool registry. To ban a
newly retired token, append one entry here — the test needs no edit.

Kept in tests/helpers (not src) so the ban list ships nothing to production.
"""

from __future__ import annotations


# (token, why-it-is-banned) — the reason renders in the failure message so the
# offender's author knows what to write instead.
BANNED_AGENT_PROSE_TOKENS: tuple[tuple[str, str], ...] = (
    (
        "acknowledge_closeout_todo",
        "retired complete_job flag (BE-9012b) — the closeout TODO auto-completes structurally; "
        "the server accepts-and-ignores the flag, so prose teaching it gives no-op advice",
    ),
    (
        "acknowledge_messages_on_complete",
        "retired complete_job flag (BE-9012b) — the messages gate blocks only on genuine "
        "action-required posts; there is no drain-bypass flag",
    ),
    (
        "claude_code_cli",
        "legacy execution-mode token (BE-9035c collapsed 6 modes onto 'multi_terminal' + 'subagent')",
    ),
    (
        "codex_cli",
        "legacy execution-mode token (BE-9035c) — canonical modes are 'multi_terminal' and 'subagent'",
    ),
    (
        "gemini_cli",
        "legacy execution-mode token (BE-9035c) — canonical modes are 'multi_terminal' and 'subagent'",
    ),
    (
        "antigravity_cli",
        "legacy execution-mode token (BE-9035c) — canonical modes are 'multi_terminal' and 'subagent'",
    ),
    # NOTE: "generic_mcp" is deliberately NOT banned. Besides its legacy-mode life it
    # is the REGISTERED harness-agnostic tool_type (BE-9013) whose CH3 rung renders
    # "(generic_mcp)" on purpose — banning it would fight that shipped design.
)


# (tool_name, token) pairs the LIVE-REGISTRY scan skips — each is a deliberate,
# documented survivor, not a prose regression:
#
# * complete_job keeps its two RETIRED flags on the SIGNATURE (BE-9012b shim:
#   accepted-and-ignored so in-flight callers do not 422) — the parameter NAMES
#   necessarily appear in the tool schema. Their descriptions say RETIRED /
#   "do not pass it"; only the unavoidable schema keys survive.
# * write_memory_entry's acknowledge_closeout_todo is a LIVE, working flag
#   (BE-6208a) that merely shares its spelling with complete_job's retired one.
# * giljo_setup's platform parameter takes the CURRENT export-platform vocabulary
#   (EXPORT_PLATFORMS: claude_code / gemini_cli / codex_cli / antigravity_cli) —
#   platform identity, not execution-mode vocabulary; same spelling, different axis.
TOOL_PROSE_SURVIVORS: frozenset[tuple[str, str]] = frozenset(
    {
        ("complete_job", "acknowledge_closeout_todo"),
        ("complete_job", "acknowledge_messages_on_complete"),
        ("write_memory_entry", "acknowledge_closeout_todo"),
        ("giljo_setup", "gemini_cli"),
        ("giljo_setup", "codex_cli"),
        ("giljo_setup", "antigravity_cli"),
    }
)
