"""
ProjectOrchestrator - Core orchestration engine for GiljoAI MCP.

Manages project lifecycle, agent spawning, handoffs, context tracking,
and multi-project concurrency with tenant isolation.

⚠️  IMPORTANT - Product Vision Field Migration (Handover 0128e):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
This file has been migrated to use Product.vision_documents relationship.
DO NOT use deprecated Product fields (vision_path, vision_document, vision_type, chunked).
✅ Use: product.primary_vision_text, product.primary_vision_path, product.vision_is_chunked
See: src/giljo_mcp/models/products.py for helper properties
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import selectinload, joinedload

from .agent_job_manager import AgentJobManager
from .agent_selector import AgentSelector
from .context_management.chunker import VisionDocumentChunker
from .database import get_db_manager
from .enums import AgentRole, ContextStatus, ProjectStatus, ProjectType
from .mission_planner import MissionPlanner
from .models import AgentTemplate, Message, Product, Project
from .models.agent_identity import AgentJob, AgentExecution
from .agent_message_queue import AgentMessageQueue
from .optimization import MissionOptimizationInjector, SerenaOptimizer
from .template_adapter import MissionTemplateGeneratorV2
from .workflow_engine import WorkflowEngine


logger = logging.getLogger(__name__)


# ContextStatus enum moved to enums.py


class ProjectOrchestrator:
    """
    Core orchestration engine managing project lifecycle, agents, and context.

    Features:
    - State machine for project lifecycle
    - Agent spawning with role templates
    - Intelligent handoff mechanism
    - Context usage tracking with indicators
    - Multi-project support with tenant isolation
    """

    DEFAULT_AGENT_CONTEXT_BUDGET = 30000  # Default context budget per agent

    # Agent mission templates
    AGENT_MISSIONS = {
        AgentRole.ORCHESTRATOR: """
        You are the project orchestrator responsible for:
        - Breaking down the project mission into actionable tasks
        - Coordinating agent activities and handoffs
        - Monitoring progress and context usage
        - Ensuring project completion within budget
        """,
        AgentRole.ANALYZER: """
        You are the analyzer responsible for:
        - Understanding requirements and constraints
        - Analyzing existing codebase and patterns
        - Creating architectural designs and specifications
        - Identifying potential risks and dependencies
        """,
        AgentRole.IMPLEMENTER: """
        You are the implementer responsible for:
        - Writing clean, maintainable code
        - Following architectural specifications exactly
        - Implementing features according to requirements
        - Ensuring code quality and standards compliance
        """,
        AgentRole.TESTER: """
        You are the tester responsible for:
        - Writing comprehensive test suites
        - Validating implementation against requirements
        - Finding and documenting bugs
        - Ensuring code coverage and quality metrics
        """,
        AgentRole.REVIEWER: """
        You are the reviewer responsible for:
        - Reviewing code for quality and standards
        - Identifying potential improvements
        - Ensuring security best practices
        - Validating architectural compliance
        """,
    }

    def __init__(self):
        """Initialize the orchestrator."""
        self.db_manager = get_db_manager()
        self._active_projects: dict[str, Project] = {}
        self._context_monitors: dict[str, asyncio.Task] = {}
        # Initialize template generator
        self.template_generator = MissionTemplateGeneratorV2(self.db_manager)
        # Initialize Serena optimization system
        self.serena_optimizer = None  # Initialize lazily per tenant

        # Phase 2: Initialize orchestration components (Handover 0020)
        self.mission_planner = MissionPlanner(self.db_manager)
        self.agent_selector = AgentSelector(self.db_manager)
        self.workflow_engine = WorkflowEngine(self.db_manager)

        # Phase 3: Initialize agent job manager (Handover 0045)
        self.agent_job_manager = AgentJobManager(self.db_manager)

        # Messaging queue (Handover 0120: MessageQueue with compatibility layer)
        self.comm_queue = AgentMessageQueue(self.db_manager)

    # ========================================================================
    # HANDOVER 0045 - Phase 3: Multi-Tool Agent Orchestration Routing
    # ========================================================================

    async def _get_agent_template(
        self, role: str, tenant_key: str, product_id: Optional[str] = None
    ) -> Optional[AgentTemplate]:
        """
        Get agent template for role with cascade resolution.

        Resolution order (highest to lowest priority):
        1. Product-specific template (if product_id provided)
        2. Tenant-specific template (user customizations)
        3. System default template (is_default=True)

        Args:
            role: Agent role name (e.g., "implementer", "tester")
            tenant_key: Tenant key for multi-tenant isolation
            product_id: Optional product ID for product-specific templates

        Returns:
            AgentTemplate instance or None if no template found

        Multi-tenant isolation:
            - Only returns templates owned by tenant
            - No cross-tenant leakage possible
        """
        async with self.db_manager.get_session_async() as session:
            # Try product-specific template first (if product_id provided)
            if product_id:
                stmt = select(AgentTemplate).where(
                    AgentTemplate.tenant_key == tenant_key,
                    AgentTemplate.role == role,
                    AgentTemplate.product_id == product_id,
                    AgentTemplate.is_active == True,
                )
                result = await session.execute(stmt)
                template = result.scalar_one_or_none()
                if template:
                    logger.info(
                        f"[_get_agent_template] Found product-specific template for "
                        f"role={role}, product={product_id}, tenant={tenant_key}"
                    )
                    return template

            # Try tenant-specific template (no product_id constraint)
            stmt = select(AgentTemplate).where(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.role == role,
                AgentTemplate.product_id == None,
                AgentTemplate.is_active == True,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                logger.info(
                    f"[_get_agent_template] Found tenant-specific template for role={role}, tenant={tenant_key}"
                )
                return template

            # Try system default template (is_default=True, any tenant)
            stmt = select(AgentTemplate).where(
                AgentTemplate.role == role,
                AgentTemplate.is_default == True,
                AgentTemplate.is_active == True,
            )
            result = await session.execute(stmt)
            template = result.scalar_one_or_none()
            if template:
                logger.info(f"[_get_agent_template] Found system default template for role={role}")
                return template

            logger.warning(
                f"[_get_agent_template] No template found for role={role}, tenant={tenant_key}, product={product_id}"
            )
            return None

    async def _spawn_claude_code_agent(
        self,
        session,
        project: Project,
        role: AgentRole,
        template: AgentTemplate,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
    ) -> AgentExecution:
        """
        Spawn Claude Code agent for project execution.

        Process:
        1. Generate mission with MCP coordination instructions
        2. Apply Serena optimization for context prioritization
        3. Create Agent record with mode='claude'

        Args:
            project: Project instance
            role: Agent role enum
            template: AgentTemplate instance
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions

        Returns:
            Created Agent instance with mode='claude'

        Integration:
            - Includes MCP checkpoint instructions in mission
            - Applies Serena optimization for context prioritization
            - Agent templates must be manually exported via My Settings → Integrations
        """
        # 1. Generate mission with MCP coordination instructions
        if custom_mission:
            mission = custom_mission
        else:
            # Generate mission using template generator
            mission = await self.template_generator.generate_agent_mission(
                role=role.value,
                project_name=project.name,
                custom_mission=None,
                additional_instructions=additional_instructions,
            )

        # Add MCP coordination protocol to mission
        mcp_instructions = self._generate_mcp_instructions(project.tenant_key, role.value, mission)
        mission = f"{mission}\n\n{mcp_instructions}"

        # 2. Apply Serena optimization
        optimizer = self._get_serena_optimizer(project.tenant_key)
        if optimizer:
            try:
                injector = MissionOptimizationInjector(optimizer)

                context_data = {
                    "project_id": project.id,
                    "project_type": "general",
                    "codebase_size": "medium",
                    "primary_language": "python",
                }

                optimized_mission = await injector.inject_optimization_rules(
                    agent_role=role.value, mission=mission, context_data=context_data
                )

                logger.info(f"[_spawn_claude_code_agent] Enhanced {role.value} agent mission with Serena optimization")
                mission = optimized_mission

            except Exception as e:
                logger.warning(f"[_spawn_claude_code_agent] Failed to inject Serena optimization: {e}")
                # Continue with original mission

        # 3. Create AgentJob (work order) and AgentExecution (executor instance)
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=project.tenant_key,
            project_id=project.id,
            mission=mission,
            job_type=role.value,
            status="active",
        )
        session.add(agent_job)

        # Create AgentExecution (executor instance)
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=project.tenant_key,
            agent_type=role.value,
            agent_name=role.value,
            instance_number=1,
            status="waiting",
            progress=0,
            tool_type="claude",
            messages=[],
            spawned_by=parent_agent_id,
            meta_data={
                "template_id": template.id,
                "template_name": template.name,
                "tool": template.tool,
            },
        )
        session.add(agent_execution)
        await session.commit()
        await session.refresh(agent_execution)

        logger.info(
            f"[_spawn_claude_code_agent] Created Claude Code agent: role={role.value}, "
            f"template={template.name}, project={project.id}, job_id={job_id}, agent_id={agent_id}"
        )

        return agent_execution

    # ========================================================================
    # Messaging helpers (Handover 0118)
    # ========================================================================

    async def send_welcome_broadcast(self, project_id: str) -> int:
        """Send a welcome/directive message to all active agent jobs in a project.

        Uses the per-job JSONB message queue so agents can retrieve via
        get_next_instruction/receive_messages.

        Returns the number of messages sent.
        """
        async with self.db_manager.get_session_async() as session:
            # Get project and jobs
            result = await session.execute(
                select(Project).where(Project.id == project_id).options(selectinload(Project.agent_jobs_v2))
            )
            project = result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            sent = 0
            tenant_key = project.tenant_key
            jobs = [j for j in project.agent_jobs_v2]

            for job in jobs:
                try:
                    await self.comm_queue.send_message(
                        session=session,
                        job_id=job.job_id,
                        tenant_key=tenant_key,
                        from_agent="orchestrator",
                        to_agent=job.job_type,
                        message_type="orchestrator_instruction",
                        content=(
                            "Team assembled. Check messages before starting. "
                            "Report progress at milestones. Flag issues immediately."
                        ),
                        priority=1,
                    )
                    sent += 1
                except Exception:
                    # Continue sending to others; errors are logged at queue level
                    continue

            return sent

    async def broadcast_team_status(self, project_id: str) -> dict[str, Any]:
        """Broadcast a concise team status to all agents in the project."""
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(Project).where(Project.id == project_id).options(selectinload(Project.agent_jobs_v2))
            )
            project = result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            tenant_key = project.tenant_key
            jobs = list(project.agent_jobs_v2)

            # Compose a short status line
            parts = []
            for job in jobs:
                parts.append(f"{job.job_type}:{job.status}")
            content = "Team status: " + ", ".join(parts)

            sent = 0
            for job in jobs:
                try:
                    await self.comm_queue.send_message(
                        session=session,
                        job_id=job.job_id,
                        tenant_key=tenant_key,
                        from_agent="orchestrator",
                        to_agent=job.job_type,
                        message_type="orchestrator_instruction",
                        content=content,
                        priority=0,
                    )
                    sent += 1
                except Exception:
                    continue

            return {"sent": sent, "content": content}

    async def poll_and_handle_messages(
        self,
        project_id: str,
        iterations: int = 10,
        interval_seconds: float = 3.0,
    ) -> dict[str, Any]:
        """Poll agent message queues and handle progress/errors.

        - Acknowledges unread messages addressed to orchestrator or broadcast
        - For 'error' messages: replies with a directive placeholder
        - Returns summary counts
        """
        import asyncio as _asyncio

        progress_count = 0
        error_count = 0
        acknowledged = 0

        async with self.db_manager.get_session_async() as session:
            # Load project and jobs
            result = await session.execute(
                select(Project).where(Project.id == project_id).options(selectinload(Project.agent_jobs_v2))
            )
            project = result.scalar_one_or_none()
            if not project:
                raise ValueError(f"Project {project_id} not found")

            tenant_key = project.tenant_key
            jobs = list(project.agent_jobs_v2)

        # Poll loop (use fresh sessions inside loop for isolation)
        for _ in range(max(1, int(iterations))):
            async with self.db_manager.get_session_async() as session:
                for job in jobs:
                    # Get all unread messages for this job (broadcast or directed to orchestrator)
                    result = await self.comm_queue.get_messages(
                        session=session,
                        job_id=job.job_id,
                        tenant_key=tenant_key,
                        to_agent=None,
                        message_type=None,
                        unread_only=True,
                    )
                    msgs = result.get("messages", []) if isinstance(result, dict) else []

                    for msg in msgs:
                        mtype = msg.get("type")
                        content = msg.get("content", "")

                        # Count and handle
                        if mtype == "progress":
                            progress_count += 1
                        elif mtype == "error":
                            error_count += 1
                            # Send quick directive back to agent with acknowledgment of the error
                            try:
                                await self.comm_queue.send_message(
                                    session=session,
                                    job_id=job.job_id,
                                    tenant_key=tenant_key,
                                    from_agent="orchestrator",
                                    to_agent=job.job_type,
                                    message_type="orchestrator_instruction",
                                    content=(
                                        "Error received. Investigating. Provide minimal repro if possible; "
                                        "stand by for updated instructions."
                                    ),
                                    priority=2,
                                )
                            except Exception:
                                pass

                        # Message will be auto-acknowledged when retrieved via receive_messages

            await _asyncio.sleep(interval_seconds)

        return {
            "progress": progress_count,
            "errors": error_count,
            "acknowledged": acknowledged,
            "iterations": iterations,
        }

    async def _spawn_generic_agent(
        self,
        session,
        project: Project,
        role: AgentRole,
        template: AgentTemplate,
        custom_mission: Optional[str] = None,
        additional_instructions: Optional[str] = None,
        parent_agent_id: Optional[str] = None,
    ) -> AgentExecution:
        """
        Spawn generic agent (Codex/Gemini with job queue).

        Process:
        1. Create MCP job via AgentJobManager
        2. Generate CLI prompt with MCP tool examples
        3. Create Agent record with mode='codex'/'gemini', job_id, status='waiting_acknowledgment'
        4. Store CLI prompt in Agent metadata

        Args:
            project: Project instance
            role: Agent role enum
            template: AgentTemplate instance
            custom_mission: Optional custom mission override
            additional_instructions: Optional additional instructions

        Returns:
            Created Agent instance with mode='codex' or 'gemini', linked to job

        Integration:
            - Uses AgentJobManager for job creation
            - Links Agent to Job via job_id
            - Generates copy-paste ready CLI prompt
        """
        # 1. Generate mission
        if custom_mission:
            mission = custom_mission
        else:
            mission = await self.template_generator.generate_agent_mission(
                role=role.value,
                project_name=project.name,
                custom_mission=None,
                additional_instructions=additional_instructions,
            )

        # Add MCP coordination protocol
        mcp_instructions = self._generate_mcp_instructions(project.tenant_key, role.value, mission)
        full_mission = f"{mission}\n\n{mcp_instructions}"

        # 2. Create AgentJob (work order) and AgentExecution (executor instance)
        job_id = str(uuid4())
        agent_id = str(uuid4())

        # Create AgentJob (work order)
        agent_job = AgentJob(
            job_id=job_id,
            tenant_key=project.tenant_key,
            project_id=project.id,
            mission=full_mission,
            job_type=role.value,
            status="active",
        )
        session.add(agent_job)

        # Create AgentExecution (executor instance)
        agent_execution = AgentExecution(
            agent_id=agent_id,
            job_id=job_id,
            tenant_key=project.tenant_key,
            agent_type=role.value,
            agent_name=role.value,
            instance_number=1,
            status="waiting_acknowledgment",
            progress=0,
            tool_type=template.tool,  # 'codex' or 'gemini'
            messages=[],
            spawned_by=parent_agent_id,
            meta_data={
                "template_id": template.id,
                "template_name": template.name,
                "tool": template.tool,
            },
        )
        session.add(agent_execution)
        await session.commit()
        await session.refresh(agent_execution)

        logger.info(
            f"[_spawn_generic_agent] Created {template.tool} agent: role={role.value}, "
            f"job_id={job_id}, agent_id={agent_id}, project={project.id}"
        )

        # 3. Generate CLI prompt with direct parameters
        cli_prompt = self._generate_cli_prompt(
            job_id=job_id,
            agent_type=role.value,
            mission=full_mission,
            status="waiting_acknowledgment",
            template=template,
            project=project,
            tenant_key=project.tenant_key,
        )

        # Update agent_execution with CLI prompt
        if not agent_execution.meta_data:
            agent_execution.meta_data = {}
        agent_execution.meta_data["cli_prompt"] = cli_prompt
        await session.commit()

        return agent_execution

    def _generate_mcp_instructions(self, tenant_key: str, agent_role: str, mission_text: Optional[str] = None) -> str:
        """
        Generate MCP coordination protocol instructions.

        Includes:
        - Checkpoint recommendations (every 2-3 tasks)
        - MCP tool call examples (acknowledge_job, report_progress, complete_job, report_error)
        - Tenant-specific examples (include tenant_key)

        Args:
            tenant_key: Tenant key for multi-tenant isolation
            agent_role: Agent role for contextualized examples

        Returns:
            Formatted MCP instructions text
        """
        base = f"""
