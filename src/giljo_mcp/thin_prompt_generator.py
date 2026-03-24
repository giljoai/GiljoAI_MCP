"""
Thin Client Prompt Generator (Handover 0088, 0315)

REPLACES: OrchestratorPromptGenerator (prompt_generator.py)

KEY DIFFERENCE: Generates ~600 token prompts with MCP tool references (Handover 0315).
Orchestrators fetch context on-demand via MCP tools (context prioritization enabled).

Architecture (Handover 0315):
- User configures priorities (Handover 0313) and depth (Handover 0314)
- Generator creates thin prompt listing available MCP tools by priority
- Orchestrator fetches context on-demand via MCP tool calls
- Simple handover available via UI button (simple-handover REST endpoint) when context reset needed (0461c)

Token Reduction:
- Fat Prompt (v1.0): ~3500 tokens (inline context embedded in prompt)
- Thin Prompt (v2.0): ~600 tokens (MCP tool references only)
- Reduction: ~82% token savings on initial prompt

MCP Tools (Handover 0280-0281 Monolithic Context):
- get_orchestrator_instructions(job_id): Complete mission with prioritized context (tenant auto-injected)

Priority System (Handover 0313):
- Priority 1 (CRITICAL): Fetch first, essential for mission planning
- Priority 2 (IMPORTANT): Fetch if budget allows, enhances quality
- Priority 3 (NICE_TO_HAVE): Fetch if extra budget, provides additional context
- Priority 4 (EXCLUDED): Not listed in prompt, ignored by orchestrator

Depth Configuration (Handover 0314):
- vision_documents: "none" | "light" | "medium" | "full"
- memory_last_n_projects: 1 | 3 | 5 | 10
- git_commits: 10 | 25 | 50 | 100
- agent_templates: "type_only" | "full"
- tech_stack_sections: "required" | "all"
- architecture_depth: "overview" | "detailed"

Author: GiljoAI Development Team
Date: 2025-11-02 (Initial), 2025-11-17 (Handover 0315)
Priority: CRITICAL - Enables Commercial Product
"""

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from src.giljo_mcp._config_io import read_config
from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob


logger = logging.getLogger(__name__)


def _get_ssl_protocol() -> str:
    """Get HTTP protocol based on SSL configuration in config.yaml.

    Returns:
        "https" if ssl_enabled is True in config.yaml, "http" otherwise.
    """
    try:
        import yaml

        config_path = Path(__file__).parent.parent.parent / "config.yaml"
        if config_path.exists():
            with open(config_path) as f:
                config = yaml.safe_load(f) or {}
            return "https" if config.get("features", {}).get("ssl_enabled", False) else "http"
    except (OSError, ValueError, ImportError):
        pass
    return "http"


def build_continuation_prompt(
    project_id: str,
    agent_id: str,
    job_id: str,
    project_name: str | None = None,
    product_id: str | None = None,
) -> str:
    """
    Build a continuation prompt for orchestrator session refresh.

    Canonical prompt builder for all handover paths (REST endpoint, slash command,
    ThinClientPromptGenerator). Reads MCP URL from config including external_host
    for public IP deployments.

    Args:
        project_id: Project UUID
        agent_id: Agent execution ID (WHO - executor ID for MCP calls)
        job_id: Job ID (WHAT - work order ID)
        project_name: Optional project display name (for human readability)
        product_id: Optional product UUID (for fetch_context call)

    Returns:
        Continuation prompt string
    """
    # Resolve MCP URL from config (supports external_host for public IP)
    config = get_config()
    mcp_host = config.server.api_host

    # Check for external_host override (public IP deployments)
    try:
        config_data = read_config()
        external_host = config_data.get("services", {}).get("external_host")
        if external_host:
            mcp_host = external_host
    except (OSError, ValueError, KeyError):
        pass  # nosec B110

    mcp_port = config.server.api_port
    mcp_proto = _get_ssl_protocol()
    mcp_url = f"{mcp_proto}://{mcp_host}:{mcp_port}/mcp"

    # Build project display
    project_display = f' "{project_name}"' if project_name else ""

    # Build product_id display for fetch_context call
    product_param = product_id if product_id else "<fetch from project>"

    return f"""I am Orchestrator for Project{project_display} (CONTINUATION SESSION).

A previous session ran out of context. I am continuing the work.

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {job_id}
  THE Project ID: {project_id}

MCP Server: {mcp_url}
Note: tenant_key is auto-injected by server from your API key session

FIRST ACTIONS (DO NOT RE-STAGE):

1. Verify MCP: mcp__giljo-mcp__health_check()
   -> Expected: {{"status": "healthy"}}

2. Signal you are alive:
   mcp__giljo-mcp__report_progress(
       job_id="{job_id}",
       todo_items=[{{"content": "Continuation startup", "status": "in_progress"}}]
   )

3. Read 360 Memory for session context:
   mcp__giljo-mcp__fetch_context(
       product_id="{product_param}",
       categories=["memory_360"]
   )
   -> Look for the most recent "handover_closeout" entry (authored by job {job_id})
   -> Contains: previous progress, current status, next steps

4. Check messages + retrieve execution plan (can run in parallel):
   mcp__giljo-mcp__receive_messages(agent_id="{agent_id}")
   mcp__giljo-mcp__get_agent_mission(job_id="{job_id}")
   -> Mission contains: team roster with agent_id UUIDs, execution strategy, completion criteria

5. Check workflow status:
   mcp__giljo-mcp__get_workflow_status(project_id="{project_id}")

AFTER CONTEXT GATHERING — decide next action based on workflow status:
- If all agents completed: proceed to closeout (update your own todos to completed via report_progress, then complete_job, then close_project_and_update_memory)
- If agents still working: ask user if they want you to auto-monitor agents (sleep and periodically check progress and message queues). Warn user this can drastically increase token consumption.
- If agents blocked: send messages to resolve blockers
- If agents failed: assess and re-spawn if needed

CRITICAL RULES:
- Do NOT call get_orchestrator_instructions() to re-stage
- Do NOT re-write the project mission
- Read 360 Memory handover_closeout for context from previous session
- You are CONTINUING work, not starting from scratch
"""


