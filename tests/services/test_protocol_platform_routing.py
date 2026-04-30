# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""
Tests for platform-detect routing in protocol generation (HO1020 / Wave 2 Item 2).

Background
----------
The bug: ``mission_service._exec_mode_to_tool.get(project_exec_mode, "claude-code")``
silently mapped any unknown execution_mode -- including the model default
``multi_terminal`` -- to ``claude-code``. The downstream worker protocol then injected
``Task(subagent_type=...)`` syntax into agents that have no Claude Code Task tool
available, causing them to fail at startup.

Fix shape
---------
1. Map ``multi_terminal`` to itself in the dict (route to existing generic branch).
2. Flip ALL fallback defaults from ``"claude-code"`` to ``"multi_terminal"`` so an
   unknown execution_mode fails-safe to the platform-neutral MCP-only protocol
   instead of dangerously injecting Task() syntax.
3. Reframe the generic branch around "each terminal is a job order" semantics.

Sites covered
-------------
- ``src/giljo_mcp/services/mission_service.py`` (line ~527)
- ``src/giljo_mcp/services/mission_orchestration_service.py`` (line ~475)
- ``src/giljo_mcp/services/protocol_sections/chapters_reference.py`` (lines 11, 286)
- ``src/giljo_mcp/services/protocol_sections/agent_protocol.py`` (line ~305)
"""

from __future__ import annotations

from giljo_mcp.services.protocol_sections.agent_protocol import _generate_agent_protocol
from giljo_mcp.services.protocol_sections.chapters_reference import (
    _REACTIVATION_SPAWN_BLOCKS,
    _build_ch3_spawning_rules,
    _build_reactivation_spawn_block,
)


# ---- Helpers --------------------------------------------------------------


def _render_orchestrator_protocol(execution_mode: str) -> str:
    """Render the orchestrator-flavor agent protocol for a given execution_mode.

    Mirrors the fork in ``_generate_agent_protocol`` for ``job_type == 'orchestrator'``,
    which selects the constellation wake-pattern that historically leaked Task() syntax
    when execution_mode was misclassified as 'claude-code'.
    """
    return _generate_agent_protocol(
        job_id="job-test",
        tenant_key="tk_test",
        agent_name="orchestrator",
        agent_id="exec-test",
        execution_mode=execution_mode,
        git_integration_enabled=False,
        job_type="orchestrator",
        tool=execution_mode if execution_mode in ("codex", "gemini", "claude-code") else "multi_terminal",
    )


# ---- Worker / orchestrator protocol rendering ----------------------------


class TestExecutionModeRouting:
    """End-to-end protocol rendering must follow execution_mode, not silently
    coerce to claude-code on unknown values."""

    def test_protocol_renders_task_syntax_for_claude_code_cli(self):
        """claude-code execution_mode must still render Task()/subagent_type syntax."""
        ch3 = _build_ch3_spawning_rules(tool="claude-code")
        assert "Task(subagent_type=" in ch3
        assert "CLAUDE CODE CLI" in ch3

    def test_protocol_renders_no_task_syntax_for_multi_terminal(self):
        """multi_terminal must NOT render platform-specific spawn invocation forms.
        HO1025: bare `Task()` / `spawn_agent()` may appear in the cross-platform
        `phase` educational block; gate the actual invocation forms instead."""
        ch3 = _build_ch3_spawning_rules(tool="multi_terminal")
        assert "Task(subagent_type=" not in ch3
        assert "spawn_agent(agent=" not in ch3
        assert "ANY MCP-CONNECTED AGENT" in ch3

    def test_protocol_falls_back_to_generic_for_unknown_mode(self):
        """An unrecognized tool (future mode, typo) must fall back to the generic
        platform-neutral block -- NOT to claude-code."""
        ch3 = _build_ch3_spawning_rules(tool="some_future_mode")
        # Generic else branch signature
        assert "ANY MCP-CONNECTED AGENT" in ch3
        # And NOT the claude-code block
        assert "Task(subagent_type=" not in ch3
        assert "CLAUDE CODE CLI" not in ch3

    def test_protocol_renders_codex_syntax_for_codex_cli(self):
        """Regression guard: codex stays on its own native spawn syntax."""
        ch3 = _build_ch3_spawning_rules(tool="codex")
        assert "spawn_agent(" in ch3
        assert "gil-" in ch3
        assert "CODEX CLI" in ch3
        assert "Task(subagent_type=" not in ch3

    def test_protocol_renders_gemini_syntax_for_gemini_cli(self):
        """Regression guard: gemini stays on @-syntax. HO1025: bare
        `spawn_agent()` may appear in the cross-platform `phase` educational
        block; gate the codex-specific invocation form instead."""
        ch3 = _build_ch3_spawning_rules(tool="gemini")
        assert "@" in ch3
        assert "GEMINI CLI" in ch3
        assert "Task(subagent_type=" not in ch3
        assert "spawn_agent(agent=" not in ch3


# ---- Reactivation spawn block fallback -----------------------------------


class TestReactivationSpawnBlockFallback:
    """``_build_reactivation_spawn_block`` must fail-safe to multi_terminal,
    not to claude-code, when the requested tool is unknown."""

    def test_reactivation_spawn_block_default_for_unknown_tool(self):
        block = _build_reactivation_spawn_block(tool="unknown")
        assert block == _REACTIVATION_SPAWN_BLOCKS["multi_terminal"]
        assert "Task(subagent_type=" not in block

    def test_reactivation_spawn_block_for_known_claude_code(self):
        """Regression guard: explicit claude-code still returns its native block."""
        block = _build_reactivation_spawn_block(tool="claude-code")
        assert block == _REACTIVATION_SPAWN_BLOCKS["claude-code"]
        assert "Task(subagent_type=" in block

    def test_reactivation_spawn_block_for_multi_terminal(self):
        """multi_terminal exists in the dict and renders platform-neutral instructions."""
        block = _build_reactivation_spawn_block(tool="multi_terminal")
        assert "Task(subagent_type=" not in block
        assert "spawn_agent(" not in block
        # Platform-neutral wording
        assert "Open a new terminal" in block or "new terminal" in block.lower()


# ---- Generic-branch prose: "each terminal is a job order" framing --------


class TestGenericBranchJobOrderFraming:
    """The multi_terminal generic branch is reworded around the user's framing:
    each terminal is one job order, cross-agent coordination is MCP-only."""

    def test_generic_branch_uses_job_order_framing(self):
        ch3 = _build_ch3_spawning_rules(tool="multi_terminal")
        assert "job order" in ch3.lower()

    def test_generic_branch_is_explicit_about_mcp_only_coordination(self):
        ch3 = _build_ch3_spawning_rules(tool="multi_terminal")
        # The generic branch must reference the MCP coordination tools by name.
        assert "spawn_job" in ch3
        assert "send_message" in ch3

    def test_generic_branch_includes_predecessor_handling_guidance(self):
        """multi_terminal CH3 must mention predecessor_job_id so the orchestrator
        knows it can pass a previous agent's job_id when a successor needs to
        read prior output. HO1022: prose collapsed from 2 multi-paragraph blocks
        (CHAINING PHASES + REACTIVATION) into a single PHASE HANDOFF sentence.
        Server now auto-detects chain vs replacement from predecessor status."""
        ch3 = _build_ch3_spawning_rules(tool="multi_terminal")
        assert "predecessor_job_id" in ch3
        assert "PHASE HANDOFF" in ch3

    def test_phase_parameter_block_renders_in_all_branches(self):
        """HO1025: CH3 PARAMETER REQUIREMENTS now documents the `phase` field
        explicitly. Concept (same phase = parallel, higher = sequential) is
        mode-agnostic; enforcement differs (multi_terminal: server/dashboard
        groups by phase; subagent: orchestrator manages ordering inline). The
        block must render in every branch so test-agent friction #4/#5 are
        addressed regardless of which mode the project picks."""
        for tool in ("multi_terminal", "claude-code", "codex", "gemini"):
            ch3 = _build_ch3_spawning_rules(tool=tool)
            assert "── phase (optional" in ch3, f"phase block missing in {tool} branch"
            assert "Same phase number" in ch3
            assert "Higher phase number" in ch3

    def test_predecessor_guidance_is_multi_terminal_only(self):
        """The multi_terminal-specific PHASE HANDOFF prose explaining the
        predecessor preamble injection is gated to the multi_terminal branch.
        Subagent branches still mention predecessor_job_id only in the brief
        cross-platform `phase` educational tip (HO1025), not in the dedicated
        PHASE HANDOFF block. Server silently skips preamble injection in
        subagent modes; orchestrator splices predecessor findings inline using
        its CLI's native return value. HO1022 removed the per-subagent
        PREDECESSOR PARAMETER USAGE blocks since they were teaching the
        orchestrator about a server-internal decision."""
        for tool in ("claude-code", "codex", "gemini"):
            ch3 = _build_ch3_spawning_rules(tool=tool)
            assert "PHASE HANDOFF:" not in ch3, (
                f"{tool} branch must not contain the multi_terminal-specific "
                f"PHASE HANDOFF block -- server skips preamble injection in "
                f"subagent modes"
            )


# ---- Agent protocol signature defaults -----------------------------------


class TestAgentProtocolDefaults:
    """The fail-safe default for ``tool`` must be ``multi_terminal``, not
    ``claude-code``, on every protocol entry point."""

    def test_generate_agent_protocol_default_is_multi_terminal(self):
        """When no execution_mode/tool is supplied, the rendered protocol must
        not leak Task() syntax into the agent's instructions."""
        # Worker protocol path -- defaults must NOT inject Task() syntax.
        protocol = _generate_agent_protocol(
            job_id="job-test",
            tenant_key="tk_test",
            agent_name="implementer",
            agent_id="exec-test",
            # No execution_mode or tool kwargs -- exercise defaults.
            git_integration_enabled=False,
            job_type="agent",
        )
        # Workers do not render CH3 spawning rules at all; they get the 5-phase
        # lifecycle. The default tool flows into _build_conditional_blocks
        # (gil_add command). The fail-safe is that no CLI-specific spawn syntax
        # ever appears in a worker mission rendered with default args.
        assert "Task(subagent_type=" not in protocol
        assert "spawn_agent(agent=" not in protocol

    def test_orchestrator_protocol_default_does_not_leak_task_syntax(self):
        """Orchestrator protocol with a multi_terminal execution_mode must use
        the multi-terminal constellation wake-pattern, NOT claude-code's."""
        protocol = _render_orchestrator_protocol(execution_mode="multi_terminal")
        assert "Task() processes" not in protocol
        assert "spawn_agent() processes" not in protocol


