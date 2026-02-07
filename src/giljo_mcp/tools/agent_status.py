"""
MCP Tool for Agent Status Management (Handover 0073, 0366c).

Provides set_agent_status tool for agents to update their own status
in the orchestration grid with progress tracking and enhanced visibility.

Production-grade features:
- Multi-tenant isolation enforcement
- Comprehensive error handling
- State machine validation
- WebSocket event broadcasting
- Type validation and safety checks

Handover 0366c Changes:
- Refactored to use agent_id (executor UUID) instead of job_id
- Queries AgentExecution table instead of Job/MCPAgentJob
- Returns both agent_id and job_id in responses
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentExecution


logger = logging.getLogger(__name__)

# Valid status values (Handover 0113 - 7 State System)
VALID_STATUSES = {"waiting", "working", "blocked", "complete", "failed", "cancelled", "decommissioned"}

# Terminal states (cannot transition from these)
TERMINAL_STATES = {"failed", "cancelled", "decommissioned"}


# Module-level state holder
class _AgentStatusState:
    """State holder to avoid global statement."""

    db_manager: Any | None = None


def init_for_testing(db_manager):
    """
    Initialize module-level database manager for testing.

    This function is called by tests to initialize the module without going through
    the full MCP registration process.

    Args:
        db_manager: Database manager instance for testing
    """
    _AgentStatusState.db_manager = db_manager


async def set_agent_status(
    agent_id: str,
    tenant_key: str,
    status: str,
    progress: int | None = None,
    reason: str | None = None,
    current_task: str | None = None,
    estimated_completion: datetime | None = None,
) -> dict[str, Any]:
    """
    MCP tool for agents to update their own status in the orchestration grid.

    Args:
        agent_id: Agent execution ID to update (the WHO - specific executor instance)
        tenant_key: Tenant identifier for multi-tenant isolation
        status: One of ['waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned']
        progress: int | None - Progress percentage (0-100), required for 'working' status
        reason: str | None - Reason for 'failed' or 'blocked' status
        current_task: str | None - Description of current task (for 'working' status)
        estimated_completion: datetime | None - When agent expects to complete

    Returns:
        dict: {
            "success": bool,
            "agent_id": str,  # Executor identifier (the WHO)
            "job_id": str,    # Work order context (the WHAT)
            "old_status": str,
            "new_status": str,
            "message": str
        }

    Raises:
        ValueError: If invalid status, invalid progress range, or missing required fields
        ValueError: If agent execution doesn't exist or belongs to different tenant
        ValueError: If attempting invalid state transition

    Security:
        - Multi-tenant isolation enforced via tenant_key filtering
        - Only executions belonging to the specified tenant can be updated
        - No cross-tenant status updates possible

    State Machine (Handover 0113 - 7 State System):
        - Cannot transition from terminal states ('failed', 'cancelled', 'decommissioned')
        - 'working' status requires progress parameter
        - 'failed' and 'blocked' statuses require reason parameter
        - 'decommissioned' state returns special error message for visibility
    """
    try:
        # Validate input parameters
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

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

        # Try to import websocket_manager, but make it optional for testing
        try:
            from api.websocket import websocket_manager
        except (ImportError, AttributeError):
            websocket_manager = None

        # Use module-level db_manager (injected by tests or register function)
        if _AgentStatusState.db_manager is None:
            from giljo_mcp.database import DatabaseManager

            db_manager = DatabaseManager()
        else:
            db_manager = _AgentStatusState.db_manager

        async with db_manager.get_session_async() as session:
            # Get execution with tenant isolation (Handover 0366c)
            stmt = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id, AgentExecution.tenant_key == tenant_key
            )
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Agent execution {agent_id} not found for tenant {tenant_key}")

            # Store old status for response
            old_status = execution.status

            # Validate state machine - cannot transition from terminal states
            if old_status in TERMINAL_STATES:
                raise ValueError(
                    f"Cannot transition from terminal state '{old_status}'. Execution is already in final state."
                )

            # Update status
            execution.status = status

            # Update progress if provided
            if progress is not None:
                execution.progress = progress

            # Update current task if provided
            if current_task is not None:
                execution.current_task = current_task

            # Update estimated completion if provided
            if estimated_completion is not None:
                execution.estimated_completion = estimated_completion

            # Set block reason for blocked status
            if status == "blocked" and reason:
                execution.block_reason = reason
            elif status != "blocked":
                # Clear block reason if not blocked
                execution.block_reason = None

            # Set completed_at timestamp for complete status
            if status == "complete" and not execution.completed_at:
                execution.completed_at = datetime.now(timezone.utc)

            # Commit changes
            await session.commit()
            await session.refresh(execution)

            # Broadcast WebSocket event (optional in test environments)
            if websocket_manager:
                try:
                    await websocket_manager.broadcast_agent_status_update(
                        job_id=execution.job_id,
                        tenant_key=tenant_key,
                        old_status=old_status,
                        new_status=status,
                        progress=progress,
                        current_task=current_task,
                        block_reason=reason if status == "blocked" else None,
                        estimated_completion=estimated_completion,
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                    logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                    # Non-critical - continue without WebSocket broadcast

            logger.info(
                f"[set_agent_status] Execution {agent_id} status updated: {old_status} -> {status}, tenant={tenant_key}"
            )

            return {
                "success": True,
                "agent_id": agent_id,
                "job_id": execution.job_id,
                "old_status": old_status,
                "new_status": status,
                "message": f"Status updated to '{status}' successfully",
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[set_agent_status] Error updating status: {e}", exc_info=True)
        raise ValueError(f"Failed to update agent status: {e!s}") from e


async def report_progress(
    agent_id: str,
    tenant_key: str,
    progress: dict,
) -> dict[str, Any]:
    """
    MCP tool for agents to report progress updates (Handover 0107).

    Updates the last_progress_at timestamp for health monitoring and stores
    latest progress information in execution metadata.

    Args:
        agent_id: Agent execution ID to update (the WHO - specific executor instance)
        tenant_key: Tenant identifier for multi-tenant isolation
        progress: Progress data dict (step, details, percentage, etc.)

    Returns:
        dict: {
            "success": bool,
            "agent_id": str,  # Executor identifier (the WHO)
            "job_id": str,    # Work order context (the WHAT)
            "timestamp": str (ISO format),
            "message": str
        }

    Raises:
        ValueError: If invalid parameters or agent execution doesn't exist

    Security:
        - Multi-tenant isolation enforced via tenant_key filtering
        - Only executions belonging to the specified tenant can be updated
    """
    try:
        # Validate input parameters
        if not agent_id or not agent_id.strip():
            raise ValueError("agent_id cannot be empty")

        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not progress or not isinstance(progress, dict):
            raise ValueError("progress must be a non-empty dictionary")

        # Try to import websocket_manager, but make it optional for testing
        try:
            from api.websocket import websocket_manager
        except (ImportError, AttributeError):
            websocket_manager = None

        # Use module-level db_manager (injected by tests or register function)
        if _AgentStatusState.db_manager is None:
            from giljo_mcp.database import DatabaseManager

            db_manager = DatabaseManager()
        else:
            db_manager = _AgentStatusState.db_manager

        async with db_manager.get_session_async() as session:
            # Get execution with tenant isolation (Handover 0366c)
            stmt = select(AgentExecution).where(
                AgentExecution.agent_id == agent_id, AgentExecution.tenant_key == tenant_key
            )
            result = await session.execute(stmt)
            execution = result.scalar_one_or_none()

            if not execution:
                raise ValueError(f"Agent execution {agent_id} not found for tenant {tenant_key}")

            # Update last_progress_at timestamp
            now = datetime.now(timezone.utc)
            execution.last_progress_at = now

            # Update progress percentage if provided in dict
            if "percentage" in progress:
                execution.progress = progress["percentage"]
            if "current_task" in progress:
                execution.current_task = progress["current_task"]

            # Commit changes
            await session.commit()
            await session.refresh(execution)

            # Broadcast WebSocket event (optional in test environments)
            if websocket_manager:
                try:
                    await websocket_manager.broadcast(
                        {
                            "type": "job:progress_update",
                            "agent_id": agent_id,
                            "job_id": execution.job_id,
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "tenant_key": tenant_key,
                            "progress": progress,
                            "timestamp": now.isoformat(),
                        }
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket failures should not break core operations
                    logger.warning(f"Failed to broadcast WebSocket event: {ws_error}")
                    # Non-critical - continue without WebSocket broadcast

            logger.info(f"[report_progress] Execution {agent_id} progress updated, tenant={tenant_key}")

            return {
                "success": True,
                "agent_id": agent_id,
                "job_id": execution.job_id,
                "timestamp": now.isoformat(),
                "message": "Progress reported successfully",
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[report_progress] Error reporting progress: {e}", exc_info=True)
        raise ValueError(f"Failed to report progress: {e!s}") from e