def build_retirement_prompt(
    project_id: str,
    agent_id: str,
    job_id: str,
    project_name: str | None = None,
    git_enabled: bool = False,
    project_taxonomy: str = "",
) -> str:
    """
    Build a retirement prompt for the old orchestrator terminal session.

    This prompt instructs the orchestrator to write rich session context to 360 Memory
    before the terminal session ends. The orchestrator has the actual context (decisions,
    progress, blockers) that a bare-bones DB stats dump cannot capture.

    Args:
        project_id: Project UUID
        agent_id: Agent execution ID (WHO - executor ID)
        job_id: Job ID (WHAT - work order ID)
        project_name: Optional project display name
        git_enabled: Whether git integration is enabled for this product
        project_taxonomy: Project taxonomy alias (e.g. "BE-0042a")

    Returns:
        Retirement prompt string for the old orchestrator
    """
    project_display = f' "{project_name}"' if project_name else ""

    # Build git closeout commit instruction (only when git integration + git history enabled)
    git_closeout_section = ""
    if git_enabled:
        tag = project_taxonomy or project_name or project_id[:8]
        display_name = project_name or "this project"
        git_closeout_section = f"""
BETWEEN STEP 5 and STEP 6, create a git closeout commit to preserve project history:

git commit --allow-empty -m "closeout({tag}): {display_name}

Completed: <today's date YYYY-MM-DD>
Key outcomes:
- <list each concrete outcome from this session>"

This commit makes project history searchable via git log --grep="closeout" or git log --grep="{tag}".
"""

    return f"""ORCHESTRATOR SESSION RETIREMENT{project_display}

Your terminal session is ending due to context exhaustion. Execute these steps IN ORDER to close out all subagents and preserve session context.

YOUR IDENTITY:
  Agent ID: {agent_id}
  Job ID: {job_id}
  Project ID: {project_id}

Timeout: If any agent is still "working" after 60 seconds, skip it and document as unresolved.

STEP 1 — Pre-flight: Gather team state (do NOT modify anything yet)

mcp__giljo-mcp__get_workflow_status(project_id="{project_id}")

Record:
- Which agents need cleanup (status is NOT "complete" and NOT "decommissioned")
- Which agents have messages_waiting > 0 or incomplete todos
- Which agents can be skipped (status "complete" with 0 messages waiting and all todos done, or status "decommissioned")

STEP 2 — Drain and close out each subagent

LOOP over each non-orchestrator agent from Step 1 that needs cleanup:

  2a. Drain their messages:
      mcp__giljo-mcp__receive_messages(agent_id="<agent_id>")
      Record any important content for the 360 Memory summary.

  2b. If agent has incomplete todos, mark remaining as skipped:
      mcp__giljo-mcp__report_progress(
          job_id="<their_job_id>",
          todo_items=[
              ...keep completed items as "completed",
              ...mark remaining pending/in_progress items as "skipped"
          ]
      )
      NOTE: This will fail on agents already in "complete" status.
      If it fails, skip and include their incomplete todos in your 360 Memory summary instead.

  2c. ONLY if agent is NOT already "complete", force complete it:
      mcp__giljo-mcp__complete_job(
          job_id="<their_job_id>",
          result={{
              "summary": "Handed over due to context exhaustion. Skipped items documented in 360 Memory.",
              "status": "handed_over"
          }}
      )
      Do NOT call complete_job() on agents already in "complete" status — it will fail.

Skip agents in status "decommissioned".
Skip agents in status "complete" with 0 unread messages and all todos done (fully clean).

STEP 3 — Drain YOUR OWN message queue

mcp__giljo-mcp__receive_messages(agent_id="{agent_id}")

STEP 4 — Report progress (signal alive on dashboard)

mcp__giljo-mcp__report_progress(
    job_id="{job_id}",
    todo_items=[...mark your own items appropriately...]
)

STEP 5 — Write 360 Memory ONCE (this is the ONLY write, must succeed first attempt)

mcp__giljo-mcp__write_360_memory(
    project_id="{project_id}",
    entry_type="handover_closeout",
    author_job_id="{job_id}",
    summary="<Include ALL of the following sections:
      COMPLETED WORK: <what was accomplished this session>
      IN-PROGRESS WORK: <what was actively being worked on>
      UNRESOLVED ITEMS FOR CONTINUATION SESSION:
        - Agent <name> (job_id: <id>): skipped todos: [list], important messages: [list]
        - <repeat for each unresolved agent>
        - What the continuation orchestrator needs to address
      BLOCKERS: <any known blockers>>",
    key_outcomes=["<list each concrete outcome from this session>"],
    decisions_made=["<list architectural/design decisions and rationale>"]
)
{git_closeout_section}
STEP 6 — Confirm to user

Print: "Session context saved to 360 Memory. All subagents closed out. You may now close this terminal and paste the continuation prompt in a new terminal."

CRITICAL: Do NOT skip the memory write. The continuation session depends on this context.
CRITICAL: Do NOT call complete_job() on YOUR OWN job. You are NOT done - your work continues in a new terminal.
"""


@dataclass
class ThinPromptResponse:
    """Thin client prompt response."""

    prompt: str
    orchestrator_id: str
    project_id: str
    project_name: str
    estimated_prompt_tokens: int
    mcp_tool_name: str
    instructions_stored: bool


