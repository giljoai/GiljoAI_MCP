# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Base class for platform-specific execution prompt builders.

Extracted shared sections from Claude/Codex/Gemini builders (quality-sprint-002e).
Each builder overrides only platform-specific methods:
- platform_name: Header label (e.g., "Claude Code CLI Mode")
- _build_spawning_section: Platform-specific agent invocation syntax
- _build_agent_name_line: How agent names are displayed per platform
- _build_extra_sections: Optional extra sections (e.g., Claude's CLI constraints)
- _build_completion_section: Override if platform needs different completion logic
"""

from __future__ import annotations


class ExecutionPromptBuilderBase:
    """Base class providing shared prompt sections for execution-phase builders.

    Subclasses must implement:
    - platform_name (property): e.g., "Claude Code CLI Mode"
    - _build_spawning_section: Platform-specific spawning template
    - _build_agent_name_line: Agent name formatting per platform

    Subclasses may override:
    - _build_extra_sections: Additional platform-specific sections (default: empty)
    - _build_completion_section: If completion logic differs from base
    - _build_execution_directive_text: Platform-specific wording for the directive
    """

    @property
    def platform_name(self) -> str:
        """Return the platform name for the prompt header."""
        raise NotImplementedError("Subclasses must define platform_name")

    def build_execution_prompt(self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False) -> str:
        """Build the full execution prompt by composing shared and platform-specific sections.

        This is the public interface. All builders produce prompts via this method.

        Args:
            orchestrator_id: Job ID for the orchestrator
            project: Project model (needs .name, .id, .product_id, .taxonomy_alias)
            agent_jobs: List of agent job objects
            git_enabled: Whether git integration is enabled

        Returns:
            Complete execution prompt string
        """
        sections = [
            self._build_context_recap(orchestrator_id, project, agent_jobs),
            self._build_agent_list(orchestrator_id, project, agent_jobs),
            self._build_spawning_section(agent_jobs),
            self._build_monitoring_section(project),
            self._build_context_refresh_section(orchestrator_id),
            *self._build_extra_sections(orchestrator_id, project, agent_jobs),
            self._build_completion_section(orchestrator_id, project, agent_jobs, git_enabled),
        ]
        lines = []
        for section in sections:
            lines.extend(section)
        return "\n".join(lines)

    def _build_context_recap(self, orchestrator_id: str, project, agent_jobs: list) -> list[str]:
        """Build identity, health check, and context recap section (shared)."""
        return [
            f"# GiljoAI Implementation Phase - {self.platform_name}",
            "",
            "## Who You Are",
            f"You are Orchestrator (job_id: {orchestrator_id}) for project '{project.name}'",
            f"Project ID: {project.id}",
            f"Product ID: {project.product_id}",
            "",
            "## MANDATORY STARTUP — both calls, in order, no skipping",
            "",
            "**1. Verify MCP connection:**",
            "```python",
            "mcp__giljo_mcp__health_check()",
            "```",
            'Expected: `{"status": "healthy"}`. If failed, STOP and report error.',
            "",
            "**2. Fetch your execution plan AND operating protocol:**",
            "```python",
            f'mcp__giljo_mcp__get_agent_mission(job_id="{orchestrator_id}")',
            "```",
            "NOT optional — even if you remember staging from a prior session. This call:",
            "  - transitions you `waiting → working` on the server (skipping leaves you invisible on the dashboard)",
            "  - returns `full_protocol` — the coordination loop, blocker handling, closeout ordering. Without it you WILL get closeout wrong.",
            "  - returns `current_team_state` — LIVE agent statuses. Any memory you have from staging is stale.",
            "",
            "**GATE: before invoking any agent below, `full_protocol` text must be in THIS session's context. If not, you skipped step 2. Go back.**",
            "",
            "If `full_protocol` conflicts with anything else in this prompt, `full_protocol` wins.",
            "Note: tenant_key is auto-injected by server from your API key session.",
            "",
            *self._build_execution_plan_details(),
            "## What You've Already Done",
            "In a PREVIOUS session, you completed staging:",
            "- Analyzed project requirements",
            "- Created mission plan",
            f"- Spawned {len(agent_jobs) if agent_jobs else 0} specialist agents",
            "",
            "## Current State",
            "All agent jobs are in waiting status, ready for execution.",
            "Your job now: Spawn and coordinate these agents to complete the project.",
            "---",
            "",
        ]

    def _build_execution_plan_details(self) -> list[str]:
        """Build additional execution plan detail lines.

        ClaudePromptBuilder includes extra detail about plan contents.
        Other builders keep it minimal.
        """
        return [
            "Follow this plan to coordinate agents.",
            "",
        ]

    def _build_agent_list(self, orchestrator_id: str, project, agent_jobs: list) -> list[str]:
        """Build the agent jobs listing section (shared, with per-platform name formatting)."""
        agent_spawn_lines = []
        if agent_jobs:
            for idx, agent in enumerate(agent_jobs, 1):
                mission = getattr(agent.job, "mission", None) or "(No mission assigned)"
                mission_summary = mission[:100] + "..." if len(mission) > 100 else mission

                agent_spawn_lines.extend(
                    [
                        f"**{idx}. {agent.agent_name}**",
                        self._build_agent_name_line(agent),
                        f"   - Agent Type: `{agent.agent_display_name}` (display category)",
                        f"   - Job ID: `{agent.job_id}`",
                        f"   - Status: {agent.status}",
                        f"   - Mission Summary: {mission_summary}",
                        "",
                    ]
                )
        else:
            agent_spawn_lines.append("(No agents spawned yet - use spawn_job() first)")

        return [
            "## Agent Jobs to Execute",
            "",
            *self._build_agent_list_preamble(),
            *agent_spawn_lines,
            "## EXECUTION DIRECTIVE",
            "",
            *self._build_execution_directive_text(),
        ]

    def _build_agent_list_preamble(self) -> list[str]:
        """Preamble text before agent listing. Override for platform-specific wording."""
        return [
            "Below are the specialist agents spawned during staging.",
            "",
        ]

    def _build_agent_name_line(self, agent) -> str:
        """Format the agent name line. Overridden per platform."""
        return f"   - Agent Name: `{agent.agent_name}`"

    def _build_execution_directive_text(self) -> list[str]:
        """Execution directive wording. Override for platform-specific tool references."""
        return [
            "After fetching your mission, you MUST invoke every agent listed above.",
            "Do NOT skip agents. Do NOT summarize the plan and stop. Your job is to",
            "launch each agent, monitor their progress,",
            "and close out the project when all agents are complete.",
            "",
        ]

    def _build_spawning_section(self, agent_jobs: list) -> list[str]:
        """Build platform-specific spawning template. Must be overridden."""
        raise NotImplementedError("Subclasses must implement _build_spawning_section")

    def _build_monitoring_section(self, project) -> list[str]:
        """Build the monitoring section (shared)."""
        return [
            "## Monitoring Agent Progress",
            "",
            "### mcp__giljo_mcp__get_workflow_status()",
            "Check all agent statuses:",
            "```python",
            f'mcp__giljo_mcp__get_workflow_status(project_id="{project.id}")',
            "```",
            "Note: tenant_key is auto-injected by server from your API key session",
            "",
        ]

    def _build_context_refresh_section(self, orchestrator_id: str) -> list[str]:
        """Build the context refresh section (shared)."""
        return [
            "## Refreshing Your Context",
            "",
            "If you need to re-read your orchestrator mission:",
            "```python",
            f'mcp__giljo_mcp__get_orchestrator_instructions(job_id="{orchestrator_id}")',
            "```",
            "",
        ]

    def _build_extra_sections(self, orchestrator_id: str, project, agent_jobs: list) -> list[list[str]]:
        """Return additional platform-specific sections. Default: none."""
        return []

    def _build_git_closeout_lines(self, project, git_enabled: bool) -> list[str]:
        """Build git closeout commit lines (shared helper)."""
        if not git_enabled:
            return []
        tag = getattr(project, "taxonomy_alias", None) or project.name
        return [
            "### Git Closeout Commit",
            "Before calling complete_job, create a closeout commit:",
            "```bash",
            f'git commit --allow-empty -m "closeout({tag}): {project.name}',
            "",
            "Completed: <today YYYY-MM-DD>",
            "Key outcomes:",
            '- <list each concrete outcome>"',
            "```",
            "",
        ]

    def _build_completion_section(
        self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool
    ) -> list[str]:
        """Build the completion section. Override for extended completion (e.g., Claude)."""
        git_closeout_lines = self._build_git_closeout_lines(project, git_enabled)
        return [
            "## When You're Done",
            "",
            "1. Check all agents via mcp__giljo_mcp__get_workflow_status()",
            "2. Ensure all have status='complete'",
            "3. Review final deliverables",
            *git_closeout_lines,
            "### Complete Your Orchestrator Job",
            "```python",
            f'mcp__giljo_mcp__complete_job(job_id="{orchestrator_id}")',
            "```",
            "",
        ]
