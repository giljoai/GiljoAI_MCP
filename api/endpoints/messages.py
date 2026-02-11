"""
Message management API endpoints
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from api.endpoints.dependencies import get_message_service
from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.services.message_service import MessageService


router = APIRouter()


class MessageSend(BaseModel):
    to_agents: list[str] = Field(..., description="Recipient agent names")
    content: str = Field(..., description="Message content")
    project_id: str = Field(..., description="Project ID")
    message_type: str = Field("direct", description="Message type")
    priority: str = Field("normal", description="Message priority")
    from_agent: Optional[str] = Field(None, description="Sender agent name")


class MessageResponse(BaseModel):
    id: str
    from_agent: str = Field(..., serialization_alias="from")
    to_agents: list[str]
    to_agent: Optional[str] = None  # Single recipient for frontend compatibility
    content: str
    message_type: str = Field(..., serialization_alias="type")
    priority: str
    status: str
    created_at: datetime

    model_config = {"populate_by_name": True}


class MessageSendRequest(BaseModel):
    """Request schema for unified UI messaging endpoint (Handover 0299)."""

    project_id: str = Field(..., description="Project ID")
    to_agents: list[str] = Field(..., description="Recipient agent IDs. Use ['all'] for broadcast.")
    content: str = Field(..., description="Message content")
    message_type: str = Field("direct", description="Message type: 'direct' or 'broadcast'")
    priority: str = Field("normal", description="Message priority: 'low', 'normal', 'high'")


@router.post("/", response_model=MessageResponse)
async def send_message(
    message: MessageSend,
    current_user: User = Depends(get_current_active_user),
    message_service: MessageService = Depends(get_message_service),
):
    """Send a message to agents"""
    from api.app import state

    # Service raises exceptions on error
    result = await message_service.send_message(
        to_agents=message.to_agents,
        content=message.content,
        project_id=message.project_id,
        message_type=message.message_type,
        priority=message.priority,
        from_agent=message.from_agent,
        tenant_key=current_user.tenant_key,  # Handover 0733: Enforce tenant isolation
    )

    # Handover 0730b: Service returns direct response (no "data" wrapper)
    message_id = result.get("message_id")

    response = MessageResponse(
        id=message_id,
        from_agent=message.from_agent or "orchestrator",
        to_agents=message.to_agents,
        content=message.content,
        message_type=message.message_type,
        priority=message.priority,
        status="pending",
        created_at=datetime.now(timezone.utc),
    )

    # Broadcast new message
    if state.websocket_manager:
        await state.websocket_manager.broadcast_message_update(
            message_id=message_id,
            project_id=message.project_id,
            update_type="new",
            message_data={
                "from_agent": message.from_agent or "orchestrator",
                "to_agents": message.to_agents,
                "content": message.content,
                "priority": message.priority,
                "status": "pending",
            },
        )

    return response


@router.post("/send", response_model=dict)
async def send_message_from_ui(
    payload: MessageSendRequest,
    current_user: User = Depends(get_current_active_user),
    message_service: MessageService = Depends(get_message_service),
):
    """
    Unified endpoint for UI messaging (broadcast and direct) - Handover 0299.

    Uses the same MessageService that MCP tools use, providing a single
    entry point for both broadcast (to_agents=['all']) and direct messages.

    Returns:
        dict with success, message_id, and to_agents fields
    """
    # Service raises exceptions on error
    result = await message_service.send_message(
        to_agents=payload.to_agents,
        content=payload.content,
        project_id=payload.project_id,
        message_type=payload.message_type,
        priority=payload.priority,
        from_agent="user",  # UI messages always come from "user"
        tenant_key=current_user.tenant_key,  # Handover 0405: Required for broadcast fan-out
    )

    # Handover 0730b: Service returns direct response (no "data" wrapper)
    return {
        "success": True,
        "message_id": result.get("message_id"),
        "to_agents": result.get("to_agents", payload.to_agents),
    }


@router.get("/", response_model=list[MessageResponse])
async def list_messages(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name (to or from)"),
    status: Optional[str] = Query(None, description="Filter by status"),
    current_user: User = Depends(get_current_active_user),
    message_service: MessageService = Depends(get_message_service),
):
    """List all messages with optional filters

    Messages are retrieved from MessageService which handles both
    Message table and agent_executions.messages JSONB.
    """
    from api.app import state

    # Check if database is available (not in setup mode)
    if not state.db_manager:
        # In setup mode, return empty list
        return []

    # Use MessageService to list messages (raises exceptions on error)
    messages_data = await message_service.list_messages(
        project_id=project_id,
        status=status,
        tenant_key=current_user.tenant_key,
    )

    messages = []

    for msg in messages_data.get("messages", []):
        # Apply agent_name filter if provided
        if agent_name and msg.get("from_agent") != agent_name and msg.get("to_agent") != agent_name:
            continue

        # Parse created_at
        created_at_str = msg.get("created_at")
        if created_at_str:
            try:
                created_at = datetime.fromisoformat(created_at_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = datetime.now(timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)

        to_agent_val = msg.get("to_agent")
        messages.append(
            MessageResponse(
                id=msg.get("id", str(uuid4())),
                from_agent=msg.get("from_agent", "developer"),
                to_agents=[to_agent_val] if to_agent_val else [],
                to_agent=to_agent_val,
                content=msg.get("content", ""),
                message_type=msg.get("type", "direct"),
                priority=msg.get("priority", "normal"),
                status=msg.get("status", "pending"),
                created_at=created_at,
            )
        )

    # Sort by timestamp (newest first)
    messages.sort(key=lambda m: m.created_at, reverse=True)
    return messages


@router.get("/agent/{agent_name}", response_model=list[MessageResponse])
async def get_messages(
    agent_name: str,
    project_id: Optional[str] = Query(None, description="Project ID filter"),
    current_user: User = Depends(get_current_active_user),
    message_service: MessageService = Depends(get_message_service),
):
    """Get pending messages for an agent"""
    # Service raises exceptions on error
    result = await message_service.get_messages(agent_name=agent_name, project_id=project_id, status="pending")

    messages = []
    for msg in result.get("messages", []):
        # Parse created timestamp
        created_str = msg.get("created")
        if created_str:
            try:
                created_at = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                created_at = datetime.now(timezone.utc)
        else:
            created_at = datetime.now(timezone.utc)

        messages.append(
            MessageResponse(
                id=msg["id"],
                from_agent=msg.get("from", "orchestrator"),
                to_agents=[agent_name],
                content=msg["content"],
                message_type=msg.get("type", "direct"),
                priority=msg.get("priority", "normal"),
                status="pending",
                created_at=created_at,
            )
        )

    return messages


@router.post("/{message_id}/complete")
async def complete_message(
    message_id: str,
    agent_name: str = Query(..., description="Agent completing the message"),
    result: str = Query(..., description="Completion result"),
    current_user: User = Depends(get_current_active_user),
    message_service: MessageService = Depends(get_message_service),
):
    """Mark message as completed"""
    from api.app import state

    # Service raises exceptions on error
    await message_service.complete_message(message_id=message_id, agent_name=agent_name, result=result)

    # Broadcast message completion
    if state.websocket_manager:
        await state.websocket_manager.broadcast_message_update(
            message_id=message_id,
            project_id="",  # Could be enhanced to fetch from message
            update_type="completed",
            message_data={"completed_by": agent_name, "result": result, "status": "completed"},
        )

    return {"message": "Message completed", "result": result}


class BroadcastMessage(BaseModel):
    project_id: str = Field(..., description="Project ID to broadcast to")
    content: str = Field(..., description="Broadcast message content")
    priority: str = Field("normal", description="Message priority")
    from_agent: Optional[str] = Field(None, description="Sender name (defaults to 'user')")


@router.post("/broadcast", response_model=dict)
async def broadcast_message(
    broadcast: BroadcastMessage,
    current_user: User = Depends(get_current_active_user),
    message_service: MessageService = Depends(get_message_service),
):
    """Broadcast message to all active agents in a project"""
    from api.app import state

    # Check if database is available
    if not state.db_manager:
        raise HTTPException(status_code=503, detail="Database not available")

    # Use MessageService to broadcast (it handles finding active agents, raises exceptions on error)
    message_result = await message_service.broadcast(
        content=broadcast.content,
        project_id=broadcast.project_id,
        priority=broadcast.priority,
        from_agent=broadcast.from_agent or "user",
    )

    # Handover 0730b: Service returns direct response (no "data" wrapper)
    message_id = message_result.get("message_id")
    agent_names = message_result.get("to_agents", [])

    # Broadcast WebSocket notification
    if state.websocket_manager:
        await state.websocket_manager.broadcast_message_update(
            message_id=message_id,
            project_id=broadcast.project_id,
            update_type="broadcast",
            message_data={
                "from_agent": broadcast.from_agent or "user",
                "to_agents": agent_names,
                "content": broadcast.content,
                "priority": broadcast.priority,
                "status": "pending",
                "recipient_count": len(agent_names),
            },
        )

    return {
        "success": True,
        "message_id": message_id,
        "recipient_count": len(agent_names),
        "recipients": agent_names,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