# ---- Service-layer dict mappings (mission_service / mission_orchestration) ----


class TestServiceLayerExecModeMapping:
    """The two parallel dict-fallback sites must agree on the same fail-safe
    default and the same mapping for multi_terminal.

    Implemented as source-text assertions against the service files because
    the bug is a single-character literal (``"claude-code"`` vs
    ``"multi_terminal"``) inside an inline ``.get()`` call. A live render
    test would only catch one half of the regression; the source-text guard
    catches anyone re-introducing either half.
    """

    def test_mission_service_routes_multi_terminal_to_itself(self):
        """The exec_mode_to_tool dict in mission_service must include
        ``"multi_terminal": "multi_terminal"`` so it is NOT silently
        re-mapped to ``claude-code`` by the .get() fallback."""
        from pathlib import Path

        src = Path("src/giljo_mcp/services/mission_service.py").read_text(encoding="utf-8")
        # The dict must have an explicit multi_terminal entry.
        assert '"multi_terminal": "multi_terminal"' in src

    def test_mission_service_fallback_default_is_multi_terminal(self):
        from pathlib import Path

        src = Path("src/giljo_mcp/services/mission_service.py").read_text(encoding="utf-8")
        # No remaining .get(..., "claude-code") calls in the exec-mode dict block.
        assert '_exec_mode_to_tool.get(project_exec_mode, "claude-code")' not in src
        assert '_exec_mode_to_tool.get(project_exec_mode, "multi_terminal")' in src

    def test_mission_orchestration_service_fallback_default_is_multi_terminal(self):
        from pathlib import Path

        src = Path("src/giljo_mcp/services/mission_orchestration_service.py").read_text(encoding="utf-8")
        assert 'execution_mode_to_tool.get(execution_mode, "claude-code")' not in src
        assert 'execution_mode_to_tool.get(execution_mode, "multi_terminal")' in src


# ---- Function signature defaults flipped to multi_terminal ---------------


class TestSignatureDefaults:
    """All protocol entry points whose ``tool`` parameter has a default must
    default to ``multi_terminal`` -- the fail-safe option."""

    def test_chapters_reference_ch3_default_is_multi_terminal(self):
        import inspect

        sig = inspect.signature(_build_ch3_spawning_rules)
        assert sig.parameters["tool"].default == "multi_terminal"

    def test_generate_agent_protocol_default_tool_is_multi_terminal(self):
        import inspect

        sig = inspect.signature(_generate_agent_protocol)
        assert sig.parameters["tool"].default == "multi_terminal"
