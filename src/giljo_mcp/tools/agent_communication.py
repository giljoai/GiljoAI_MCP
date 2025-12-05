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
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional

from fastmcp import FastMCP

from giljo_mcp.agent_message_queue import AgentMessageQueue
from giljo_mcp.agent_job_manager import AgentJobManager
from giljo_mcp.database import DatabaseManager
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


def register_agent_communication_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register agent-orchestrator communication tools with the MCP server"""

    # Initialize managers
    job_manager = AgentJobManager(db_manager)
    comm_queue = AgentMessageQueue(db_manager)  # Using compatibility layer

    @mcp.tool()
    async def check_orchestrator_messages(
        job_id: str,
        tenant_key: str,
        agent_name: Optional[str] = None,
        message_type: Optional[str] = None,
        unread_only: bool = True,
    ) -> dict[str, Any]:
        """
        Check for messages from the orchestrator or other agents.

        This tool supports the polling pattern (30-60 second intervals) for
        real-time agent visualization and communication.

        Args:
            job_id: Agent job ID to check messages for
            tenant_key: Tenant key for multi-tenant isolation
            agent_name: Optional filter by recipient agent name
            message_type: Optional filter by message type (task, info, error, etc.)
            unread_only: Only return unacknowledged messages (default: True)

        Returns:
            Dict with status, message count, and list of messages
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get messages using MessageQueue
                result = await comm_queue.get_messages(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    to_agent=agent_name,
                    message_type=message_type,
                    unread_only=unread_only,
                )

                if result["status"] == "error":
                    logger.error(f"Failed to get messages for job {job_id}: {result['error']}")
                    return result

                messages = result["messages"]

                # Format messages for agent consumption
                formatted_messages = []
                for msg in messages:
                    formatted_messages.append(
                        {
                            "message_id": msg["id"],
                            "from_agent": msg["from_agent"],
                            "to_agent": msg.get("to_agent"),
                            "type": msg["type"],
                            "content": msg["content"],
                            "priority": msg["priority"],
                            "acknowledged": msg.get("acknowledged", False),
                            "timestamp": msg["timestamp"],
                            "metadata": msg.get("metadata", {}),
                        }
                    )

                logger.info(
                    f"Retrieved {len(formatted_messages)} messages for job {job_id} (unread_only={unread_only})"
                )

                return {
                    "success": True,
                    "job_id": job_id,
                    "message_count": len(formatted_messages),
                    "messages": formatted_messages,
                    "has_unread": any(not msg["acknowledged"] for msg in formatted_messages),
                }

        except Exception as e:
            logger.exception(f"Failed to check orchestrator messages for job {job_id}")
            return {"success": False, "error": str(e), "job_id": job_id}

    @mcp.tool()
    async def acknowledge_message(
        job_id: str,
        tenant_key: str,
        message_id: str,
        agent_id: str,
        response_data: Optional[dict] = None,
    ) -> dict[str, Any]:
        """
        Acknowledge receipt of a message and optionally provide a response.

        This signals to the orchestrator/sender that the message was received
        and understood. The acknowledgment triggers WebSocket events for real-time
        visualization updates.

        Args:
            job_id: Agent job ID containing the message
            tenant_key: Tenant key for multi-tenant isolation
            message_id: ID of the message to acknowledge
            agent_id: ID of the agent acknowledging the message
            response_data: Optional dict with response information

        Returns:
            Dict with success status and acknowledgment details
        """
        try:
            async with db_manager.get_session_async() as session:
                # Acknowledge message using MessageQueue
                result = comm_queue.acknowledge_message(
                    session=session,
                    job_id=job_id,
                    tenant_key=tenant_key,
                    message_id=message_id,
                    agent_id=agent_id,
                )

                if result["status"] == "error":
                    logger.error(f"Failed to acknowledge message {message_id}: {result['error']}")
                    return {
                        "success": False,
                        "error": result["error"],
                        "message_id": message_id,
                    }

                logger.info(f"Message {message_id} acknowledged by agent {agent_id}")

                # Prepare response
                response = {
                    "success": True,
                    "message_id": message_id,
                    "agent_id": agent_id,
                    "acknowledged_at": datetime.now(timezone.utc).isoformat(),
                }

                if response_data:
                    response["response_data"] = response_data

                # TODO: Trigger WebSocket event for acknowledgment
                # This will be implemented in the next phase
                # await websocket_manager.broadcast_message_acknowledged(...)

                return response

        except Exception as e:
            logger.exception(f"Failed to acknowledge message {message_id}")
            return {
                "success": False,
                "error": str(e),
                "message_id": message_id,
            }

    @mcp.tool()
    async def report_status(
        job_id: str,
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

        Args:
            job_id: Agent job ID to update
            tenant_key: Tenant key for multi-tenant isolation
            status: Current status (pending, active, completed, failed)
            current_task: Description of current task being worked on
            progress_percentage: Progress from 0-100
            context_usage: Current context token usage
            artifacts_created: List of artifact dicts with {type, path, lines, timestamp}
            metadata: Additional metadata to store with status update

        Returns:
            Dict with success status and updated job information
        """
        try:
            # Build status update metadata
            update_metadata = metadata or {}

            # Add status details to metadata
            status_details = {}

            if current_task:
                status_details["current_task"] = current_task

            if progress_percentage is not None:
                # Validate progress percentage
                if progress_percentage < 0 or progress_percentage > 100:
                    return {
                        "success": False,
                        "error": "progress_percentage must be between 0 and 100",
                        "job_id": job_id,
                    }
                status_details["progress_percentage"] = progress_percentage

            if context_usage is not None:
                status_details["context_usage"] = context_usage

            if artifacts_created:
                status_details["artifacts_created"] = artifacts_created

            # Combine status details with metadata
            if status_details:
                update_metadata.update(status_details)

            # Create status message
            if current_task:
                update_metadata["message"] = current_task

            # Update job status using AgentJobManager
            async with db_manager.get_session_async() as session:
                # Get current job to check status transitions
                job = await session.run_sync(
                    lambda sync_session: job_manager.get_job(
                        tenant_key=tenant_key,
                        job_id=job_id,
                    )
                )

                if not job:
                    return {
                        "success": False,
                        "error": f"Job {job_id} not found for tenant {tenant_key}",
                        "job_id": job_id,
                    }

                # Update job status based on the status parameter
                if status == "completed":
                    # Complete the job
                    updated_job = await session.run_sync(
                        lambda sync_session: job_manager.complete_job(
                            tenant_key=tenant_key,
                            job_id=job_id,
                            result=update_metadata,
                        )
                    )
                elif status == "failed":
                    # Fail the job
                    updated_job = await session.run_sync(
                        lambda sync_session: job_manager.fail_job(
                            tenant_key=tenant_key,
                            job_id=job_id,
                            error=update_metadata,
                        )
                    )
                else:
                    # Regular status update
                    updated_job = await session.run_sync(
                        lambda sync_session: job_manager.update_job_status(
                            tenant_key=tenant_key,
                            job_id=job_id,
                            status=status,
                            metadata=update_metadata,
                        )
                    )

                logger.info(
                    f"Status updated for job {job_id}: {status} "
                    f"(progress: {progress_percentage}%, task: {current_task})"
                )

                # TODO: Trigger WebSocket event for status update
                # This will be implemented in the next phase
                # await websocket_manager.broadcast_agent_update(...)

                return {
                    "success": True,
                    "job_id": job_id,
                    "status": updated_job.status,
                    "updated_at": datetime.now(timezone.utc).isoformat(),
                    "progress_percentage": progress_percentage,
                    "current_task": current_task,
                }

        except ValueError as ve:
            # Handle invalid status transitions
            logger.error(f"Invalid status transition for job {job_id}: {ve}")
            return {
                "success": False,
                "error": str(ve),
                "job_id": job_id,
            }
        except Exception as e:
            logger.exception(f"Failed to report status for job {job_id}")
            return {
                "success": False,
                "error": str(e),
                "job_id": job_id,
            }

    logger.info(
        "Agent communication tools registered (check_orchestrator_messages, acknowledge_message, report_status)"
    )