class ThinClientPromptGenerator:
    """
    Generates thin client prompts for orchestrators.

    CRITICAL: This enables the context prioritization and orchestration feature.

    Architecture:
    - Prompt contains only identity (~10 lines, 50 tokens)
    - Mission fetched via get_orchestrator_instructions() MCP tool
    - Field priorities applied at fetch time, not embed time

    Workflow:
    1. Create orchestrator job in database
    2. Store basic mission placeholder
    3. Generate thin prompt with orchestrator_id
    4. Return prompt to user
    5. User pastes into Claude Code CLI
    6. Orchestrator calls get_orchestrator_instructions(job_id)
    7. MCP tool generates condensed mission with field priorities (6K tokens)

    Benefits:
    - Professional UX (copy 10 lines, not 3000)
    - context prioritization and orchestration ACTIVE (applied by MCP tool)
    - Dynamic mission updates possible
    - Commercial-grade appearance

    Note: Mission condensation happens in the MCP tool get_orchestrator_instructions(),
    not here. This generator just creates the thin prompt and placeholder job.
    """

    def __init__(self, db: AsyncSession, tenant_key: str):
        """
        Initialize thin client prompt generator.

        Args:
            db: Database session
            tenant_key: Tenant isolation key
        """
        self.db = db
        self.tenant_key = tenant_key

    async def generate(
        self,
        project_id: str,
        user_id: str | None = None,
        tool: str = "universal",
        field_toggles: dict[str, bool | None] = None,
        depth_config: dict[str, Any | None] = None,  # NEW PARAMETER (Handover 0315)
        continuation_mode: bool = False,  # NEW PARAMETER (Handover 0461c)
    ) -> dict[str, Any]:
        """
        Generate a thin orchestrator prompt for a specified project.

        Handover 0088: Uses metadata JSONB column for storing field_toggles,
        user_id, tool, and other thin client data.

        Handover 0315: Generates thin prompts (~600 tokens) that reference MCP tools
        for on-demand context fetching, replacing fat prompts (~3500 tokens) with
        inline context.

        Handover 0461c: Added continuation_mode parameter for session handover.
        When True, generates continuation prompt that reads 360 Memory.

        Args:
            project_id: Project UUID
            user_id: Optional user ID for tracking and fetching toggle/depth config
            tool: AI coding agent (claude-code, codex, gemini, universal)
            field_toggles: Optional field toggle config (True=enabled, False=disabled)
            depth_config: Optional depth configuration (v2.0 depth settings)
            continuation_mode: If True, generate continuation prompt (reads 360 Memory instead of re-staging)

        Returns:
            Dict with orchestrator_id and thin_prompt
        """
        # Fetch project using tenant_key from instance
        project_stmt = select(Project).where(and_(Project.id == project_id, Project.tenant_key == self.tenant_key))
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Fetch product for context injection
        product = await self._fetch_product(project_id)

        # Handover 0315: Fetch user toggle and depth config if user_id provided
        if user_id and (not field_toggles or not depth_config):
            from src.giljo_mcp.models.auth import User

            user_stmt = select(User).where(and_(User.id == user_id, User.tenant_key == self.tenant_key))
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user:
                # Use user config if not provided
                if not field_toggles and user.field_priority_config:
                    raw_config = user.field_priority_config.get("priorities", {})
                    field_toggles = {
                        k: v.get("toggle", True) if isinstance(v, dict) else bool(v) for k, v in raw_config.items()
                    }

                if not depth_config and user.depth_config:
                    depth_config = user.depth_config

        # Apply defaults for depth_config if still not set
        if not depth_config:
            depth_config = {
                "vision_documents": "medium",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_templates": "type_only",
                "tech_stack_sections": "all",
                "architecture_depth": "overview",
            }

        # Handover 0111 - Issue #2: Check for existing active orchestrator BEFORE creating new one
        # This prevents duplicate orchestrator creation on every "Stage Project" button click
        # Handover 0367c-2: Use AgentExecution only (no fallback to MCPAgentJob)
        # FIX 2 (Handover 0485): Use exclusion-based filter (finds: waiting, working, complete, blocked)
        existing_exec_stmt = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))  # Eager load for job_metadata access
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                AgentJob.project_id == project_id,
                AgentExecution.agent_display_name == "orchestrator",
                AgentExecution.tenant_key == self.tenant_key,
                ~AgentExecution.status.in_(["decommissioned"]),  # Handover 0491: Simplified statuses
            )
            .order_by(AgentExecution.started_at.desc())
        )

        existing_exec_result = await self.db.execute(existing_exec_stmt)
        existing_execution = existing_exec_result.scalars().first()

        if existing_execution:
            # Reuse existing active orchestrator
            orchestrator_id = existing_execution.job_id  # WHAT - work order ID
            agent_id = existing_execution.agent_id  # WHO - executor ID (for MCP tool calls)
            execution_id = existing_execution.id  # UNIQUE row ID - for frontend Map key

            # BUG FIX (Handover 0275): Update job_metadata when reusing orchestrator
            # Handover 0367c-2: Update AgentJob.job_metadata (persistent work order metadata)

            # Update parent AgentJob metadata
            if existing_execution.job:
                existing_execution.job.job_metadata = {
                    "field_toggles": field_toggles or {},
                    "depth_config": depth_config,
                    "user_id": user_id,
                    "tool": tool,
                    "created_via": "thin_client_generator",
                    "reused_at": str(datetime.now(timezone.utc)),
                }
                await self.db.commit()

            logger.info(
                f"[ThinPromptGenerator] Reusing existing orchestrator {orchestrator_id} "
                f"for project {project_id} - metadata updated"
            )
        else:
            # No active orchestrator exists - create new one
            logger.info(
                f"[ThinPromptGenerator] Creating NEW orchestrator for project {project_id} "
                f"(no active orchestrator found)"
            )

            # Store project mission as placeholder
            # IMPORTANT: The REAL condensed mission (with context prioritization) is generated
            # by the MCP tool get_orchestrator_instructions() when the orchestrator calls it.
            # This placeholder ensures the job exists in the database for MCP lookup.
            placeholder_mission = project.mission or f"Orchestrator mission for project: {project.name}"

            # Generate orchestrator_id (full UUID for consistency)
            orchestrator_id = str(uuid4())
            agent_id = str(uuid4())

            # Handover 0366: Create dual-model pattern (AgentJob + AgentExecution)
            # Step 1: Create AgentJob (work order - persistent across succession)
            agent_job = AgentJob(
                job_id=orchestrator_id,
                tenant_key=self.tenant_key,
                project_id=project_id,
                mission=placeholder_mission,  # Placeholder - real mission from MCP tool
                job_type="orchestrator",
                status="active",
                job_metadata={
                    "field_toggles": field_toggles or {},
                    "depth_config": depth_config,  # Handover 0315
                    "user_id": user_id,
                    "tool": tool,
                    "created_via": "thin_client_generator",
                },
            )
            self.db.add(agent_job)

            # Step 2: Create AgentExecution (executor instance)
            agent_execution = AgentExecution(
                agent_id=agent_id,
                job_id=orchestrator_id,
                tenant_key=self.tenant_key,
                agent_display_name="orchestrator",  # Lowercase for frontend compatibility
                agent_name="orchestrator",  # Type key for color lookup
                status="waiting",
                progress=0,
                tool_type=tool,
            )
            self.db.add(agent_execution)

            # Handover 0425: Set project staging_status to 'staging' when orchestrator is created
            # This enables the Staged column in ProjectsView to show "Yes"
            project.staging_status = "staging"
            project.updated_at = datetime.now(timezone.utc)

            await self.db.commit()
            await self.db.refresh(agent_job)
            await self.db.refresh(agent_execution)
            await self.db.refresh(project)  # Refresh project to get updated staging_status

            # Get execution_id after refresh (DB assigns id)
            execution_id = agent_execution.id  # UNIQUE row ID - for frontend Map key

            logger.info(
                f"[ThinPromptGenerator] Created orchestrator {orchestrator_id}, project staging_status='staged'"
            )

        # Handover 0461c: Generate continuation prompt if continuation_mode enabled
        if continuation_mode:
            # Get MCP server URL
            config = get_config()
            mcp_host = self._get_external_host()
            mcp_port = config.server.api_port
            mcp_proto = self._get_protocol()
            mcp_url = f"{mcp_proto}://{mcp_host}:{mcp_port}"

            thin_prompt = self._generate_continuation_prompt(
                project_name=project.name,
                agent_id=agent_id,
                orchestrator_id=orchestrator_id,
                project_id=project_id,
                product_id=str(product.id) if product else None,
                mcp_url=mcp_url,
            )
        else:
            # Handover 0315: Generate thin prompt with MCP tool references (NOT fat prompt)
            # Handover 0388: Pass agent_id for correct MCP tool call in prompt
            thin_prompt = await self._generate_thin_prompt(
                orchestrator_id=orchestrator_id,
                agent_id=agent_id,  # WHO - executor ID for MCP tool calls
                project_id=project_id,
                project=project,
                product=product,
                tool=tool,
                field_toggles=field_toggles or {},
                depth_config=depth_config,
                user_id=user_id,
            )

        # Estimate prompt tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(thin_prompt) // 4

        logger.info(
            f"[ThinPromptGenerator] Generated thin prompt for {orchestrator_id}: "
            f"~{estimated_tokens} tokens (target: 600, reduction from fat: ~{3500 - estimated_tokens})"
        )

        # Handover 0276: Regenerate orchestrator instructions with current settings
        # This enables "Stage Project refresh" - when user changes field toggles
        # and clicks "Stage Project" again, they get updated instructions immediately
        regenerated_mission = await self._regenerate_mission(
            product=product, project=project, field_toggles=field_toggles or {}, user_id=user_id
        )

        # Estimate tokens
        estimated_mission_tokens = len(regenerated_mission) // 4 if regenerated_mission else 0

        if regenerated_mission:
            logger.info(
                f"[ThinPromptGenerator] Regenerated orchestrator instructions for {orchestrator_id}: "
                f"~{estimated_mission_tokens} tokens (reflects current toggle config)"
            )
        else:
            logger.warning(f"[ThinPromptGenerator] Mission regeneration returned empty for {orchestrator_id}")

        return {
            "orchestrator_id": orchestrator_id,  # WHAT - work order/job ID (backward compat)
            "agent_id": agent_id,  # WHO - executor ID for MCP tool calls (Handover 0388)
            "execution_id": execution_id,  # UNIQUE row ID - for frontend Map key (prevents duplicates)
            "thin_prompt": thin_prompt,
            "estimated_prompt_tokens": estimated_tokens,
            # Handover 0276: Include regenerated mission in response
            "mission": regenerated_mission,
            "estimated_mission_tokens": estimated_mission_tokens,
        }

    async def _regenerate_mission(
        self, product: Product, project: Project, field_toggles: dict[str, bool], user_id: str | None
    ) -> str:
        """
        Regenerate orchestrator mission with current toggle config.

        Handover 0276: Enables "Stage Project refresh" - user changes settings,
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

            # Product description (always include if available)
            if product and product.description:
                mission_parts.append(f"## Product\n{product.description}")

            # Project description
            if project.description:
                mission_parts.append(f"## Project Goal\n{project.description}")

            # Project mission (if exists)
            if project.mission:
                mission_parts.append(f"## Mission\n{project.mission}")

            # Tech stack (from product config_data)
            if field_toggles.get("tech_stack", True) and product and product.config_data:
                tech_stack = product.config_data.get("tech_stack", {})
                if tech_stack:
                    tech_parts = []
                    if isinstance(tech_stack, dict):
                        if tech_stack.get("languages"):
                            tech_parts.append(f"Languages: {', '.join(tech_stack['languages'])}")
                        if tech_stack.get("frameworks"):
                            tech_parts.append(f"Frameworks: {', '.join(tech_stack['frameworks'])}")
                    elif isinstance(tech_stack, list):
                        tech_parts.append(f"Stack: {', '.join(tech_stack)}")
                    elif isinstance(tech_stack, str):
                        tech_parts.append(f"Stack: {tech_stack}")
                    if tech_parts:
                        mission_parts.append(f"## Tech Stack\n{chr(10).join(tech_parts)}")

            # Architecture (from product config_data)
            if field_toggles.get("architecture", True) and product and product.config_data:
                architecture = product.config_data.get("architecture", {})
                if architecture and architecture.get("patterns"):
                    mission_parts.append(f"## Architecture\n{', '.join(architecture['patterns'])}")

            # Join all parts
            if mission_parts:
                regenerated = "\n\n".join(mission_parts)
                logger.debug(
                    f"[ThinPromptGenerator] Mission regenerated: {len(mission_parts)} sections, "
                    f"{len(regenerated)} chars"
                )
                return regenerated
            # Fallback if no parts available
            logger.warning("[ThinPromptGenerator] No mission parts available for regeneration")
            return project.mission or f"Mission for project: {project.name}"

        except Exception:  # Broad catch: prompt fallback, returns safe default
            logger.exception("[ThinPromptGenerator] Failed to regenerate mission")
            # Return project mission as fallback
            return project.mission or f"Mission for project: {project.name}"

    def _build_thin_prompt(self, orchestrator_id: str, project_id: str, project_name: str, tool: str) -> str:
        """
        Build thin client prompt (~10 lines).

        This is THE critical output - must be concise and professional.

        Includes MCP connection details (Amendment C).
        """
        # Get MCP server configuration
        config = get_config()

        # Use external_host (user-facing IP) not api_host (bind address 0.0.0.0)
        # External host is configured during installation for network access
        # Need to read config.yaml directly as ConfigManager doesn't load services section
        try:
            config_data = read_config()
            mcp_host = config_data.get("services", {}).get("external_host") or config.server.api_host
        except (OSError, ValueError, KeyError):  # nosec B110
            # Fallback to api_host if YAML loading fails
            mcp_host = config.server.api_host

        mcp_port = config.server.api_port
        mcp_proto = self._get_protocol()
        mcp_url = f"{mcp_proto}://{mcp_host}:{mcp_port}"

        # Generate API key hint (if configured)
        api_key_configured = bool(config.server.api_key)
        auth_note = "(authenticated)" if api_key_configured else "(check config.yaml for API key)"

        return f"""I am Orchestrator for GiljoAI Project "{project_name}".

