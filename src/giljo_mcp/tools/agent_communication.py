"""
INTERNAL/LEGACY: Agent-Orchestrator Communication Tools

WARNING: These tools are INTERNAL and for backward compatibility only.
HTTP MCP agents should use MessageService for all messaging operations.

This module is retained for:
- Legacy orchestrator code compatibility
- Internal testing and debugging
- Potential future deprecation

See Handovers 0295, 0298 for the messaging contract and cleanup decisions.

DO NOT use these tools for new development.
Use MessageService and the canonical MCP messaging tools instead.

Original Purpose (Handover 0040):
Professional Agent Flow Visualization - enables agents to poll for messages,
acknowledge receipt, and report status updates.

These tools support the 30-60 second polling pattern for real-time visualization.

Handover 0366c: Updated to use agent_id (executor) instead of job_id (work order).
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import FastMCP
from sqlalchemy import select, and_

from giljo_mcp.agent_message_queue import AgentMessageQueue
from giljo_mcp.agent_job_manager import AgentJobManager
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager
from giljo_mcp.models.agent_identity import AgentExecution
from giljo_mcp.services.message_service_0366b import MessageService


logger = logging.getLogger(__name__)


def register_agent_communication_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register agent-orchestrator communication tools with the MCP server"""

    # Initialize managers
    job_manager = AgentJobManager(db_manager)
    comm_queue = AgentMessageQueue(db_manager)  # Using compatibility layer

    @mcp.tool()
    async def check_orchestrator_messages(
        agent_id: str,
        tenant_key: str,
        message_type: Optional[str] = None,
        unread_only: bool = True,
    ) -> dict[str, Any]:
        """
        Check for messages from the orchestrator or other agents.

        This tool supports the polling pattern (30-60 second intervals) for
        real-time agent visualization and communication.

        Handover 0366c: Updated to use agent_id (executor) instead of job_id (work order).

        Args:
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation
            message_type: Optional filter by message type (task, info, error, etc.)
            unread_only: Only return unacknowledged messages (default: True)

        Returns:
            Dict with status, message count, and list of messages
        """
        try:
            # Use MessageService for agent_id-based routing
            message_service = MessageService(
                db_manager=db_manager,
                tenant_manager=tenant_manager,
                websocket_manager=None,
            )

            # Receive messages using agent_id (returns list directly)
            messages = await message_service.receive_messages(
                agent_id=agent_id,
                tenant_key=tenant_key,
                limit=10,
            )

            # Filter by message type if specified
            if message_type:
                messages = [msg for msg in messages if msg.get("type") == message_type]

            logger.info(
                f"Retrieved {len(messages)} messages for agent {agent_id} (unread_only={unread_only})"
            )

            return {
                "success": True,
                "agent_id": agent_id,
                "message_count": len(messages),
                "messages": messages,
                "has_unread": any(not msg.get("acknowledged", False) for msg in messages),
            }

        except Exception as e:
            logger.exception(f"Failed to check orchestrator messages for agent {agent_id}")
            return {"success": False, "error": str(e), "agent_id": agent_id}

    @mcp.tool()
    async def report_status(
        agent_id: str,
        tenant_key: str,
        status: str,
        current_task: Optional[str] = None,
        progress_percentage: Optional[int] = None,
        context_usage: Optional[int] = None,
        artifacts_created: Optional[list[dict]] = None,
        metadata: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Report agent status and progress to the orchestrator.

        This tool enables real-time status updates for visualization, including
        current task, progress percentage, context usage, and artifact creation.
        Updates trigger WebSocket events for the flow visualization UI.

        Handover 0366c: Updated to use agent_id (executor) instead of job_id (work order).
        Status updates now target AgentExecution (executor instance), not AgentJob (work order).

        Args:
            agent_id: Agent execution ID (executor UUID)
            tenant_key: Tenant key for multi-tenant isolation
            status: Current status (waiting, working, blocked, complete, failed, cancelled)
            current_task: Description of current task being worked on
            progress_percentage: Progress from 0-100
            context_usage: Current context token usage
            artifacts_created: List of artifact dicts with {type, path, lines, timestamp}
            metadata: Additional metadata to store with status update

        Returns:
            Dict with success status and updated execution information
        """
        try:
            # Validate progress percentage
            if progress_percentage is not None:
                if progress_percentage < 0 or progress_percentage > 100:
                    return {
                        "success": False,
                        "error": "progress_percentage must be between 0 and 100",
                        "agent_id": agent_id,
                    }

            # Update execution status using agent_id
            async with db_manager.get_session_async() as session:
                # Get execution by agent_id
                result = await session.execute(
                    select(AgentExecution).where(
                        and_(
                            AgentExecution.agent_id == agent_id,
                            AgentExecution.tenant_key == tenant_key
                        )
                    )
                )
                execution = result.scalar_one_or_none()

                if not execution:
                    return {
                        "success": False,
                        "error": f"Execution {agent_id} not found for tenant {tenant_key}",
                        "agent_id": agent_id,
                    }

                # Update execution fields
                if status:
                    execution.status = status

                if current_task is not None:
                    execution.current_task = current_task

                if progress_percentage is not None:
                    execution.progress = progress_percentage
                    execution.last_progress_at = datetime.now(timezone.utc)

                if context_usage is not None:
                    execution.context_used = context_usage

                # Handle completion
                if status == "complete":
                    execution.completed_at = datetime.now(timezone.utc)
                    execution.progress = 100

                # Handle failure
                if status == "failed":
                    execution.completed_at = datetime.now(timezone.utc)
                    if metadata and "error" in metadata:
                        execution.failure_reason = metadata.get("error", "")[:50]  # Truncate to 50 chars

                await session.commit()
                await session.refresh(execution)

                logger.info(
                    f"Status updated for agent {agent_id}: {status} "
                    f"(progress: {progress_percentage}%, task: {current_task})"
                )

                # TODO: Trigger WebSocket event for status update
                # This will be implemented in the next phase
                # await websocket_manager.broadcast_agent_update(...)

                return {
                    "success": True,
                    "agent_id": agent_id,
                    "status": execution.status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "progress_percentage": execution.progress,
                    "current_task": execution.current_task,
                }

        except ValueError as ve:
            # Handle invalid status transitions
            logger.error(f"Invalid status transition for agent {agent_id}: {ve}")
            return {
                "success": False,
                "error": str(ve),
                "agent_id": agent_id,
            }
        except Exception as e:
            logger.exception(f"Failed to report status for agent {agent_id}")
            return {
                "success": False,
                "error": str(e),
                "agent_id": agent_id,
            }

    logger.info(
        "Agent communication tools registered (check_orchestrator_messages, report_status)"
    )
