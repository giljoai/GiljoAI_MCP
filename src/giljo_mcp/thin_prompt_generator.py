"""
Thin Client Prompt Generator (Handover 0088, 0315)

REPLACES: OrchestratorPromptGenerator (prompt_generator.py)

KEY DIFFERENCE: Generates ~600 token prompts with MCP tool references (Handover 0315).
Orchestrators fetch context on-demand via MCP tools (context prioritization enabled).

Architecture (Handover 0315):
- User configures priorities (Handover 0313) and depth (Handover 0314)
- Generator creates thin prompt listing available MCP tools by priority
- Orchestrator fetches context on-demand via MCP tool calls
- Context usage stays within 90% budget (automatic succession trigger)

Token Reduction:
- Fat Prompt (v1.0): ~3500 tokens (inline context embedded in prompt)
- Thin Prompt (v2.0): ~600 tokens (MCP tool references only)
- Reduction: ~82% token savings on initial prompt

MCP Tools (Handover 0315 Phase 1):
- fetch_vision_document(chunking): Vision document chunks
- fetch_360_memory(last_n_projects): Sequential project history
- fetch_git_history(commits): Recent git commits
- fetch_agent_templates(detail): Active agent configurations
- fetch_tech_stack(sections): Tech stack information
- fetch_architecture(depth): Architecture documentation

Priority System (Handover 0313):
- Priority 1 (CRITICAL): Fetch first, essential for mission planning
- Priority 2 (IMPORTANT): Fetch if budget allows, enhances quality
- Priority 3 (NICE_TO_HAVE): Fetch if extra budget, provides additional context
- Priority 4 (EXCLUDED): Not listed in prompt, ignored by orchestrator

Depth Configuration (Handover 0314):
- vision_chunking: "none" | "light" | "moderate" | "heavy"
- memory_last_n_projects: 1 | 3 | 5 | 10
- git_commits: 10 | 25 | 50 | 100
- agent_template_detail: "minimal" | "standard" | "full"
- tech_stack_sections: "required" | "all"
- architecture_depth: "overview" | "detailed"

Author: GiljoAI Development Team
Date: 2025-11-02 (Initial), 2025-11-17 (Handover 0315)
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
    6. Orchestrator calls get_orchestrator_instructions(orchestrator_id)
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
        user_id: Optional[str] = None,
        tool: str = "universal",
        instance_number: int = 1,
        field_priorities: Optional[Dict[str, int]] = None,
        depth_config: Optional[Dict[str, Any]] = None  # NEW PARAMETER (Handover 0315)
    ) -> Dict[str, Any]:
        """
        Generate a thin orchestrator prompt for a specified project.

        Handover 0088: Now uses metadata JSONB column instead of handover_summary
        for storing field_priorities, user_id, tool, and other thin client data.

        Handover 0315: Generates thin prompts (~600 tokens) that reference MCP tools
        for on-demand context fetching, replacing fat prompts (~3500 tokens) with
        inline context.

        Args:
            project_id: Project UUID
            user_id: Optional user ID for tracking and fetching priorities/depth config
            tool: AI coding tool (claude-code, codex, gemini, universal)
            instance_number: Orchestrator instance number (for succession)
            field_priorities: Optional field importance weights (v2.0 categories)
            depth_config: Optional depth configuration (v2.0 depth settings)

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

        # Fetch product for context injection
        product = await self._fetch_product(project_id)

        # Handover 0315: Fetch user priorities and depth config if user_id provided
        if user_id and (not field_priorities or not depth_config):
            from src.giljo_mcp.models.auth import User

            user_stmt = select(User).where(
                and_(
                    User.id == user_id,
                    User.tenant_key == self.tenant_key
                )
            )
            user_result = await self.db.execute(user_stmt)
            user = user_result.scalar_one_or_none()

            if user:
                # Use user config if not provided
                if not field_priorities and user.field_priority_config:
                    field_priorities = user.field_priority_config

                if not depth_config and user.depth_config:
                    depth_config = user.depth_config

        # Apply defaults for depth_config if still not set
        if not depth_config:
            depth_config = {
                "vision_chunking": "moderate",
                "memory_last_n_projects": 3,
                "git_commits": 25,
                "agent_template_detail": "standard",
                "tech_stack_sections": "all",
                "architecture_depth": "overview"
            }

        # Handover 0111 - Issue #2: Check for existing active orchestrator BEFORE creating new one
        # This prevents duplicate orchestrator creation on every "Stage Project" button click
        # Fixed: Include "working" status, remove invalid "active" and "pending" statuses
        existing_orch_stmt = select(MCPAgentJob).where(
            and_(
                MCPAgentJob.project_id == project_id,
                MCPAgentJob.agent_type == "orchestrator",
                MCPAgentJob.tenant_key == self.tenant_key,
                MCPAgentJob.status.in_(["waiting", "working"])  # Only active orchestrator statuses
            )
        ).order_by(MCPAgentJob.created_at.desc())  # Get most recent if multiple exist

        existing_orch_result = await self.db.execute(existing_orch_stmt)
        existing_orchestrator = existing_orch_result.scalars().first()  # Use first() to handle edge case of multiple active orchestrators

        if existing_orchestrator:
            # Reuse existing active orchestrator (no database write)
            orchestrator_id = existing_orchestrator.job_id
            instance_number = existing_orchestrator.instance_number

            logger.info(
                f"[ThinPromptGenerator] Reusing existing orchestrator {orchestrator_id} "
                f"(instance #{instance_number}) for project {project_id}"
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

            # Create orchestrator job with metadata (Handover 0088 + 0315)
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
                # Handover 0088 + 0315: Store thin client data in metadata column
                job_metadata={
                    "field_priorities": field_priorities or {},
                    "depth_config": depth_config,  # NEW: Handover 0315
                    "user_id": user_id,
                    "tool": tool,
                    "created_via": "thin_client_generator"
                }
            )

            self.db.add(orchestrator)
            await self.db.commit()
            await self.db.refresh(orchestrator)

            logger.info(
                f"[ThinPromptGenerator] Created orchestrator {orchestrator_id} "
                f"(instance #{instance_number})"
            )

        # Handover 0315: Generate thin prompt with MCP tool references (NOT fat prompt)
        thin_prompt = await self._generate_thin_prompt(
            orchestrator_id=orchestrator_id,
            project_id=project_id,
            project=project,
            product=product,
            instance_number=instance_number,
            tool=tool,
            field_priorities=field_priorities or {},
            depth_config=depth_config
        )

        # Estimate prompt tokens (rough: 1 token ≈ 4 characters)
        estimated_tokens = len(thin_prompt) // 4

        logger.info(
            f"[ThinPromptGenerator] Generated thin prompt for {orchestrator_id}: "
            f"~{estimated_tokens} tokens (target: 600, reduction from fat: ~{3500 - estimated_tokens})"
        )

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

