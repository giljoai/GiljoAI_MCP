"""
ProjectOrchestrator - Core orchestration engine for GiljoAI MCP.

Manages project lifecycle, agent spawning, handoffs, context tracking,
and multi-project concurrency with tenant isolation.
"""

import asyncio
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from .agent_selector import AgentSelector
from .context_management.chunker import VisionDocumentChunker
from .database import get_db_manager
from .enums import AgentRole, ContextStatus, ProjectStatus, ProjectType
from .mission_planner import MissionPlanner
from .models import Agent, Message, Product, Project
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

    def _get_serena_optimizer(self, tenant_key: str) -> SerenaOptimizer:
        """Get or create SerenaOptimizer for tenant (lazy initialization)"""
        if not self.serena_optimizer:
            self.serena_optimizer = SerenaOptimizer(self.db_manager, tenant_key)
        return self.serena_optimizer

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
            context_budget: Token budget for the project

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
                status=ProjectStatus.PLANNING.value,
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
        Activate a project, transitioning from DRAFT to ACTIVE.

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
                ProjectStatus.PLANNING.value,
                ProjectStatus.PAUSED.value,
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

    async def pause_project(self, project_id: str) -> Project:
        """
        Pause an active project.

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

            if project.status != ProjectStatus.ACTIVE.value:
                raise ValueError("Can only pause active projects")

            project.status = ProjectStatus.PAUSED.value
            await session.commit()
            await session.refresh(project)

            # Stop context monitoring
            await self._stop_context_monitor(project_id)

            logger.info(f"Paused project {project_id}")
            return project

    async def resume_project(self, project_id: str) -> Project:
        """
        Resume a paused project.

        Args:
            project_id: Project UUID

        Returns:
            Updated Project instance
        """
        return await self.activate_project(project_id)

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

    async def archive_project(self, project_id: str) -> Project:
        """
        Archive a completed project.

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

            if project.status != ProjectStatus.COMPLETED.value:
                raise ValueError("Can only archive completed projects")

            project.status = ProjectStatus.ARCHIVED.value
            await session.commit()
            await session.refresh(project)

            logger.info(f"Archived project {project_id}")
            return project

    async def spawn_agent(
        self,
        project_id: str,
        role: AgentRole,
        custom_mission: Optional[str] = None,
        project_type: Optional[ProjectType] = None,
        additional_instructions: Optional[str] = None,
    ) -> Agent:
        """
        Spawn a new agent with role-based mission template enhanced with Serena optimization.

        Args:
            project_id: Project UUID
            role: Agent role from AgentRole enum
            custom_mission: Optional custom mission override
            project_type: Optional project type for customization
            additional_instructions: Optional additional instructions

        Returns:
            Created Agent instance with optimized mission
        """
        async with self.db_manager.get_session_async() as session:
            # Get project
            result = await session.execute(select(Project).where(Project.id == project_id))
            project = result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

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

            # Create agent with optimized mission
            agent = Agent(
                tenant_key=project.tenant_key,
                project_id=project_id,
                name=role.value,
                role=role.value,
                mission=mission,
                status="active",
                context_used=0,
            )

            session.add(agent)
            await session.commit()
            await session.refresh(agent)

            logger.info(f"Spawned optimized {role.value} agent {agent.id} for project {project_id}")
            return agent

    async def spawn_agents_parallel(
        self,
        project_id: str,
        agents: list[tuple[AgentRole, Optional[str]]],
        project_type: Optional[ProjectType] = None,
    ) -> list[Agent]:
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
            result = await session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()

            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Check if approaching limit
            usage_ratio = agent.context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET
            if usage_ratio < 0.7:
                return None

            # Generate context limit instructions
            instructions = self.template_generator.generate_context_limit_instructions(
                current_agent=agent.name,
                next_agent="orchestrator",
                reason=f"Context usage at {agent.context_used}/{self.DEFAULT_AGENT_CONTEXT_BUDGET} tokens",
            )

            # Create message with instructions
            message = Message(
                tenant_key=agent.tenant_key,
                project_id=agent.project_id,
                from_agent_id=None,  # System message
                to_agents=[agent.name],
                message_type="system",
                content=instructions,
                priority="high",
                status="pending",
            )

            session.add(message)
            await session.commit()
            await session.refresh(message)

            logger.warning(f"Agent {agent.name} approaching context limit: {usage_ratio:.1%}")
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
            from_result = await session.execute(select(Agent).where(Agent.id == from_agent_id))
            from_agent = from_result.scalar_one_or_none()

            to_result = await session.execute(select(Agent).where(Agent.id == to_agent_id))
            to_agent = to_result.scalar_one_or_none()

            if not from_agent or not to_agent:
                raise ValueError("Agent not found")

            if from_agent.project_id != to_agent.project_id:
                raise ValueError("Agents must be in same project")

            # Generate handoff instructions
            AgentRole(from_agent.role)
            AgentRole(to_agent.role)
            context.get("summary", "Work completed by previous agent")

            handoff_instructions = self.template_generator.generate_handoff_instructions(
                from_agent=from_agent.name,
                to_agent=to_agent.name,
                handoff_context=context,
            )

            # Package handoff context
            handoff_context = {
                "from_agent": from_agent.name,
                "to_agent": to_agent.name,
                "context_used": from_agent.context_used,
                "context_budget": self.DEFAULT_AGENT_CONTEXT_BUDGET,
                "handoff_reason": self._get_handoff_reason(from_agent),
                "transfer_data": context,
                "handoff_instructions": handoff_instructions,
            }

            # Create handoff message
            message = Message(
                tenant_key=from_agent.tenant_key,
                project_id=from_agent.project_id,
                from_agent_id=from_agent.id,
                to_agents=[to_agent.name],
                message_type="handoff",
                content=str(handoff_context),
                priority="high",
                status="pending",
            )

            # Update agent states
            from_agent.status = "handed_off"
            to_agent.status = "active"

            session.add(message)
            await session.commit()
            await session.refresh(message)

            logger.info(f"Handoff from {from_agent.name} to {to_agent.name}")
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
            result = await session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()

            if not agent:
                return False, None

            usage_ratio = agent.context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET

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

    async def update_context_usage(self, agent_id: str, tokens_used: int) -> Agent:
        """
        Update agent's context usage.

        Args:
            agent_id: Agent UUID
            tokens_used: Additional tokens used

        Returns:
            Updated Agent instance
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()

            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            # Update agent context
            agent.context_used += tokens_used

            # Also update project context
            project_result = await session.execute(select(Project).where(Project.id == agent.project_id))
            project = project_result.scalar_one_or_none()
            if project:
                project.context_used += tokens_used

            await session.commit()
            await session.refresh(agent)

            # Check if handoff needed
            needs_handoff, reason = await self.check_handoff_needed(agent_id)
            if needs_handoff:
                logger.warning(f"Agent {agent.name} needs handoff: {reason}")

            return agent

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

            result = await session.execute(query.options(selectinload(Project.agents)))
            return result.scalars().all()

    async def get_project_agents(self, project_id: str) -> list[Agent]:
        """
        Get all agents for a project.

        Args:
            project_id: Project UUID

        Returns:
            List of Agent instances
        """
        async with self.db_manager.get_session_async() as session:
            result = await session.execute(select(Agent).where(Agent.project_id == project_id))
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
            result = await session.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()

            if not agent:
                raise ValueError(f"Agent {agent_id} not found")

            usage_ratio = agent.context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET
            status = self.get_context_status(agent.context_used, self.DEFAULT_AGENT_CONTEXT_BUDGET)

            return {
                "agent_id": agent.id,
                "agent_name": agent.name,
                "context_used": agent.context_used,
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
                        select(Project).where(Project.id == project_id).options(selectinload(Project.agents))
                    )
                    project = result.scalar_one_or_none()

                    if not project or project.status != ProjectStatus.ACTIVE.value:
                        break

                    # Check each agent
                    for agent in project.agents:
                        if agent.status == "active":
                            needs_handoff, reason = await self.check_handoff_needed(agent.id)
                            if needs_handoff:
                                logger.warning(f"Agent {agent.name} in project {project.name} needs handoff: {reason}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.exception(f"Error monitoring project {project_id}: {e}")
                await asyncio.sleep(60)  # Back off on error

    def _get_handoff_reason(self, agent: Agent) -> str:
        """Get the reason for handoff based on agent state."""
        usage_ratio = agent.context_used / self.DEFAULT_AGENT_CONTEXT_BUDGET

        if usage_ratio >= 0.8:
            return f"Context usage at {round(usage_ratio * 100)}%"
        if agent.status == "error":
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
                select(Project).where(Project.tenant_key == tenant_key).options(selectinload(Project.agents))
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
                select(Project).where(Project.id == project_id).options(selectinload(Project.agents))
            )
            project = project_result.scalar_one_or_none()

            if not project:
                raise ValueError(f"Project {project_id} not found")

            # Get optimizer for tenant
            optimizer = self._get_serena_optimizer(project.tenant_key)

            # Generate reports for each agent
            agent_reports = {}
            total_operations = 0
            total_tokens_saved = 0

            for agent in project.agents:
                try:
                    agent_report = await optimizer.generate_savings_report(agent.id)
                    agent_reports[agent.id] = {
                        "agent_name": agent.name,
                        "agent_role": agent.role,
                        "report": agent_report,
                    }

                    total_operations += agent_report.get("total_operations", 0)
                    total_tokens_saved += agent_report.get("total_tokens_saved", 0)

                except Exception as e:
                    logger.warning(f"Failed to get optimization report for agent {agent.id}: {e}")
                    agent_reports[agent.id] = {
                        "agent_name": agent.name,
                        "agent_role": agent.role,
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
            return "High optimization potential - expect 60-90% token reduction"
        if rules_applied >= 3:
            return "Medium optimization potential - expect 40-70% token reduction"
        return "Basic optimization applied - expect 20-50% token reduction"

    #  ====================  Phase 2: Orchestration Enhancement Methods (Handover 0020) ====================

    async def generate_mission_plan(self, product: "Product", project_description: str) -> dict[str, Any]:
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

        Returns:
            Dict mapping agent roles to Mission objects
        """
        # 1. Analyze requirements
        requirements = await self.mission_planner.analyze_requirements(product, project_description)

        # 2. Generate missions based on requirements
        missions = await self.mission_planner.generate_missions(requirements=requirements, product=product)

        logger.info(f"Generated mission plan for product {product.id}: " f"{len(missions)} missions created")

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

        logger.info(f"Selected {len(agent_configs)} agents for mission: " f"{[ac.role for ac in agent_configs]}")

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
        self, tenant_key: str, product_id: str, project_requirements: str
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

        Returns:
            Dict with:
            - project_id: Created project ID
            - mission_plan: Generated missions
            - selected_agents: List of agent roles
            - spawned_jobs: List of job IDs
            - workflow_result: Workflow execution result
            - token_reduction: Token reduction metrics
        """
        # 1. Load product and validate vision
        async with self.db_manager.get_session_async() as session:
            product = await session.get(Product, product_id)
            if not product or product.tenant_key != tenant_key:
                raise ValueError(f"Product {product_id} not found")

            # Get vision content (inline or file-based)
            if product.vision_type == "inline":
                vision_content = product.vision_document
            elif product.vision_type == "file" and product.vision_path:
                vision_content = Path(product.vision_path).read_text(encoding="utf-8")
            else:
                raise ValueError(f"Product {product_id} has no vision document")

        # 2. Chunk vision if needed
        if not product.chunked:
            logger.info(f"Chunking vision document for product {product_id}")
            chunker = VisionDocumentChunker(target_chunk_size=2000)
            chunks = chunker.chunk_document(vision_content, product_id=product_id)

            # Store chunks in database (via ContextRepository or direct insert)
            # For now, just mark as chunked
            async with self.db_manager.get_session_async() as session:
                db_product = await session.get(Product, product_id)
                db_product.chunked = True
                await session.commit()

            logger.info(f"Chunked vision into {len(chunks)} chunks")

        # 3. Create project
        project = await self.create_project(
            name=f"Vision Project: {product.name}",
            mission=project_requirements,
            tenant_key=tenant_key,
            context_budget=150000,
        )

        # 4. Generate mission plan
        missions = await self.generate_mission_plan(product, project_requirements)

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

        # 8. Calculate token reduction metrics
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