IDENTITY:
- Orchestrator ID: {orchestrator_id}
- Project ID: {project_id}

MCP CONNECTION:
- Server URL: {mcp_url}
- Tool Prefix: mcp__giljo-mcp__
- Auth Status: {auth_note}

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)
You are STAGING the project by creating a mission plan. You will NOT execute the work yourself.
Your job is to: 1) Analyze requirements, 2) Create mission plan, 3) Assign work to specialist agents.

MCP TOOLS AVAILABLE (ALL start with "mcp__giljo-mcp__"):
✓ health_check() - Verify MCP connection
✓ get_orchestrator_instructions(job_id) - Fetch context (tenant auto-injected by server)
✓ update_project_mission(project_id, mission) - Save mission plan
✓ spawn_agent_job(agent_display_name, agent_name, mission, project_id) - Create agents
✓ get_workflow_status(project_id) - Check spawned agents
✓ send_message(to_agents, content, project_id, message_type, priority) - Send message to agents (use agent_id UUIDs in to_agents)

STARTUP SEQUENCE:
1. Verify MCP: mcp__giljo-mcp__health_check()
2. Fetch context: mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}')
   └─► Returns: Project.description (user requirements), Product context, Agent templates
   └─► Note: tenant_key auto-injected by server from your API key session
3. CREATE MISSION: Analyze requirements → Generate execution plan (context prioritization and orchestration)
4. PERSIST MISSION: mcp__giljo-mcp__update_project_mission('{project_id}', your_created_mission)
   └─► Saves to Project.mission field for UI display
5. SPAWN AGENTS: mcp__giljo-mcp__spawn_agent_job() to create specialist agent jobs
   └─► Agents will EXECUTE the work (not you)
   └─► SAVE each spawn response's agent_id - needed for UUID-based messaging later
6. SIGNAL COMPLETE: mcp__giljo-mcp__send_message() to broadcast staging done
   └─► Message: "STAGING_COMPLETE: Mission created, N agents spawned: [list agent names]"
   └─► This enables the Implement button in UI (required for workflow)

MESSAGING RULE: Always use agent_id UUIDs in send_message(to_agents=[...]).
Each spawn_agent_job() returns an agent_id UUID. Never use display names in to_agents.