## MCP Coordination Protocol

**IMPORTANT**: Use MCP tools for coordination and progress tracking.

### Checkpointing Guidelines
- Report progress every 2-3 completed tasks
- Use `report_progress` tool to save state
- Include files modified and context used
- Request handoff if context usage exceeds 25K tokens

### MCP Tool Examples

1. **Acknowledge Job** (First step after assignment):
```
acknowledge_job(
    job_id="<your-job-id>",
    agent_id="{agent_role}",
    tenant_key="{tenant_key}"
)
```

2. **Report Progress** (After completing tasks):
```
report_progress(
    job_id="<your-job-id>",
    completed_todo="Implemented user authentication module",
    files_modified=["src/auth.py", "tests/test_auth.py"],
    context_used=15000,
    tenant_key="{tenant_key}"
)
```

3. **Complete Job** (When mission accomplished):
```
complete_job(
    job_id="<your-job-id>",
    result={{
        "summary": "Successfully implemented feature X",
        "files_created": ["src/new_module.py"],
        "files_modified": ["src/main.py"],
        "tests_written": ["tests/test_new_module.py"],
        "coverage": "95%",
        "notes": "All tests passing"
    }},
    tenant_key="{tenant_key}"
)
```

4. **Report Error** (If blocking issues encountered):
```
report_error(
    job_id="<your-job-id>",
    error_type="test_failure",  # build_failure, test_failure, validation_error, dependency_error, runtime_error, unknown
    error_message="<full error details>",
    context="What you were doing when error occurred",
    tenant_key="{tenant_key}"
)
```

