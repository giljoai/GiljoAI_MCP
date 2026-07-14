# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""IMP-5036 task d7d8a5ea (BE-5072) -- 002e sub-service test coverage.

ExecutionPromptBuilderBase was the only Sprint 002e extraction shipped
without any test file. Per IMP-5036 mission DoD: at minimum 1 new unit
test per sub-service that previously had none.

Coverage targets here:
- the base class composes the documented section order
- subclasses must implement platform_name and _build_spawning_section
- git-enabled closeout adds a commit block; disabled omits it
- agent-list section handles empty and non-empty agent lists
- subclass overrides (extra sections, completion section) compose correctly
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from giljo_mcp.prompts.execution_prompt_base import ExecutionPromptBuilderBase


class _MinimalBuilder(ExecutionPromptBuilderBase):
    """Concrete subclass providing the bare minimum needed to call
    build_execution_prompt without NotImplementedError.
    """

    @property
    def platform_name(self) -> str:
        return "Test Platform"

    def _build_spawning_section(self, agent_jobs: list) -> list[str]:
        return ["## Spawning", f"agents={len(agent_jobs)}", ""]


def _make_project(taxonomy_alias: str | None = "BE-5072") -> SimpleNamespace:
    return SimpleNamespace(
        id="proj-001",
        name="Test Project",
        product_id="prod-001",
        taxonomy_alias=taxonomy_alias,
    )


def _make_agent_job(
    name: str = "implementer",
    display_name: str = "impl",
    job_id: str = "job-001",
    mission: str = "Do the thing",
    status: str = "waiting",
):
    return SimpleNamespace(
        agent_name=name,
        agent_display_name=display_name,
        job_id=job_id,
        status=status,
        job=SimpleNamespace(mission=mission),
    )


class TestPlatformNameRequired:
    def test_platform_name_default_raises(self):
        """Direct base instances must raise NotImplementedError on platform_name."""
        with pytest.raises(NotImplementedError, match="platform_name"):
            _ = ExecutionPromptBuilderBase().platform_name


class TestSpawningSectionRequired:
    def test_default_spawning_raises(self):
        """Subclasses must override _build_spawning_section."""

        class _Bare(ExecutionPromptBuilderBase):
            @property
            def platform_name(self) -> str:
                return "Bare"

        with pytest.raises(NotImplementedError, match="_build_spawning_section"):
            _Bare()._build_spawning_section([])


class TestBuildExecutionPromptSectionOrder:
    def test_sections_compose_in_documented_order(self):
        """build_execution_prompt MUST produce sections in the order:
        context_recap -> agent_list -> spawning -> monitoring -> context_refresh
        -> extra -> completion. Order is the API contract for builders that
        override individual sections.
        """
        builder = _MinimalBuilder()
        project = _make_project()
        agent_jobs = [_make_agent_job()]

        prompt = builder.build_execution_prompt(
            orchestrator_id="orch-1",
            project=project,
            agent_jobs=agent_jobs,
            git_enabled=False,
        )

        idx_recap = prompt.index("## Who You Are")
        idx_agents = prompt.index("## Agent Jobs to Execute")
        idx_spawning = prompt.index("## Spawning")
        idx_monitoring = prompt.index("## Monitoring Agent Progress")
        idx_refresh = prompt.index("## Refreshing Your Context")
        idx_completion = prompt.index("## When You're Done")
        assert idx_recap < idx_agents < idx_spawning < idx_monitoring < idx_refresh < idx_completion


class TestAgentList:
    def test_empty_agent_list_emits_placeholder(self):
        builder = _MinimalBuilder()
        prompt = builder.build_execution_prompt("orch-1", _make_project(), [], git_enabled=False)
        assert "(No agents spawned yet" in prompt

    def test_long_mission_is_truncated(self):
        builder = _MinimalBuilder()
        long_mission = "x" * 250
        agent = _make_agent_job(mission=long_mission)
        prompt = builder.build_execution_prompt("orch-1", _make_project(), [agent], git_enabled=False)
        # Truncation is at 100 chars + "..."
        assert "x" * 100 + "..." in prompt
        # Full mission must NOT appear (would mean truncation broke)
        assert long_mission not in prompt


class TestNewAgentSpawnJobFirstRule:
    """INF-6002 regression: the EXECUTION DIRECTIVE must tell the orchestrator
    that a NEW agent (not in the spawned team list — e.g. a deferred
    tester/reviewer) requires spawn_job FIRST, before launching it. Without
    this, orchestrators launch verification agents straight through the
    harness spawn mechanism and they get no MCP record / audit trail.
    """

    def test_directive_carries_spawn_job_first_rule(self):
        builder = _MinimalBuilder()
        prompt = builder.build_execution_prompt("orch-1", _make_project(), [_make_agent_job()], git_enabled=False)
        assert "spawn_job" in prompt
        assert "untracked and unauditable" in prompt
        # The rule must reference the deferred verification case explicitly.
        assert "tester/reviewer" in prompt

    def test_rule_present_even_with_no_agents(self):
        """The rule is unconditional — it renders regardless of the team list."""
        builder = _MinimalBuilder()
        prompt = builder.build_execution_prompt("orch-1", _make_project(), [], git_enabled=False)
        assert "spawn_job` FIRST" in prompt


class TestGitCloseout:
    def test_git_disabled_omits_commit_block(self):
        builder = _MinimalBuilder()
        prompt = builder.build_execution_prompt("orch-1", _make_project(), [], git_enabled=False)
        assert "Git Closeout Commit" not in prompt

    def test_git_enabled_emits_commit_block_with_taxonomy_alias(self):
        builder = _MinimalBuilder()
        project = _make_project(taxonomy_alias="BE-5072")
        prompt = builder.build_execution_prompt("orch-1", project, [], git_enabled=True)
        assert "Git Closeout Commit" in prompt
        assert "closeout(BE-5072)" in prompt

    def test_git_enabled_falls_back_to_project_name_when_no_taxonomy(self):
        builder = _MinimalBuilder()
        project = _make_project(taxonomy_alias=None)
        prompt = builder.build_execution_prompt("orch-1", project, [], git_enabled=True)
        assert "closeout(Test Project)" in prompt


class TestSubclassOverrides:
    def test_extra_sections_inserted_before_completion(self):
        """_build_extra_sections content lands between context_refresh and
        completion (per the build_execution_prompt section list).
        """

        class _WithExtras(_MinimalBuilder):
            def _build_extra_sections(self, orchestrator_id, project, agent_jobs):
                return [["## Custom Extra", "extra content", ""]]

        prompt = _WithExtras().build_execution_prompt("orch-1", _make_project(), [], git_enabled=False)
        idx_extra = prompt.index("## Custom Extra")
        idx_refresh = prompt.index("## Refreshing Your Context")
        idx_completion = prompt.index("## When You're Done")
        assert idx_refresh < idx_extra < idx_completion

    def test_agent_name_line_override_changes_output(self):
        class _CustomAgentLine(_MinimalBuilder):
            def _build_agent_name_line(self, agent) -> str:
                return f"   - Custom: <{agent.agent_name}>"

        prompt = _CustomAgentLine().build_execution_prompt(
            "orch-1", _make_project(), [_make_agent_job(name="implementer")], git_enabled=False
        )
        assert "- Custom: <implementer>" in prompt
        assert "- Agent Name: `implementer`" not in prompt