CRITICAL DISTINCTIONS:
- Project.description = User-written requirements (READ THIS for context)
- Project.mission = YOUR OUTPUT (condensed execution plan you CREATE in Step 3)
- Agent jobs = Specialist agents who will DO THE ACTUAL WORK (you coordinate them)

CONNECTION TROUBLESHOOTING:
If MCP fails: Check server running at {mcp_url}/health
Logs: ~/.giljo_mcp/logs/mcp_adapter.log

Begin by verifying MCP connection, then fetch context and CREATE the mission plan.
"""

    async def _generate_thin_prompt(
        self,
        orchestrator_id: str,
        agent_id: str,  # Handover 0388: WHO - executor ID (for identity tracking, NOT MCP tool calls)
        project_id: str,
        project: Any,
        product: Any,
        tool: str,
        field_toggles: dict[str, bool],
        depth_config: dict[str, Any],
        user_id: str | None = None,
    ) -> str:
        """
        Generate thin prompt listing available MCP tools (Handover 0315).

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
            depth_config: User depth configuration (vision_documents, memory_last_n_projects, etc.)

        Returns:
            Thin prompt with MCP tool references
        """
        # Monolithic Context Architecture (Handover 0280-0281)
        # All context fetched via single MCP tool: get_orchestrator_instructions()
        # Priority filtering and depth configuration applied server-side

        # Get MCP server configuration
        config = get_config()

        # Use external_host (user-facing IP) not api_host (bind address 0.0.0.0)
        try:
            config_data = read_config()
            mcp_host = config_data.get("services", {}).get("external_host") or config.server.api_host
        except (OSError, ValueError, KeyError):  # nosec B110
            # Fallback to api_host if YAML loading fails
            mcp_host = config.server.api_host

        mcp_port = config.server.api_port
        mcp_proto = self._get_protocol()
        mcp_url = f"{mcp_proto}://{mcp_host}:{mcp_port}"

        # Generate API key hint (if configured)
        api_key_configured = bool(config.server.api_key)
        auth_note = "(authenticated)" if api_key_configured else "(check config.yaml for API key)"

        # Build thin prompt with MCP tool reference (Monolithic Context Architecture)
        # Handover 0388: Updated IDENTITY to show agent_id (WHO) and job_id (WHAT) separately
        prompt = f"""I am Orchestrator for GiljoAI Project "{project.name}".

IDENTITY:
- Orchestrator Agent ID: {agent_id}
- Job ID: {orchestrator_id}
- Project ID: {project_id}

MCP CONNECTION:
- Server URL: {mcp_url}
- Tool Prefix: mcp__giljo-mcp__
- Auth Status: {auth_note}

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)
You are STAGING the project by creating a mission plan. You will NOT execute the work yourself.
Your job is to: 1) Analyze requirements, 2) Create mission plan, 3) Assign work to specialist agents.

PROJECT CONTEXT (Inline - ~200 tokens):
- Name: {project.name}
- Description: {project.description or "(No description provided)"}
- Mission: {project.mission or "(Mission will be created by you)"}

WORKFLOW:
1. Verify MCP connection: mcp__giljo-mcp__health_check()
   → Expected: {{"status": "healthy", "database": "connected"}}
   → If failed: STOP and report error - do NOT proceed
2. Fetch complete context: mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}')
   → Returns configured context (vision, tech stack, architecture, memory, git history, templates)
   → User toggle/depth configuration automatically applied server-side
   → Depth configuration (chunking, commit count, etc.) pre-configured
   → Note: tenant_key auto-injected by server from your API key session
3. Create condensed mission plan from fetched context
4. Persist mission: mcp__giljo-mcp__update_project_mission('{project_id}', mission)
5. Spawn specialist agents: mcp__giljo-mcp__spawn_agent_job(agent_display_name, agent_name, mission, '{project_id}')
   → SAVE each response's agent_id UUID - needed for UUID-based messaging
6. Monitor: mcp__giljo-mcp__get_workflow_status('{project_id}')
7. Signal complete: mcp__giljo-mcp__send_message(to_agents=['all'], content='STAGING_COMPLETE: Mission created, N agents spawned: [list names]', project_id='{project_id}', message_type='broadcast')
   → This broadcast enables the Implement button in UI (REQUIRED)

Claude Code: Use TodoWrite tool to track workflow progress.

MESSAGING RULE: Always use agent_id UUIDs in send_message(to_agents=[...]).
Each spawn_agent_job() returns an agent_id UUID. Never use display names in to_agents.

CRITICAL DISTINCTIONS:
- Project.description = User-written requirements (already provided above)
- Project.mission = YOUR OUTPUT (condensed execution plan you CREATE in Step 2)
- Agent jobs = Specialist agents who will DO THE ACTUAL WORK (you coordinate them)

MCP CORE TOOLS (Always Available - tenant_key auto-injected by server):
✓ mcp__giljo-mcp__health_check() - Verify MCP connection
✓ mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}') - Fetch complete prioritized context
✓ mcp__giljo-mcp__update_project_mission('{project_id}', mission) - Save mission plan
✓ mcp__giljo-mcp__spawn_agent_job(agent_display_name, agent_name, mission, '{project_id}') - Create agents (returns agent_id UUID)
✓ mcp__giljo-mcp__get_workflow_status('{project_id}') - Check spawned agents
✓ mcp__giljo-mcp__send_message(to_agents, content, project_id, message_type, priority) - Send message (use agent_id UUIDs in to_agents)

CONNECTION TROUBLESHOOTING:
If MCP fails: Check server running at {mcp_url}/health
Logs: ~/.giljo_mcp/logs/mcp_adapter.log

