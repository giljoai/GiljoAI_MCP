"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

import logging
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import select, update

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import Agent, Message, Project, Task
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ToolAccessor:
    """Provides direct access to MCP tool functionality for API"""

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager

    # Project Tools

    async def create_project(self, name: str, mission: str, agents: Optional[list[str]] = None, product_id: Optional[str] = None, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """Create a new project"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Use provided tenant key or generate a new one
                if not tenant_key:
                    tenant_key = f"tk_{uuid4().hex}"

                # Create project
                project = Project(
                    name=name,
                    mission=mission,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status="active",
                    context_budget=150000,
                    context_used=0,
                )

                session.add(project)
                await session.commit()

                project_id = str(project.id)

                # Initialize agents if provided
                if agents:
                    for agent_name in agents:
                        agent = Agent(
                            name=agent_name,
                            project_id=project.id,
                            tenant_key=tenant_key,
                            status="active",
                            role=agent_name,  # Use agent name as default role
                        )
                        session.add(agent)
                    await session.commit()

                logger.info(f"Created project {project_id} with tenant key {tenant_key}")

                return {
                    "success": True,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "name": name,
                    "status": "active",
                }

        except Exception as e:
            logger.exception(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    async def list_projects(self, status: Optional[str] = None) -> dict[str, Any]:
        """List all projects with optional status filter"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                query = select(Project).where(Project.tenant_key == tenant_key)
                if status:
                    query = query.where(Project.status == status)

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    # Get agent count and message count for this project
                    agent_count = 0
                    message_count = 0

                    project_list.append(
                        {
                            "id": str(project.id),
                            "name": project.name,
                            "mission": project.mission,
                            "status": project.status,
                            "tenant_key": project.tenant_key,
                            "product_id": project.product_id,
                            "created_at": project.created_at.isoformat(),
                            "updated_at": (
                                project.updated_at.isoformat() if project.updated_at else project.created_at.isoformat()
                            ),
                            "context_budget": project.context_budget,
                            "context_used": project.context_used,
                            "agent_count": agent_count,
                            "message_count": message_count,
                        }
                    )

                return {"success": True, "projects": project_list}

        except Exception as e:
            logger.exception(f"Failed to list projects: {e}")
            return {"success": False, "error": str(e)}

    async def get_project(self, project_id: str) -> dict[str, Any]:
        """Get a specific project by ID"""
        try:
            async with self.db_manager.get_session_async() as session:
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "status": project.status,
                        "product_id": project.product_id,
                        "tenant_key": project.tenant_key,
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                        "created_at": project.created_at.isoformat() if project.created_at else None,
                        "updated_at": project.updated_at.isoformat() if project.updated_at else None,
                    }
                }

        except Exception as e:
            logger.exception(f"Failed to get project: {e}")
            return {"success": False, "error": str(e)}

    async def switch_project(self, project_id: str) -> dict[str, Any]:
        """Switch to a different project"""
        try:
            async with self.db_manager.get_session_async() as db_session:
                from giljo_mcp.models import Session as SessionModel
                from giljo_mcp.tenant import current_tenant

                # Find project
                query = select(Project).where(Project.id == project_id)
                result = await db_session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": f"Project {project_id} not found"}

                # Set tenant context
                self.tenant_manager.set_current_tenant(project.tenant_key)
                current_tenant.set(project.tenant_key)

                # Create new session if needed
                session_query = select(SessionModel).where(
                    SessionModel.project_id == project.id,
                    SessionModel.status == "active"
                )
                session_result = await db_session.execute(session_query)
                active_session = session_result.scalar_one_or_none()

                if not active_session:
                    active_session = SessionModel(
                        project_id=project.id,
                        started_at=datetime.now(),
                        status="active",
                    )
                    db_session.add(active_session)
                    await db_session.commit()

                logger.info(f"Switched to project '{project.name}' (ID: {project_id})")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": project.name,
                    "mission": project.mission,
                    "tenant_key": project.tenant_key,
                    "session_id": str(active_session.id),
                    "context_usage": f"{project.context_used}/{project.context_budget}",
                }

        except Exception as e:
            logger.exception(f"Failed to switch project: {e}")
            return {"success": False, "error": str(e)}

    async def project_status(self, project_id: Optional[str] = None) -> dict[str, Any]:
        """Get comprehensive project status"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Get project
                query = select(Project)
                if project_id:
                    query = query.where(Project.id == project_id)
                else:
                    query = query.where(Project.status == "active").limit(1)

                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get agents
                agent_result = await session.execute(select(Agent).where(Agent.project_id == project.id))
                agents = agent_result.scalars().all()

                # Get pending messages
                message_result = await session.execute(
                    select(Message).where(Message.project_id == project.id, Message.status == "pending")
                )
                pending_messages = len(message_result.scalars().all())

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "status": project.status,
                        "tenant_key": project.tenant_key,
                        "product_id": project.product_id,
                        "created_at": project.created_at.isoformat(),
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    },
                    "agents": [{"name": agent.name, "status": agent.status, "role": agent.role} for agent in agents],
                    "pending_messages": pending_messages,
                }

        except Exception as e:
            logger.exception(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    async def close_project(self, project_id: str, summary: str) -> dict[str, Any]:
        """Close a completed project with summary"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Update project status
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(
                        status="completed",
                        updated_at=datetime.utcnow(),
                        meta_data={"summary": summary},
                    )
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                await session.commit()

                logger.info(f"Closed project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} closed successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to close project: {e}")
            return {"success": False, "error": str(e)}

    async def update_project_mission(self, project_id: str, mission: str) -> dict[str, Any]:
        """Update the mission field after orchestrator analysis"""
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(mission=mission, updated_at=datetime.utcnow())
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                await session.commit()

                return {"success": True, "message": "Mission updated successfully"}

        except Exception as e:
            logger.exception(f"Failed to update mission: {e}")
            return {"success": False, "error": str(e)}

    # Agent Tools

    async def ensure_agent(self, project_id: str, agent_name: str, mission: Optional[str] = None) -> dict[str, Any]:
        """Ensure an agent exists for work on a project"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                # Get project with tenant filtering
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Check if agent exists
                agent_result = await session.execute(
                    select(Agent).where(
                        Agent.name == agent_name, Agent.project_id == project_id, Agent.tenant_key == tenant_key
                    )
                )
                agent = agent_result.scalar_one_or_none()

                if agent:
                    return {
                        "success": True,
                        "agent": agent_name,
                        "agent_id": str(agent.id),
                        "message": "Agent already exists",
                    }

                # Create agent
                agent = Agent(
                    name=agent_name,
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    status="active",
                    role=mission or "worker",
                )

                session.add(agent)
                await session.commit()

                return {
                    "success": True,
                    "agent": agent_name,
                    "agent_id": str(agent.id),
                    "message": "Agent created successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to ensure agent: {e}")
            return {"success": False, "error": str(e)}

    async def agent_health(self, agent_name: Optional[str] = None) -> dict[str, Any]:
        """Check agent health and context usage"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                if agent_name:
                    result = await session.execute(
                        select(Agent).where(Agent.name == agent_name, Agent.tenant_key == tenant_key)
                    )
                    agents = [result.scalar_one_or_none()]
                else:
                    result = await session.execute(select(Agent).where(Agent.tenant_key == tenant_key))
                    agents = result.scalars().all()

                if not agents or (len(agents) == 1 and not agents[0]):
                    return {"success": False, "error": "No agents found"}

                health_data = []
                for agent in agents:
                    if agent:
                        health_data.append(
                            {
                                "name": agent.name,
                                "status": agent.status,
                                "context_used": agent.context_used or 0,
                                "project_id": str(agent.project_id),
                                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                                "last_active": agent.updated_at.isoformat() if agent.updated_at else None,
                            }
                        )

                return {
                    "success": True,
                    "health": health_data[0] if agent_name else health_data,
                }

        except Exception as e:
            logger.exception(f"Failed to check agent health: {e}")
            return {"success": False, "error": str(e)}

    async def decommission_agent(self, agent_name: str, project_id: str, reason: str = "completed") -> dict[str, Any]:
        """Gracefully end an agent's work"""
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(
                    update(Agent)
                    .where(Agent.name == agent_name, Agent.project_id == project_id)
                    .values(status="decommissioned", meta_data={"reason": reason})
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Agent not found"}

                await session.commit()

                return {
                    "success": True,
                    "message": f"Agent {agent_name} decommissioned",
                }

        except Exception as e:
            logger.exception(f"Failed to decommission agent: {e}")
            return {"success": False, "error": str(e)}

    async def spawn_agent(self, name: str, role: str, mission: str) -> dict[str, Any]:
        """Spawn a new agent (alias for ensure_agent with role parameter)"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active project. Switch project first."}

            async with self.db_manager.get_session_async() as session:
                # Find project by tenant key
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Create agent using ensure_agent
                result = await self.ensure_agent(str(project.id), name, mission)
                if result.get("success"):
                    result["role"] = role
                return result

        except Exception as e:
            logger.exception(f"Failed to spawn agent: {e}")
            return {"success": False, "error": str(e)}

    async def list_agents(self, status: Optional[str] = None) -> dict[str, Any]:
        """List agents in current project"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active project. Switch project first."}

            async with self.db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Query agents
                query = select(Agent).where(Agent.project_id == project.id)
                if status:
                    query = query.where(Agent.status == status)

                result = await session.execute(query)
                agents = result.scalars().all()

                agent_list = []
                for agent in agents:
                    agent_list.append({
                        "id": str(agent.id),
                        "name": agent.name,
                        "role": agent.role,
                        "status": agent.status,
                        "context_used": agent.context_used,
                        "mission": agent.mission,
                        "created_at": agent.created_at.isoformat() if agent.created_at else None,
                    })

                return {"success": True, "agents": agent_list, "count": len(agent_list)}

        except Exception as e:
            logger.exception(f"Failed to list agents: {e}")
            return {"success": False, "error": str(e)}

    async def get_agent_status(self, agent_name: str) -> dict[str, Any]:
        """Get detailed status of a specific agent"""
        return await self.agent_health(agent_name)

    async def update_agent(self, agent_name: str, **kwargs) -> dict[str, Any]:
        """Update agent properties"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active project"}

            async with self.db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Find agent
                agent_query = select(Agent).where(
                    Agent.project_id == project.id,
                    Agent.name == agent_name
                )
                agent_result = await session.execute(agent_query)
                agent = agent_result.scalar_one_or_none()

                if not agent:
                    return {"success": False, "error": f"Agent '{agent_name}' not found"}

                # Update fields
                for key, value in kwargs.items():
                    if hasattr(agent, key):
                        setattr(agent, key, value)

                await session.commit()

                return {
                    "success": True,
                    "agent_name": agent_name,
                    "updated_fields": list(kwargs.keys())
                }

        except Exception as e:
            logger.exception(f"Failed to update agent: {e}")
            return {"success": False, "error": str(e)}

    async def retire_agent(self, agent_name: str, reason: str = "completed") -> dict[str, Any]:
        """Retire an agent (alias for decommission_agent)"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active project"}

            async with self.db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                return await self.decommission_agent(agent_name, str(project.id), reason)

        except Exception as e:
            logger.exception(f"Failed to retire agent: {e}")
            return {"success": False, "error": str(e)}

    # Message Tools

    async def send_message(
        self,
        to_agents: list[str],
        content: str,
        project_id: str,
        message_type: str = "direct",
        priority: str = "normal",
        from_agent: Optional[str] = None,
    ) -> dict[str, Any]:
        """Send message to one or more agents"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Get project
                result = await session.execute(select(Project).where(Project.id == project_id))
                project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Create message
                message = Message(
                    project_id=project.id,
                    tenant_key=project.tenant_key,
                    from_agent_id=from_agent or "orchestrator",
                    to_agents=to_agents,
                    content=content,
                    message_type=message_type,
                    priority=priority,
                    status="pending",
                )

                session.add(message)
                await session.commit()

                return {
                    "success": True,
                    "message_id": str(message.id),
                    "to_agents": to_agents,
                    "type": message_type,
                }

        except Exception as e:
            logger.exception(f"Failed to send message: {e}")
            return {"success": False, "error": str(e)}

    async def get_messages(self, agent_name: str, project_id: Optional[str] = None) -> dict[str, Any]:
        """Retrieve pending messages for an agent"""
        try:
            async with self.db_manager.get_session_async() as session:
                query = select(Message).where(Message.status == "pending")

                if project_id:
                    query = query.where(Message.project_id == project_id)

                result = await session.execute(query)
                messages = result.scalars().all()

                # Filter messages for this agent
                agent_messages = []
                for msg in messages:
                    if agent_name in msg.to_agents or not msg.to_agents:
                        agent_messages.append(
                            {
                                "id": str(msg.id),
                                "from": msg.from_agent_id,
                                "content": msg.content,
                                "type": msg.message_type,
                                "priority": msg.priority,
                                "created": msg.created_at.isoformat(),
                            }
                        )

                return {
                    "success": True,
                    "agent": agent_name,
                    "count": len(agent_messages),
                    "messages": agent_messages,
                }

        except Exception as e:
            logger.exception(f"Failed to get messages: {e}")
            return {"success": False, "error": str(e)}

    async def acknowledge_message(self, message_id: str, agent_name: str) -> dict[str, Any]:
        """Mark message as received by agent"""
        try:
            async with self.db_manager.get_session_async() as session:
                result = await session.execute(select(Message).where(Message.id == message_id))
                message = result.scalar_one_or_none()

                if not message:
                    return {"success": False, "error": "Message not found"}

                # Add to acknowledged_by array
                if not message.acknowledged_by:
                    message.acknowledged_by = []

                if agent_name not in message.acknowledged_by:
                    message.acknowledged_by.append(agent_name)
                    await session.commit()

                return {
                    "success": True,
                    "message_id": message_id,
                    "acknowledged_by": agent_name,
                }

        except Exception as e:
            logger.exception(f"Failed to acknowledge message: {e}")
            return {"success": False, "error": str(e)}

    async def complete_message(self, message_id: str, agent_name: str, result: str) -> dict[str, Any]:
        """Mark message as completed with result"""
        try:
            async with self.db_manager.get_session_async() as session:
                msg_result = await session.execute(select(Message).where(Message.id == message_id))
                message = msg_result.scalar_one_or_none()

                if not message:
                    return {"success": False, "error": "Message not found"}

                # Update message
                message.status = "completed"
                message.result = result
                message.completed_by = agent_name
                message.completed_at = datetime.utcnow()

                await session.commit()

                return {
                    "success": True,
                    "message_id": message_id,
                    "completed_by": agent_name,
                }

        except Exception as e:
            logger.exception(f"Failed to complete message: {e}")
            return {"success": False, "error": str(e)}

    async def broadcast(self, content: str, project_id: str, priority: str = "normal") -> dict[str, Any]:
        """Broadcast message to all agents in project"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Get all agents in project
                result = await session.execute(select(Agent).where(Agent.project_id == project_id))
                agents = result.scalars().all()

                if not agents:
                    return {"success": False, "error": "No agents found in project"}

                agent_names = [agent.name for agent in agents]

                # Send message to all agents
                return await self.send_message(
                    to_agents=agent_names,
                    content=content,
                    project_id=project_id,
                    message_type="broadcast",
                    priority=priority,
                    from_agent="orchestrator",
                )

        except Exception as e:
            logger.exception(f"Failed to broadcast message: {e}")
            return {"success": False, "error": str(e)}

    async def receive_messages(self, agent_id: str, limit: int = 10) -> dict[str, Any]:
        """Receive pending messages for an agent (alias for get_messages)"""
        return await self.get_messages(agent_id, limit=limit)

    async def list_messages(self, project_id: Optional[str] = None, status: Optional[str] = None) -> dict[str, Any]:
        """List messages in a project"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key and not project_id:
                return {"success": False, "error": "No active project"}

            async with self.db_manager.get_session_async() as session:
                if project_id:
                    query = select(Message).where(Message.project_id == project_id)
                else:
                    # Find project by tenant key
                    project_query = select(Project).where(Project.tenant_key == tenant_key)
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()
                    if not project:
                        return {"success": False, "error": "Project not found"}
                    query = select(Message).where(Message.project_id == project.id)

                if status:
                    query = query.where(Message.status == status)

                result = await session.execute(query)
                messages = result.scalars().all()

                message_list = []
                for msg in messages:
                    message_list.append({
                        "id": str(msg.id),
                        "from_agent": msg.from_agent,
                        "to_agent": msg.to_agent,
                        "type": msg.type,
                        "content": msg.content,
                        "status": msg.status,
                        "priority": msg.priority,
                        "created_at": msg.created_at.isoformat() if msg.created_at else None,
                    })

                return {"success": True, "messages": message_list, "count": len(message_list)}

        except Exception as e:
            logger.exception(f"Failed to list messages: {e}")
            return {"success": False, "error": str(e)}

    # Task Tools

    async def log_task(self, content: str, category: Optional[str] = None, priority: str = "medium") -> dict[str, Any]:
        """Quick task capture"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Get the first active project as context (or create a default one)
                from sqlalchemy import select

                stmt = select(Project).where(Project.status == "active").limit(1)
                result = await session.execute(stmt)
                project = result.scalar_one_or_none()

                if not project:
                    # Create a default project for task logging
                    project = Project(
                        name="Default Tasks",
                        mission="Default project for task logging",
                        tenant_key=f"tk_{uuid4().hex[:12]}",
                        status="active",
                    )
                    session.add(project)
                    await session.flush()

                task = Task(
                    tenant_key=project.tenant_key,
                    product_id=project.product_id,  # Inherit product_id from project
                    project_id=str(project.id),
                    title=content,  # Use content as title
                    description=content,  # Also store as description
                    category=category,
                    priority=priority,
                    status="pending",
                )

                session.add(task)
                await session.commit()

                return {
                    "success": True,
                    "task_id": str(task.id),
                    "message": "Task logged successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to log task: {e}")
            return {"success": False, "error": str(e)}

    async def create_task(self, title: str, description: str, priority: str = "medium", assigned_to: Optional[str] = None) -> dict[str, Any]:
        """Create a new task"""
        return await self.log_task(description, category=title, priority=priority)

    async def list_tasks(self, status: Optional[str] = None, assigned_to: Optional[str] = None) -> dict[str, Any]:
        """List tasks"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active project"}

            async with self.db_manager.get_session_async() as session:
                # Find project
                project_query = select(Project).where(Project.tenant_key == tenant_key)
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Query tasks
                query = select(Task).where(Task.project_id == project.id)
                if status:
                    query = query.where(Task.status == status)

                result = await session.execute(query)
                tasks = result.scalars().all()

                task_list = []
                for task in tasks:
                    task_list.append({
                        "id": str(task.id),
                        "description": task.description,
                        "status": task.status,
                        "priority": task.priority,
                        "created_at": task.created_at.isoformat() if task.created_at else None,
                    })

                return {"success": True, "tasks": task_list, "count": len(task_list)}

        except Exception as e:
            logger.exception(f"Failed to list tasks: {e}")
            return {"success": False, "error": str(e)}

    async def update_task(self, task_id: str, **kwargs) -> dict[str, Any]:
        """Update a task"""
        try:
            async with self.db_manager.get_session_async() as session:
                task_query = select(Task).where(Task.id == task_id)
                task_result = await session.execute(task_query)
                task = task_result.scalar_one_or_none()

                if not task:
                    return {"success": False, "error": f"Task {task_id} not found"}

                # Update fields
                for key, value in kwargs.items():
                    if hasattr(task, key):
                        setattr(task, key, value)

                await session.commit()

                return {"success": True, "task_id": task_id, "updated_fields": list(kwargs.keys())}

        except Exception as e:
            logger.exception(f"Failed to update task: {e}")
            return {"success": False, "error": str(e)}

    async def assign_task(self, task_id: str, agent_name: str) -> dict[str, Any]:
        """Assign a task to an agent"""
        return await self.update_task(task_id, assigned_to=agent_name, status="assigned")

    async def complete_task(self, task_id: str) -> dict[str, Any]:
        """Mark a task as completed"""
        return await self.update_task(task_id, status="completed")

    # Context Tools (simplified stubs for now)

    async def get_context_index(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get the context index for intelligent querying"""
        return {"success": True, "index": {"documents": [], "sections": []}}

    async def get_vision(self, part: int = 1, max_tokens: int = 20000) -> dict[str, Any]:
        """Get the vision document"""
        return {
            "success": True,
            "part": part,
            "total_parts": 1,
            "content": "Vision document placeholder",
            "tokens": 100,
        }

    async def get_vision_index(self) -> dict[str, Any]:
        """Get the vision document index"""
        return {"success": True, "index": {"files": [], "chunks": []}}

    async def get_product_settings(self, product_id: Optional[str] = None) -> dict[str, Any]:
        """Get all product settings for analysis"""
        return {
            "success": True,
            "settings": {"product_id": product_id or "default", "config": {}},
        }

    async def discover_context(self, path: Optional[str] = None) -> dict[str, Any]:
        """Discover project context"""
        return {"success": True, "context": {"files": [], "structure": {}}}

    async def get_file_context(self, file_path: str) -> dict[str, Any]:
        """Get context for a specific file"""
        return {"success": True, "file_path": file_path, "context": {}}

    async def search_context(self, query: str, file_types: Optional[list[str]] = None) -> dict[str, Any]:
        """Search project context"""
        return {"success": True, "results": [], "query": query}

    async def get_context_summary(self) -> dict[str, Any]:
        """Get a summary of project context"""
        return {"success": True, "summary": "Context summary placeholder"}

    # Template Tools

    async def list_templates(self) -> dict[str, Any]:
        """List available templates"""
        return {"success": True, "templates": []}

    async def get_template(self, template_name: str) -> dict[str, Any]:
        """Get a specific template"""
        return {"success": True, "template": {"name": template_name, "content": ""}}

    async def create_template(self, name: str, content: str, **kwargs) -> dict[str, Any]:
        """Create a new template"""
        return {"success": True, "template_id": "new-template", "name": name}

    async def update_template(self, template_id: str, **kwargs) -> dict[str, Any]:
        """Update a template"""
        return {"success": True, "template_id": template_id, "updated": True}