MCP TOOLS AVAILABLE (ALL start with "mcp__giljo-mcp__"):
✓ health_check() - Verify MCP connection
✓ get_orchestrator_instructions(orchestrator_id, tenant_key) - Fetch context
✓ update_project_mission(project_id, mission) - Save mission plan
✓ spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key) - Create agents
✓ get_workflow_status(project_id, tenant_key) - Check spawned agents

STARTUP SEQUENCE:
1. Verify MCP: mcp__giljo-mcp__health_check()
2. Fetch context: mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}', '{self.tenant_key}')
   └─► Returns: Project.description (user requirements), Product context, Agent templates
3. CREATE MISSION: Analyze requirements → Generate execution plan (context prioritization and orchestration)
4. PERSIST MISSION: mcp__giljo-mcp__update_project_mission('{project_id}', your_created_mission)
   └─► Saves to Project.mission field for UI display
5. SPAWN AGENTS: mcp__giljo-mcp__spawn_agent_job() to create specialist agent jobs
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

    async def _generate_thin_prompt(
        self,
        orchestrator_id: str,
        project_id: str,
        project: Any,
        product: Any,
        instance_number: int,
        tool: str,
        field_priorities: Dict[str, int],
        depth_config: Dict[str, Any]
    ) -> str:
        """
        Generate thin prompt listing available MCP tools by priority (Handover 0315).

        Returns ~600 token prompt (vs ~3500 in fat prompt) that references MCP tools
        for on-demand context fetching.

        Args:
            orchestrator_id: Orchestrator job UUID
            project_id: Project UUID
            project: Project model
            product: Product model
            instance_number: Orchestrator instance number
            tool: AI coding tool (claude-code, codex, gemini, universal)
            field_priorities: User field priority configuration (1=CRITICAL, 2=IMPORTANT, 3=NICE_TO_HAVE, 4=EXCLUDED)
            depth_config: User depth configuration (vision_chunking, memory_last_n_projects, etc.)

        Returns:
            Thin prompt with MCP tool references grouped by priority
        """
        # Group MCP tools by priority
        priority_groups = {
            1: [],  # CRITICAL
            2: [],  # IMPORTANT
            3: [],  # NICE_TO_HAVE
            4: []   # EXCLUDED (don't list)
        }

        # Map categories to MCP tools with depth parameters (from Handover 0315 Phase 1)
        # CRITICAL: tenant_key must be passed to all tools for multi-tenant isolation
        category_to_tool = {
            "product_core": [
                f"fetch_tech_stack(product_id='{product.id}', tenant_key='{self.tenant_key}', sections='{depth_config.get('tech_stack_sections', 'all')}')",
                f"fetch_architecture(product_id='{product.id}', tenant_key='{self.tenant_key}', depth='{depth_config.get('architecture_depth', 'overview')}')"
            ],
            "vision_documents": [
                f"fetch_vision_document(product_id='{product.id}', tenant_key='{self.tenant_key}', chunking='{depth_config.get('vision_chunking', 'moderate')}')"
            ],
            "agent_templates": [
                f"get_available_agents(tenant_key='{self.tenant_key}', active_only=True)"
            ],
            "project_context": [
                # Inline project data (small, ~200 tokens) - NOT an MCP tool
                None  # Special case: embedded inline below
            ],
            "memory_360": [
                f"fetch_360_memory(product_id='{product.id}', tenant_key='{self.tenant_key}', last_n_projects={depth_config.get('memory_last_n_projects', 3)})"
            ],
            "git_history": [
                f"fetch_git_history(product_id='{product.id}', tenant_key='{self.tenant_key}', commits={depth_config.get('git_commits', 25)})"
            ]
        }

        # Group tools by priority
        for category, priority in field_priorities.items():
            if category in category_to_tool:
                tools = category_to_tool[category]
                if tools and tools[0] is not None:  # Skip None entries (inline data)
                    priority_groups[priority].extend(tools)

        # Get MCP server configuration
        config = get_config()

        # Use external_host (user-facing IP) not api_host (bind address 0.0.0.0)
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

        # Build thin prompt with MCP tool references
        prompt = f"""I am Orchestrator #{instance_number} for GiljoAI Project "{project.name}".

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

PROJECT CONTEXT (Inline - ~200 tokens):
- Name: {project.name}
- Description: {project.description or '(No description provided)'}
- Mission: {project.mission or '(Mission will be created by you)'}

MCP CONTEXT TOOLS AVAILABLE (Fetch on-demand by priority):

Priority 1 (CRITICAL - Fetch First):
"""

        # Add Priority 1 tools
        if priority_groups[1]:
            for tool_ref in priority_groups[1]:
                prompt += f"  - `{tool_ref}`\n"
        else:
            prompt += "  (No CRITICAL context tools configured)\n"

        prompt += "\nPriority 2 (IMPORTANT - Fetch if Budget Allows):\n"

        # Add Priority 2 tools
        if priority_groups[2]:
            for tool_ref in priority_groups[2]:
                prompt += f"  - `{tool_ref}`\n"
        else:
            prompt += "  (No IMPORTANT context tools configured)\n"

        prompt += "\nPriority 3 (NICE_TO_HAVE - Fetch if Extra Budget):\n"

        # Add Priority 3 tools
        if priority_groups[3]:
            for tool_ref in priority_groups[3]:
                prompt += f"  - `{tool_ref}`\n"
        else:
            prompt += "  (No NICE_TO_HAVE context tools configured)\n"

        # Add workflow instructions
        prompt += """

MCP TOOL LIMITS:
Each tool call returns <24K tokens. For large content:
- Vision/Memory tools support pagination (offset/limit)
- Check metadata.has_more for additional calls
- Make unlimited calls as needed

WORKFLOW:
1. Fetch context by priority (1→2→3) within token budget
2. Create condensed mission plan from fetched context
3. Persist mission: update_project_mission(project_id, mission)
4. Spawn specialist agents: spawn_agent_job()
5. Monitor: get_workflow_status(project_id, tenant_key)

Trigger succession if context usage >90%.
Claude Code: Use TodoWrite tool to track workflow progress.

CRITICAL DISTINCTIONS:
- Project.description = User-written requirements (already provided above)
- Project.mission = YOUR OUTPUT (condensed execution plan you CREATE in Step 2)
- Agent jobs = Specialist agents who will DO THE ACTUAL WORK (you coordinate them)

MCP CORE TOOLS (Always Available):
✓ mcp__giljo-mcp__health_check() - Verify MCP connection
✓ mcp__giljo-mcp__get_orchestrator_instructions('{orchestrator_id}', '{self.tenant_key}') - Fetch full context
✓ mcp__giljo-mcp__update_project_mission(project_id, mission) - Save mission plan
✓ mcp__giljo-mcp__spawn_agent_job(agent_type, agent_name, mission, project_id, tenant_key) - Create agents
✓ mcp__giljo-mcp__get_workflow_status(project_id, tenant_key) - Check spawned agents

CONNECTION TROUBLESHOOTING:
If MCP fails: Check server running at {mcp_url}/health
Logs: ~/.giljo_mcp/logs/mcp_adapter.log

Begin by verifying MCP connection, then fetch context by priority, and CREATE the mission plan.
"""

        return prompt

    def _inject_360_memory(self, product) -> str:
        """
        Inject 360 Memory System context into prompt.

        ALWAYS included in orchestrator prompts to provide cumulative product knowledge.

        Args:
            product: Product model with product_memory JSONB field

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
        if not product or not product.product_memory:
            return """
