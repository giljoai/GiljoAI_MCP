# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Harness-neutral subagent execution prompt builder (BE-9099).

The TRUE fallback for ``execution_mode='subagent'`` when NO concrete detected harness
(claude-code / codex / gemini / antigravity) claims the render — i.e. the ``generic``
floor (undetected clientInfo, or a stored ``generic_mcp`` legacy row) and ``opencode``
(a first-class detectable harness with no dedicated implement builder). It renders the
same shared execution-phase scaffold as the CLI builders, but its spawn section is the
platform-neutral subagent instruction rather than a CLI-specific ``Task()`` / ``@agent``
template.

BE-9099 fix: before this builder existed, ``subagent`` fell through
``_TOOL_TYPE_TO_PROMPT_TYPE.get('generic', ...)`` to the multi_terminal orchestrator
builder and shipped the per-session multi-terminal seed to every subagent orchestrator.
This builder makes ``multi_terminal_orchestrator`` UNREACHABLE from ``subagent`` — it
NEVER emits "PER-SESSION AGENT SEED" / "Open a NEW SESSION".

Edition Scope: CE (the thin-prompt/implement path is CE core; SaaS unaffected).
"""

from __future__ import annotations

from giljo_mcp.platform_registry import (
    GENERIC_HARNESS,
    GENERIC_SUBAGENT_SPAWN_SYNTAX,
    get_harness,
)
from giljo_mcp.prompts.execution_prompt_base import ExecutionPromptBuilderBase


class SubagentPromptBuilder(ExecutionPromptBuilderBase):
    """Builds harness-neutral subagent execution prompts for the implementation phase.

    ``resolved_harness`` is the token from ``effective_harness`` (``generic`` for an
    undetected/floor session, ``opencode`` for a detected opencode session, or a
    legacy declared token). The spawn section is sourced from the registry — a concrete
    harness row's :attr:`Harness.spawn_syntax` (e.g. opencode), else the universal
    :data:`GENERIC_SUBAGENT_SPAWN_SYNTAX`. The prose is NEVER hand-written here, so a
    registry edit is the single source of truth.
    """

    def __init__(self, resolved_harness: str | None = None):
        self._resolved_harness = resolved_harness or GENERIC_HARNESS

    @property
    def platform_name(self) -> str:
        return "Subagent Mode"

    def _spawn_syntax(self) -> str:
        """Resolve the spawn instruction from the registry (BE-9099).

        Mirrors mission_orchestration_builders: a concrete harness row supplies its
        ``spawn_syntax``; the ``generic`` floor (``get_harness`` -> ``None``) supplies
        the universal subagent prose. Single source of truth — no local literals.
        """
        harness = get_harness(self._resolved_harness)
        return harness.spawn_syntax if harness is not None else GENERIC_SUBAGENT_SPAWN_SYNTAX

    def _build_agent_name_line(self, agent) -> str:
        return f"   - Agent Name: `{agent.agent_name}` (used as-is when you spawn it)"

    def _build_execution_directive_text(self) -> list[str]:
        return [
            "After fetching your mission, you MUST invoke every agent listed above.",
            "Do NOT skip agents. Do NOT summarize the plan and stop. Spawn each agent",
            "as a SUBAGENT in THIS session using your harness's own spawn mechanism —",
            "do NOT open a new terminal window or paste a prompt into a separate session.",
            "Monitor their progress and close out the project when all agents are complete.",
            "",
        ]

    def _build_spawning_section(self, agent_jobs: list) -> list[str]:
        """Build the platform-neutral subagent spawn section (BE-9099).

        Renders the registry-sourced spawn instruction — never a CLI-specific template
        and never the multi_terminal per-session seed.
        """
        lines = [
            "## How to Spawn Agents (subagent mode)",
            "",
            self._spawn_syntax(),
            "",
            "For EACH agent below, spawn it and give it this first instruction:",
            "",
            "```",
            "You are {agent_name} (job_id: {job_id})",
            "",
            'First action: Call get_job_mission(job_id="{job_id}")',
            "Note: tenant_key is auto-injected by server from your API key session.",
            "This returns your `mission` and `full_protocol`.",
            "Follow `full_protocol` for all lifecycle behavior.",
            "```",
            "",
        ]

        if agent_jobs:
            first = agent_jobs[0]
            lines.extend(
                [
                    "### Example: First Agent",
                    "```",
                    f"You are {first.agent_name} (job_id: {first.job_id})",
                    "",
                    f'First action: Call get_job_mission(job_id="{first.job_id}")',
                    "Note: tenant_key is auto-injected by server from your API key session.",
                    "This returns your `mission` and `full_protocol`.",
                    "Follow `full_protocol` for all lifecycle behavior.",
                    "```",
                    "",
                ]
            )

        return lines
