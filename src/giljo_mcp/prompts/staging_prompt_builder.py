# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Staging and thin-prompt builders.

Extracted from ThinClientPromptGenerator (Handover 0950g).
Builds staging-phase prompts and mission regeneration logic.
"""

import logging
from typing import Any

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import Product, Project


logger = logging.getLogger(__name__)


class StagingPromptBuilder:
    """Builds staging-phase prompts and handles mission regeneration."""

    def build_thin_prompt(
        self,
        orchestrator_id: str,
        agent_id: str,
        project_id: str,
        project: Any,
        product: Any,
        tool: str,
        field_toggles: dict[str, bool],
        depth_config: dict[str, Any],
        user_id: str | None = None,
    ) -> str:
        """Generate thin prompt listing available MCP tools (Handover 0315).

        Returns ~600 token prompt (vs ~3500 in fat prompt) that references MCP tools
        for on-demand context fetching.

        Args:
            orchestrator_id: Job ID (WHAT - work order UUID)
            agent_id: Agent execution ID (WHO - executor UUID, for identity tracking only)
            project_id: Project UUID
            project: Project model
            product: Product model
            tool: AI coding agent (claude-code, codex, gemini, universal)
            field_toggles: User field toggle config (True=enabled, False=disabled)
            depth_config: User depth configuration
            user_id: Optional user ID

        Returns:
            Thin prompt with MCP tool references
        """
        config = get_config()
        mcp_host = config.get_nested("services.external_host") or config.server.api_host
        mcp_port = config.server.api_port
        mcp_proto = "https" if config.get_nested("features.ssl_enabled", default=False) else "http"
        mcp_url = f"{mcp_proto}://{mcp_host}:{mcp_port}"

        api_key_configured = bool(config.server.api_key)
        auth_note = "(authenticated)" if api_key_configured else "(check config.yaml for API key)"

        prompt = f"""I am Orchestrator for GiljoAI Project "{project.name}".

IDENTITY:
- Orchestrator Agent ID: {agent_id}
- Job ID: {orchestrator_id}
- Project ID: {project_id}

MCP CONNECTION:
- Server URL: {mcp_url}
- Tool Prefix: mcp__giljo_mcp__
- Auth Status: {auth_note}

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)
You are STAGING the project by creating a mission plan. You will NOT execute the work yourself.
Your job is to: 1) Analyze requirements, 2) Create mission plan, 3) Assign work to specialist agents.

PROJECT CONTEXT (Inline - ~200 tokens):
- Name: {project.name}
- Description: {project.description or "(No description provided)"}
- Mission: {project.mission or "(Mission will be created by you)"}

WORKFLOW:
1. Verify MCP connection: mcp__giljo_mcp__health_check()
   → Expected: {{"status": "healthy", "database": "connected"}}
   → If failed: STOP and report error - do NOT proceed
2. Fetch complete context: mcp__giljo_mcp__get_orchestrator_instructions('{orchestrator_id}')
   → Returns configured context (vision, tech stack, architecture, memory, git history, templates)
   → User toggle/depth configuration automatically applied server-side
   → Depth configuration (chunking, commit count, etc.) pre-configured
   → Note: tenant_key auto-injected by server from your API key session
3. Create condensed mission plan from fetched context
4. Persist mission: mcp__giljo_mcp__update_project_mission('{project_id}', mission)
5. Spawn specialist agents: mcp__giljo_mcp__spawn_agent_job(agent_display_name, agent_name, mission, '{project_id}')
   → SAVE each response's agent_id UUID - needed for UUID-based messaging
6. Monitor: mcp__giljo_mcp__get_workflow_status('{project_id}')
7. Signal complete: mcp__giljo_mcp__send_message(to_agents=['all'], content='STAGING_COMPLETE: Mission created, N agents spawned: [list names]', project_id='{project_id}', message_type='broadcast')
   → This broadcast enables the Implement button in UI (REQUIRED)

Claude Code: Use TodoWrite tool to track workflow progress.

MESSAGING RULE: Always use agent_id UUIDs in send_message(to_agents=[...]).
Each spawn_agent_job() returns an agent_id UUID. Never use display names in to_agents.

CRITICAL DISTINCTIONS:
- Project.description = User-written requirements (already provided above)
- Project.mission = YOUR OUTPUT (condensed execution plan you CREATE in Step 2)
- Agent jobs = Specialist agents who will DO THE ACTUAL WORK (you coordinate them)