## 360 Memory System
No previous project history available. Starting fresh.
"""

        history_entries = product.product_memory.get("sequential_history", [])
        context_data = product.product_memory.get("context", {})
        objectives = context_data.get("objectives", []) if isinstance(context_data, dict) else []

        history_count = len(history_entries)

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
            for obj in objectives[:3]:  # Limit to top 3 objectives
                memory_lines.append(f"- {obj}")

        memory_lines.append("\nAccess via: product_memory.sequential_history and product_memory.context")

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
            "Combine git history with 360 Memory for full context."
        ]

        return "\n".join(git_lines)

    async def _fetch_product(self, project_id: str) -> Optional[Any]:
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
            and_(
                ProjectModel.id == project_id,
                ProjectModel.tenant_key == self.tenant_key
            )
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        if not project:
            return None

        # Fetch product via project.product_id
        product_stmt = select(Product).where(
            and_(
                Product.id == project.product_id,
                Product.tenant_key == self.tenant_key
            )
        )
        product_result = await self.db.execute(product_stmt)
        product = product_result.scalar_one_or_none()

        return product

    async def _fetch_project(self, project_id: str) -> Optional[Any]:
        """
        Fetch project by ID.

        Args:
            project_id: Project UUID

        Returns:
            Project model or None if not found
        """
        from src.giljo_mcp.models.projects import Project as ProjectModel

        project_stmt = select(ProjectModel).where(
            and_(
                ProjectModel.id == project_id,
                ProjectModel.tenant_key == self.tenant_key
            )
        )
        project_result = await self.db.execute(project_stmt)
        project = project_result.scalar_one_or_none()

        return project

    async def _build_thin_prompt_with_memory(
        self,
        orchestrator_id: str,
        project_id: str,
        project_name: str,
        instance_number: int,
        tool: str,
        product,
        field_priorities: Optional[Dict[str, int]] = None
    ) -> str:
        """
        Build thin client prompt WITH 360 Memory, Git integration, and Agent templates.

        This extends _build_thin_prompt with context injection.

        Handover 0306: Now includes agent templates based on field priority configuration.

        Args:
            orchestrator_id: Orchestrator job UUID
            project_id: Project UUID
            project_name: Project display name
            instance_number: Orchestrator instance number
            tool: AI coding tool (claude-code, codex, gemini, universal)
            product: Product model for context injection
            field_priorities: Optional user field priority config

        Returns:
            Enhanced thin prompt with memory, git, and agent template sections
        """
        # Get base prompt (existing logic)
        base_prompt = self._build_thin_prompt(
            orchestrator_id=orchestrator_id,
            project_id=project_id,
            project_name=project_name,
            instance_number=instance_number,
            tool=tool
        )

        # Inject 360 Memory (ALWAYS)
        memory_section = self._inject_360_memory(product)

        # Inject Git integration (CONDITIONAL)
        git_section = self._inject_git_instructions(product)

        # Handover 0306: Inject Agent Templates (CONDITIONAL - based on priority)
        # Handover 0246c: Agent templates no longer embedded (use get_available_agents MCP tool)
        agent_section = ""  # Deprecated: templates fetched via MCP tool

        # Insert injections BEFORE "YOUR ROLE" section
        # This places context EARLY in the prompt for maximum impact
        insertion_marker = "YOUR ROLE: PROJECT STAGING"

        if insertion_marker in base_prompt:
            # Split at marker and insert context
            before_role, after_role = base_prompt.split(insertion_marker, 1)
            enhanced_prompt = (
                before_role +
                memory_section +
                git_section +
                agent_section +
                "\n" +
                insertion_marker +
                after_role
            )
        else:
            # Fallback: append at end if marker not found
            enhanced_prompt = base_prompt + memory_section + git_section + agent_section

        return enhanced_prompt

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
        return self._build_multi_terminal_execution_prompt(
            orchestrator_id=orchestrator_job_id,
            project=project,
            agent_jobs=agent_jobs
        )

    async def generate_staging_prompt(
        self,
        orchestrator_id: str,
        project_id: str,
        claude_code_mode: bool = False
    ) -> str:
        """
        Generate staging phase prompt with 7-task workflow.

        Handover 0246a: Implements complete staging workflow with:
        1. Identity & Context Verification
        2. MCP Health Check
        3. Environment Understanding
        4. Agent Discovery & Version Check (CRITICAL)
        5. Context Prioritization & Mission Creation
        6. Agent Job Spawning
        7. Activation

        Handover 0247 Gaps:
        - Gap 1: Version comparison logic added to Task 4
        - Gap 2: CLAUDE.md reading instruction added to Task 3

        Args:
            orchestrator_id: Orchestrator job UUID
            project_id: Project UUID
            claude_code_mode: Use Claude Code CLI mode (default: False)

        Returns:
            Staging prompt (~800-1000 tokens with all tasks)

        Raises:
            ValueError: If project or product not found
        """
        logger.info(
            "Generating staging prompt",
            extra={
                "orchestrator_id": orchestrator_id,
                "project_id": project_id,
                "claude_code_mode": claude_code_mode,
                "tenant_key": self.tenant_key
            }
        )

        # Fetch required data (reuse existing helpers)
        project = await self._fetch_project(project_id)
        product = await self._fetch_product(project_id)

        if not project or not product:
            logger.error(
                f"Project {project_id} or product not found",
                extra={"project_id": project_id, "tenant_key": self.tenant_key}
            )
            raise ValueError(f"Project {project_id} or its product not found")

        # Determine execution mode label
        execution_mode = "Claude Code CLI" if claude_code_mode else "Manual Multi-Terminal"

        # Build 7-task staging prompt (optimized for <1200 tokens)
        prompt = f"""STAGING WORKFLOW: {project.name}
{'='*70}
IDENTITY
Project ID: {project_id}
Product ID: {product.id}
Tenant: {self.tenant_key}
Orchestrator: {orchestrator_id}
Mode: {execution_mode}
WebSocket: Active

