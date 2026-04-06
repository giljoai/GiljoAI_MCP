"""Multi-terminal (platform-agnostic) orchestrator prompt builder.

Extracted from CodexPromptBuilder (Handover 0950 orchestrator fix).
Builds the thinnest possible implementation prompt — identity + single
instruction to call get_agent_mission(). All behavioral protocol lives
server-side.
"""


class MultiTerminalPromptBuilder:
    """Builds platform-agnostic multi-terminal orchestrator prompts."""

    def build_execution_prompt(self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False) -> str:
        """Build multi-terminal orchestrator implementation prompt (Handover 0830).

        Genuinely thin: identity + single instruction to call get_agent_mission().
        All behavioral protocol, team state, and tool catalog live server-side
        in get_agent_mission() response — never baked into the prompt.
        """
        lines = [
            "# GiljoAI Implementation Phase - Orchestrator",
            "",
            "## FIRST ACTION (MANDATORY)",
            "Verify MCP connection:",
            "```",
            "mcp__giljo_mcp__health_check()",
            "```",
            "",
            f"You are the ORCHESTRATOR for project '{project.name}'.",
            f"Job ID: `{orchestrator_id}` | Project ID: `{project.id}`",
            "",
            "Call `get_agent_mission` to receive your current team state and operating protocol:",
            "```",
            f'mcp__giljo_mcp__get_agent_mission(job_id="{orchestrator_id}")',
            "```",
        ]
        return "\n".join(lines)