5. **Get Next Instruction** (Check for orchestrator messages):
```
get_next_instruction(
    job_id="<your-job-id>",
    agent_type="{agent_role}",
    tenant_key="{tenant_key}"
)
```

### Tenant Isolation
All MCP tool calls MUST include `tenant_key="{tenant_key}"` for multi-tenant isolation.
"""

        # Handover 0277: Optionally append simplified Serena MCP notice when enabled
        try:
            config = self._read_config()
            serena_section = config.get("features", {}).get("serena_mcp", {})
            serena_enabled = bool(serena_section.get("use_in_prompts", False))
        except Exception:
            serena_enabled = False

        if serena_enabled:
            from giljo_mcp.prompt_generation.serena_instructions import generate_serena_instructions
            serena_notice = generate_serena_instructions(enabled=True)
            base = base + "\n\n" + serena_notice

        return base

    def _generate_cli_prompt(
        self,
        job_id: str,
        agent_type: str,
        mission: str,
        status: str,
        template: AgentTemplate,
        project: Project,
        tenant_key: str,
    ) -> str:
        """
        Generate copy-paste ready CLI prompt for Codex/Gemini agents.

        Includes:
        - Job information (job_id, agent_type)
        - Mission text
        - Behavioral rules from template
        - Success criteria from template
        - MCP tool call examples (tenant-specific)

        Args:
            job_id: Job ID
            agent_type: Agent role/type for display purposes
            mission: Mission text
            status: Job status
            template: AgentTemplate instance
            project: Project instance
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Formatted CLI prompt ready for copy-paste

        Usage:
            User copies this prompt and pastes into Codex/Gemini CLI
        """
        behavioral_rules = ""
        if template.behavioral_rules and len(template.behavioral_rules) > 0:
            behavioral_rules = "\n## Behavioral Rules\n" + "\n".join(f"- {rule}" for rule in template.behavioral_rules)

        success_criteria = ""
        if template.success_criteria and len(template.success_criteria) > 0:
            success_criteria = "\n## Success Criteria\n" + "\n".join(
                f"- {criterion}" for criterion in template.success_criteria
            )

        mcp_instructions = self._generate_mcp_instructions(tenant_key, agent_type, mission)

        return f"""