Begin by verifying MCP connection, then fetch complete context, and CREATE the mission plan.
"""

        return prompt

    async def _inject_360_memory(self, session, product_id: str, tenant_key: str, product: Any | None = None) -> str:
        """
        Inject 360 Memory System context into prompt.

        Updated in Handover 0390b: Reads count from product_memory_entries table.

        ALWAYS included in orchestrator prompts to provide cumulative product knowledge.

        Args:
            session: AsyncSession for database access
            product_id: Product UUID
            tenant_key: Tenant identifier
            product: Optional Product model (for objectives from JSONB)

        Returns:
            Formatted 360 memory section (always present, even if no history)

        Examples:
            With history:
                ## 360 Memory System
                Product has 5 previous project history entries.
                Review these to inform decisions and avoid past mistakes.

            Without history:
                ## 360 Memory System
                No previous project history yet. You're starting fresh.
        """
        from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

        # Get count from table (fetch limited set for count)
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_for_context(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            limit=100,  # Reasonable limit for counting
        )
        history_count = len(entries)

        # Get objectives from JSONB (still in product_memory)
        objectives = []
        if product and product.product_memory:
            context_data = product.product_memory.get("context", {})
            objectives = context_data.get("objectives", []) if isinstance(context_data, dict) else []

        # Build memory section
        memory_lines = ["\n## 360 Memory System"]

        if history_count > 0:
            memory_lines.append(f"Product has {history_count} previous project history entries.")
            memory_lines.append("Review these to inform decisions and avoid past mistakes.")
        else:
            memory_lines.append("No previous project history yet. You're starting fresh.")

        # Add objectives if available
        if objectives:
            memory_lines.append("\nProduct Objectives:")
            memory_lines.extend([f"- {obj}" for obj in objectives[:3]])  # Limit to top 3 objectives

        memory_lines.append("\nAccess via: fetch_context(categories=['memory_360']) MCP tool")

        return "\n".join(memory_lines)

    def _inject_git_instructions(self, product) -> str:
        """
        Inject Git integration instructions into prompt (CONDITIONAL).

        Only included when product.product_memory.git_integration.enabled = True.
        Provides git command instructions for agents to run locally using user's credentials.

        Args:
            product: Product model with product_memory JSONB field

        Returns:
            Formatted git integration section (empty string if disabled)

        Examples:
            Git enabled:
                ## Git Integration
                Use git commands for additional context:
                - git log --oneline -20 main
                - git log --since="1 week ago" --pretty=format:"%h - %s (%an, %ar)"

            Git disabled:
                "" (empty string)
        """
        if not product or not product.product_memory:
            return ""

        git_config = product.product_memory.get("git_integration", {})

        # Return empty string if git integration disabled or not configured
        if not git_config.get("enabled", False):
            return ""

        # Extract config with defaults
        commit_limit = git_config.get("commit_limit", 20)
        default_branch = git_config.get("default_branch", "")

        # Build branch reference (only if specified)
        branch_ref = f" {default_branch}" if default_branch else ""

        # Build git instructions section
        git_lines = [
            "\n## Git Integration",
            "Use git commands for additional context:",
            f"- git log --oneline -{commit_limit}{branch_ref}",
            '- git log --since="1 week ago" --pretty=format:"%h - %s (%an, %ar)"',
            "- git show --stat HEAD~5..HEAD",
            "",
            "Combine git history with 360 Memory for full context.",
        ]

        return "\n".join(git_lines)

    async def _fetch_product(self, project_id: str) -> Any | None:
        """
        Fetch product for a given project.

        Args:
            project_id: Project UUID

        Returns:
            Product model or None if not found
        """
        from src.giljo_mcp.models.products import Product
        from src.giljo_mcp.models.projects import Project as ProjectModel

        # Fetch project first
        project_stmt = select(ProjectModel).where(
            and_(ProjectModel.id == project_id, ProjectModel.tenant_key == self.tenant_key)
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            return None

        # Fetch product via project.product_id
        product_stmt = select(Product).where(
            and_(Product.id == project.product_id, Product.tenant_key == self.tenant_key)
        )
        product_result = await self.db.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        return product

    async def _fetch_project(self, project_id: str) -> Any | None:
        """
        Fetch project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project model or None if not found
        """
        from src.giljo_mcp.models.projects import Project as ProjectModel

        project_stmt = select(ProjectModel).where(
            and_(ProjectModel.id == project_id, ProjectModel.tenant_key == self.tenant_key)
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        return project

    async def _build_thin_prompt_with_memory(
        self,
        session,
        orchestrator_id: str,
        project_id: str,
        project_name: str,
        tool: str,
        product,
        field_toggles: dict[str, bool | None] = None,
    ) -> str:
        """
        Build thin client prompt WITH 360 Memory, Git integration, and Agent templates.

        Updated in Handover 0390b: Now async, reads memory count from table.

        This extends _build_thin_prompt with context injection.

        Args:
            session: AsyncSession for database access
            orchestrator_id: Orchestrator job UUID
            project_id: Project UUID
            project_name: Project display name
            tool: AI coding agent (claude-code, codex, gemini, universal)
            product: Product model for context injection
            field_toggles: Optional user field toggle config

        Returns:
            Enhanced thin prompt with memory, git, and agent template sections
        """
        # Get base prompt (existing logic)
        base_prompt = self._build_thin_prompt(
            orchestrator_id=orchestrator_id,
            project_id=project_id,
            project_name=project_name,
            tool=tool,
        )

        # Inject 360 Memory (ALWAYS) - now async
        memory_section = await self._inject_360_memory(
            session=session,
            product_id=str(product.id),
            tenant_key=product.tenant_key,
            product=product,
        )

        # Inject Git integration (CONDITIONAL)
        git_section = self._inject_git_instructions(product)

        # Handover 0306: Inject Agent Templates (CONDITIONAL - based on priority)
        # Handover 0246c: Agent templates returned inline by get_orchestrator_instructions()
        agent_section = ""  # Templates included in orchestrator instructions response

        # Insert injections BEFORE "YOUR ROLE" section
        # This places context EARLY in the prompt for maximum impact
        insertion_marker = "YOUR ROLE: PROJECT STAGING"

        if insertion_marker in base_prompt:
            # Split at marker and insert context
            before_role, after_role = base_prompt.split(insertion_marker, 1)
            enhanced_prompt = (
                before_role + memory_section + git_section + agent_section + "\n" + insertion_marker + after_role
            )
        else:
            # Fallback: append at end if marker not found
            enhanced_prompt = base_prompt + memory_section + git_section + agent_section

        return enhanced_prompt

    def _get_external_host(self) -> str:
        """
        Get external MCP server host from config.

        Returns external_host for user-facing connections,
        falls back to api_host if not configured.
        """
        try:
            config_data = read_config()
            external_host = config_data.get("services", {}).get("external_host")
            if external_host:
                return external_host
        except (OSError, ValueError, KeyError):
            pass  # nosec B110

        # Fallback to api_host from config
        config = get_config()
        return config.server.api_host

    def _get_protocol(self) -> str:
        """Get HTTP protocol based on SSL configuration."""
        return _get_ssl_protocol()

    async def generate_staging_prompt(self, orchestrator_id: str, project_id: str, agent_id: str = None) -> str:
        """
        Generate thin-client orchestrator staging prompt (Handover 0415).

        Minimal prompt that provides identity credentials and instructs orchestrator
        to fetch complete workflow guide from orchestrator_protocol field via MCP.

        Handover 0429 Phase 4: Returns continuation prompt for instance > 1.

        Args:
            orchestrator_id: Job ID (WHAT - work order UUID)
            project_id: Project UUID
            agent_id: Agent execution ID (WHO - executor UUID for MCP tool calls, Handover 0388)

        Returns:
            Thin staging prompt (~113 tokens) OR continuation prompt for successors

        Raises:
            ValueError: If project or product not found
        """
        project = await self._fetch_project(project_id)
        product = await self._fetch_product(project_id)

        if not project or not product:
            raise ValueError(f"Project {project_id} or its product not found")

        # Handover 0388: If agent_id not provided, fetch from database
        execution = None
        if not agent_id:
            exec_stmt = (
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    AgentJob.job_id == orchestrator_id,
                    AgentExecution.tenant_key == self.tenant_key,
                )
            )
            exec_result = await self.db.execute(exec_stmt)
            execution = exec_result.scalars().first()
            if execution:
                agent_id = execution.agent_id
            else:
                # Fallback: use orchestrator_id if no execution found (legacy)
                agent_id = orchestrator_id
        else:
            # If agent_id provided, fetch execution (for potential future use)
            exec_stmt = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == self.tenant_key,
            )
            exec_result = await self.db.execute(exec_stmt)
            execution = exec_result.scalars().first()

        # Get MCP server URL
        config = get_config()
        mcp_host = self._get_external_host()
        mcp_port = config.server.api_port
        mcp_proto = self._get_protocol()
        mcp_url = f"{mcp_proto}://{mcp_host}:{mcp_port}"

        # Handover 0415: Thin client prompt with explicit "YOUR" labels
        # Handover 0424: Added health_check as mandatory first step
        # Handover 0431: Removed self_identity fetch - now included in get_orchestrator_instructions() response
        prompt = f"""You are the ORCHESTRATOR for project "{project.name}"

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {orchestrator_id}
  THE Project ID: {project_id}