{'='*70}
TASK 1: IDENTITY & CONTEXT VERIFICATION
{'='*70}
Verify project identity and orchestrator connection.

1. Confirm project ID: {project_id}
2. Confirm product ID: {product.id}
3. Confirm tenant: {self.tenant_key}
4. Verify orchestrator: {orchestrator_id}
5. Check WebSocket

Result: All identifiers confirmed | Timeout: 10s

{'='*70}
TASK 2: MCP HEALTH CHECK
{'='*70}
Verify MCP server health and tool availability.

1. Call health_check() MCP tool
2. Verify response < 2s
3. List MCP tools
4. Validate: get_available_agents(), fetch_product_context(), fetch_vision_document(), fetch_git_history(), fetch_360_memory()

Result: MCP confirmed | Timeout: 10s

{'='*70}
TASK 3: ENVIRONMENT UNDERSTANDING
{'='*70}
Understand project environment.

1. Read CLAUDE.md in project folder (if exists)
2. Extract tech stack
3. Parse structure
4. Load config

Result: Environment analyzed | Timeout: 30s

{'='*70}
TASK 4: AGENT DISCOVERY & VERSION CHECK
{'='*70}
Discover agents and validate compatibility.

1. Call get_available_agents(include_versions=true) MCP tool
   Returns: agents with version, capabilities, type
