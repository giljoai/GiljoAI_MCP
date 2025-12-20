"""
MCP Tools for Orchestrator Succession Management.

Handover 0080: Tools for orchestrators to manage succession lifecycle.

Tools:
- create_successor_orchestrator: Spawn successor and perform handover
- check_succession_status: Check if succession needed
"""

import logging
from typing import Any, Literal

from fastmcp import FastMCP
from sqlalchemy import select

from giljo_mcp.database import DatabaseManager
from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


# ============================================================================
# Tool Registration
# ============================================================================


def register_succession_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register orchestrator succession tools with the MCP server."""

    @mcp.tool()
    async def trigger_succession(
        agent_id: str,
        tenant_key: str,
        reason: Literal["context_limit", "manual", "phase_transition"] = "context_limit",
    ) -> dict[str, Any]:
        """
        Trigger succession for current agent execution.

        Handover 0366c: Updated to use agent_id (executor) instead of job_id (work order).

        This tool allows an agent to spawn a successor when:
        - Context window approaches capacity (90%+)
        - Manual handover requested
        - Project phase transition requires fresh context

        The tool performs:
        1. Creates new executor on SAME job (instance_number + 1)
        2. Generates compressed handover summary (<10K tokens)
        3. Marks current executor as complete
        4. Returns successor details for user launch

        Args:
            agent_id: UUID of current agent execution (the WHO - executor)
            tenant_key: Tenant key for multi-tenant isolation
            reason: Succession reason ('context_limit', 'manual', 'phase_transition')

        Returns:
            Dict containing:
            - current_agent_id: Current executor's agent_id
            - successor_agent_id: New executor's agent_id
            - job_id: Work order UUID (persists across succession)
            - instance_number: New instance number
            - handover_summary: Compressed state transfer
            - status: "waiting" (requires manual launch)

        Raises:
            ValueError: If agent_id not found or invalid

        Example:
            >>> result = await trigger_succession(
            ...     agent_id="exec-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
            ...     tenant_key="tenant-123",
            ...     reason="context_limit"
            ... )
            >>> print(f"Successor created: {result['successor_agent_id']}")
            >>> print(f"Instance number: {result['instance_number']}")
        """
        async with db_manager.get_session_async() as session:
            result = await _internal_trigger_succession(
                session=session,
                agent_id=agent_id,
                tenant_key=tenant_key,
                reason=reason,
            )

            logger.info(
                f"Succession completed: agent {result['current_agent_id']} → {result['successor_agent_id']}, "
                f"job_id: {result['job_id']}, "
                f"instance {result['instance_number']}, "
                f"reason: {reason}"
            )

            # Add user-friendly message
            result["message"] = (
                f"Successor agent created (instance {result['instance_number']}). "
                f"Original agent marked complete. "
                f"Launch successor manually from dashboard."
            )

            return result

    @mcp.tool()
    async def check_succession_status(
        agent_id: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """
        Check if agent execution should trigger succession.

        Handover 0366c: Updated to use agent_id (executor) instead of job_id.

        Analyzes context usage and returns recommendation for succession.

        Args:
            agent_id: UUID of agent execution to check
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict containing:
            - should_trigger: Boolean recommendation
            - context_used: Current context usage in tokens
            - context_budget: Maximum context budget
            - usage_percentage: Percentage used
            - threshold_reached: True if >= 90%
            - instance_number: Current instance number
            - recommendation: Human-readable recommendation

        Example:
            >>> status = await check_succession_status(agent_id, tenant_key)
            >>> if status['should_trigger']:
            ...     print(status['recommendation'])
        """
        from giljo_mcp.models.agent_identity import AgentExecution

        async with db_manager.get_session_async() as session:
            # Retrieve agent execution
            query = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id,
                AgentExecution.tenant_key == tenant_key,
            )
            result = await session.execute(query)
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Agent execution {agent_id} not found for tenant {tenant_key}")

            # Initialize succession manager
            manager = OrchestratorSuccessionManager(session, tenant_key)

            # Check if succession should be triggered
            should_trigger = manager.should_trigger_succession(execution)

            # Calculate usage percentage
            used = execution.context_used
            budget = execution.context_budget
            usage_percentage = (used / budget * 100) if budget > 0 else 0

            # Generate recommendation
            if usage_percentage >= 90:
                recommendation = (
                    f"Context usage at {usage_percentage:.1f}%. "
                    f"Succession recommended immediately to avoid context overflow."
                )
            elif usage_percentage >= 75:
                recommendation = (
                    f"Context usage at {usage_percentage:.1f}%. "
                    f"Consider planning succession for upcoming phase transition."
                )
            else:
                recommendation = f"Context usage at {usage_percentage:.1f}%. No succession needed at this time."

            return {
                "should_trigger": should_trigger,
                "context_used": used,
                "context_budget": budget,
                "usage_percentage": round(usage_percentage, 2),
                "threshold_reached": usage_percentage >= 90,
                "instance_number": execution.instance_number,
                "recommendation": recommendation,
            }


# ============================================================================
# Helper: Internal succession trigger (for testing)
# ============================================================================


async def _internal_trigger_succession(
    session,
    agent_id: str,
    tenant_key: str,
    reason: str = "context_limit",
) -> dict[str, Any]:
    """
    Internal helper for triggering succession (used by API endpoints and tests).

    Handover 0366c: Updated to use agent_id (executor UUID) instead of job_id.

    Args:
        session: Database session
        agent_id: Agent ID (executor UUID) to hand over from
        tenant_key: Tenant key for isolation
        reason: Succession reason

    Returns:
        Dict with successor details including:
        - current_agent_id: Current executor's agent_id
        - successor_agent_id: Successor executor's agent_id
        - job_id: Work order UUID (persists across succession)
        - instance_number: New instance number
    """
    # Import new models
    from giljo_mcp.models.agent_identity import AgentExecution

    # Retrieve current execution by agent_id
    query = select(AgentExecution).where(
        AgentExecution.agent_id == agent_id,
        AgentExecution.tenant_key == tenant_key,
    )
    result = await session.execute(query)
    current_execution = result.scalar_one_or_none()

    if not current_execution:
        raise ValueError(f"Agent execution {agent_id} not found for tenant {tenant_key}")

    if current_execution.status == "complete":
        raise ValueError(f"Agent {agent_id} is already complete. Cannot trigger succession.")

    # Initialize succession manager
    manager = OrchestratorSuccessionManager(session, tenant_key)

    # Create successor execution (on SAME job)
    successor_execution = await manager.create_successor(current_execution, reason=reason)

    # Generate handover summary
    handover_summary = manager.generate_handover_summary(current_execution)

    # Store handover summary in successor
    successor_execution.handover_summary = handover_summary
    await session.commit()

    # Refresh objects
    await session.refresh(current_execution)
    await session.refresh(successor_execution)

    return {
        "success": True,
        "current_agent_id": current_execution.agent_id,
        "successor_agent_id": successor_execution.agent_id,
        "job_id": current_execution.job_id,  # SAME job persists
        "instance_number": successor_execution.instance_number,
        "status": successor_execution.status,
        "handover_summary": handover_summary,
    }