MCP Server: {mcp_url}
Note: tenant_key is auto-injected by server from your API key session (secure server-side isolation)

START NOW:
1. Verify MCP: mcp__giljo-mcp__health_check()
   → Expected: {{"status": "healthy"}} - If failed, STOP and report error
2. Fetch instructions: mcp__giljo-mcp__get_orchestrator_instructions(job_id='{orchestrator_id}')
   → Response includes orchestrator_protocol (5-chapter workflow) AND orchestrator_identity (behavioral guidance)
"""

        return prompt

    def generate_implementation_prompt(self, prompt_type: str, **kwargs) -> str:
        """Generate an implementation prompt by type.

        Args:
            prompt_type: One of 'multi_terminal_orchestrator', 'claude_code_execution'
            **kwargs: Parameters passed to the underlying builder
                - orchestrator_id: str
                - project: Project model
                - agent_jobs: list of AgentExecution
                - git_enabled: bool

        Returns:
            The generated prompt string

        Raises:
            ValueError: If prompt_type is unknown
        """
        builders = {
            "multi_terminal_orchestrator": self._build_multi_terminal_orchestrator_prompt,
            "claude_code_execution": self._build_claude_code_execution_prompt,
        }
        builder = builders.get(prompt_type)
        if not builder:
            raise ValueError(f"Unknown prompt type: {prompt_type}. Valid types: {list(builders.keys())}")
        return builder(**kwargs)

    def _generate_continuation_prompt(
        self,
        project_name: str,
        agent_id: str,
        orchestrator_id: str,
        project_id: str,
        product_id: str | None,
        mcp_url: str,
    ) -> str:
        """
        Generate continuation prompt. Delegates to module-level build_continuation_prompt().

        Args:
            project_name: Project display name
            agent_id: Agent execution ID (WHO)
            orchestrator_id: Job ID (WHAT)
            project_id: Project UUID
            product_id: Product UUID (for fetch_context call)
            mcp_url: MCP server URL (ignored - resolved from config by canonical builder)

        Returns:
            Continuation prompt string
        """
        return build_continuation_prompt(
            project_id=project_id,
            agent_id=agent_id,
            job_id=orchestrator_id,
            project_name=project_name,
            product_id=product_id,
        )

    def _build_claude_code_execution_prompt(
        self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False
    ) -> str:
        """
        Build Claude Code subagent mode execution prompt.

        Orchestrator spawns sub-agents using Task tool.
        Sub-agents receive identity via instructions string.

        Used by GET /api/prompts/implementation/{project_id} endpoint.
        """
        # SECTION 1: Context Recap
        context_recap = [
            "# GiljoAI Implementation Phase - Claude Code CLI Mode",
            "",
            "## FIRST ACTION (MANDATORY)",
            "Before anything else, verify MCP connection:",
            "```python",
            "mcp__giljo-mcp__health_check()",
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
            f'mcp__giljo-mcp__get_agent_mission(job_id="{orchestrator_id}")',
            "```",
            "Note: tenant_key is auto-injected by server from your API key session",
            "",
            "This returns your plan with:",
            "- Agent execution order (sequential/parallel/hybrid)",
            "- Dependency graph between agents",
            "- Coordination checkpoints",
            "- Success criteria for each phase",
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

        # SECTION 2: Agent Jobs List
        agent_spawn_lines = []
        if agent_jobs:
            for idx, agent in enumerate(agent_jobs, 1):
                mission = getattr(agent.job, "mission", None) or "(No mission assigned)"
                mission_summary = mission[:100] + "..." if len(mission) > 100 else mission

                agent_spawn_lines.extend(
                    [
                        f"**{idx}. {agent.agent_name}**",
                        f"   - Agent Name: `{agent.agent_name}` (matches .claude/agents/{agent.agent_name}.md)",
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
            "Each has a unique job_id and agent_display_name.",
            "",
            *agent_spawn_lines,
        ]

        # SECTION 3: Task Tool Spawning Template
        spawning_section = [
            "## How to Spawn Agents via Task Tool",
            "",
            "### Spawning Template",
            "Use this exact syntax to spawn each agent in parallel:",
            "",
            "```python",
            "Task(",
            '    subagent_type="{agent_name}",  # CRITICAL: Use agent_name (template filename)',
            '    instructions="""',
            "    You are {agent_name} (job_id: {job_id})",
            "    ",
            '    First action: Call mcp__giljo-mcp__get_agent_mission(job_id="{job_id}")',
            "    Note: tenant_key is auto-injected by server from your API key session",
            "    This returns your `mission` and `full_protocol`.",
            "    Follow `full_protocol` for all lifecycle behavior",
            "    (startup, planning, progress, messaging, completion, error handling).",
            '    """',
            ")",
            "```",
            "",
        ]

        # Add concrete example if agents exist
        if agent_jobs:
            first = agent_jobs[0]
            spawning_section.extend(
                [
                    "### Example: First Agent",
                    "```python",
                    "Task(",
                    f'    subagent_type="{first.agent_name}",',
                    '    instructions="""',
                    f"    You are {first.agent_name} (job_id: {first.job_id})",
                    "    ",
                    f'    First action: Call mcp__giljo-mcp__get_agent_mission(job_id="{first.job_id}")',
                    "    Note: tenant_key is auto-injected by server from your API key session",
                    "    This returns your `mission` and `full_protocol`.",
                    "    Follow `full_protocol` for all lifecycle behavior",
                    "    (startup, planning, progress, messaging, completion, error handling).",
                    '    """',
                    ")",
                    "```",
                    "",
                    "**Task Tool Parameter Naming**:",
                    "- Task(subagent_type=X) uses agent_name value",
                    "- agent_name: Template filename (e.g., 'tdd-implementor')",
                    "- Do NOT use agent_display_name (e.g., 'implementer') - it will fail",
                    "",
                    "### Spawning Strategy",
                    "**Spawning Mode**: Use foreground (default) when you need to observe agent output in real-time. Use `run_in_background=true` for independent parallel agents — poll status via `get_workflow_status()`. Background execution is fully supported and reliable.",
                    "",
                    "Choose spawning approach based on job requirements:",
                    "- **Sequential**: Spawn one agent, wait for completion, then next (best for dependent tasks)",
                    "- **Parallel**: Multiple Task() calls in single message (best for independent tasks)",
                    "",
                    "Each agent runs independently and coordinates via MCP server.",
                    "",
                ]
            )

        # SECTION 4: Monitoring Instructions
        monitoring_section = [
            "## Monitoring Agent Progress",
            "",
            "### mcp__giljo-mcp__get_workflow_status()",
            "Check all agent statuses:",
            "```python",
            f'mcp__giljo-mcp__get_workflow_status(project_id="{project.id}")',
            "```",
            "Note: tenant_key is auto-injected by server from your API key session",
            "",
            "Returns:",
            "```json",
            "{",
            '  "agents": [',
            '    {"job_id": "...", "status": "working", "progress": 45},',
            '    {"job_id": "...", "status": "blocked", "block_reason": "..."}',
            "  ]",
            "}",
            "```",
            "",
            "### Handle Blockers",
            "- When agent status is 'blocked', read their messages",
            "- Respond via mcp__giljo-mcp__send_message(to_agents=['<agent-id-uuid>'], ...) using agent_id UUID",
            "- Update their next_instruction field if needed",
            "",
            "### Message Handling",
            "- Agents report progress via mcp__giljo-mcp__report_progress() and mcp__giljo-mcp__send_message()",
            "- Monitor messages for questions or blockers",
            "- Respond promptly to keep workflow moving",
            "- ALWAYS use agent_id UUIDs in to_agents (from spawn_agent_job responses), never display names",
            "",
        ]

        # SECTION 5: Context Refresh Capability
        context_refresh_section = [
            "## Refreshing Your Context",
            "",
            "If you need to re-read your orchestrator mission:",
            "```python",
            f'mcp__giljo-mcp__get_orchestrator_instructions(job_id="{orchestrator_id}")',
            "```",
            "Note: tenant_key is auto-injected by server from your API key session",
            "",
            "This MCP tool fetches your original staging mission and context.",
            "Use this if you lose track of project objectives or need to verify requirements.",
            "",
        ]

        # SECTION 6: CLI Mode Constraints
        cli_constraints_section = [
            "## CLI Mode Constraints",
            "",
            "**WARNING: Agent Template Files Required**",
            "- Each agent_name needs a file: `.claude/agents/{agent_name}.md`",
            '- If file is missing: "Subagent type not found" error',
            '- Example: agent_name="<agent_name>" requires `.claude/agents/<agent_name>.md`',
            "",
            "**WARNING: Exact Naming Required**",
            "- Task tool parameter `subagent_type` expects `agent_name`, NOT `agent_display_name`",
            "- agent_name: Template filename (see allowed_agent_names in instructions)",
            '- agent_display_name: Display category (e.g., "implementer")',
            '- Using agent_display_name will fail with "Subagent type not found"',
            "",
            "**WARNING: MCP Communication Only**",
            "- All agents run in THIS terminal (Claude Code CLI mode)",
            "- Coordination happens via MCP server (not direct communication)",
            "- All MCP tools have tenant_key auto-injected by server from API key session",
            "",
        ]

        # SECTION 7: Completion Instructions
        git_closeout_lines = []
        if git_enabled:
            tag = getattr(project, "taxonomy_alias", None) or project.name
            git_closeout_lines = [
                "### Git Closeout Commit",
                "Before calling complete_job, create a closeout commit to preserve project history:",
                "```bash",
                f'git commit --allow-empty -m "closeout({tag}): {project.name}',
                "",
                "Completed: <today YYYY-MM-DD>",
                "Key outcomes:",
                '- <list each concrete outcome>"',
                "```",
                f'This makes project history searchable via `git log --grep="closeout"` or `git log --grep="{tag}"`.',
                "",
            ]

        completion_section = [
            "## When You're Done",
            "",
            "### Verify Sub-Agents Completed",
            "1. Check all agents via mcp__giljo-mcp__get_workflow_status()",
            "2. Ensure all have status='complete' (no failures or blockers)",
            "3. Review final deliverables",
            "",
            "### If Agents Are NOT Complete (CLOSEOUT_BLOCKED Recovery)",
            "",
            "If `get_workflow_status()` shows agents not in 'complete' or 'decommissioned' status,",
            "you MUST resolve them before closeout. For each non-complete agent:",
            "",
            "1. **Drain their messages:**",
            '   `mcp__giljo-mcp__receive_messages(agent_id="<their_agent_id>")`',
            "   Record any important content for the 360 Memory summary.",
            "",
            "2. **Process incomplete todos** — mark remaining items as completed or skipped:",
            "   ```python",
            "   mcp__giljo-mcp__report_progress(",
            '       job_id="<their_job_id>",',
            "       todo_items=[",
            '           ...keep completed items as "completed",',
            '           ...mark remaining pending/in_progress items as "skipped"',
            "       ]",
            "   )",
            "   ```",
            '   NOTE: This will fail on agents already in "complete" status. If it fails, skip this step.',
            "",
            "3. **Force-complete the agent** (ONLY if NOT already 'complete'):",
            "   ```python",
            "   mcp__giljo-mcp__complete_job(",
            '       job_id="<their_job_id>",',
            '       result={"summary": "Force-completed by orchestrator during closeout.", "status": "force_completed"}',
            "   )",
            "   ```",
            '   Do NOT call complete_job() on agents already in "complete" status.',
            "",
            "Skip agents in status 'decommissioned'.",
            "After all agents are resolved, proceed with closeout below.",
            "",
            *git_closeout_lines,
            "### Complete Your Orchestrator Job",
            "When all sub-agents are done and project is complete:",
            "```python",
            f'mcp__giljo-mcp__complete_job(job_id="{orchestrator_id}")',
            "```",
            "",
            "### Handover (if needed)",
            "If you reach context limits before completion:",
            "- Use the Hand Over button in the UI to reset your context",
            "- Your session context will be saved to 360 Memory",
            "- You'll receive a continuation prompt to continue work",
            "",
        ]

        # Combine all sections
        all_sections = (
            context_recap
            + agent_list_section
            + spawning_section
            + monitoring_section
            + context_refresh_section
            + cli_constraints_section
            + completion_section
        )

        return "\n".join(all_sections)

    def _build_multi_terminal_orchestrator_prompt(
        self, orchestrator_id: str, project, agent_jobs: list, git_enabled: bool = False
    ) -> str:
        """
        Build multi-terminal orchestrator implementation prompt (Handover 0830).

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
            "mcp__giljo-mcp__health_check()",
            "```",
            "",
            f"You are the ORCHESTRATOR for project '{project.name}'.",
            f"Job ID: `{orchestrator_id}` | Project ID: `{project.id}`",
            "",
            "Call `get_agent_mission` to receive your current team state and operating protocol:",
            "```",
            f'mcp__giljo-mcp__get_agent_mission(job_id="{orchestrator_id}")',
            "```",
        ]
        return "\n".join(lines)