2. Execute: ls ~/.claude/agents/*.md (or Windows equivalent)
   Compare expected vs actual filenames
3. For each agent:
   - Extract version from MCP response
   - Verify file exists with correct version date
   - Check compatibility
   - Validate capabilities
   - Verify initialization
4. Build compatibility matrix
5. WARN USER if version mismatch detected
   Example: MCP expects implementer_11242024.md but found implementer_11222024.md

Criteria: version >= min_required, has required_capabilities, status=initialized

CRITICAL: Call get_available_agents() - do NOT hardcode agents

Result: Compatible agents discovered | Timeout: 30s

{'='*70}
TASK 5: CONTEXT PRIORITIZATION & MISSION
{'='*70}
Build unified mission with user priorities.

1. Fetch context via MCP tools:
   - fetch_product_context()
   - fetch_vision_document()
   - fetch_git_history()
   - fetch_360_memory()
2. Synthesize mission (<10K tokens)
3. Store via update_project_mission()

Result: Mission created | Timeout: 60s

{'='*70}
TASK 6: AGENT JOB SPAWNING
{'='*70}
Create agent jobs.

1. For each compatible agent:
   - spawn_agent_job()
   - status: waiting
   - mode: {(claude_code_mode and 'claude_code') or 'manual'}
   - mission from Task 5
2. Verify creation

Result: Jobs created | Timeout: 30s

{'='*70}
TASK 7: PROJECT ACTIVATION
{'='*70}
Activate project and begin orchestration.

1. Set status: active
2. Enable WebSocket
3. Init health monitor
4. Start polling (5s)
5. Track context usage
6. Emit project:activated
7. Log start

Result: Project active | Timeout: 10s | Status: COMPLETE

{'='*70}
END STAGING WORKFLOW
{'='*70}
"""

        # Calculate token count (conservative estimate: 1 token ≈ 4 characters)
        estimated_tokens = len(prompt) // 4

        logger.info(
            "Staging prompt generated successfully",
            extra={
                "orchestrator_id": orchestrator_id,
                "project_id": project_id,
                "project_name": project.name,
                "estimated_tokens": estimated_tokens,
                "prompt_length": len(prompt),
                "execution_mode": execution_mode,
                "tenant_key": self.tenant_key
            }
        )

        return prompt

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
        
        Handover 0247 Gap 3: Added Product ID to identity section.
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
Project ID: {project.id}
Product ID: {project.product_id}
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
        
        Handover 0247 Gap 3: Added Product ID to identity section.
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

        sections = [
            "PROJECT EXECUTION PHASE - CLAUDE CODE SUBAGENT MODE\n",
            f"Orchestrator ID: {orchestrator_id}",
            f"Project ID: {project.id}",
            f"Product ID: {project.product_id}",
            f"Project: {project.name}",
            f"Tenant Key: {self.tenant_key}\n",
            "YOUR ROLE: SPAWN & COORDINATE SUB-AGENTS\n",
            "STEP 1: ACTIVATE AGENT TEAM",
            "For each agent below, spawn Claude Code sub-agent using Task tool:\n",
            agent_list + "\n",
            "(Pattern: spawn_agent_job() already called during staging - use existing IDs)\n",
            "STEP 2: REMIND EACH SUB-AGENT",
            f"- acknowledge_job(job_id=\"{{{{job_id}}}}\", agent_id=\"{{{{agent_id}}}}\", tenant_key=\"{self.tenant_key}\")",
            "- report_progress() after milestones",
            "- receive_messages() for commands",
            "- complete_job() when done\n",
            "STEP 3: COORDINATE WORKFLOW",
            "- Monitor via get_workflow_status()",
            "- Respond to agent messages",
            "- Handle blockers\n",
            "Reference: See Handover 0106b for full sub-agent spawn instructions"
        ]
        
        return "\n".join(sections)

    def _get_field_priority(self, field_name: str, user_priorities: Optional[dict]) -> Optional[int]:
        """
        Get priority for a specific field from user config or defaults.

        Args:
            field_name: Field name (e.g., "agent_templates")
            user_priorities: User's custom field priority config (optional)

        Returns:
            Priority level (1-3) or None if unassigned

        Example:
            >>> priority = self._get_field_priority("agent_templates", {"agent_templates": 2})
            >>> print(priority)
            2
        """
        from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY

        # Check user custom priorities first
        if user_priorities and field_name in user_priorities:
            return user_priorities[field_name]

        # Fall back to default priorities
        default_fields = DEFAULT_FIELD_PRIORITY.get("fields", {})
        return default_fields.get(field_name)
