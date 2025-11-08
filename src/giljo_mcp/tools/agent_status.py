"""
MCP Tool for Agent Status Management (Handover 0073).

Provides set_agent_status tool for agents to update their own status
in the orchestration grid with progress tracking and enhanced visibility.

Production-grade features:
- Multi-tenant isolation enforcement
- Comprehensive error handling
- State machine validation
- WebSocket event broadcasting
- Type validation and safety checks
"""

import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy import select

from ..models import Job


logger = logging.getLogger(__name__)

# Valid status values (Handover 0113 - 7 State System)
VALID_STATUSES = {"waiting", "working", "blocked", "complete", "failed", "cancelled", "decommissioned"}

# Terminal states (cannot transition from these)
TERMINAL_STATES = {"failed", "cancelled", "decommissioned"}


async def set_agent_status(
    job_id: str,
    tenant_key: str,
    status: str,
    progress: Optional[int] = None,
    reason: Optional[str] = None,
    current_task: Optional[str] = None,
    estimated_completion: Optional[datetime] = None,
) -> Dict[str, Any]:
    """
    MCP tool for agents to update their own status in the orchestration grid.

    Args:
        job_id: Agent job ID to update
        tenant_key: Tenant identifier for multi-tenant isolation
        status: One of ['waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned']
        progress: Optional[int] - Progress percentage (0-100), required for 'working' status
        reason: Optional[str] - Reason for 'failed' or 'blocked' status
        current_task: Optional[str] - Description of current task (for 'working' status)
        estimated_completion: Optional[datetime] - When agent expects to complete

    Returns:
        dict: {
            "success": bool,
            "job_id": str,
            "old_status": str,
            "new_status": str,
            "message": str
        }

    Raises:
        ValueError: If invalid status, invalid progress range, or missing required fields
        ValueError: If job doesn't exist or belongs to different tenant
        ValueError: If attempting invalid state transition

    Security:
        - Multi-tenant isolation enforced via tenant_key filtering
        - Only jobs belonging to the specified tenant can be updated
        - No cross-tenant status updates possible

    State Machine (Handover 0113 - 7 State System):
        - Cannot transition from terminal states ('failed', 'cancelled', 'decommissioned')
        - 'working' status requires progress parameter
        - 'failed' and 'blocked' statuses require reason parameter
        - 'decommissioned' state returns special error message for visibility
    """
    try:
        # Validate input parameters
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not status or status not in VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of: {', '.join(sorted(VALID_STATUSES))}")

        # Validate progress range
        if progress is not None and (progress < 0 or progress > 100):
            raise ValueError(f"progress must be between 0 and 100, got: {progress}")

        # Validate required fields for specific statuses
        if status == "working" and progress is None:
            raise ValueError("progress is required when status='working'")

        if status in ("failed", "blocked") and not reason:
            raise ValueError(f"reason is required when status='{status}'")

        # Import database manager and websocket manager
        from api.websocket import websocket_manager

        from ..database import DatabaseManager

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            # Get job with tenant isolation
            stmt = select(Job).where(Job.job_id == job_id, Job.tenant_key == tenant_key)
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            # Store old status for response
            old_status = job.status

            # Validate state machine - cannot transition from terminal states
            if old_status in TERMINAL_STATES:
                # Handover 0113: Special message for decommissioned agents
                if old_status == "decommissioned":
                    return {
                        "success": False,
                        "error": "AGENT_DECOMMISSIONED",
                        "job_id": job_id,
                        "old_status": old_status,
                        "message": f"Agent {job_id} has been decommissioned (project closeout complete). Spawn a new agent if needed.",
                        "decommissioned_at": job.decommissioned_at.isoformat() if job.decommissioned_at else None,
                    }
                raise ValueError(
                    f"Cannot transition from terminal state '{old_status}'. Job is already in final state."
                )

            # Update status
            job.status = status

            # Update progress if provided
            if progress is not None:
                job.progress = progress

            # Update current task if provided
            if current_task is not None:
                job.current_task = current_task

            # Update estimated completion if provided
            if estimated_completion is not None:
                job.estimated_completion = estimated_completion

            # Set block reason for blocked status
            if status == "blocked" and reason:
                job.block_reason = reason
            elif status != "blocked":
                # Clear block reason if not blocked
                job.block_reason = None

            # Set completed_at timestamp for complete status
            if status == "complete" and not job.completed_at:
                job.completed_at = datetime.now(timezone.utc)

            # Commit changes
            await session.commit()
            await session.refresh(job)

            # Broadcast WebSocket event
            try:
                await websocket_manager.broadcast_agent_status_update(
                    job_id=job_id,
                    tenant_key=tenant_key,
                    old_status=old_status,
                    new_status=status,
                    progress=progress,
                    current_task=current_task,
                    block_reason=reason if status == "blocked" else None,
                    estimated_completion=estimated_completion,
                )
            except Exception as ws_error:
                logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                # Non-critical - continue without WebSocket broadcast

            logger.info(
                f"[set_agent_status] Job {job_id} status updated: {old_status} -> {status}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "job_id": job_id,
                "old_status": old_status,
                "new_status": status,
                "message": f"Status updated to '{status}' successfully",
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[set_agent_status] Error updating status: {e}", exc_info=True)
        raise ValueError(f"Failed to update agent status: {e!s}")


async def report_progress(
    job_id: str,
    tenant_key: str,
    progress: dict,
) -> Dict[str, Any]:
    """
    MCP tool for agents to report progress updates (Handover 0107).

    Updates the last_progress_at timestamp for health monitoring and stores
    latest progress information in job metadata.

    Args:
        job_id: Agent job ID to update
        tenant_key: Tenant identifier for multi-tenant isolation
        progress: Progress data dict (step, details, percentage, etc.)

    Returns:
        dict: {
            "success": bool,
            "job_id": str,
            "timestamp": str (ISO format),
            "message": str
        }

    Raises:
        ValueError: If invalid parameters or job doesn't exist

    Security:
        - Multi-tenant isolation enforced via tenant_key filtering
        - Only jobs belonging to the specified tenant can be updated
    """
    try:
        # Validate input parameters
        if not job_id or not job_id.strip():
            raise ValueError("job_id cannot be empty")

        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not progress or not isinstance(progress, dict):
            raise ValueError("progress must be a non-empty dictionary")

        # Import database manager and websocket manager
        from api.websocket import websocket_manager

        from ..database import DatabaseManager
        from ..models import MCPAgentJob

        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            # Get job with tenant isolation
            stmt = select(MCPAgentJob).where(
                MCPAgentJob.job_id == job_id,
                MCPAgentJob.tenant_key == tenant_key
            )
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            # Update last_progress_at timestamp
            now = datetime.now(timezone.utc)
            job.last_progress_at = now

            # Store progress in job_metadata
            if job.job_metadata is None:
                job.job_metadata = {}
            job.job_metadata["latest_progress"] = progress
            job.job_metadata["latest_progress_timestamp"] = now.isoformat()

            # Commit changes
            await session.commit()
            await session.refresh(job)

            # Broadcast WebSocket event
            try:
                await websocket_manager.broadcast(
                    {
                        "type": "job:progress_update",
                        "job_id": job_id,
                        "tenant_key": tenant_key,
                        "progress": progress,
                        "timestamp": now.isoformat(),
                    }
                )
            except Exception as ws_error:
                logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                # Non-critical - continue without WebSocket broadcast

            logger.info(
                f"[report_progress] Job {job_id} progress updated, tenant={tenant_key}"
            )

            return {
                "success": True,
                "job_id": job_id,
                "timestamp": now.isoformat(),
                "message": "Progress reported successfully",
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[report_progress] Error reporting progress: {e}", exc_info=True)
        raise ValueError(f"Failed to report progress: {e!s}")


def register_agent_status_tools(server, db_manager, tenant_manager=None):
    """
    Register agent status tools with MCP server.

    Args:
        server: MCP server instance with @server.tool() decorator
        db_manager: DatabaseManager instance (not directly used, but kept for consistency)
        tenant_manager: Optional TenantManager instance (not used for these tools)
    """

    @server.tool()
    async def set_agent_status_tool(
        job_id: str,
        tenant_key: str,
        status: str,
        progress: Optional[int] = None,
        reason: Optional[str] = None,
        current_task: Optional[str] = None,
        estimated_completion: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """
        Update agent job status with progress tracking.

        Agents use this tool to report their current status to the orchestration grid,
        enabling real-time visibility and coordination.

        Args:
            job_id: Agent job ID to update
            tenant_key: Tenant identifier for multi-tenant isolation
            status: Status value (waiting, preparing, working, review, complete, failed, blocked)
            progress: Progress percentage 0-100 (required for 'working')
            reason: Reason for failed/blocked status (required for 'failed'/'blocked')
            current_task: Description of current task being executed
            estimated_completion: ISO datetime string for estimated completion

        Returns:
            Status update result with old and new status

        Examples:
            Update to working status:
            >>> set_agent_status_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     status="working",
            ...     progress=45,
            ...     current_task="Implementing authentication module"
            ... )

            Report blocked status:
            >>> set_agent_status_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     status="blocked",
            ...     reason="Waiting for API key configuration"
            ... )
        """
        return await set_agent_status(
            job_id=job_id,
            tenant_key=tenant_key,
            status=status,
            progress=progress,
            reason=reason,
            current_task=current_task,
            estimated_completion=estimated_completion,
        )

    @server.tool()
    async def report_progress_tool(
        job_id: str,
        tenant_key: str,
        progress: dict,
    ) -> Dict[str, Any]:
        """
        Report progress update for agent job (Handover 0107).

        Agents use this tool to report progress updates, which updates the
        last_progress_at timestamp for health monitoring and stores the
        latest progress information.

        Args:
            job_id: Agent job ID
            tenant_key: Tenant identifier for multi-tenant isolation
            progress: Progress data dict (should contain keys like: step, details, percentage, etc.)

        Returns:
            Progress update result with job_id and timestamp

        Examples:
            Report progress:
            >>> report_progress_tool(
            ...     job_id="abc-123",
            ...     tenant_key="tenant-xyz",
            ...     progress={
            ...         "step": "database_setup",
            ...         "details": "Creating tables",
            ...         "percentage": 45
            ...     }
            ... )
        """
        return await report_progress(
            job_id=job_id,
            tenant_key=tenant_key,
            progress=progress,
        )

    logger.info("[agent_status] Registered agent status tools for MCP orchestration")
