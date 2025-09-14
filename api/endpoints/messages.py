"""
Message management API endpoints
"""

from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime

router = APIRouter()

class MessageSend(BaseModel):
    to_agents: List[str] = Field(..., description="Recipient agent names")
    content: str = Field(..., description="Message content")
    project_id: str = Field(..., description="Project ID")
    message_type: str = Field("direct", description="Message type")
    priority: str = Field("normal", description="Message priority")
    from_agent: Optional[str] = Field(None, description="Sender agent name")

class MessageResponse(BaseModel):
    id: str
    from_agent: str
    to_agents: List[str]
    content: str
    message_type: str
    priority: str
    status: str
    created_at: datetime

@router.post("/send", response_model=MessageResponse)
async def send_message(message: MessageSend):
    """Send a message to agents"""
    from api.app import state
    
    try:
        result = await state.api_state.tool_accessor.send_message(
            to_agents=message.to_agents,
            content=message.content,
            project_id=message.project_id,
            message_type=message.message_type,
            priority=message.priority,
            from_agent=message.from_agent
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to send message"))
        
        response = MessageResponse(
            id=result["message_id"],
            from_agent=message.from_agent or "orchestrator",
            to_agents=message.to_agents,
            content=message.content,
            message_type=message.message_type,
            priority=message.priority,
            status="pending",
            created_at=datetime.utcnow()
        )
        
        # Broadcast new message
        if state.api_state.websocket_manager:
            await state.api_state.websocket_manager.broadcast_message_update(
                message_id=result["message_id"],
                project_id=message.project_id,
                update_type="new",
                message_data={
                    "from_agent": message.from_agent or "orchestrator",
                    "to_agents": message.to_agents,
                    "content": message.content,
                    "priority": message.priority,
                    "status": "pending"
                }
            )
        
        return response
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{agent_name}", response_model=List[MessageResponse])
async def get_messages(
    agent_name: str,
    project_id: Optional[str] = Query(None, description="Project ID filter")
):
    """Get pending messages for an agent"""
    from api.app import state
    
    try:
        result = await state.api_state.tool_accessor.get_messages(
            agent_name=agent_name,
            project_id=project_id
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to get messages"))
        
        messages = []
        for msg in result.get("messages", []):
            messages.append(MessageResponse(
                id=msg["id"],
                from_agent=msg.get("from", "orchestrator"),
                to_agents=[agent_name],
                content=msg["content"],
                message_type=msg.get("type", "direct"),
                priority=msg.get("priority", "normal"),
                status="pending",
                created_at=datetime.fromisoformat(msg["created"])
            ))
        
        return messages
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{message_id}/acknowledge")
async def acknowledge_message(
    message_id: str,
    agent_name: str = Query(..., description="Agent acknowledging the message")
):
    """Acknowledge message receipt"""
    from api.app import state
    
    try:
        result = await state.api_state.tool_accessor.acknowledge_message(
            message_id=message_id,
            agent_name=agent_name
        )
        
        if not result.get("success"):
            raise HTTPException(status_code=400, detail=result.get("error", "Failed to acknowledge message"))
        
        # Broadcast message acknowledgment
        if state.api_state.websocket_manager:
            # Get message details to include project_id
            # For now, we'll broadcast without project_id (could be enhanced)
            await state.api_state.websocket_manager.broadcast_message_update(
                message_id=message_id,
                project_id=result.get("project_id", ""),
                update_type="acknowledged",
                message_data={
                    "acknowledged_by": agent_name,
                    "status": "acknowledged"
                }
            )
        
        return {"success": True, "message": "Message acknowledged"}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{message_id}/complete")
async def complete_message(
    message_id: str,
    agent_name: str = Query(..., description="Agent completing the message"),
    result: str = Query(..., description="Completion result")
):
    """Mark message as completed"""
    from api.app import state
    
    try:
        complete_result = await state.api_state.tool_accessor.complete_message(
            message_id=message_id,
            agent_name=agent_name,
            result=result
        )
        
        if not complete_result.get("success"):
            raise HTTPException(status_code=400, detail=complete_result.get("error", "Failed to complete message"))
        
        # Broadcast message completion
        if state.api_state.websocket_manager:
            await state.api_state.websocket_manager.broadcast_message_update(
                message_id=message_id,
                project_id=complete_result.get("project_id", ""),
                update_type="completed",
                message_data={
                    "completed_by": agent_name,
                    "result": result,
                    "status": "completed"
                }
            )
        
        return {"success": True, "message": "Message completed", "result": result}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))