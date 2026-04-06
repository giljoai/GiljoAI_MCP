"""Codex CLI execution prompt builder.

Extracted from ThinClientPromptGenerator (Handover 0950g).
Builds implementation-phase prompts for Codex CLI subagent mode.
"""


class CodexPromptBuilder:
    """Builds Codex CLI execution prompts for the implementation phase."""

    def build_execution_prompt(self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False) -> str:
        """Build Codex CLI subagent mode execution prompt (Handover 0838).

        Like Claude Code mode but uses spawn_agent() with 'gil-' prefix on agent names.
        """
        context_recap = [
            "# GiljoAI Implementation Phase - Codex CLI Mode",
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
                        f"   - Agent Name: `{agent.agent_name}` → Codex: `gil-{agent.agent_name}`",
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
            "Each has a unique job_id. In Codex CLI, ALL agent names require the 'gil-' prefix.",
            "",
            *agent_spawn_lines,
        ]

        spawning_section = [
            "## How to Spawn Agents via Codex spawn_agent",
            "",
            "### CRITICAL: Template-First Spawning",
            "The `agent=` parameter loads an INSTALLED agent template from",
            "`~/.codex/agents/gil-{agent_name}.toml`. This template contains the agent's",
            "developer_instructions, model config, and sandbox settings.",
            "The agent ALREADY KNOWS its role — you do NOT re-explain it.",
            "",
            "### NEVER spawn generic workers",
            "- NEVER spawn a generic/default Codex worker and instruct it to 'act as' a GiljoAI agent",
            "- NEVER use agent='worker', agent='implementer', agent='tester', or any unprefixed name",
            "- If a gil-* template is missing, STOP and report the mismatch: do not substitute a generic agent",
            "- DO NOT re-explain the agent's role in instructions= (the template handles this)",
            "- DO NOT override template behavior with lengthy instruction text",
            "",
            "### Always use 'gil-' prefix",
            "The server returns agent_name WITHOUT the prefix. You MUST prepend 'gil-'.",
            "Built-in Codex roles shadow unprefixed names.",
            "",
            "### Spawning Template",
            "```",
            "spawn_agent(",
            '    agent="gil-{agent_name}",  # loads ~/.codex/agents/gil-{agent_name}.toml',
            '    instructions="""',
            "    You are {agent_name} (job_id: {job_id})",
            "    ",
            '    First action: Call mcp__giljo_mcp__get_agent_mission(job_id="{job_id}")',
            "    Note: tenant_key is auto-injected by server from your API key session",
            "    This returns your `mission` and `full_protocol`.",
            "    Follow `full_protocol` for all lifecycle behavior.",
            '    """',
            ")",
            "```",
            "Keep instructions= MINIMAL — only the job_id and mission fetch call above.",
            "",
        ]

        if agent_jobs:
            first = agent_jobs[0]
            spawning_section.extend(
                [
                    "### Example: First Agent",
                    "```",
                    "spawn_agent(",
                    f'    agent="gil-{first.agent_name}",  # gil- prefix!',
                    '    instructions="""',
                    f"    You are {first.agent_name} (job_id: {first.job_id})",
                    "    ",
                    f'    First action: Call mcp__giljo_mcp__get_agent_mission(job_id="{first.job_id}")',
                    "    Note: tenant_key is auto-injected by server from your API key session",
                    "    This returns your `mission` and `full_protocol`.",
                    "    Follow `full_protocol` for all lifecycle behavior.",
                    '    """',
                    ")",
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
