"""
Agent Job Status Update Tool for GiljoAI MCP

Handover 0066: Agent Self-Navigation for Kanban Board
Enables agents to move themselves between Kanban columns by updating their job status.

This tool supports the 4-column Kanban workflow:
- Pending: Jobs created, waiting for agent to start
- Active: Jobs in progress (agent working)
- Completed: Jobs finished successfully
- Blocked: Jobs failed or waiting for feedback

NO drag-drop functionality - agents move themselves using this MCP tool.
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import FastMCP

from giljo_mcp.agent_job_manager import AgentJobManager
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


def register_agent_job_status_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register agent job status update tools with the MCP server"""

    # Initialize job manager
    job_manager = AgentJobManager(db_manager)

    # Valid statuses for Kanban board (Handover 0066)
    VALID_STATUSES = {"pending", "active", "completed", "blocked"}

    @mcp.tool()
    async def update_job_status(
        job_id: str,
        tenant_key: str,
        new_status: str,
        reason: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Update job status for agent self-navigation on Kanban board.

        This tool enables agents to move themselves between Kanban columns by
        updating their job status. Agents must call this tool to report progress
        and navigate the workflow.

        Valid Status Transitions:
        - pending -> active: Agent starts work (sets started_at)
        - pending -> blocked: Agent cannot start (early failure detection)
        - active -> completed: Agent finishes successfully (sets completed_at)
        - active -> blocked: Agent encounters blocker (sets completed_at)

        Kanban Columns (4 total):
        1. Pending: Jobs created, waiting for agent to start
        2. Active: Jobs in progress (agent working)
        3. Completed: Jobs finished successfully
        4. Blocked: Jobs failed OR waiting for feedback (combined status)

        Args:
            job_id: Job identifier (UUID from job assignment)
            tenant_key: Tenant key for multi-tenant isolation
            new_status: New status (pending, active, completed, blocked)
            reason: Optional reason for status change (recommended for blocked status)

        Returns:
            Dict with success status, old/new status, and updated timestamps

        Examples:
            # Agent starts work
            mcp.call_tool("update_job_status", {
                "job_id": "uuid",
                "tenant_key": "tenant-key",
                "new_status": "active"
            })

            # Agent encounters blocker
            mcp.call_tool("update_job_status", {
                "job_id": "uuid",
                "tenant_key": "tenant-key",
                "new_status": "blocked",
                "reason": "Need database schema clarification"
            })

            # Agent completes work
            mcp.call_tool("update_job_status", {
                "job_id": "uuid",
                "tenant_key": "tenant-key",
                "new_status": "completed"
            })

        Handover 0066: Agent Self-Navigation
        - Agents move themselves between columns (NO drag-drop by users)
        - Updates trigger WebSocket events for real-time Kanban board updates
        - Multi-tenant isolation enforced at database level
        """
        try:
            # Input validation
            if not job_id:
                logger.error("Empty job_id provided to update_job_status")
                return {
                    "success": False,
                    "error": "job_id cannot be empty",
                    "job_id": job_id,
                }

            if not tenant_key:
                logger.error("Empty tenant_key provided to update_job_status")
                return {
                    "success": False,
                    "error": "tenant_key cannot be empty",
                    "job_id": job_id,
                }

            # Validate status
            if new_status not in VALID_STATUSES:
                logger.error(f"Invalid status '{new_status}' provided to update_job_status")
                return {
                    "success": False,
                    "error": f"Invalid status. Must be one of: {', '.join(sorted(VALID_STATUSES))}",
                    "job_id": job_id,
                }

            async with db_manager.get_session_async() as session:
                # Get current job with tenant isolation
                job = await session.run_sync(
                    lambda sync_session: job_manager.get_job(
                        tenant_key=tenant_key,
                        job_id=job_id,
                    )
                )

                if not job:
                    logger.error(f"Job {job_id} not found for tenant {tenant_key} in update_job_status")
                    return {
                        "success": False,
                        "error": f"Job {job_id} not found for tenant {tenant_key}",
                        "job_id": job_id,
                    }

                # Store old status for response
                old_status = job.status

                # Build metadata for status update
                metadata = {}
                if reason:
                    metadata["reason"] = reason
                    metadata["message"] = f"Status changed to {new_status}: {reason}"
                else:
                    metadata["message"] = f"Status changed to {new_status}"

                # Handle different status transitions
                if new_status == "completed":
                    # Use complete_job for completed status
                    updated_job = await session.run_sync(
                        lambda sync_session: job_manager.complete_job(
                            tenant_key=tenant_key,
                            job_id=job_id,
                            result=metadata,
                        )
                    )
                elif new_status == "blocked":
                    # Update to blocked status and set completed_at
                    # Handover 0066: 'blocked' is a terminal state like 'completed'
                    def update_to_blocked(sync_session):
                        from sqlalchemy import select

                        from giljo_mcp.models import Job

                        # Get job
                        stmt = select(Job).where(Job.tenant_key == tenant_key, Job.job_id == job_id)
                        db_job = sync_session.execute(stmt).scalar_one_or_none()

                        if not db_job:
                            raise ValueError(f"Job {job_id} not found")

                        # Validate transition
                        job_manager._validate_status_transition(db_job.status, "blocked")

                        # Update status and completed_at
                        db_job.status = "blocked"
                        db_job.completed_at = datetime.now(timezone.utc)

                        # Add message if provided
                        if metadata and "message" in metadata:
                            message = job_manager._create_message(metadata["message"])
                            db_job.messages = db_job.messages + [message]

                        sync_session.commit()
                        sync_session.refresh(db_job)
                        return db_job

                    updated_job = await session.run_sync(update_to_blocked)
                elif new_status == "active":
                    # Acknowledge job (moves to active and sets started_at)
                    if old_status == "pending":
                        updated_job = await session.run_sync(
                            lambda sync_session: job_manager.acknowledge_job(
                                tenant_key=tenant_key,
                                job_id=job_id,
                            )
                        )
                    else:
                        # Already active or transitioning from another state
                        updated_job = await session.run_sync(
                            lambda sync_session: job_manager.update_job_status(
                                tenant_key=tenant_key,
                                job_id=job_id,
                                status=new_status,
                                metadata=metadata,
                            )
                        )
                else:
                    # Generic status update (e.g., back to pending)
                    updated_job = await session.run_sync(
                        lambda sync_session: job_manager.update_job_status(
                            tenant_key=tenant_key,
                            job_id=job_id,
                            status=new_status,
                            metadata=metadata,
                        )
                    )

                # Build response with timestamp information
                response = {
                    "success": True,
                    "job_id": job_id,
                    "old_status": old_status,
                    "new_status": updated_job.status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                }

                # Add timestamps based on status
                if updated_job.started_at:
                    response["started_at"] = updated_job.started_at.isoformat()

                if updated_job.completed_at:
                    response["completed_at"] = updated_job.completed_at.isoformat()

                # Add reason to response if provided
                if reason:
                    response["reason"] = reason

                logger.info(
                    f"Job {job_id} status updated: {old_status} -> {updated_job.status} "
                    f"for tenant {tenant_key}" + (f" (reason: {reason})" if reason else "")
                )

                # TODO: Trigger WebSocket event for Kanban board real-time updates
                # This will be implemented in the next phase
                # await websocket_manager.broadcast_job_status_changed(...)

                return response

        except ValueError as ve:
            # Handle invalid status transitions from AgentJobManager
            logger.error(f"Invalid status transition for job {job_id}: {ve}")
            return {
                "success": False,
                "error": str(ve),
                "job_id": job_id,
            }
        except Exception as e:
            logger.exception(f"Failed to update status for job {job_id}")
            return {
                "success": False,
                "error": str(e),
                "job_id": job_id,
            }

    logger.info("Agent job status tools registered (update_job_status)")
