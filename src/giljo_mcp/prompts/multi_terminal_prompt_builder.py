# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Multi-terminal (platform-agnostic) orchestrator prompt builder.

Extracted from CodexPromptBuilder (Handover 0950 orchestrator fix).
Builds the thinnest possible implementation prompt — identity + single
instruction to call get_agent_mission(). All behavioral protocol lives
server-side.
"""

from giljo_mcp.prompts._canonical_tool_list import render_toolsearch_call_one_line


def _project_title(project) -> str:
    has_taxonomy = bool(getattr(project, "project_type_id", None) or getattr(project, "series_number", None))
    if has_taxonomy:
        return f"{project.taxonomy_alias} {project.name}"
    return project.name


class MultiTerminalPromptBuilder:
    """Builds platform-agnostic multi-terminal orchestrator prompts."""

    def build_execution_prompt(
        self,
        orchestrator_id: str,
        project,
        agent_jobs: list,
        git_enabled: bool = False,
        tool: str = "multi_terminal",
    ) -> str:
        """Build multi-terminal orchestrator implementation prompt (Handover 0830).

        Genuinely thin: identity + single instruction to call get_agent_mission().
        All behavioral protocol, team state, and tool catalog live server-side
        in get_agent_mission() response — never baked into the prompt.

        CE-0033 Task 5: ``tool`` lets callers opt into a Step 0 ToolSearch
        bootstrap when the operator is running a Claude-Code-style harness
        that defers MCP tool schemas. Default ``"multi_terminal"`` keeps the
        prompt unchanged for platform-neutral / Codex / Gemini operators —
        the bootstrap is noise there.
        """
        lines = [
            "# GiljoAI Implementation Phase - Orchestrator",
            "",
        ]
        if tool == "claude-code":
            lines.extend(
                [
                    "## STEP 0: TOOLSEARCH BOOTSTRAP (Claude Code only — first action)",
                    "",
                    "Claude Code defers MCP tool schemas behind `ToolSearch`. Before health_check,",
                    "fire this single call to load the canonical orchestrator tool set:",
                    "```",
                    render_toolsearch_call_one_line(),
                    "```",
                    "",
                ]
            )
        lines.extend(
            [
                "## FIRST ACTION (MANDATORY)",
                "Verify MCP connection:",
                "```",
                "mcp__giljo_mcp__health_check()",
                "```",
                "",
                f"You are the ORCHESTRATOR for project '{_project_title(project)}'.",
                f"Job ID: `{orchestrator_id}` | Project ID: `{project.id}`",
                "",
                "Call `get_agent_mission` to receive your current team state and operating protocol:",
                "```",
                f'mcp__giljo_mcp__get_agent_mission(job_id="{orchestrator_id}")',
                "```",
            ]
        )
        return "\n".join(lines)
