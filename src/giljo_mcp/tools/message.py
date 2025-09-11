"""
Message Communication Tools for GiljoAI MCP
Handles inter-agent messaging: send, get, acknowledge, broadcast
"""

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from uuid import uuid4
import json

from fastmcp import FastMCP
from sqlalchemy import select, update, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import DatabaseManager
from ..tenant import TenantManager, current_tenant
from ..models import Project, Agent, Message
from ..queue import MessageQueue

logger = logging.getLogger(__name__)


def register_message_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register message communication tools with the MCP server"""
    
    # Initialize the MessageQueue system
    message_queue = MessageQueue(db_manager, tenant_manager)
    
    @mcp.tool()
    async def send_message(
        to_agents: List[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
        from_agent: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Send message to one or more agents
        
        Args:
            to_agents: List of recipient agent names
            content: Message content
            project_id: Project ID
            message_type: Type of message (direct, broadcast, etc.)
            priority: Message priority (low, normal, high, critical)
            from_agent: Sender agent name (optional - defaults to 'orchestrator' if not specified)
            
        Returns:
            Message sending confirmation
        """
        try:
            async with db_manager.get_session() as session:
                # Verify project exists
                project_query = select(Project).where(Project.id == project_id)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()
                
                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found"
                    }
                
                # Default from_agent to orchestrator if not specified
                if not from_agent:
                    from_agent = "orchestrator"
                
                # Get sender agent if specified
                from_agent_id = None
                if from_agent and from_agent != "system":
                    sender_query = select(Agent).where(
                        and_(
                            Agent.project_id == project_id,
                            Agent.name == from_agent
                        )
                    )
                    sender_result = await session.execute(sender_query)
                    sender = sender_result.scalar_one_or_none()
                    if sender:
                        from_agent_id = str(sender.id)
                
                # Verify all recipient agents exist
                verified_recipients = []
                failed_recipients = []
                
                for agent_name in to_agents:
                    agent_query = select(Agent).where(
                        and_(
                            Agent.project_id == project_id,
                            Agent.name == agent_name
                        )
                    )
                    agent_result = await session.execute(agent_query)
                    recipient = agent_result.scalar_one_or_none()
                    
                    if recipient:
                        verified_recipients.append(agent_name)
                    else:
                        failed_recipients.append(agent_name)
                        logger.warning(f"Recipient agent '{agent_name}' not found")
                
                if not verified_recipients:
                    return {
                        "success": False,
                        "error": "No valid recipients found",
                        "failed_recipients": failed_recipients
                    }
                
                # Get tenant key
                tenant_key = project.tenant_key
                
                # Create single message for all recipients
                message = Message(
                    tenant_key=tenant_key,
                    project_id=project_id,
                    from_agent_id=from_agent_id,
                    to_agents=verified_recipients,
                    message_type=message_type,
                    content=content,
                    priority=priority,
                    status="pending",
                    acknowledged_by=[],
                    completed_by=[]
                )
                
                # Use the MessageQueue to enqueue the message
                message_id = await message_queue.enqueue(message)
                
                logger.info(f"Sent message from '{from_agent}' to {verified_recipients}")
                
                return {
                    "success": True,
                    "message_id": message_id,
                    "recipients": verified_recipients,
                    "failed_recipients": failed_recipients,
                    "from": from_agent,
                    "to": verified_recipients
                }
                
        except Exception as e:
            logger.error(f"Failed to send messages: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def get_messages(
        agent_name: str,
        project_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve pending messages for an agent
        
        Args:
            agent_name: Name of the agent to get messages for
            project_id: Optional project ID (uses current if not specified)
            
        Returns:
            List of pending messages for the agent
        """
        try:
            async with db_manager.get_session() as session:
                # Get project ID if not provided
                if not project_id:
                    tenant_key = tenant_manager.get_current_tenant()
                    if not tenant_key:
                        return {
                            "success": False,
                            "error": "No active project. Use switch_project first."
                        }
                    
                    project_query = select(Project).where(Project.tenant_key == tenant_key)
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()
                    
                    if not project:
                        return {
                            "success": False,
                            "error": "Project not found"
                        }
                    project_id = project.id
                
                # Use the MessageQueue to dequeue messages for the agent
                messages = await message_queue.dequeue(agent_name, batch_size=10)
                
                message_list = []
                for msg in messages:
                    # Auto-acknowledge the message
                    if msg.status == "pending":
                        msg.status = "acknowledged"
                        msg.acknowledged_at = datetime.utcnow()
                        
                        # Add to acknowledged_by array if not already there
                        if not msg.acknowledged_by:
                            msg.acknowledged_by = []
                        
                        # Check if agent hasn't already acknowledged
                        already_acknowledged = any(
                            ack.get("agent_name") == agent_name 
                            for ack in msg.acknowledged_by
                        )
                        
                        if not already_acknowledged:
                            msg.acknowledged_by.append({
                                "agent_name": agent_name,
                                "timestamp": datetime.utcnow().isoformat()
                            })
                    
                    # Get sender name
                    from_agent_name = "system"
                    if msg.from_agent_id:
                        sender_query = select(Agent).where(Agent.id == msg.from_agent_id)
                        sender_result = await session.execute(sender_query)
                        sender = sender_result.scalar_one_or_none()
                        if sender:
                            from_agent_name = sender.name
                    
                    message_list.append({
                        "id": str(msg.id),
                        "from": from_agent_name,
                        "type": msg.message_type,
                        "subject": msg.subject,
                        "content": msg.content,
                        "priority": msg.priority,
                        "created": msg.created_at.isoformat() if msg.created_at else None
                    })
                
                # Commit auto-acknowledgments
                await session.commit()
                
                logger.info(f"Retrieved {len(message_list)} messages for agent '{agent_name}'")
                
                return {
                    "success": True,
                    "agent": agent_name,
                    "count": len(message_list),
                    "messages": message_list
                }
                
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def acknowledge_message(
        message_id: str,
        agent_name: str
    ) -> Dict[str, Any]:
        """
        Mark message as received by agent
        
        Args:
            message_id: UUID of the message to acknowledge
            agent_name: Name of the agent acknowledging the message
            
        Returns:
            Acknowledgment confirmation
        """
        try:
            async with db_manager.get_session() as session:
                # Find the message
                message_query = select(Message).where(Message.id == message_id)
                message_result = await session.execute(message_query)
                message = message_result.scalar_one_or_none()
                
                if not message:
                    return {
                        "success": False,
                        "error": f"Message {message_id} not found"
                    }
                
                # Verify the agent is in the recipients
                if agent_name not in (message.to_agents or []):
                    return {
                        "success": False,
                        "error": f"Message is not for agent '{agent_name}'"
                    }
                
                # Update message status
                if message.status == "pending":
                    message.status = "acknowledged"
                    message.acknowledged_at = datetime.utcnow()
                    
                    # Update acknowledged_by array
                    if not message.acknowledged_by:
                        message.acknowledged_by = []
                    
                    # Check if agent hasn't already acknowledged
                    already_acknowledged = any(
                        ack.get("agent_name") == agent_name 
                        for ack in message.acknowledged_by
                    )
                    
                    if not already_acknowledged:
                        message.acknowledged_by.append({
                            "agent_name": agent_name,
                            "timestamp": datetime.utcnow().isoformat()
                        })
                    
                    await session.commit()
                    
                    logger.info(f"Message {message_id} acknowledged by agent '{agent_name}'")
                    
                    return {
                        "success": True,
                        "message_id": str(message.id),
                        "agent": agent_name,
                        "status": "acknowledged"
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Message already has status: {message.status}"
                    }
                
        except Exception as e:
            logger.error(f"Failed to acknowledge message: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def complete_message(
        message_id: str,
        agent_name: str,
        result: str,
        completion_notes: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Mark message as completed with result
        
        Args:
            message_id: UUID of the message to complete
            agent_name: Name of the agent completing the message
            result: Result or response to the message
            completion_notes: Optional notes about why/how the message was completed
            
        Returns:
            Completion confirmation
        """
        try:
            async with db_manager.get_session() as session:
                # Find the message
                message_query = select(Message).where(Message.id == message_id)
                message_result = await session.execute(message_query)
                message = message_result.scalar_one_or_none()
                
                if not message:
                    return {
                        "success": False,
                        "error": f"Message {message_id} not found"
                    }
                
                # Verify the agent is in the recipients
                if agent_name not in (message.to_agents or []):
                    return {
                        "success": False,
                        "error": f"Message is not for agent '{agent_name}'"
                    }
                
                # Update message status
                if message.status in ["pending", "acknowledged"]:
                    message.status = "completed"
                    message.completed_at = datetime.utcnow()
                    
                    # Store result in meta_data
                    if not message.meta_data:
                        message.meta_data = {}
                    message.meta_data["result"] = result
                    
                    # Update completed_by array
                    if not message.completed_by:
                        message.completed_by = []
                    
                    # Check if agent hasn't already marked as complete
                    already_completed = any(
                        comp.get("agent_name") == agent_name 
                        for comp in message.completed_by
                    )
                    
                    if not already_completed:
                        completion_entry = {
                            "agent_name": agent_name,
                            "timestamp": datetime.utcnow().isoformat()
                        }
                        if completion_notes:
                            completion_entry["notes"] = completion_notes
                        message.completed_by.append(completion_entry)
                    
                    await session.commit()
                    
                    logger.info(f"Message {message_id} completed by agent '{agent_name}'")
                    
                    return {
                        "success": True,
                        "message_id": str(message.id),
                        "agent": agent_name,
                        "status": "completed",
                        "result_stored": True
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Message already has status: {message.status}"
                    }
                
        except Exception as e:
            logger.error(f"Failed to complete message: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def broadcast(
        content: str,
        project_id: str,
        priority: str = "normal"
    ) -> Dict[str, Any]:
        """
        Broadcast message to all agents in project
        
        Args:
            content: Message content to broadcast
            project_id: UUID of the project
            priority: Message priority (low, normal, high, critical)
            
        Returns:
            Broadcast confirmation
        """
        try:
            async with db_manager.get_session() as session:
                # Get all agents in the project
                agent_query = select(Agent).where(
                    and_(
                        Agent.project_id == project_id,
                        Agent.status != "decommissioned"
                    )
                )
                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()
                
                if not agents:
                    return {
                        "success": False,
                        "error": "No active agents in project"
                    }
                
                message_ids = []
                
                # Get tenant key
                project_query = select(Project).where(Project.id == project_id)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()
                
                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found"
                    }
                
                tenant_key = project.tenant_key
                agent_names = [agent.name for agent in agents]
                
                # Create single broadcast message for all agents
                message = Message(
                    tenant_key=tenant_key,
                    project_id=project_id,
                    from_agent_id=None,  # System broadcast
                    to_agents=agent_names,
                    message_type="broadcast",
                    content=content,
                    priority=priority,
                    status="pending",
                    acknowledged_by=[],
                    completed_by=[]
                )
                session.add(message)
                await session.flush()
                message_id = str(message.id)
                
                await session.commit()
                
                logger.info(f"Broadcast sent to {len(agents)} agents in project {project_id}")
                
                return {
                    "success": True,
                    "broadcast_to": len(agents),
                    "agents": agent_names,
                    "message_id": message_id,
                    "priority": priority
                }
                
        except Exception as e:
            logger.error(f"Failed to broadcast message: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    @mcp.tool()
    async def log_task(
        content: str,
        category: Optional[str] = None,
        priority: str = "medium"
    ) -> Dict[str, Any]:
        """
        Quick task capture for logging work items
        
        Args:
            content: Task description
            category: Optional task category
            priority: Task priority (low, medium, high)
            
        Returns:
            Task logging confirmation
        """
        try:
            # Get current tenant
            tenant_key = tenant_manager.get_current_tenant()
            if not tenant_key:
                return {
                    "success": False,
                    "error": "No active project. Use switch_project first."
                }
            
            async with db_manager.get_session() as session:
                # Find project by tenant key
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()
                
                if not project:
                    return {
                        "success": False,
                        "error": "Project not found"
                    }
                
                # Create a system message for task logging
                task_message = Message(
                    tenant_key=project.tenant_key,
                    project_id=project.id,
                    from_agent_id=None,  # System message
                    to_agents=["orchestrator"],
                    message_type="task_log",
                    subject=f"Task: {category}" if category else "Task Log",
                    content=content,
                    priority=priority,
                    status="pending",
                    acknowledged_by=[],
                    completed_by=[]
                )
                session.add(task_message)
                await session.commit()
                
                logger.info(f"Logged task in project {project.name}")
                
                return {
                    "success": True,
                    "task_id": str(task_message.id),
                    "category": category,
                    "priority": priority,
                    "logged_at": task_message.created_at.isoformat()
                }
                
        except Exception as e:
            logger.error(f"Failed to log task: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    logger.info("Message communication tools registered")