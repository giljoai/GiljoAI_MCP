"""
Orchestration MCP Tools - Handover 0020 Phase 3B

Provides MCP tools for intelligent multi-agent orchestration with 70% token reduction.
Exposes orchestration capabilities via Model Context Protocol for agent coordination.
"""

import logging
from typing import Any

from fastmcp import FastMCP
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Agent, MCPAgentJob, Project
from giljo_mcp.orchestrator import ProjectOrchestrator


logger = logging.getLogger(__name__)


def register_orchestration_tools(mcp: FastMCP, db_manager: DatabaseManager) -> None:
    """
    Register orchestration tools with the MCP server.

    Args:
        mcp: FastMCP server instance
        db_manager: Database manager for data access
    """

    @mcp.tool()
    async def orchestrate_project(
        project_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Complete project orchestration workflow.

        Triggers the full orchestration pipeline:
        1. Vision processing and analysis
        2. Mission generation for specialized agents
        3. Agent selection based on requirements
        4. Agent job spawning
        5. Workflow coordination

        Args:
            project_id: Project database ID (UUID)
            tenant_key: Tenant isolation key

        Returns:
            Dictionary containing:
            - project_id: Created/used project ID
            - mission_plan: Generated missions for agents
            - selected_agents: List of agent types selected
            - spawned_jobs: List of spawned job IDs
            - workflow_result: Workflow execution result
            - token_reduction: Token reduction metrics

        Example:
            {
                'project_id': 'proj-123',
                'mission_plan': {...},
                'selected_agents': ['implementer', 'tester'],
                'spawned_jobs': ['job-1', 'job-2'],
                'workflow_result': {...},
                'token_reduction': {'reduction_percent': 70.0}
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {'error': 'Project ID is required'}

            if not tenant_key or not tenant_key.strip():
                return {'error': 'Tenant key is required'}

            # Get project by ID with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Project).where(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {'error': f"Project '{project_id}' not found"}

                # Ensure project has product_id
                if not project.product_id:
                    return {'error': f"Project '{project_id}' has no associated product"}

                # Initialize orchestrator
                orchestrator = ProjectOrchestrator()

                # Run orchestration workflow
                logger.info(
                    f"Starting orchestration for project {project.id} "
                    f"(name: {project.name}, tenant: {tenant_key})"
                )

                result_dict = await orchestrator.process_product_vision(
                    tenant_key=tenant_key,
                    product_id=project.product_id,
                    project_requirements=project.mission
                )

                logger.info(
                    f"Orchestration completed for project {project.id}. "
                    f"Spawned {len(result_dict.get('spawned_jobs', []))} jobs."
                )

                return result_dict

        except ValueError as e:
            logger.error(f"Orchestration validation error: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"Orchestration failed: {e}", exc_info=True)
            return {'error': f"Orchestration failed: {str(e)}"}

    @mcp.tool()
    async def get_agent_mission(
        agent_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Retrieve mission for a specific agent.

        Returns the markdown-formatted mission that was generated for the agent
        during orchestration. This mission contains the agent's specific objectives,
        context, and instructions.

        Args:
            agent_id: Agent database ID (UUID)
            tenant_key: Tenant key for isolation

        Returns:
            Dictionary containing:
            - mission: Markdown-formatted mission content
            - agent_id: Agent ID
            - agent_name: Agent name
            - agent_type: Agent type/role

        Example:
            {
                'mission': '# Mission: Implement Features\n\n...',
                'agent_id': 'agent-123',
                'agent_name': 'Feature Implementer',
                'agent_type': 'implementer'
            }
        """
        try:
            # Validate inputs
            if not agent_id or not agent_id.strip():
                return {'error': 'Agent ID is required'}

            if not tenant_key or not tenant_key.strip():
                return {'error': 'Tenant key is required'}

            # Get agent with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Agent).where(
                        Agent.id == agent_id,
                        Agent.tenant_key == tenant_key
                    )
                )
                agent = result.scalar_one_or_none()

                if not agent:
                    return {'error': f"Agent '{agent_id}' not found"}

                # Check if agent has mission
                if not agent.mission:
                    return {'error': f"Agent '{agent_id}' has no mission assigned"}

                logger.info(f"Retrieved mission for agent {agent_id} ({agent.name})")

                return {
                    'mission': agent.mission,
                    'agent_id': agent.id,
                    'agent_name': agent.name,
                    'agent_type': getattr(agent, 'type', getattr(agent, 'role', 'unknown'))
                }

        except Exception as e:
            logger.error(f"Failed to get agent mission: {e}", exc_info=True)
            return {'error': f"Failed to get agent mission: {str(e)}"}

    @mcp.tool()
    async def get_workflow_status(
        project_id: str,
        tenant_key: str
    ) -> dict[str, Any]:
        """
        Get current workflow status for a project.

        Provides real-time status of the orchestration workflow including:
        - Active agents (currently working)
        - Completed agents (finished their work)
        - Failed agents (encountered errors)
        - Current workflow stage
        - Overall progress percentage

        Args:
            project_id: Project database ID (UUID)
            tenant_key: Tenant key for isolation

        Returns:
            Dictionary containing:
            - active_agents: Count of agents currently working
            - completed_agents: Count of completed agents
            - failed_agents: Count of failed agents
            - pending_agents: Count of pending agents
            - current_stage: Current workflow stage description
            - progress_percent: Overall progress (0-100)
            - total_agents: Total number of agents

        Example:
            {
                'active_agents': 2,
                'completed_agents': 3,
                'failed_agents': 0,
                'pending_agents': 1,
                'current_stage': 'Implementation',
                'progress_percent': 60.0,
                'total_agents': 6
            }
        """
        try:
            # Validate inputs
            if not project_id or not project_id.strip():
                return {'error': 'Project ID is required'}

            if not tenant_key or not tenant_key.strip():
                return {'error': 'Tenant key is required'}

            # Verify project exists with tenant isolation
            async with db_manager.get_session_async() as session:
                result = await session.execute(
                    select(Project).where(
                        Project.id == project_id,
                        Project.tenant_key == tenant_key
                    )
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {'error': f"Project '{project_id}' not found"}

                # Get all MCPAgentJobs for this project/tenant
                # Note: MCPAgentJob doesn't have project_id, so we filter by tenant_key
                jobs_result = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.tenant_key == tenant_key
                    )
                )
                jobs = jobs_result.scalars().all()

                # Count by status
                active_count = sum(1 for job in jobs if job.status == 'active')
                completed_count = sum(1 for job in jobs if job.status == 'completed')
                failed_count = sum(1 for job in jobs if job.status == 'failed')
                pending_count = sum(1 for job in jobs if job.status == 'pending')
                total_count = len(jobs)

                # Calculate progress percentage
                if total_count > 0:
                    progress_percent = (completed_count / total_count) * 100.0
                else:
                    progress_percent = 0.0

                # Determine current stage
                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == total_count:
                    current_stage = "Completed"
                elif failed_count > 0:
                    current_stage = f"In Progress (with {failed_count} failure(s))"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                logger.info(
                    f"Workflow status for project {project_id}: "
                    f"{completed_count}/{total_count} completed ({progress_percent:.1f}%)"
                )

                return {
                    'active_agents': active_count,
                    'completed_agents': completed_count,
                    'failed_agents': failed_count,
                    'pending_agents': pending_count,
                    'current_stage': current_stage,
                    'progress_percent': round(progress_percent, 2),
                    'total_agents': total_count
                }

        except Exception as e:
            logger.error(f"Failed to get workflow status: {e}", exc_info=True)
            return {'error': f"Failed to get workflow status: {str(e)}"}
