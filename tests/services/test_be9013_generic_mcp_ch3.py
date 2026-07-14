# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""BE-9013 / BE-9035c — generic_mcp collapse contract + CH3 ladder block (unit layer).

Fast, DB-free coverage of the pieces the MCP-boundary test
(tests/integration/test_be9013_generic_mcp_mode_mcp_boundary.py) drives end to end.

BE-9035c collapsed execution_mode to the 2 canonical modes (multi_terminal / subagent).
``generic_mcp`` is NO LONGER a Platform/registry row — it is a member of
LEGACY_MODE_ALIASES that folds to ``subagent`` and maps to the ``generic`` floor tool.
These tests pin that collapse contract, and the CH3 ladder's PREFERRED / SELF-ADOPT /
FLOOR rungs (enriched by BE-9034 absorption) plus the preset-tuned self-adopt variant —
rendered identically for the legacy ``generic_mcp`` token AND the ``generic`` floor tool.

Edition Scope: Both. Pure functions — no DB, no module-level mutable state.
"""

from __future__ import annotations

from giljo_mcp import platform_registry as reg
from giljo_mcp.services.protocol_sections.chapters_reference import _build_ch3_spawning_rules


# ---------------------------------------------------------------------------
# Collapse contract — generic_mcp is a legacy alias, NOT a registry row (BE-9035c)
# ---------------------------------------------------------------------------


def test_generic_mcp_is_a_legacy_alias_not_a_registry_row():
    # The generic_mcp Platform/registry ROW is gone — it is now purely a legacy token.
    assert "generic_mcp" in reg.LEGACY_MODE_ALIASES
    assert "generic_mcp" in reg.ACCEPTED_EXECUTION_MODES
    # No registry row / mode object answers to it anymore.
    assert reg.get_platform("generic_mcp") is None
    assert reg.get_mode("generic_mcp") is None
    # It folds to the canonical subagent mode on read (never rewritten in storage).
    assert reg.normalize_execution_mode("generic_mcp") == "subagent"
    # And it renders/routes as a subagent orchestrator.
    assert reg.is_subagent_mode("generic_mcp") is True
    assert reg.is_subagent_render("generic_mcp") is True


def test_generic_mcp_maps_to_the_generic_floor_tool():
    # generic_mcp no longer maps to itself — it maps to the "generic" floor tool, the
    # SAME tool the canonical subagent mode maps to (the collapse target).
    assert reg.tool_for_mode("generic_mcp") == "generic"
    assert reg.EXECUTION_MODE_TO_TOOL["generic_mcp"] == "generic"
    assert reg.EXECUTION_MODE_TO_TOOL["subagent"] == "generic"
    # CLI_BINARIES is unchanged — generic_mcp contributes no launcher of its own.
    assert "generic_mcp" not in reg.CLI_BINARIES.values()


# ---------------------------------------------------------------------------
# CH3 ladder rungs
# ---------------------------------------------------------------------------


def test_generic_mcp_ch3_renders_full_ladder_by_default():
    ch3 = _build_ch3_spawning_rules("generic_mcp")
    # The collapse: the legacy generic_mcp token AND the "generic" floor tool render the
    # SAME universal ladder — both are subagent-shaped, neither has a dedicated block.
    assert _build_ch3_spawning_rules("generic") == ch3
    # PREFERRED — BE-9034 absorption: the rung now OPENS with the DELEGATE-FIRST banner.
    assert "DELEGATE FIRST — you are an ORCHESTRATOR, not the implementer." in ch3
    assert "ANY MCP-CONNECTED AGENT (generic_mcp)" in ch3
    assert "OPTION A — ONE TERMINAL PER AGENT" in ch3
    assert "OPTION B — IN-PROCESS SUBAGENT" in ch3
    # The literal opencode Windows launch line + the cmd /k (not pwsh -NoExit) PATH note.
    assert 'cmd /k opencode --prompt "<prompt>"' in ch3
    assert "the cmd /k wrapper (NOT pwsh -NoExit) so opencode.cmd resolves from PATH." in ch3
    # OS-generic launchers named for macOS / Linux.
    assert "gnome-terminal --working-directory=" in ch3 and "osascript" in ch3
    # OPTION B still names the harness subagent mechanisms.
    assert "a Task tool" in ch3 and "an agent spawner" in ch3
    # FALLBACK — self-adopt, VERIFY-FIRST guard (BE-9034), granted-permission framing.
    assert "[IF YOU CANNOT DO THE ABOVE]" in ch3
    assert "VERIFY FIRST: does your harness have ANY spawn / subagent / delegate mechanism" in ch3
    assert "SELF-ADOPT is the LAST resort" in ch3
    assert "SELF-ADOPT the queued jobs" in ch3
    # Permission is now framed as "subagent mode", never the old "generic_mcp mode"
    # (the phrase wraps across a line in this render, so match its parts).
    assert "GRANTED by your choice" in ch3 and "subagent mode" in ch3
    assert "never applies in" in ch3 and "multi_terminal mode" in ch3
    assert "GRANTED by your choice of generic_mcp mode" not in ch3
    assert "get_job_mission" in ch3 and "complete_job" in ch3
    # FLOOR.
    assert "[FLOOR]" in ch3
    assert "[YOUR PATH — Generic MCP]" in ch3
    # No chat-only exclusion on the default render.
    assert "CANNOT self-adopt a CODE job" not in ch3


def test_generic_mcp_ch3_chat_preset_tunes_self_adopt_to_planning_only():
    chat = reg.get_preset("chat")
    ch3 = _build_ch3_spawning_rules("generic_mcp", preset=chat)
    assert "[YOUR PATH — Chat]" in ch3
    assert "CANNOT self-adopt a CODE job" in ch3
    assert "PLANNING / PM jobs" in ch3
    # Self-adopt stays reachable (planning/PM), still granted-permission framed — as
    # "subagent mode" (the collapse renamed the old "generic_mcp mode" wording).
    assert "SELF-ADOPT" in ch3 and "GRANTED by your choice of subagent mode" in ch3
    assert "GRANTED by your choice of generic_mcp mode" not in ch3
    # The capable (code-inclusive) phrasing is swapped out.
    assert "SELF-ADOPT the queued jobs" not in ch3


def test_generic_mcp_ch3_shell_bearing_preset_keeps_capable_self_adopt():
    # desktop_app has a shell (shared_working_tree) -> self-adopt covers code jobs.
    desktop = reg.get_preset("desktop_app")
    assert desktop.has_shell is True
    ch3 = _build_ch3_spawning_rules("generic_mcp", preset=desktop)
    assert "[YOUR PATH — Desktop App]" in ch3
    assert "SELF-ADOPT the queued jobs" in ch3
    assert "CANNOT self-adopt a CODE job" not in ch3


def test_preset_kwarg_is_inert_for_non_generic_tools():
    # The new preset kwarg must not perturb any other tool's render (byte-identity).
    chat = reg.get_preset("chat")
    for tool in ("multi_terminal", "claude-code", "codex", "gemini"):
        assert _build_ch3_spawning_rules(tool) == _build_ch3_spawning_rules(tool, preset=chat)
