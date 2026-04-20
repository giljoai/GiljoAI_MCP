# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Gemini CLI execution prompt builder.

Extracted from CodexPromptBuilder (Handover 0950 orchestrator fix).
Refactored to inherit from ExecutionPromptBuilderBase (quality-sprint-002e).
"""

from giljo_mcp.prompts.execution_prompt_base import ExecutionPromptBuilderBase


class GeminiPromptBuilder(ExecutionPromptBuilderBase):
    """Builds Gemini CLI execution prompts for the implementation phase."""

    @property
    def platform_name(self) -> str:
        return "Gemini CLI Mode"

    def _build_agent_name_line(self, agent) -> str:
        return f"   - Agent Name: `{agent.agent_name}` (used as-is in Gemini)"

    def _build_execution_directive_text(self) -> list[str]:
        return [
            "After fetching your mission, you MUST invoke every agent listed above.",
            "Do NOT skip agents. Do NOT summarize the plan and stop. Your job is to",
            "invoke each agent using `@{agent_name}` as shown below, monitor their progress,",
            "and close out the project when all agents are complete.",
            "",
            "**Preferred mode: background execution.** If Gemini CLI supports running",
            "subagents in the background or asynchronously, use that mode for independent",
            "agents so the user can continue interacting. Poll progress via",
            "`get_workflow_status()`. Only block on an agent when the next agent depends",
            "on its output.",
            "",
        ]

    def _build_spawning_section(self, agent_jobs: list) -> list[str]:
        """Build Gemini @agent invocation template section."""
        lines = [
            "## How to Invoke Agents in Gemini CLI",
            "",
            "### Invocation Template",
            "Invoke each agent using `@{agent_name}` with the instructions below.",
            "The agents already exist \u2014 you are invoking them, not creating them.",
            "",
            "```",
            "@{agent_name}",
            "You are {agent_name} (job_id: {job_id})",
            "",
            'First action: Call mcp__giljo_mcp__get_agent_mission(job_id="{job_id}")',
            "Note: tenant_key is auto-injected by server from your API key session",
            "This returns your `mission` and `full_protocol`.",
            "Follow `full_protocol` for all lifecycle behavior.",
            "```",
            "",
            "Or equivalently: `/agent {agent_name}` with the same instructions.",
            "",
        ]

        if agent_jobs:
            first = agent_jobs[0]
            lines.extend(
                [
                    "### Example: First Agent",
                    "```",
                    f"@{first.agent_name}",
                    f"You are {first.agent_name} (job_id: {first.job_id})",
                    "",
                    f'First action: Call mcp__giljo_mcp__get_agent_mission(job_id="{first.job_id}")',
                    "Note: tenant_key is auto-injected by server from your API key session",
                    "This returns your `mission` and `full_protocol`.",
                    "Follow `full_protocol` for all lifecycle behavior.",
                    "```",
                    "",
                ]
            )

        return lines
