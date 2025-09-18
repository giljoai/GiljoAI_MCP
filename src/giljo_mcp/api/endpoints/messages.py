"""
Message communication REST API endpoints
Exposes message MCP tools as HTTP endpoints
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from src.giljo_mcp.database import DatabaseManager


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/messages", tags=["messages"])

# Request/Response models
class SendMessageRequest(BaseModel):
    to_agents: List[str]
    content: str
    project_id: str
    message_type: str = "direct"
    priority: str = "normal"
    from_agent: Optional[str] = None

class BroadcastRequest(BaseModel):
    content: str
    project_id: str
    priority: str = "normal"

class CompleteMessageRequest(BaseModel):
    agent_name: str
    result: str
    completion_notes: Optional[str] = None

class LogTaskRequest(BaseModel):
    content: str
    category: Optional[str] = None
    priority: str = "medium"

class MessageResponse(BaseModel):
    success: bool
    message_id: Optional[str] = None
    recipients: Optional[List[str]] = None
    status: Optional[str] = None
    error: Optional[str] = None


@router.post("/send", response_model=MessageResponse)
async def send_message(request: SendMessageRequest):
    """Send a message to one or more agents"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Message, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Verify project exists
            project_query = select(Project).where(Project.id == request.project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Get sender agent if specified
            from_agent_id = None
            if request.from_agent:
                sender_query = select(Agent).where(
                    Agent.project_id == request.project_id,
                    Agent.name == request.from_agent
                )
                sender_result = await session.execute(sender_query)
                sender_agent = sender_result.scalar_one_or_none()

                if not sender_agent:
                    raise HTTPException(status_code=404, detail=f"Sender agent '{request.from_agent}' not found")
                from_agent_id = sender_agent.id

            # Verify recipient agents exist
            for agent_name in request.to_agents:
                agent_query = select(Agent).where(
                    Agent.project_id == request.project_id,
                    Agent.name == agent_name
                )
                agent_result = await session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    raise HTTPException(status_code=404, detail=f"Recipient agent '{agent_name}' not found")

            # Create message
            message = Message(
                tenant_key=project.tenant_key,
                project_id=request.project_id,
                from_agent_id=from_agent_id,
                to_agents=request.to_agents,
                message_type=request.message_type,
                content=request.content,
                priority=request.priority,
                status="pending",
                created_at=datetime.now(timezone.utc),
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(message)
            await session.commit()

            return MessageResponse(
                success=True,
                message_id=str(message.id),
                recipients=request.to_agents,
                status="sent"
            )

    except Exception as e:
        logger.exception(f"Failed to send message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/agent/{agent_name}")
async def get_messages_for_agent(
    agent_name: str,
    project_id: Optional[str] = Query(None, description="Project ID for context"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of messages to return")
):
    """Get pending messages for an agent"""
    try:
        from sqlalchemy import select

        from src.giljo_mcp.models import Message

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Build query for pending messages for this agent
            query = select(Message).where(
                Message.to_agents.contains([agent_name]),
                Message.status.in_(["pending", "acknowledged"])
            )
            
            if project_id:
                query = query.where(Message.project_id == project_id)
                
            query = query.order_by(Message.created_at.desc()).limit(limit)
            
            result = await session.execute(query)
            messages = result.scalars().all()

            return {
                "success": True,
                "agent_name": agent_name,
                "message_count": len(messages),
                "messages": [
                    {
                        "id": str(msg.id),
                        "from_agent": msg.from_agent_id,
                        "content": msg.content,
                        "priority": msg.priority,
                        "created_at": msg.created_at.isoformat(),
                        "status": msg.status,
                        "message_type": msg.message_type
                    }
                    for msg in messages
                ]
            }

    except Exception as e:
        logger.exception(f"Failed to get messages for agent: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/broadcast")
async def broadcast_message(request: BroadcastRequest):
    """Broadcast a message to all agents in a project"""
    try:
        from datetime import datetime, timezone

        from sqlalchemy import select

        from src.giljo_mcp.models import Agent, Message, Project

        db_manager = DatabaseManager(is_async=True)
        await db_manager.create_tables_async()

        async with db_manager.get_session_async() as session:
            # Verify project exists
            project_query = select(Project).where(Project.id == request.project_id)
            project_result = await session.execute(project_query)
            project = project_result.scalar_one_or_none()

            if not project:
                raise HTTPException(status_code=404, detail="Project not found")

            # Get all active agents in the project
            agents_query = select(Agent).where(
                Agent.project_id == request.project_id,
                Agent.status.in_(["active", "working", "idle"])
            )
            agents_result = await session.execute(agents_query)
            agents_list = agents_result.scalars().all()

            if not agents_list:
                raise HTTPException(status_code=400, detail="No active agents found in project")

            agent_names = [agent.name for agent in agents_list]

            # Create broadcast message
            broadcast_message = Message(
                tenant_key=project.tenant_key,
                project_id=request.project_id,
                from_agent_id=None,  # System broadcast
                to_agents=agent_names,
                message_type="broadcast",
                subject="Project Broadcast",
                content=request.content,
                priority=request.priority,
                status="pending",
                created_at=datetime.now(timezone.utc),
                acknowledged_by=[],
                completed_by=[]
            )
            session.add(broadcast_message)
            await session.commit()

            return {
                "success": True,
                "broadcast_to": "all_active_agents",
                "agents": agent_names,
                "message_id": str(broadcast_message.id),
                "priority": request.priority,
                "agent_count": len(agent_names)
            }

    except Exception as e:
        logger.exception(f"Failed to broadcast message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/log-task")
async def log_task(request: LogTaskRequest):
    """Log a quick task for capture"""
    try:
        from datetime import datetime, timezone

        from src.giljo_mcp.models import Task
        from src.giljo_mcp.tenant import TenantManager

        db_manager = DatabaseManager(is_async=True)
        tenant_manager = TenantManager()
        await db_manager.create_tables_async()

        # Get current tenant context
        current_tenant = tenant_manager.get_current_tenant()
        if not current_tenant:
            raise HTTPException(status_code=400, detail="No active tenant context. Please select a project first.")

        async with db_manager.get_session_async() as session:
            # Create quick task capture
            task = Task(
                tenant_key=current_tenant,
                title=request.content[:255],  # Truncate to fit title field
                description=request.content,
                category=request.category,
                priority=request.priority,
                status="pending",
                created_at=datetime.now(timezone.utc),
                meta_data={
                    "source": "quick_capture",
                    "logged_via": "messages_api"
                }
            )
            session.add(task)
            await session.commit()

            return {
                "success": True,
                "task_id": str(task.id),
                "category": request.category,
                "priority": request.priority,
                "logged_at": task.created_at.isoformat(),
                "title": task.title
            }

    except Exception as e:
        logger.exception(f"Failed to log task: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_messages(
    project_id: Optional[str] = Query(None, description="Filter by project ID"),
    agent_name: Optional[str] = Query(None, description="Filter by agent name"),
    status: Optional[str] = Query(None, description="Filter by message status"),
    priority: Optional[str] = Query(None, description="Filter by priority"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of messages to return"),
    offset: int = Query(0, ge=0, description="Number of messages to skip")
):
    """List messages with optional filtering"""
    try:
        # This would need a custom implementation as there's no direct list_messages tool
        # For now, return empty list with proper structure
        return {
            "success": True,
            "count": 0,
            "messages": [],
            "filters": {
                "project_id": project_id,
                "agent_name": agent_name,
                "status": status,
                "priority": priority
            }
        }

    except Exception as e:
        logger.exception(f"Failed to list messages: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{message_id}")
async def get_message(message_id: str):
    """Get a specific message by ID"""
    try:
        # This would need a custom implementation as there's no direct get_message tool
        # For now, return not found
        raise HTTPException(status_code=404, detail="Message not found")

    except Exception as e:
        logger.exception(f"Failed to get message: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{message_id}")
async def delete_message(message_id: str):
    """Delete a message (soft delete)"""
    try:
        # This would need a custom implementation
        # For now, return not implemented
        raise HTTPException(status_code=501, detail="Message deletion not implemented")

    except Exception as e:
        logger.exception(f"Failed to delete message: {e}")
        raise HTTPException(status_code=500, detail=str(e))