MCP CORE TOOLS (Always Available - tenant_key auto-injected by server):
✓ mcp__giljo_mcp__health_check() - Verify MCP connection
✓ mcp__giljo_mcp__get_orchestrator_instructions('{orchestrator_id}') - Fetch complete prioritized context
✓ mcp__giljo_mcp__update_project_mission('{project_id}', mission) - Save mission plan
✓ mcp__giljo_mcp__spawn_agent_job(agent_display_name, agent_name, mission, '{project_id}') - Create agents (returns agent_id UUID)
✓ mcp__giljo_mcp__get_workflow_status('{project_id}') - Check spawned agents
✓ mcp__giljo_mcp__send_message(to_agents, content, project_id, message_type, priority) - Send message (use agent_id UUIDs in to_agents)

CONNECTION TROUBLESHOOTING:
If MCP fails: Check server running at {mcp_url}/health
Logs: ~/.giljo_mcp/logs/mcp_adapter.log

Begin by verifying MCP connection, then fetch complete context, and CREATE the mission plan.
"""

        return prompt

    def build_staging_prompt(
        self,
        project: Any,
        product: Any,
        orchestrator_id: str,
        project_id: str,
        agent_id: str,
        mcp_url: str,
    ) -> str:
        """Build the thin-client staging prompt text (Handover 0415).

        Args:
            project: Project model
            product: Product model
            orchestrator_id: Job ID (WHAT - work order UUID)
            project_id: Project UUID
            agent_id: Agent execution ID (WHO)
            mcp_url: Full MCP server URL

        Returns:
            Thin staging prompt (~113 tokens)
        """
        prompt = f"""You are the ORCHESTRATOR for project "{project.name}"

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {orchestrator_id}
  THE Project ID: {project_id}

MCP Server: {mcp_url}
Note: tenant_key is auto-injected by server from your API key session (secure server-side isolation)

START NOW:
1. Verify MCP: mcp__giljo_mcp__health_check()
   → Expected: {{"status": "healthy"}} - If failed, STOP and report error
2. Fetch instructions: mcp__giljo_mcp__get_orchestrator_instructions(job_id='{orchestrator_id}')
   → Response includes orchestrator_protocol (5-chapter workflow) AND orchestrator_identity (behavioral guidance)
"""

        return prompt

    def regenerate_mission(
        self, product: Product, project: Project, field_toggles: dict[str, bool], user_id: str | None
    ) -> str:
        """Regenerate orchestrator mission with current toggle config.

        Handover 0276: Enables "Stage Project refresh" — user changes settings,
        clicks "Stage Project", gets updated instructions immediately.

        Args:
            product: Product model with vision and config
            project: Project model with description
            field_toggles: Field toggle config (True=enabled, False=disabled)
            user_id: User ID for audit trail

        Returns:
            Regenerated mission string with current context
        """
        try:
            mission_parts = []

            if product and product.description:
                mission_parts.append(f"## Product\n{product.description}")

            if project.description:
                mission_parts.append(f"## Project Goal\n{project.description}")

            if project.mission:
                mission_parts.append(f"## Mission\n{project.mission}")

            if field_toggles.get("tech_stack", True) and product and product.tech_stack:
                ts = product.tech_stack
                tech_parts = []
                if ts.programming_languages:
                    tech_parts.append(f"Languages: {ts.programming_languages}")
                if ts.frontend_frameworks:
                    tech_parts.append(f"Frontend: {ts.frontend_frameworks}")
                if ts.backend_frameworks:
                    tech_parts.append(f"Backend: {ts.backend_frameworks}")
                if tech_parts:
                    mission_parts.append(f"## Tech Stack\n{chr(10).join(tech_parts)}")

            if field_toggles.get("architecture", True) and product and product.architecture:
                arch = product.architecture
                if arch.primary_pattern:
                    mission_parts.append(f"## Architecture\n{arch.primary_pattern}")

            if mission_parts:
                regenerated = "\n\n".join(mission_parts)
                logger.debug(
                    f"[StagingPromptBuilder] Mission regenerated: {len(mission_parts)} sections, "
                    f"{len(regenerated)} chars"
                )
                return regenerated
            logger.warning("[StagingPromptBuilder] No mission parts available for regeneration")
            return project.mission or f"Mission for project: {project.name}"

        except Exception:  # Broad catch: prompt fallback, returns safe default
            logger.exception("[StagingPromptBuilder] Failed to regenerate mission")
            return project.mission or f"Mission for project: {project.name}"