# {template.name} Agent - Job {job_id}

## Job Information
- **Job ID**: `{job_id}`
- **Agent Type**: `{agent_type}`
- **Project**: {project.name}
- **Tenant**: `{tenant_key}`
- **Status**: {status}

## Mission
{mission}

{behavioral_rules}

{success_criteria}

{mcp_instructions}

## Getting Started

1. **First Step**: Acknowledge this job
   ```
   acknowledge_job(
       job_id="{job_id}",
       agent_id="{agent_type}",
       tenant_key="{tenant_key}"
   )
   ```

2. **Work on mission**: Follow the mission instructions above

3. **Report progress**: Every 2-3 completed tasks
   ```
   report_progress(
       job_id="{job_id}",
       completed_todo="Description of what you completed",
       files_modified=["list", "of", "files"],
       context_used=<estimated_tokens>,
       tenant_key="{tenant_key}"
   )
   ```

4. **Complete job**: When mission accomplished
   ```
   complete_job(
       job_id="{job_id}",
       result={{
           "summary": "Mission summary",
           "files_created": [],
           "files_modified": [],
           "tests_written": [],
           "coverage": "percentage",
           "notes": "additional notes"
       }},
       tenant_key="{tenant_key}"
   )
   ```

---
**Copy this entire prompt and paste into your Codex/Gemini CLI to begin work.**
"""

    def _get_serena_optimizer(self, tenant_key: str) -> Optional[SerenaOptimizer]:
        """Get or create SerenaOptimizer for tenant (lazy initialization)"""
        config = self._read_config()
        if not config.get("features", {}).get("serena_mcp", {}).get("use_in_prompts", False):
            return None

        if not self.serena_optimizer:
            self.serena_optimizer = SerenaOptimizer(self.db_manager, tenant_key)
        return self.serena_optimizer

    def _read_config(self) -> dict:
        """Read config.yaml."""
        config_path = Path.cwd() / "config.yaml"
        if not config_path.exists():
            return {}

        try:
            with open(config_path, encoding="utf-8") as f:
                import yaml

                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to read config: {e}")
            return {}

    async def create_project(
        self,
        name: str,
        mission: str,
        tenant_key: Optional[str] = None,
        context_budget: int = 150000,
    ) -> Project:
        """
        Create a new project in DRAFT state.

        Args:
            name: Project name
            mission: Project mission/description
            tenant_key: Optional tenant key for isolation
            context_budget: Internal - hardcoded budget (not user-configurable)

        Returns:
            Created Project instance
        """
        async with self.db_manager.get_session_async() as session:
            # Generate tenant key if not provided
            if not tenant_key:
                tenant_key = self.db_manager.generate_tenant_key()

            project = Project(
                name=name,
                mission=mission,
                tenant_key=tenant_key,
                status=ProjectStatus.INACTIVE.value,  # Handover 0071: Projects start as inactive
                context_budget=context_budget,
                context_used=0,
            )

            session.add(project)
            await session.commit()
            await session.refresh(project)

            logger.info(f"Created project {project.id}: {name}")
            return project

    async def activate_project(self, project_id: str) -> Project:
        """
        Activate a project, transitioning from INACTIVE to ACTIVE (Handover 0071).

        Args:
            project_id: Project UUID

        Returns:
            Updated Project instance
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            if project.status not in [
                ProjectStatus.INACTIVE.value,
                ProjectStatus.COMPLETED.value,
            ]:
                raise ValueError(f"Cannot activate project in {project.status} state")

            project.status = ProjectStatus.ACTIVE.value
            await session.commit()
            await session.refresh(project)

            # Cache active project
            self._active_projects[project_id] = project

            # Start context monitoring
            await self._start_context_monitor(project_id)

            logger.info(f"Activated project {project_id}")
            return project

    async def deactivate_project(self, project_id: str) -> Project:
        """
        Deactivate an active project, transitioning from ACTIVE to INACTIVE (Handover 0071).

        Sets project status to INACTIVE, stops context monitoring, and removes from active cache.
        This frees up the active project slot for the product.

        Args:
            project_id: Project UUID

        Returns:
            Updated Project instance

        Raises:
            ValueError: If project not found or not in ACTIVE status
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            if project.status != ProjectStatus.ACTIVE.value:
                raise ValueError(
                    f"Cannot deactivate project in {project.status} state. Only ACTIVE projects can be deactivated."
                )

            project.status = ProjectStatus.INACTIVE.value
            await session.commit()
            await session.refresh(project)

            # Stop context monitoring
            await self._stop_context_monitor(project_id)

            # Remove from active cache
            self._active_projects.pop(project_id, None)

            logger.info(f"[Handover 0071] Deactivated project {project_id}")
            return project

    async def complete_project(self, project_id: str, summary: Optional[str] = None) -> Project:
        """
        Complete a project, marking it as finished.

        Args:
            project_id: Project UUID
            summary: Optional completion summary

        Returns:
            Updated Project instance
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            project.status = ProjectStatus.COMPLETED.value
            project.completed_at = datetime.now(timezone.utc)

            if summary:
                if not project.meta_data:
                    project.meta_data = {}
                project.meta_data["completion_summary"] = summary

            await session.commit()
            await session.refresh(project)

            # Clean up
            await self._stop_context_monitor(project_id)
            self._active_projects.pop(project_id, None)

            logger.info(f"Completed project {project_id}")
            return project

    async def spawn_agent(
        self,
        project_id: str,
        role: AgentRole,
        custom_mission: Optional[str] = None,
        project_type: Optional[ProjectType] = None,
        additional_instructions: Optional[str] = None,
    ) -> AgentExecution:
        """
        Spawn a new agent with intelligent routing to Claude Code OR Codex/Gemini.

        **HANDOVER 0045 - Phase 3**: Routes agents based on template.tool field:
        - tool='claude' → Claude Code (hybrid mode with auto-export)
        - tool='codex' → Codex CLI (job queue mode)
        - tool='gemini' → Gemini CLI (job queue mode)

        Args:
            project_id: Project UUID
            role: Agent role from AgentRole enum
            custom_mission: Optional custom mission override
            project_type: Optional project type for customization
            additional_instructions: Optional additional instructions

        Returns:
            Created Agent instance (backward compatible)

        Routing Logic:
            1. Query template by role and tenant_key
            2. Check template.tool field
            3. Route to _spawn_claude_code_agent() OR _spawn_generic_agent()
            4. Fallback to original logic if no template found
        """
        async with self.db_manager.get_session_async() as session:
            # Get project
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Handover 0050: Validate product is active before spawning agents
            if project.product_id:
                product = await session.get(Product, project.product_id)
                if product and not product.is_active:
                    raise ValueError(
                        f"Cannot spawn agent - product '{product.name}' is not active. "
                        f"Please activate the product before spawning agents."
                    )

            # HANDOVER 0045: Try to get agent template for routing
            template = await self._get_agent_template(
                role=role.value,
                tenant_key=project.tenant_key,
                product_id=project.product_id,  # Pass product_id for product-specific templates
            )

            # Route based on template.tool field
            if template:
                logger.info(
                    f"[spawn_agent] Routing {role.value} agent via template: "
                    f"tool={template.tool}, template={template.name}"
                )

                if template.tool == "claude":
                    # Claude Code mode: Auto-export template + create agent
                    agent = await self._spawn_claude_code_agent(
                        session=session,
                        project=project,
                        role=role,
                        template=template,
                        custom_mission=custom_mission,
                        additional_instructions=additional_instructions,
                    )
                elif template.tool in ["codex", "gemini"]:
                    # Generic mode: Create job + link agent
                    agent = await self._spawn_generic_agent(
                        session=session,
                        project=project,
                        role=role,
                        template=template,
                        custom_mission=custom_mission,
                        additional_instructions=additional_instructions,
                    )
                else:
                    logger.warning(f"[spawn_agent] Unknown tool type: {template.tool}, falling back to default")
                    # Fallback to original logic
                    template = None  # Force fallback

                # If routing succeeded, return agent (already persisted by spawn methods)
                if template:
                    logger.info(f"[spawn_agent] Spawned {agent.mode} agent for project {project_id}")
                    return agent

            # FALLBACK: Original spawn logic (no template or unknown tool)
            logger.info(f"[spawn_agent] No template found for {role.value}, using legacy spawn logic")

            # Generate mission based on role
            if role == AgentRole.ORCHESTRATOR:
                # Use comprehensive orchestrator template
                additional_context = {"project_type": project_type} if project_type else None
                mission = await self.template_generator.generate_orchestrator_mission(
                    project_name=project.name,
                    project_mission=project.mission,
                    additional_context=additional_context,
                )
            else:
                # Use role-specific agent template
                mission = await self.template_generator.generate_agent_mission(
                    role=role.value,
                    project_name=project.name,
                    custom_mission=custom_mission,
                    additional_instructions=additional_instructions,
                )

            # SERENA OPTIMIZATION: Inject optimization rules into mission
            try:
                optimizer = self._get_serena_optimizer(project.tenant_key)
                injector = MissionOptimizationInjector(optimizer)

                # Gather context for optimization
                context_data = {
                    "project_id": project_id,
                    "project_type": project_type.value if project_type else "general",
                    "codebase_size": "medium",  # Could be determined dynamically
                    "primary_language": "python",  # Could be detected from project
                }

                # Inject optimization rules
                optimized_mission = await injector.inject_optimization_rules(
                    agent_role=role.value, mission=mission, context_data=context_data
                )

                logger.info(f"Enhanced {role.value} agent mission with Serena optimization rules")
                mission = optimized_mission

            except Exception as e:
                logger.warning(f"Failed to inject Serena optimization rules: {e}")
                # Continue with original mission if optimization fails

            # Create AgentJob (work order) and AgentExecution (executor instance)
            job_id = str(uuid4())
            agent_id = str(uuid4())

            # Create AgentJob (work order)
            agent_job = AgentJob(
                job_id=job_id,
                tenant_key=project.tenant_key,
                project_id=project_id,
                mission=mission,
                job_type=role.value,
                status="active",
            )
            session.add(agent_job)

            # Create AgentExecution (executor instance)
            agent_execution = AgentExecution(
                agent_id=agent_id,
                job_id=job_id,
                tenant_key=project.tenant_key,
                agent_type=role.value,
                agent_name=role.value,
                instance_number=1,
                status="waiting",
                progress=0,
                tool_type="claude",  # Default to claude for legacy
                messages=[],
                spawned_by=None,  # No parent in fallback path
            )
            session.add(agent_execution)
            await session.commit()
            await session.refresh(agent_execution)

            logger.info(
                f"Spawned optimized {role.value} agent (fallback): job_id={job_id}, "
                f"agent_id={agent_id}, project={project_id}"
            )

            return agent_execution

    async def spawn_agents_parallel(
        self,
        project_id: str,
        agents: list[tuple[AgentRole, Optional[str]]],
        project_type: Optional[ProjectType] = None,
    ) -> list[AgentExecution]:
        """
        Spawn multiple agents in parallel with coordination instructions.

        Args:
            project_id: Project UUID
            agents: List of (role, custom_mission) tuples
            project_type: Optional project type for customization

        Returns:
            List of created Agent instances
        """
        async with self.db_manager.get_session_async() as session:
            # Get project
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Generate parallel startup instructions
            agent_names = [role.value for role, _ in agents]
            parallel_instructions = self.template_generator.generate_parallel_startup_instructions(
                agents=agent_names, project_name=project.name
            )

            # Create all agents
            created_agents = []
            for role, custom_mission in agents:
                agent = await self.spawn_agent(
                    project_id=project_id,
                    role=role,
                    custom_mission=custom_mission,
                    project_type=project_type,
                    additional_instructions=parallel_instructions,
                )
                created_agents.append(agent)

            logger.info(f"Spawned {len(created_agents)} agents in parallel for project {project_id}")
            return created_agents

    async def handle_context_limit(self, agent_id: str) -> Optional[Message]:
        """
        Handle agent approaching context limit with proper instructions.

        Args:
            agent_id: Agent UUID

        Returns:
            Context limit message if needed
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentExecution)
                .options(joinedload(AgentExecution.job))
                .where(AgentExecution.agent_id == agent_id)
            )
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Agent {agent_id} not found")

            # Check if approaching limit
            context_used = execution.meta_data.get("context_used", 0) if execution.meta_data else 0
            usage_ratio = context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET
            if usage_ratio < 0.7:
                return None

            # Generate context limit instructions
            instructions = self.template_generator.generate_context_limit_instructions(
                current_agent=execution.agent_name,
                next_agent="orchestrator",
                reason=f"Context usage at {context_used}/{self.DEFAULT_AGENT_CONTEXT_BUDGET} tokens",
            )

            # Create message with instructions
            message = Message(
                tenant_key=execution.tenant_key,
                project_id=execution.job.project_id,
                to_agents=[execution.agent_name],
                message_type="system",
                content=instructions,
                priority="high",
                status="pending",
            )

            session.add(message)
            await session.commit()
            await session.refresh(message)

            logger.warning(f"Agent {execution.agent_name} approaching context limit: {usage_ratio:.1%}")
            return message

    async def handoff(self, from_agent_id: str, to_agent_id: str, context: dict[str, Any]) -> Message:
        """
        Perform intelligent handoff between agents.

        Args:
            from_agent_id: Source agent UUID
            to_agent_id: Target agent UUID
            context: Context to transfer

        Returns:
            Handoff message
        """
        async with self.db_manager.get_session_async() as session:
            # Get both agents
            from_result = await session.execute(
                select(AgentExecution)
                .options(joinedload(AgentExecution.job))
                .where(AgentExecution.agent_id == from_agent_id)
            )
            from_execution = from_result.scalar_one_or_none()

            to_result = await session.execute(
                select(AgentExecution)
                .options(joinedload(AgentExecution.job))
                .where(AgentExecution.agent_id == to_agent_id)
            )
            to_execution = to_result.scalar_one_or_none()

            if not from_execution or not to_execution:
                raise ValueError("Agent not found")

            if from_execution.job.project_id != to_execution.job.project_id:
                raise ValueError("Agents must be in same project")

            # Generate handoff instructions
            AgentRole(from_execution.agent_type)
            AgentRole(to_execution.agent_type)
            context.get("summary", "Work completed by previous agent")

            handoff_instructions = self.template_generator.generate_handoff_instructions(
                from_agent=from_execution.agent_name,
                to_agent=to_execution.agent_name,
                handoff_context=context,
            )

            # Get context_used from metadata
            from_context_used = from_execution.meta_data.get("context_used", 0) if from_execution.meta_data else 0

            # Package handoff context
            handoff_context = {
                "from_agent": from_execution.agent_name,
                "to_agent": to_execution.agent_name,
                "context_used": from_context_used,
                "context_budget": self.DEFAULT_AGENT_CONTEXT_BUDGET,
                "handoff_reason": self._get_handoff_reason(from_execution),
                "transfer_data": context,
                "handoff_instructions": handoff_instructions,
            }
            handoff_context["_from_agent_id"] = from_execution.agent_id  # Store sender in context

            # Create handoff message
            message = Message(
                tenant_key=from_execution.tenant_key,
                project_id=from_execution.job.project_id,
                to_agents=[to_execution.agent_name],
                message_type="handoff",
                content=str(handoff_context),
                priority="high",
                status="pending",
            )

            # Update agent states
            from_execution.status = "handed_off"
            to_execution.status = "active"

            session.add(message)
            await session.commit()
            await session.refresh(message)

            logger.info(f"Handoff from {from_execution.agent_name} to {to_execution.agent_name}")
            return message

    async def check_handoff_needed(self, agent_id: str) -> tuple[bool, Optional[str]]:
        """
        Check if an agent needs handoff based on context usage.

        Args:
            agent_id: Agent UUID

        Returns:
            Tuple of (needs_handoff, reason)
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentExecution).where(AgentExecution.agent_id == agent_id)
            )
            execution = result.scalar_one_or_none()

            if not execution:
                return False, None

            context_used = execution.meta_data.get("context_used", 0) if execution.meta_data else 0
            usage_ratio = context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET

            if usage_ratio >= 0.8:
                return True, "Context usage above 80% threshold"

            return False, None

    def get_context_status(self, context_used: int, context_budget: int) -> ContextStatus:
        """
        Get color-coded context status.

        Args:
            context_used: Tokens used
            context_budget: Total budget

        Returns:
            ContextStatus enum value
        """
        usage_ratio = context_used / context_budget

        if usage_ratio < 0.5:
            return ContextStatus.GREEN
        if usage_ratio < 0.8:
            return ContextStatus.YELLOW
        return ContextStatus.RED

    async def update_context_usage(self, agent_id: str, tokens_used: int) -> AgentExecution:
        """
        Update agent's context usage.

        Args:
            agent_id: Agent UUID
            tokens_used: Additional tokens used

        Returns:
            Updated AgentExecution instance
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentExecution)
                .options(joinedload(AgentExecution.job))
                .where(AgentExecution.agent_id == agent_id)
            )
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Agent {agent_id} not found")

            # Update execution context in metadata
            if not execution.meta_data:
                execution.meta_data = {}
            current_context = execution.meta_data.get("context_used", 0)
            execution.meta_data["context_used"] = current_context + tokens_used

            # Also update project context
            project_result = await session.execute(select(Project).where(Project.id == execution.job.project_id))
            project = project_result.scalar_one_or_none()
            if project:
                project.context_used += tokens_used

            await session.commit()
            await session.refresh(execution)

            # Check if handoff needed
            needs_handoff, reason = await self.check_handoff_needed(agent_id)
            if needs_handoff:
                logger.warning(f"Agent {execution.agent_name} needs handoff: {reason}")

            return execution

    async def get_active_projects(self, tenant_key: Optional[str] = None) -> list[Project]:
        """
        Get all active projects, optionally filtered by tenant.

        Args:
            tenant_key: Optional tenant filter

        Returns:
            List of active Project instances
        """
        async with self.db_manager.get_session_async() as session:
            query = select(Project).where(Project.status == ProjectStatus.ACTIVE.value)

            if tenant_key:
                query = query.where(Project.tenant_key == tenant_key)

            result = await session.execute(query.options(selectinload(Project.agent_jobs_v2_v2)))
            return result.scalars().all()

    async def get_project_agents(self, project_id: str) -> list[AgentExecution]:
        """
        Get all agents for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of AgentExecution instances
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentExecution)
                .options(joinedload(AgentExecution.job))
                .join(AgentJob)
                .where(AgentJob.project_id == project_id)
            )
            return result.scalars().all()

    async def get_agent_context_status(self, agent_id: str) -> dict[str, Any]:
        """
        Get detailed context status for an agent.

        Args:
            agent_id: Agent UUID

        Returns:
            Dict with context status details
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(AgentExecution).where(AgentExecution.agent_id == agent_id)
            )
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Agent {agent_id} not found")

            context_used = execution.meta_data.get("context_used", 0) if execution.meta_data else 0
            usage_ratio = context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET
            status = self.get_context_status(context_used, self.DEFAULT_AGENT_CONTEXT_BUDGET)

            return {
                "agent_id": execution.agent_id,
                "agent_name": execution.agent_name,
                "context_used": context_used,
                "context_budget": self.DEFAULT_AGENT_CONTEXT_BUDGET,
                "usage_ratio": usage_ratio,
                "usage_percentage": round(usage_ratio * 100, 2),
                "status": status.value,
                "needs_handoff": usage_ratio >= 0.8,
            }

    async def _start_context_monitor(self, project_id: str):
        """Start monitoring context for a project."""
        if project_id not in self._context_monitors:
            monitor_task = asyncio.create_task(self._monitor_project_context(project_id))
            self._context_monitors[project_id] = monitor_task

    async def _stop_context_monitor(self, project_id: str):
        """Stop monitoring context for a project."""
        if project_id in self._context_monitors:
            self._context_monitors[project_id].cancel()
            del self._context_monitors[project_id]

    async def _monitor_project_context(self, project_id: str):
        """
        Background task to monitor project context usage.

        Args:
            project_id: Project UUID
        """
        while True:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds

                async with self.db_manager.get_session_async() as session:
                    # Get project and agents
                    result = await session.execute(
                        select(Project).where(Project.id == project_id).options(selectinload(Project.agent_jobs_v2_v2))
                    )
                    project = result.scalar_one_or_none()

                    if not project or project.status != ProjectStatus.ACTIVE.value:
                        break

                    # Check each agent execution
                    for execution in project.agent_jobs_v2_v2:
                        if execution.status == "active":
                            needs_handoff, reason = await self.check_handoff_needed(execution.agent_id)
                            if needs_handoff:
                                logger.warning(f"Agent {execution.agent_name} in project {project.name} needs handoff: {reason}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error monitoring project {project_id}: {e}")
                await asyncio.sleep(60)  # Back off on error

    def _get_handoff_reason(self, execution: AgentExecution) -> str:
        """Get the reason for handoff based on agent state."""
        context_used = execution.meta_data.get("context_used", 0) if execution.meta_data else 0
        usage_ratio = context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET

        if usage_ratio >= 0.8:
            return f"Context usage at {round(usage_ratio * 100)}%"
        if execution.status == "error":
            return "Agent encountered error"
        return "Manual handoff requested"

    async def get_tenant_projects(self, tenant_key: str) -> list[Project]:
        """
        Get all projects for a tenant.

        Args:
            tenant_key: Tenant key

        Returns:
            List of Project instances
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(
                select(Project).where(Project.tenant_key == tenant_key).options(selectinload(Project.agent_jobs_v2_v2))
            )
            return result.scalars().all()

    async def allocate_resources(
        self,
        tenant_key: str,
        max_concurrent_projects: int = 5,
        total_context_budget: int = 500000,
    ) -> dict[str, Any]:
        """
        Allocate resources for a tenant across projects.

        Args:
            tenant_key: Tenant key
            max_concurrent_projects: Max concurrent projects
            total_context_budget: Total token budget

        Returns:
            Resource allocation details
        """
        projects = await self.get_tenant_projects(tenant_key)
        active_projects = [p for p in projects if p.status == ProjectStatus.ACTIVE.value]

        if len(active_projects) >= max_concurrent_projects:
            return {
                "can_create_new": False,
                "reason": f"Maximum {max_concurrent_projects} concurrent projects reached",
                "active_projects": len(active_projects),
                "total_context_used": sum(p.context_used for p in projects),
                "total_context_budget": total_context_budget,
            }

        total_used = sum(p.context_used for p in projects)
        remaining_budget = total_context_budget - total_used

        return {
            "can_create_new": True,
            "active_projects": len(active_projects),
            "max_concurrent": max_concurrent_projects,
            "total_context_used": total_used,
            "total_context_budget": total_context_budget,
            "remaining_budget": remaining_budget,
            "suggested_project_budget": min(150000, remaining_budget),
        }

    async def get_optimization_report(self, project_id: str) -> dict[str, Any]:
        """
        Generate comprehensive Serena optimization report for a project.

        Args:
            project_id: Project UUID

        Returns:
            Dict with optimization metrics and savings
        """
        async with self.db_manager.get_session_async() as session:
            # Get project and agents
            project_result = await session.execute(
                select(Project).where(Project.id == project_id).options(selectinload(Project.agent_jobs_v2_v2))
            )
            project = project_result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Get optimizer for tenant
            optimizer = self._get_serena_optimizer(project.tenant_key)

            # Generate reports for each agent execution
            agent_reports = {}
            total_operations = 0
            total_tokens_saved = 0

            for execution in project.agent_jobs_v2_v2:
                try:
                    agent_report = await optimizer.generate_savings_report(execution.agent_id)
                    agent_reports[execution.agent_id] = {
                        "agent_name": execution.agent_name,
                        "agent_role": execution.agent_type,
                        "report": agent_report,
                    }

                    total_operations += agent_report.get("total_operations", 0)
                    total_tokens_saved += agent_report.get("total_tokens_saved", 0)

                except Exception as e:
                    logger.warning(f"Failed to get optimization report for agent {execution.agent_id}: {e}")
                    agent_reports[execution.agent_id] = {
                        "agent_name": execution.agent_name,
                        "agent_role": execution.agent_type,
                        "report": {"error": str(e)},
                    }

            # Calculate project-level metrics
            context_savings_percent = 0
            if project.context_used > 0:
                # Estimate what context usage would have been without optimization
                estimated_unoptimized = project.context_used * 3  # Conservative estimate
                context_savings_percent = ((estimated_unoptimized - project.context_used) / estimated_unoptimized) * 100

            return {
                "project_id": project_id,
                "project_name": project.name,
                "project_status": project.status,
                "optimization_summary": {
                    "total_operations": total_operations,
                    "total_tokens_saved": total_tokens_saved,
                    "context_used": project.context_used,
                    "estimated_context_savings_percent": round(context_savings_percent, 1),
                    "agents_optimized": len(agent_reports),
                },
                "agent_reports": agent_reports,
                "generated_at": datetime.now(timezone.utc).isoformat(),
            }

    async def estimate_optimization_impact(self, project_id: str, agent_role: str) -> dict[str, Any]:
        """
        Estimate optimization impact before spawning an agent.

        Args:
            project_id: Project UUID
            agent_role: Role of agent to spawn

        Returns:
            Dict with estimated optimization impact
        """
        async with self.db_manager.get_session_async() as session:
            # Get project
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Get optimizer
            optimizer = self._get_serena_optimizer(project.tenant_key)
            injector = MissionOptimizationInjector(optimizer)

            # Prepare context data
            context_data = {
                "project_id": project_id,
                "project_type": "general",
                "codebase_size": "medium",
                "primary_language": "python",
            }

            # Get impact estimate
            impact = await injector.estimate_optimization_impact(agent_role, context_data)

            return {
                "project_id": project_id,
                "agent_role": agent_role,
                "estimated_impact": impact,
                "recommendation": self._get_optimization_recommendation(impact),
            }

    def _get_optimization_recommendation(self, impact: dict[str, Any]) -> str:
        """Generate optimization recommendation based on impact analysis"""

        rules_applied = impact.get("rules_applied", 0)
        context_adjustments = impact.get("context_adjustments", 0)

        if rules_applied >= 5:
            return "High optimization potential - expect 60-90% context prioritization"
        if rules_applied >= 3:
            return "Medium optimization potential - expect 40-context prioritization and orchestration"
        return "Basic optimization applied - expect 20-50% context prioritization"

    #  ====================  Phase 2: Orchestration Enhancement Methods (Handover 0020) ====================

    async def generate_mission_plan(
        self, product: "Product", project_description: str, user_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        Generate missions from vision analysis.

        Algorithm:
        1. Analyze requirements (MissionPlanner.analyze_requirements)
        2. Select agents (AgentSelector.select_agents)
        3. Generate missions (MissionPlanner.generate_missions)
        4. Return mission plan

        Args:
            product: Product with vision document
            project_description: Project requirements description
            user_id: Optional user ID for field priority configuration (Handover 0086A Task 2.1)

        Returns:
            Dict mapping agent roles to Mission objects
        """
        # Log user_id propagation for debugging (Handover 0086A Task 2.1)
        logger.info(
            "Generating mission plan",
            extra={
                "product_id": str(product.id),
                "user_id": user_id,
                "has_user_id": user_id is not None,
            },
        )

        # 1. Analyze requirements
        requirements = await self.mission_planner.analyze_requirements(product, project_description)

        # 2. Generate missions based on requirements (Handover 0086A Task 2.1)
        # Call the simplified generate_mission method with user_id for field priorities
        missions = await self.mission_planner.generate_mission(
            product=product,
            project_description=project_description,
            user_id=user_id,  # Handover 0086A Task 2.1: pass user_id for field priorities
        )

        logger.info(f"Generated mission plan for product {product.id}: {len(missions)} missions created")

        return missions

    async def select_agents_for_mission(
        self, requirements: Any, tenant_key: str, product_id: Optional[str] = None
    ) -> list[Any]:
        """
        Smart agent selection based on requirements.

        Uses AgentSelector to query database templates.

        Args:
            requirements: RequirementAnalysis from MissionPlanner
            tenant_key: Tenant key for isolation
            product_id: Optional product ID for context

        Returns:
            List of AgentConfig objects
        """
        agent_configs = await self.agent_selector.select_agents(
            requirements=requirements, tenant_key=tenant_key, product_id=product_id
        )

        logger.info(f"Selected {len(agent_configs)} agents for mission: {[ac.role for ac in agent_configs]}")

        return agent_configs

    async def coordinate_agent_workflow(
        self, agent_configs: list[Any], workflow_type: str, tenant_key: str, project_id: str
    ) -> Any:
        """
        Monitor and coordinate agent team.

        Uses WorkflowEngine to execute workflow pattern.

        Args:
            agent_configs: List of AgentConfig objects
            workflow_type: 'waterfall' or 'parallel'
            tenant_key: Tenant key for isolation
            project_id: Project ID

        Returns:
            WorkflowResult from execution
        """
        workflow_result = await self.workflow_engine.execute_workflow(
            agent_configs=agent_configs, workflow_type=workflow_type, tenant_key=tenant_key, project_id=project_id
        )

        logger.info(
            f"Workflow coordination complete for project {project_id}: "
            f"status={workflow_result.status}, "
            f"completed={len(workflow_result.completed)}, "
            f"failed={len(workflow_result.failed)}"
        )

        return workflow_result

    async def process_product_vision(
        self, tenant_key: str, product_id: str, project_requirements: str, user_id: Optional[str] = None
    ) -> dict[str, Any]:
        """
        MAIN ORCHESTRATION WORKFLOW.

        Complete workflow:
        1. Load product and validate vision
        2. Chunk vision if needed
        3. Analyze requirements
        4. Select agents
        5. Generate missions
        6. Coordinate workflow

        Args:
            tenant_key: Tenant key for isolation
            product_id: Product UUID
            project_requirements: Project requirements description
            user_id: Optional user ID for field priority configuration (Handover 0086A Task 2.1)

        Returns:
            Dict with:
            - project_id: Created project ID
            - mission_plan: Generated missions
            - selected_agents: List of agent roles
            - spawned_jobs: List of job IDs
            - workflow_result: Workflow execution result
            - token_reduction: Context prioritization metrics

        Raises:
            ValueError: If product not found or not active (Handover 0050)
        """
        # Log user_id propagation for debugging (Handover 0086A Task 2.1)
        logger.info(
            "Processing product vision",
            extra={
                "product_id": product_id,
                "tenant_key": tenant_key,
                "user_id": user_id,
                "has_user_id": user_id is not None,
            },
        )
        # 1. Load product and validate vision
        async with self.db_manager.get_session_async() as session:
            product = await session.get(Product, product_id)
            if not product or product.tenant_key != tenant_key:
                raise ValueError(f"Product {product_id} not found")

            # Handover 0050: Validate product is active before processing
            if not product.is_active:
                raise ValueError(
                    f"Cannot process product vision - product '{product.name}' is not active. "
                    f"Activate the product before creating agent missions."
                )

            # Get vision content from VisionDocument relationship
            storage_type = product.primary_vision_storage_type
            if storage_type == "inline":
                vision_content = product.primary_vision_text
            elif storage_type == "file" and product.primary_vision_path:
                vision_content = Path(product.primary_vision_path).read_text(encoding="utf-8")
            else:
                raise ValueError(f"Product {product_id} has no vision document")

        # 2. Chunk vision if needed (using new vision_documents relationship)
        if not product.vision_is_chunked:
            logger.info(f"Chunking vision document for product {product_id}")
            chunker = VisionDocumentChunker(target_chunk_size=2000)
            chunks = chunker.chunk_document(vision_content, product_id=product_id)

            # Store chunks in database and mark primary vision document as chunked
            async with self.db_manager.get_session_async() as session:
                db_product = await session.get(Product, product_id)
                # Mark the first vision document as chunked
                if db_product.vision_documents:
                    db_product.vision_documents[0].chunked = True
                await session.commit()

            logger.info(f"Chunked vision into {len(chunks)} chunks")

        # 3. Create project
        project = await self.create_project(
            name=f"Vision Project: {product.name}",
            mission=project_requirements,
            tenant_key=tenant_key,
            context_budget=150000,
        )

        # 4. Generate mission plan (Handover 0086A Task 2.1: pass user_id for field priorities)
        missions = await self.generate_mission_plan(product, project_requirements, user_id=user_id)

        # 5. Select agents
        analysis = await self.mission_planner.analyze_requirements(product, project_requirements)
        agent_configs = await self.select_agents_for_mission(
            requirements=analysis, tenant_key=tenant_key, product_id=product_id
        )

        # 6. Assign missions to agents
        for agent_config in agent_configs:
            if agent_config.role in missions:
                agent_config.mission = missions[agent_config.role]

        # 7. Coordinate workflow (default: waterfall)
        workflow_result = await self.coordinate_agent_workflow(
            agent_configs=agent_configs, workflow_type="waterfall", tenant_key=tenant_key, project_id=project.id
        )

        # 8. Calculate context prioritization metrics
        total_mission_tokens = sum(
            mission.token_count for mission in missions.values() if hasattr(mission, "token_count")
        )
        # Estimate what it would have been without optimization (3x)
        estimated_unoptimized = total_mission_tokens * 3
        token_reduction_percent = (
            ((estimated_unoptimized - total_mission_tokens) / estimated_unoptimized) * 100
            if estimated_unoptimized > 0
            else 0
        )

        # 9. Collect job IDs from workflow result
        spawned_jobs = []
        for stage in workflow_result.completed:
            if hasattr(stage, "job_ids"):
                spawned_jobs.extend(stage.job_ids)

        logger.info(
            f"Completed product vision processing for {product_id}: "
            f"project={project.id}, agents={len(agent_configs)}, "
            f"jobs={len(spawned_jobs)}, token_reduction={token_reduction_percent:.1f}%"
        )

        # 10. Return comprehensive result
        return {
            "project_id": project.id,
            "mission_plan": {role: mission.to_dict() for role, mission in missions.items()},
            "selected_agents": [ac.role for ac in agent_configs],
            "spawned_jobs": spawned_jobs,
            "workflow_result": workflow_result,
            "token_reduction": {
                "original_tokens": estimated_unoptimized,
                "optimized_tokens": total_mission_tokens,
                "reduction_percent": round(token_reduction_percent, 1),
            },
        }
