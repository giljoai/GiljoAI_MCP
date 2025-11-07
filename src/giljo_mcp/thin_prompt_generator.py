"""
Thin Client Prompt Generator (Handover 0088)

REPLACES: OrchestratorPromptGenerator (prompt_generator.py)

KEY DIFFERENCE: Generates ~10 line prompts with identity only.
Orchestrators fetch missions via MCP tools (70% token reduction enabled).

Author: GiljoAI Development Team
Date: 2025-11-02
Priority: CRITICAL - Enables Commercial Product
"""

import logging
from dataclasses import dataclass
from typing import Any, Dict, Optional
from uuid import uuid4

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.config_manager import get_config
from src.giljo_mcp.models import MCPAgentJob, Project, User


logger = logging.getLogger(__name__)


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

    CRITICAL: This enables the 70% token reduction feature.

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
    6. Orchestrator calls get_orchestrator_instructions(orchestrator_id)
    7. MCP tool generates condensed mission with field priorities (6K tokens)

    Benefits:
    - Professional UX (copy 10 lines, not 3000)
    - 70% token reduction ACTIVE (applied by MCP tool)
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
        user_id: Optional[str] = None,
        tool: str = "universal",
        instance_number: int = 1,
        field_priorities: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """
        Generate a thin orchestrator prompt for a specified project.

        Handover 0088: Now uses metadata JSONB column instead of handover_summary
        for storing field_priorities, user_id, tool, and other thin client data.

        Args:
            project_id: Project UUID
            user_id: Optional user ID for tracking
            tool: AI coding tool (claude-code, codex, gemini, universal)
            instance_number: Orchestrator instance number (for succession)
            field_priorities: Optional field importance weights

        Returns:
            Dict with orchestrator_id and thin_prompt
        """
        # Fetch project using tenant_key from instance
        project_stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.tenant_key == self.tenant_key
            )
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Store project mission as placeholder
        # IMPORTANT: The REAL condensed mission (with 70% token reduction) is generated
        # by the MCP tool get_orchestrator_instructions() when the orchestrator calls it.
        # This placeholder ensures the job exists in the database for MCP lookup.
        placeholder_mission = project.mission or f"Orchestrator mission for project: {project.name}"

        # If instance_number not provided, calculate next in sequence
        if instance_number is None or instance_number == 1:
            instance_stmt = select(func.coalesce(func.max(MCPAgentJob.instance_number), 0)).where(
                and_(
                    MCPAgentJob.tenant_key == self.tenant_key,
                    MCPAgentJob.project_id == project_id,
                    MCPAgentJob.agent_type == "orchestrator"
                )
            )
            instance_result = await self.db.execute(instance_stmt)
            instance_number = instance_result.scalar() + 1

        # Generate orchestrator_id (full UUID for consistency)
        orchestrator_id = str(uuid4())

        # Create orchestrator job with metadata (Handover 0088)
        orchestrator = MCPAgentJob(
            tenant_key=self.tenant_key,
            project_id=project_id,
            job_id=orchestrator_id,
            agent_name=f"Orchestrator #{instance_number}",
            agent_type="orchestrator",
            status="waiting",
            mission=placeholder_mission,  # Placeholder - real mission from MCP tool
            instance_number=instance_number,
            context_budget=project.context_budget,
            context_used=0,
            tool_type=tool,
            # Handover 0088: Store thin client data in metadata column
            job_metadata={
                "field_priorities": field_priorities or {},
                "user_id": user_id,
                "tool": tool,
                "created_via": "thin_client_generator"
            } if field_priorities or user_id else {}
        )

        self.db.add(orchestrator)
        await self.db.commit()
        await self.db.refresh(orchestrator)

        # Generate thin prompt
        thin_prompt = self._build_thin_prompt(
            orchestrator_id=orchestrator_id,
            project_id=project_id,
            project_name=project.name,
            instance_number=instance_number,
            tool=tool
        )

        # Estimate prompt tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(thin_prompt) // 4

        return {
            "orchestrator_id": orchestrator_id,
            "thin_prompt": thin_prompt,
            "instance_number": instance_number,
            "context_budget": project.context_budget,
            "estimated_prompt_tokens": estimated_tokens
        }

    def _build_thin_prompt(
        self,
        orchestrator_id: str,
        project_id: str,
        project_name: str,
        instance_number: int,
        tool: str
    ) -> str:
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
        from pathlib import Path

        import yaml

        try:
            config_path = Path("config.yaml")
            if config_path.exists():
                with open(config_path, encoding="utf-8") as f:
                    config_data = yaml.safe_load(f) or {}
                mcp_host = config_data.get("services", {}).get("external_host") or config.server.api_host
            else:
                mcp_host = config.server.api_host
        except Exception:
            # Fallback to api_host if YAML loading fails
            mcp_host = config.server.api_host

        mcp_port = config.server.api_port
        mcp_url = f"http://{mcp_host}:{mcp_port}"

        # Generate API key hint (if configured)
        api_key_configured = bool(config.server.api_key)
        auth_note = "(authenticated)" if api_key_configured else "(check config.yaml for API key)"

        return f"""I am Orchestrator #{instance_number} for GiljoAI Project "{project_name}".

IDENTITY:
- Orchestrator ID: {orchestrator_id}
- Project ID: {project_id}
- Tenant Key: {self.tenant_key}

MCP CONNECTION:
- Server URL: {mcp_url}
- Tool Prefix: mcp__giljo-mcp__
- Auth Status: {auth_note}

YOUR ROLE: PROJECT STAGING (NOT EXECUTION)
You are STAGING the project by creating a mission plan. You will NOT execute the work yourself.
Your job is to: 1) Analyze requirements, 2) Create mission plan, 3) Assign work to specialist agents.

STARTUP SEQUENCE:
1. Verify MCP: mcp__giljo-mcp__health_check()
2. Fetch context: mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}', '{self.tenant_key}')
   └─► Returns: Project.description (user requirements), Product context, Agent templates
3. CREATE MISSION: Analyze requirements → Generate execution plan (70% token reduction)
4. PERSIST MISSION: mcp__giljo-mcp__update_project_mission('{project_id}', your_created_mission)
   └─► Saves to Project.mission field for UI display
5. SPAWN AGENTS: Use spawn_agent_job() to create specialist agent jobs with their missions
   └─► Agents will EXECUTE the work (not you)

CRITICAL DISTINCTIONS:
- Project.description = User-written requirements (READ THIS for context)
- Project.mission = YOUR OUTPUT (condensed execution plan you CREATE in Step 3)
- Agent jobs = Specialist agents who will DO THE ACTUAL WORK (you coordinate them)

CONNECTION TROUBLESHOOTING:
If MCP fails: Check server running at {mcp_url}/health
Logs: ~/.giljo_mcp/logs/mcp_adapter.log

Begin by verifying MCP connection, then fetch context and CREATE the mission plan.
"""

    async def _get_user_field_priorities(self, user_id: str) -> Dict[str, int]:
        """
        Fetch user's field priority configuration.

        Returns dict like:
            {
                'product_vision': 10,  # Full detail
                'architecture': 7,      # Moderate
                'codebase_summary': 4,  # Abbreviated
                'dependencies': 2       # Minimal
            }
        """
        # Get user config from database
        result = await self.db.execute(
            select(User).where(
                User.id == user_id,
                User.tenant_key == self.tenant_key
            )
        )
        user = result.scalar_one_or_none()

        if not user or not user.field_priority_config:
            return {}

        return user.field_priority_config

    async def generate_execution_prompt(
        self,
        orchestrator_job_id: str,
        project_id: str,
        claude_code_mode: bool = False
    ) -> str:
        """
        Generate execution phase prompt for orchestrator.

        Handover 0109: Generates thin client prompts for project execution phase.
        Supports TWO modes:
        - Multi-terminal: User manually launches agents in separate terminals
        - Claude Code: Orchestrator spawns sub-agents using Task tool

        Args:
            orchestrator_job_id: Existing orchestrator job UUID
            project_id: Project UUID
            claude_code_mode: True for Claude Code subagent spawning, False for multi-terminal

        Returns:
            Thin prompt for execution phase (~15-20 lines)

        Raises:
            ValueError: If orchestrator job or project not found
        """
        # Fetch orchestrator job
        orch_stmt = select(MCPAgentJob).where(
            and_(
                MCPAgentJob.job_id == orchestrator_job_id,
                MCPAgentJob.tenant_key == self.tenant_key
            )
        )
        orch_result = await self.db.execute(orch_stmt)
        orchestrator = orch_result.scalar_one_or_none()

        if not orchestrator:
            raise ValueError(f"Orchestrator job {orchestrator_job_id} not found")

        # Fetch project
        project_stmt = select(Project).where(
            and_(
                Project.id == project_id,
                Project.tenant_key == self.tenant_key
            )
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            raise ValueError(f"Project {project_id} not found")

        # Fetch specialist agent jobs for this project (exclude orchestrator)
        agents_stmt = select(MCPAgentJob).where(
            and_(
                MCPAgentJob.project_id == project_id,
                MCPAgentJob.tenant_key == self.tenant_key,
                MCPAgentJob.agent_type != "orchestrator"
            )
        ).order_by(MCPAgentJob.created_at)

        agents_result = await self.db.execute(agents_stmt)
        agent_jobs = agents_result.scalars().all()

        # Generate appropriate prompt based on mode
        if claude_code_mode:
            return self._build_claude_code_execution_prompt(
                orchestrator_id=orchestrator_job_id,
                project=project,
                agent_jobs=agent_jobs
            )
        else:
            return self._build_multi_terminal_execution_prompt(
                orchestrator_id=orchestrator_job_id,
                project=project,
                agent_jobs=agent_jobs
            )

    def _build_multi_terminal_execution_prompt(
        self,
        orchestrator_id: str,
        project,
        agent_jobs: list
    ) -> str:
        """
        Build multi-terminal mode execution prompt.

        User manually launches agents in separate terminals.
        Orchestrator coordinates their work via MCP.
        """
        # Format agent list
        agent_list_lines = []
        if agent_jobs:
            for agent in agent_jobs:
                agent_list_lines.append(f"- {agent.agent_name} (Agent ID: {agent.job_id})")
        else:
            agent_list_lines.append("(No agents spawned yet)")

        agent_list = "\n".join(agent_list_lines)

        return f"""PROJECT EXECUTION PHASE - MULTI-TERMINAL MODE

Orchestrator ID: {orchestrator_id}
Project: {project.name}
Tenant Key: {self.tenant_key}

CONTEXT:
- Project mission created and persisted
- Specialist agents spawned and waiting
- User launching agents in separate terminal windows

YOUR ROLE: COORDINATE AGENT WORKFLOW
1. Monitor dashboard for agent progress updates
2. Respond to agent messages via MCP
3. Track completion status
4. Handle blockers and escalations

IMPORTANT:
- Agents check in via acknowledge_job()
- You coordinate, agents execute
- User manually manages terminal windows

AGENT TEAM:
{agent_list}

Monitor workflow via: mcp__giljo-mcp__get_workflow_status('{project.id}', '{self.tenant_key}')
"""

    def _build_claude_code_execution_prompt(
        self,
        orchestrator_id: str,
        project,
        agent_jobs: list
    ) -> str:
        """
        Build Claude Code subagent mode execution prompt.

        Orchestrator spawns sub-agents using Task tool.
        Sub-agents receive identity via instructions string.
        """
        # Format agent list with missions
        agent_spawn_lines = []
        if agent_jobs:
            for idx, agent in enumerate(agent_jobs, 1):
                mission = agent.mission or "(No mission assigned)"
                agent_spawn_lines.append(
                    f"{idx}. {agent.agent_name}:\n"
                    f"   - Mission: {mission}\n"
                    f"   - Agent ID: {agent.job_id}\n"
                    f"   - Job ID: {agent.job_id}"
                )
        else:
            agent_spawn_lines.append("(No agents spawned yet - use spawn_agent_job() first)")

        agent_list = "\n\n".join(agent_spawn_lines)

        return f"""PROJECT EXECUTION PHASE - CLAUDE CODE SUBAGENT MODE

Orchestrator ID: {orchestrator_id}
Project: {project.name}
Tenant Key: {self.tenant_key}

YOUR ROLE: SPAWN & COORDINATE SUB-AGENTS

STEP 1: ACTIVATE AGENT TEAM
For each agent below, spawn Claude Code sub-agent using Task tool:

{agent_list}

(Pattern: spawn_agent_job() already called during staging - use existing IDs)

STEP 2: REMIND EACH SUB-AGENT
- acknowledge_job(job_id="{{job_id}}", agent_id="{{agent_id}}", tenant_key="{self.tenant_key}")
- report_progress() after milestones
- receive_messages() for commands
- complete_job() when done

STEP 3: COORDINATE WORKFLOW
- Monitor via get_workflow_status()
- Respond to agent messages
- Handle blockers

Reference: See Handover 0106b for full sub-agent spawn instructions
"""
