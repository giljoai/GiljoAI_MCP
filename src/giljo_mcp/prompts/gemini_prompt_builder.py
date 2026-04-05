"""Gemini CLI execution prompt builder.

Extracted from CodexPromptBuilder (Handover 0950 orchestrator fix).
Builds implementation-phase prompts for Gemini CLI subagent mode.
"""


class GeminiPromptBuilder:
    """Builds Gemini CLI execution prompts for the implementation phase."""

    def build_execution_prompt(self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False) -> str:
        """Build Gemini CLI subagent mode execution prompt (Handover 0838).

        Uses Gemini subagent invocation syntax: @{agent_name} or /agent {agent_name}.
        """
        context_recap = [
            "# GiljoAI Implementation Phase - Gemini CLI Mode",
            "",
            "## FIRST ACTION (MANDATORY)",
            "Before anything else, verify MCP connection:",
            "```python",
            "mcp__giljo_mcp__health_check()",
            "```",
            'Expected: `{"status": "healthy"}` - If failed, STOP and report error',
            "",
            "## Who You Are",
            f"You are Orchestrator (job_id: {orchestrator_id}) for project '{project.name}'",
            f"Project ID: {project.id}",
            f"Product ID: {project.product_id}",
            "",
            "## Your Execution Plan (from Staging)",
            "",
            "Fetch your stored execution plan from staging:",
            "```python",
            f'mcp__giljo_mcp__get_agent_mission(job_id="{orchestrator_id}")',
            "```",
            "Note: tenant_key is auto-injected by server from your API key session",
            "",
            "Follow this plan to coordinate agents.",
            "",
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

        agent_spawn_lines = []
        if agent_jobs:
            for idx, agent in enumerate(agent_jobs, 1):
                mission = getattr(agent.job, "mission", None) or "(No mission assigned)"
                mission_summary = mission[:100] + "..." if len(mission) > 100 else mission
                agent_spawn_lines.extend(
                    [
                        f"**{idx}. {agent.agent_name}**",
                        f"   - Agent Name: `{agent.agent_name}` (used as-is in Gemini)",
                        f"   - Agent Type: `{agent.agent_display_name}` (display category)",
                        f"   - Job ID: `{agent.job_id}`",
                        f"   - Status: {agent.status}",
                        f"   - Mission Summary: {mission_summary}",
                        "",
                    ]
                )
        else:
            agent_spawn_lines.append("(No agents spawned yet - use spawn_agent_job() first)")

        agent_list_section = [
            "## Agent Jobs to Execute",
            "",
            "Below are the specialist agents spawned during staging.",
            "",
            *agent_spawn_lines,
        ]

        spawning_section = [
            "## How to Spawn Agents in Gemini CLI",
            "",
            "### Spawning Template",
            "Use subagent invocation with the agent_name directly:",
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
            "Or equivalently:",
            "```",
            "/agent {agent_name}",
            "<instructions as above>",
            "```",
            "",
        ]

        if agent_jobs:
            first = agent_jobs[0]
            spawning_section.extend(
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

        monitoring_section = [
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

        context_refresh_section = [
            "## Refreshing Your Context",
            "",
            "If you need to re-read your orchestrator mission:",
            "```python",
            f'mcp__giljo_mcp__get_orchestrator_instructions(job_id="{orchestrator_id}")',
            "```",
            "",
        ]

        git_closeout_lines = []
        if git_enabled:
            tag = getattr(project, "taxonomy_alias", None) or project.name
            git_closeout_lines = [
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

        completion_section = [
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

        all_sections = (
            context_recap
            + agent_list_section
            + spawning_section
            + monitoring_section
            + context_refresh_section
            + completion_section
        )
        return "\n".join(all_sections)
