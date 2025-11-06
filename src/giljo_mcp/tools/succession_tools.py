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
from giljo_mcp.models import MCPAgentJob
from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


# ============================================================================
# Tool Registration
# ============================================================================


def register_succession_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register orchestrator succession tools with the MCP server."""

    @mcp.tool()
    async def create_successor_orchestrator(
        current_job_id: str,
        tenant_key: str,
        reason: Literal["context_limit", "manual", "phase_transition"] = "context_limit",
    ) -> dict[str, Any]:
        """
        Create successor orchestrator and perform handover.

        This tool allows an orchestrator agent to spawn a successor when:
        - Context window approaches capacity (90%+)
        - Manual handover requested
        - Project phase transition requires fresh context

        The tool performs:
        1. Creates new orchestrator job (instance_number + 1)
        2. Generates compressed handover summary (<10K tokens)
        3. Marks current orchestrator as complete
        4. Returns successor details for user launch

        Args:
            current_job_id: UUID of current orchestrator job
            tenant_key: Tenant key for multi-tenant isolation
            reason: Succession reason ('context_limit', 'manual', 'phase_transition')

        Returns:
            Dict containing:
            - successor_id: UUID of new orchestrator
            - instance_number: New instance number
            - handover_summary: Compressed state transfer
            - status: "waiting" (requires manual launch)

        Raises:
            ValueError: If current_job_id not found or not an orchestrator

        Example:
            >>> result = await create_successor_orchestrator(
            ...     current_job_id="orch-6adbec5c-9e11-46b4-ad8b-060c69a8d124",
            ...     tenant_key="tenant-123",
            ...     reason="context_limit"
            ... )
            >>> print(f"Successor created: {result['successor_id']}")
            >>> print(f"Instance number: {result['instance_number']}")
        """
        with db_manager.get_session() as session:
            # Retrieve current orchestrator job
            query = select(MCPAgentJob).where(
                MCPAgentJob.job_id == current_job_id,
                MCPAgentJob.tenant_key == tenant_key,  # Tenant isolation
            )
            result = session.execute(query)
            orchestrator = result.scalar_one_or_none()

            if not orchestrator:
                raise ValueError(f"Orchestrator job {current_job_id} not found for tenant {tenant_key}")

            # Verify agent type is orchestrator
            if orchestrator.agent_type != "orchestrator":
                raise ValueError(f"Job {current_job_id} is not an orchestrator (type: {orchestrator.agent_type})")

            # Verify orchestrator is not already complete
            if orchestrator.status == "complete":
                raise ValueError(
                    f"Orchestrator {current_job_id} is already complete. "
                    f"Cannot trigger succession on completed orchestrator."
                )

            # Initialize succession manager
            manager = OrchestratorSuccessionManager(session, tenant_key)

            # Create successor
            successor = manager.create_successor(orchestrator, reason=reason)

            # Generate handover summary
            handover_summary = manager.generate_handover_summary(orchestrator)

            # Complete handover
            manager.complete_handover(orchestrator, successor, handover_summary, reason)

            # Refresh objects
            session.refresh(orchestrator)
            session.refresh(successor)

            logger.info(
                f"Succession completed: {orchestrator.job_id} → {successor.job_id}, "
                f"instance {orchestrator.instance_number} → {successor.instance_number}, "
                f"reason: {reason}"
            )

            # Return successor details
            return {
                "success": True,
                "successor_id": successor.job_id,
                "instance_number": successor.instance_number,
                "status": successor.status,  # "waiting"
                "handover_summary": handover_summary,
                "message": (
                    f"Successor orchestrator created (instance {successor.instance_number}). "
                    f"Original orchestrator marked complete. "
                    f"Launch successor manually from dashboard."
                ),
            }

    @mcp.tool()
    async def check_succession_status(
        job_id: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """
        Check if orchestrator should trigger succession.

        Analyzes context usage and returns recommendation for succession.

        Args:
            job_id: UUID of orchestrator job to check
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Dict containing:
            - should_trigger: Boolean recommendation
            - context_used: Current context usage in tokens
            - context_budget: Maximum context budget
            - usage_percentage: Percentage used
            - threshold_reached: True if >= 90%
            - recommendation: Human-readable recommendation

        Example:
            >>> status = await check_succession_status(job_id, tenant_key)
            >>> if status['should_trigger']:
            ...     print(status['recommendation'])
        """
        with db_manager.get_session() as session:
            # Retrieve orchestrator job
            query = select(MCPAgentJob).where(
                MCPAgentJob.job_id == job_id,
                MCPAgentJob.tenant_key == tenant_key,
            )
            result = session.execute(query)
            orchestrator = result.scalar_one_or_none()

            if not orchestrator:
                raise ValueError(f"Orchestrator job {job_id} not found")

            if orchestrator.agent_type != "orchestrator":
                raise ValueError(f"Job {job_id} is not an orchestrator (type: {orchestrator.agent_type})")

            # Initialize succession manager
            manager = OrchestratorSuccessionManager(session, tenant_key)

            # Check if succession should be triggered
            should_trigger = manager.should_trigger_succession(orchestrator)

            # Calculate usage percentage
            used = orchestrator.context_used
            budget = orchestrator.context_budget
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
                "instance_number": orchestrator.instance_number,
                "recommendation": recommendation,
            }


# ============================================================================
# Helper: Internal succession trigger (for testing)
# ============================================================================


async def _internal_trigger_succession(
    session,
    job_id: str,
    tenant_key: str,
    reason: str = "context_limit",
) -> dict[str, Any]:
    """
    Internal helper for triggering succession (used by API endpoints and tests).

    Args:
        session: Database session
        job_id: Orchestrator job ID
        tenant_key: Tenant key for isolation
        reason: Succession reason

    Returns:
        Dict with successor details
    """
    # Retrieve orchestrator job
    query = select(MCPAgentJob).where(
        MCPAgentJob.job_id == job_id,
        MCPAgentJob.tenant_key == tenant_key,
    )
    result = session.execute(query)
    orchestrator = result.scalar_one_or_none()

    if not orchestrator:
        raise ValueError(f"Orchestrator job {job_id} not found")

    if orchestrator.agent_type != "orchestrator":
        raise ValueError(f"Job {job_id} is not an orchestrator (type: {orchestrator.agent_type})")

    if orchestrator.status == "complete":
        raise ValueError(f"Orchestrator {job_id} is already complete. Cannot trigger succession.")

    # Initialize succession manager
    manager = OrchestratorSuccessionManager(session, tenant_key)

    # Create successor
    successor = manager.create_successor(orchestrator, reason=reason)

    # Generate handover summary
    handover_summary = manager.generate_handover_summary(orchestrator)

    # Complete handover
    manager.complete_handover(orchestrator, successor, handover_summary, reason)

    # Refresh objects
    session.refresh(orchestrator)
    session.refresh(successor)

    return {
        "success": True,
        "successor_id": successor.job_id,
        "instance_number": successor.instance_number,
        "status": successor.status,
        "handover_summary": handover_summary,
    }
