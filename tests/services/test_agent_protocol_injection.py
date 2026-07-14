# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Agent Protocol Injection Tests - Handover 0497d

TDD tests for Phase 4 conditional blocks in _generate_agent_protocol():
- /giljo guidance (multi-terminal only)
- Git commit instructions (git_integration enabled only)
- 2x2 matrix: (execution_mode x git_integration)
- Regression: Phases 1-3 and 5 unchanged regardless of toggles
"""

import pytest


def _gen_protocol(
    execution_mode: str = "multi_terminal",
    git_integration_enabled: bool = False,
    job_type: str = "agent",
) -> str:
    """Helper to call _generate_agent_protocol with test defaults."""
    from giljo_mcp.services.protocol_builder import _generate_agent_protocol

    return _generate_agent_protocol(
        job_id="test-job-id",
        tenant_key="tk_test",
        agent_name="backend-engineer",
        agent_id="test-agent-id",
        execution_mode=execution_mode,
        git_integration_enabled=git_integration_enabled,
        job_type=job_type,
    )


# ============================================================================
# GIT COMMIT INJECTION TESTS
# ============================================================================


class TestGitCommitInjection:
    """Git commit instruction in Phase 4 based on git_integration toggle."""

    def test_git_enabled_includes_commit_instruction(self):
        """When git_integration=True, Phase 4 includes git commit block."""
        protocol = _gen_protocol(git_integration_enabled=True)
        assert "git add" in protocol.lower() or "Git Commit" in protocol
        assert "commit" in protocol.lower()

    def test_git_disabled_excludes_commit_instruction(self):
        """When git_integration=False, Phase 4 does NOT include git commit block."""
        protocol = _gen_protocol(git_integration_enabled=False)
        assert "Git Commit" not in protocol
        assert "git add" not in protocol

    def test_git_enabled_mentions_commits_in_result(self):
        """Git commit block instructs agent to include commit hash in result."""
        protocol = _gen_protocol(git_integration_enabled=True)
        assert "commits" in protocol


# ============================================================================
# /GILJO INJECTION TESTS
# ============================================================================


class TestGiljoInjection:
    """Giljo guidance in Phase 4 based on execution_mode."""

    def test_multi_terminal_includes_giljo(self):
        """When execution_mode=multi_terminal, Phase 4 includes /giljo guidance."""
        protocol = _gen_protocol(execution_mode="multi_terminal")
        assert "/giljo" in protocol

    def test_cli_mode_excludes_giljo(self):
        """When execution_mode=claude_code_cli, Phase 4 does NOT include /giljo."""
        protocol = _gen_protocol(execution_mode="claude_code_cli")
        assert "/giljo" not in protocol

    def test_multi_terminal_mentions_user_guidance(self):
        """Multi-terminal /giljo block includes user-facing language."""
        protocol = _gen_protocol(execution_mode="multi_terminal")
        assert "technical debt" in protocol.lower() or "follow-up" in protocol.lower()


# ============================================================================
# 2x2 COMBINATION TESTS
# ============================================================================


class TestCombinedInjections:
    """Both toggles together in various combinations."""

    def test_both_enabled(self):
        """Multi-terminal + git enabled: both blocks present."""
        protocol = _gen_protocol(execution_mode="multi_terminal", git_integration_enabled=True)
        assert "/giljo" in protocol
        assert "Git Commit" in protocol

    def test_both_disabled(self):
        """CLI mode + git disabled: neither block present."""
        protocol = _gen_protocol(execution_mode="claude_code_cli", git_integration_enabled=False)
        assert "/giljo" not in protocol
        assert "Git Commit" not in protocol

    def test_git_only(self):
        """CLI mode + git enabled: git block present, /giljo absent."""
        protocol = _gen_protocol(execution_mode="claude_code_cli", git_integration_enabled=True)
        assert "Git Commit" in protocol
        assert "/giljo" not in protocol

    def test_giljo_only(self):
        """Multi-terminal + git disabled: /giljo present, git block absent."""
        protocol = _gen_protocol(execution_mode="multi_terminal", git_integration_enabled=False)
        assert "/giljo" in protocol
        assert "Git Commit" not in protocol


# ============================================================================
# REGRESSION TESTS
# ============================================================================


class TestProtocolRegression:
    """Phases 1-3 and 5 must be unchanged regardless of toggle settings."""

    @pytest.mark.parametrize(
        ("execution_mode", "git_enabled"),
        [
            ("multi_terminal", True),
            ("multi_terminal", False),
            ("claude_code_cli", True),
            ("claude_code_cli", False),
        ],
    )
    def test_phase1_always_present(self, execution_mode, git_enabled):
        """Phase 1 STARTUP is always present regardless of toggles."""
        protocol = _gen_protocol(execution_mode=execution_mode, git_integration_enabled=git_enabled)
        assert "Phase 1: STARTUP" in protocol
        assert "get_job_mission" in protocol

    @pytest.mark.parametrize(
        ("execution_mode", "git_enabled"),
        [
            ("multi_terminal", True),
            ("multi_terminal", False),
            ("claude_code_cli", True),
            ("claude_code_cli", False),
        ],
    )
    def test_phase2_always_present(self, execution_mode, git_enabled):
        """Phase 2 EXECUTION is always present regardless of toggles."""
        protocol = _gen_protocol(execution_mode=execution_mode, git_integration_enabled=git_enabled)
        assert "Phase 2: EXECUTION" in protocol

    @pytest.mark.parametrize(
        ("execution_mode", "git_enabled"),
        [
            ("multi_terminal", True),
            ("multi_terminal", False),
            ("claude_code_cli", True),
            ("claude_code_cli", False),
        ],
    )
    def test_phase3_always_present(self, execution_mode, git_enabled):
        """Phase 3 PROGRESS REPORTING is always present regardless of toggles."""
        protocol = _gen_protocol(execution_mode=execution_mode, git_integration_enabled=git_enabled)
        assert "Phase 3: PROGRESS REPORTING" in protocol
        assert "report_progress" in protocol

    @pytest.mark.parametrize(
        ("execution_mode", "git_enabled"),
        [
            ("multi_terminal", True),
            ("multi_terminal", False),
            ("claude_code_cli", True),
            ("claude_code_cli", False),
        ],
    )
    def test_phase4_core_always_present(self, execution_mode, git_enabled):
        """Phase 4 COMPLETION core is always present regardless of toggles."""
        protocol = _gen_protocol(execution_mode=execution_mode, git_integration_enabled=git_enabled)
        assert "Phase 4: COMPLETION" in protocol
        assert "complete_job" in protocol

    @pytest.mark.parametrize(
        ("execution_mode", "git_enabled"),
        [
            ("multi_terminal", True),
            ("multi_terminal", False),
            ("claude_code_cli", True),
            ("claude_code_cli", False),
        ],
    )
    def test_phase5_always_present(self, execution_mode, git_enabled):
        """Phase 5 ERROR HANDLING is always present regardless of toggles."""
        protocol = _gen_protocol(execution_mode=execution_mode, git_integration_enabled=git_enabled)
        assert "Phase 5: ERROR HANDLING" in protocol
        assert "set_agent_status" in protocol


class TestSpawnJobBeforeLaunchMandate:
    """BE-6010: orchestrator protocol must mandate spawn_job BEFORE launching a verification agent.

    Regression guard for the INF-6002 recurrence: subagent-mode orchestrators launched
    tester/reviewer agents via the Agent/Task tool without a preceding spawn_job, losing
    the MCP job_id, TODOs, recorded verdict, and dashboard audit trail. The mandate lives
    in the mode-independent orchestrator protocol body, so the same assertion holds for
    both execution modes.
    """

    @pytest.mark.parametrize("execution_mode", ["claude_code_cli", "multi_terminal"])
    def test_spawn_job_before_launch_mandate_present(self, execution_mode):
        """spawn_job-FIRST sequence + explicit prohibition appear in both execution modes."""
        protocol = _gen_protocol(execution_mode=execution_mode, job_type="orchestrator")
        assert "without a preceding spawn_job" in protocol
        assert "spawn_job" in protocol and "FIRST" in protocol

    @pytest.mark.parametrize("execution_mode", ["claude_code_cli", "multi_terminal"])
    def test_launch_directly_phrasing_removed(self, execution_mode):
        """The root-cause 'launch directly' phrasing must no longer appear in the spawn block."""
        protocol = _gen_protocol(execution_mode=execution_mode, job_type="orchestrator")
        assert "In subagent mode: launch directly." not in protocol


# ============================================================================
# ORCHESTRATOR TODOWRITE SCOPING TESTS
# ============================================================================


class TestOrchestratorTodoWriteScoping:
    """Phase 1 Step 4 TodoWrite scope varies by job_type."""

    def test_orchestrator_todowrite_scoped_to_coordination(self):
        """When job_type=orchestrator, protocol is the 3-phase coordination lifecycle."""
        protocol = _gen_protocol(job_type="orchestrator")
        assert "Orchestrator Coordination Protocol (3 Phases)" in protocol
        assert "ORCHESTRATOR CONSTRAINTS" in protocol

    def test_agent_todowrite_unchanged(self):
        """Default job_type=agent produces original agent-scoped TodoWrite text."""
        protocol = _gen_protocol(job_type="agent")
        assert "Break mission into 3-7" in protocol

    def test_job_type_default_backward_compat(self):
        """Omitting job_type produces same output as job_type='agent'."""
        protocol_default = _gen_protocol()
        protocol_agent = _gen_protocol(job_type="agent")
        assert protocol_default == protocol_agent
