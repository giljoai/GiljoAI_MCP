"""
Tool Accessor for API Integration
Provides direct access to MCP tool functions for API endpoints
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4

import yaml
from sqlalchemy import and_, select, update

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import MCPAgentJob, Message, Product, Project, Task
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class ToolAccessor:
    """Provides direct access to MCP tool functionality for API"""

    def __init__(self, db_manager: DatabaseManager, tenant_manager: TenantManager):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager

    # Project Tools

    async def create_project(
        self,
        name: str,
        mission: str,
        description: str = "",  # Optional description parameter
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        status: str = "inactive",  # Handover 0050b: projects default to inactive
        context_budget: int = 150000,
    ) -> dict[str, Any]:
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
                    description=description,  # Use provided description
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status=status,  # Use the passed status parameter
                    context_budget=context_budget,
                    context_used=0,
                )

                session.add(project)
                await session.commit()

                project_id = str(project.id)

                logger.info(f"Created project {project_id} with status '{status}' and tenant key {tenant_key}")

                return {
                    "success": True,
                    "project_id": project_id,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "name": name,
                    "status": status,  # Return the actual status used
                }

        except Exception as e:
            logger.exception(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    async def list_projects(self, status: Optional[str] = None, tenant_key: Optional[str] = None) -> dict[str, Any]:
        """List all projects with optional status filter and tenant filtering"""
        try:
            # Use provided tenant_key or get from context
            if not tenant_key:
                tenant_key = self.tenant_manager.get_current_tenant()

            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self.db_manager.get_tenant_session_async(tenant_key) as session:
                # TENANT ISOLATION: Only return projects for the specified tenant
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
                    },
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
                    SessionModel.project_id == project.id, SessionModel.status == "active"
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

                # Get agent jobs (migrated from Agent to MCPAgentJob - Handover 0116)
                agent_job_result = await session.execute(select(MCPAgentJob).where(MCPAgentJob.project_id == project.id))
                agent_jobs = agent_job_result.scalars().all()

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
                        "completed_at": project.completed_at.isoformat() if project.completed_at else None,
                        "context_budget": project.context_budget,
                        "context_used": project.context_used,
                    },
                    "agents": [{"name": job.agent_type, "status": job.status, "role": job.agent_type} for job in agent_jobs],
                    "pending_messages": pending_messages,
                }

        except Exception as e:
            logger.exception(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    async def close_project(self, project_id: str, summary: str) -> dict[str, Any]:
        """Close a completed project with summary (DEPRECATED: Use complete_project instead)"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Update project status with completed_at timestamp
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(
                        status="completed",
                        completed_at=datetime.utcnow(),
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

    async def complete_project(self, project_id: str, summary: Optional[str] = None) -> dict[str, Any]:
        """Mark a project as completed with completed_at timestamp"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Build update values
                update_values = {
                    "status": "completed",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                # Add summary to meta_data if provided
                if summary:
                    update_values["meta_data"] = {"summary": summary}

                result = await session.execute(update(Project).where(Project.id == project_id).values(**update_values))

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                await session.commit()

                logger.info(f"Completed project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} completed successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to complete project: {e}")
            return {"success": False, "error": str(e)}

    async def cancel_project(self, project_id: str, reason: Optional[str] = None) -> dict[str, Any]:
        """Cancel a project with completed_at timestamp"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Build update values
                update_values = {
                    "status": "cancelled",
                    "completed_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow(),
                }

                # Add reason to meta_data if provided
                if reason:
                    update_values["meta_data"] = {"cancellation_reason": reason}

                result = await session.execute(update(Project).where(Project.id == project_id).values(**update_values))

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                await session.commit()

                logger.info(f"Cancelled project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} cancelled successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to cancel project: {e}")
            return {"success": False, "error": str(e)}

    async def restore_project(self, project_id: str) -> dict[str, Any]:
        """Restore a completed or cancelled project to inactive status"""
        try:
            async with self.db_manager.get_session_async() as session:
                # Update project to inactive and clear completed_at
                result = await session.execute(
                    update(Project)
                    .where(Project.id == project_id)
                    .values(
                        status="inactive",
                        completed_at=None,
                        updated_at=datetime.utcnow(),
                    )
                )

                if result.rowcount == 0:
                    return {"success": False, "error": "Project not found"}

                await session.commit()

                logger.info(f"Restored project {project_id}")

                return {
                    "success": True,
                    "message": f"Project {project_id} restored successfully",
                }

        except Exception as e:
            logger.exception(f"Failed to restore project: {e}")
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

                # Get project for tenant_key
                project_result = await session.execute(
                    select(Project).where(Project.id == project_id)
                )
                project = project_result.scalar_one_or_none()

                await session.commit()

                # Broadcast mission update via WebSocket HTTP bridge
                logger.info(f"[WEBSOCKET DEBUG] About to broadcast mission_updated for project {project_id}")
                if project:
                    try:
                        import httpx
                        
                        logger.info(f"[WEBSOCKET DEBUG] httpx imported, creating client for HTTP bridge")

                        # Use HTTP bridge to emit WebSocket event (MCP runs in separate process)
                        async with httpx.AsyncClient() as client:
                            bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                            logger.info(f"[WEBSOCKET DEBUG] Sending POST to {bridge_url}")
                            
                            response = await client.post(
                                bridge_url,
                                json={
                                    "event_type": "project:mission_updated",
                                    "tenant_key": project.tenant_key,
                                    "data": {
                                        "project_id": project_id,
                                        "mission": mission,
                                        "token_estimate": len(mission) // 4,
                                        "user_config_applied": False,
                                        "generated_by": "orchestrator",
                                        "timestamp": datetime.utcnow().isoformat(),
                                    },
                                },
                                timeout=5.0,
                            )
                            logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response: {response.status_code}")
                            logger.info(f"[WEBSOCKET] Broadcasted mission_updated for project {project_id} via HTTP bridge")
                    except Exception as ws_error:
                        logger.error(f"[WEBSOCKET ERROR] Failed to broadcast mission_updated via HTTP bridge: {ws_error}", exc_info=True)

                return {"success": True, "message": "Mission updated successfully"}

        except Exception as e:
            logger.exception(f"Failed to update mission: {e}")
            return {"success": False, "error": str(e)}

    # Agent Tools

    async def ensure_agent(self, project_id: str, agent_name: str, mission: Optional[str] = None) -> dict[str, Any]:
        """
        DEPRECATED: Internal helper - should not be exposed as MCP tool.
        
        This tool is an internal helper that creates legacy Agent records.
        External callers should use spawn_agent_job() for agent creation.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await ensure_agent(project_id, agent_name="impl-1", mission="...")
            
            # NEW (correct for external use)
            await spawn_agent_job(
                agent_type="implementer",
                agent_name="impl-1",
                mission="...",
                project_id=project_id,
                tenant_key=tenant_key
            )
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Internal helper, shouldn't be exposed as MCP tool. Use spawn_agent_job() instead.",
            "replacement": "spawn_agent_job",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Internal helper only. External callers should use spawn_agent_job()."
        }

    async def agent_health(self, agent_name: Optional[str] = None) -> dict[str, Any]:
        """
        DEPRECATED: Use get_workflow_status() instead.
        
        This tool is a duplicate of get_agent_status and queries legacy 'agents' table.
        Use get_workflow_status() for team-level agent monitoring with 7-state model.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await agent_health(agent_name="impl-1")
            
            # NEW (correct)
            await get_workflow_status(
                project_id=project_id,
                tenant_key=tenant_key
            )
            # Returns status for ALL agents in project workflow
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Duplicate of get_agent_status. Use get_workflow_status() for team-level monitoring.",
            "replacement": "get_workflow_status",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Queries 'agents' table. Use get_workflow_status() for 7-state MCPAgentJob monitoring."
        }

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
        """
        DEPRECATED: Use spawn_agent_job() instead.
        
        This tool creates legacy Agent records (4-state model: idle, active, completed, failed).
        Handover 0116 migrates to MCPAgentJob model (7-state model).
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await spawn_agent(name="impl-1", role="implementer", mission="...")
            
            # NEW (correct)
            await spawn_agent_job(
                agent_type="implementer",
                agent_name="impl-1",
                mission="...",
                project_id=project_id,
                tenant_key=tenant_key
            )
        
        See: Comprehensive_MCP_Analysis.md lines 356-390
        """
        return {
            "error": "DEPRECATED",
            "message": "Use spawn_agent_job() instead. This tool creates legacy Agent records (4-state).",
            "replacement": "spawn_agent_job",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Creates records in 'agents' table. Dashboard reads from 'mcp_agent_jobs' table."
        }

    async def list_agents(self, status: Optional[str] = None) -> dict[str, Any]:
        """
        DEPRECATED: Use get_pending_jobs() instead.
        
        This tool queries legacy 'agents' table (4-state model).
        Dashboard reads from 'mcp_agent_jobs' table (7-state model), causing data disconnect.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await list_agents(status="active")
            
            # NEW (correct)
            await get_pending_jobs(
                agent_type="implementer",
                tenant_key=tenant_key
            )
        
        See: Comprehensive_MCP_Analysis.md lines 400-427
        """
        return {
            "error": "DEPRECATED",
            "message": "Use get_pending_jobs() instead. Dashboard uses MCPAgentJob table.",
            "replacement": "get_pending_jobs",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Queries 'agents' table. Dashboard displays 'mcp_agent_jobs' records."
        }

    async def get_agent_status(self, agent_name: str) -> dict[str, Any]:
        """
        DEPRECATED: Use get_workflow_status() instead.
        
        This tool uses legacy 4-state Agent model (idle, active, completed, failed).
        Use get_workflow_status() for 7-state MCPAgentJob model monitoring.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await get_agent_status(agent_name="impl-1")
            
            # NEW (correct)
            await get_workflow_status(
                project_id=project_id,
                tenant_key=tenant_key
            )
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Use get_workflow_status() instead. This uses 4-state Agent model.",
            "replacement": "get_workflow_status",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Queries 'agents' table (4-state). Use get_workflow_status (7-state MCPAgentJob)."
        }

    async def update_agent(self, agent_name: str, **kwargs) -> dict[str, Any]:
        """
        DEPRECATED: Use report_progress() or complete_job() instead.
        
        This tool updates legacy 'agents' table. Dashboard doesn't display these updates.
        Use report_progress() for incremental updates or complete_job() for finalization.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await update_agent(agent_name="impl-1", status="active")
            
            # NEW (in-progress updates)
            await report_progress(
                job_id=job_id,
                progress={"status": "active", "details": "..."}
            )
            
            # NEW (completion)
            await complete_job(
                job_id=job_id,
                result={"status": "completed", "output": "..."}
            )
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Use report_progress() (in-progress) or complete_job() (finished).",
            "replacement": "report_progress or complete_job",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Updates 'agents' table. Dashboard displays 'mcp_agent_jobs' updates only."
        }

    async def retire_agent(self, agent_name: str, reason: str = "completed") -> dict[str, Any]:
        """
        DEPRECATED: Agent retirement handled automatically via job lifecycle.
        
        This tool manually retires agents in legacy 'agents' table.
        In the new job model, retirement happens automatically when jobs complete or decommission.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete)
            await retire_agent(agent_name="impl-1", reason="completed")
            
            # NEW (automatic via job lifecycle)
            # No explicit retirement needed - complete_job() handles lifecycle
            await complete_job(
                job_id=job_id,
                result={"output": "..."}
            )
            # Job automatically transitions to 'completed' state
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Agent retirement handled automatically when job completes or decommissions.",
            "replacement": "Automatic via job lifecycle (use complete_job)",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Manual retirement not needed. Job state transitions handle lifecycle."
        }

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
                # Get all agent jobs in project (migrated from Agent to MCPAgentJob - Handover 0116)
                result = await session.execute(select(MCPAgentJob).where(MCPAgentJob.project_id == project_id))
                agent_jobs = result.scalars().all()

                if not agent_jobs:
                    return {"success": False, "error": "No agent jobs found in project"}

                agent_types = [job.agent_type for job in agent_jobs]

                # Send message to all agents
                return await self.send_message(
                    to_agents=agent_types,
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
                    # Find project by tenant key - prefer active project if multiple exist
                    project_query = select(Project).where(
                        and_(Project.tenant_key == tenant_key, Project.status == "active")
                    )
                    project_result = await session.execute(project_query)
                    project = project_result.scalar_one_or_none()

                    # Fallback to most recent project if no active project
                    if not project:
                        project_query = (
                            select(Project)
                            .where(Project.tenant_key == tenant_key)
                            .order_by(Project.created_at.desc())
                            .limit(1)
                        )
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
                    message_list.append(
                        {
                            "id": str(msg.id),
                            "from_agent": msg.from_agent,
                            "to_agent": msg.to_agent,
                            "type": msg.type,
                            "content": msg.content,
                            "status": msg.status,
                            "priority": msg.priority,
                            "created_at": msg.created_at.isoformat() if msg.created_at else None,
                        }
                    )

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

    async def create_task(
        self, title: str, description: str, priority: str = "medium", assigned_to: Optional[str] = None
    ) -> dict[str, Any]:
        """Create a new task"""
        return await self.log_task(description, category=title, priority=priority)

    async def list_tasks(self, status: Optional[str] = None, assigned_to: Optional[str] = None) -> dict[str, Any]:
        """List tasks"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active project"}

            async with self.db_manager.get_session_async() as session:
                # Find project - prefer active project if multiple exist
                project_query = select(Project).where(
                    and_(Project.tenant_key == tenant_key, Project.status == "active")
                )
                project_result = await session.execute(project_query)
                project = project_result.scalar_one_or_none()

                # Fallback to most recent project if no active project
                if not project:
                    project_query = (
                        select(Project)
                        .where(Project.tenant_key == tenant_key)
                        .order_by(Project.created_at.desc())
                        .limit(1)
                    )
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
                    task_list.append(
                        {
                            "id": str(task.id),
                            "description": task.description,
                            "status": task.status,
                            "priority": task.priority,
                            "created_at": task.created_at.isoformat() if task.created_at else None,
                        }
                    )

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

    async def discover_context(
        self,
        project_id: Optional[str] = None,
        path: Optional[str] = None,
        agent_role: str = "default",
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.
        
        This tool was a placeholder for context discovery functionality.
        Thin client architecture (Handover 0088) eliminated the need for this tool.
        Agents access context directly via IDE tools and get_agent_mission().
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete stub)
            await discover_context(project_id=project_id, agent_role="implementer")
            
            # NEW (no replacement needed)
            # Context provided via:
            # 1. get_agent_mission() - returns mission with embedded context
            # 2. IDE tools (Read, Grep, Glob) - direct file/codebase access
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Thin client architecture eliminated need for this tool.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Agents access context via get_agent_mission() and IDE tools (Read, Grep, Glob)."
        }

    async def get_file_context(self, file_path: str) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.
        
        This tool was a placeholder directing users to Serena MCP tools.
        Agents access files directly via IDE tools (Read, Grep).
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete stub)
            await get_file_context(file_path="src/main.py")
            
            # NEW (no replacement needed)
            # Use IDE tools directly:
            # - Read tool for file contents
            # - mcp__serena__read_file for file reading
            # - mcp__serena__get_symbols_overview for code structure
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Agents access files directly via IDE tools.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Use Read tool or Serena MCP (read_file, get_symbols_overview) for file access."
        }

    async def search_context(self, query: str, file_types: Optional[list[str]] = None) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.
        
        This tool was a placeholder directing users to Serena MCP grep tools.
        Agents use IDE search capabilities (Grep tool) directly.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete stub)
            await search_context(query="class MyClass", file_types=["*.py"])
            
            # NEW (no replacement needed)
            # Use IDE tools directly:
            # - Grep tool for pattern search
            # - mcp__serena__search_for_pattern for regex search
            # - Glob tool for file name patterns
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Agents use IDE search capabilities (Grep tool) directly.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Use Grep tool or Serena MCP (search_for_pattern) for content search."
        }

    async def get_context_summary(self, project_id: Optional[str] = None) -> dict[str, Any]:
        """
        DEPRECATED: Stub implementation - not needed.
        
        This tool was a placeholder for project context summaries.
        Thin client architecture (Handover 0088) provides context via get_agent_mission().
        Mission includes all necessary context for agents.
        This method will be removed in v3.2.0.
        
        Migration:
            # OLD (obsolete stub)
            await get_context_summary(project_id=project_id)
            
            # NEW (no replacement needed)
            # Context summary provided via:
            # - get_agent_mission() returns mission with embedded context
            # - Mission field includes project/product context
        
        See: Comprehensive_MCP_Analysis.md for migration guide
        """
        return {
            "error": "DEPRECATED",
            "message": "Stub implementation. Mission from get_agent_mission() provides context.",
            "replacement": "None - not needed",
            "documentation": "See Comprehensive_MCP_Analysis.md for migration guide",
            "removal_version": "v3.2.0",
            "reason": "Context provided via get_agent_mission() - mission field includes all necessary context."
        }

    # Template Tools

    async def list_templates(self) -> dict[str, Any]:
        """List available templates"""
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            async with self.db_manager.get_session_async() as session:
                from giljo_mcp.models import AgentTemplate

                result = await session.execute(select(AgentTemplate).where(AgentTemplate.tenant_key == tenant_key))
                templates = result.scalars().all()

                return {
                    "success": True,
                    "templates": [
                        {
                            "id": str(t.id),
                            "name": t.name,
                            "role": t.role,
                            "content": t.template_content,
                            "cli_tool": t.cli_tool,
                            "background_color": t.background_color,
                        }
                        for t in templates
                    ],
                }

        except Exception as e:
            logger.error(f"Error listing templates: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    async def get_template(self, template_name: str) -> dict[str, Any]:
        """Get a specific template"""
        return {"success": True, "template": {"name": template_name, "content": ""}}

    async def create_template(self, name: str, content: str, **kwargs) -> dict[str, Any]:
        """Create a new template"""
        return {"success": True, "template_id": "new-template", "name": name}

    async def update_template(self, template_id: str, **kwargs) -> dict[str, Any]:
        """Update a template"""
        return {"success": True, "template_id": template_id, "updated": True}

    # Agent Export Tools (Handover 0084)

    async def export_agents(
        self,
        product_path: Optional[str] = None,
        personal: bool = False,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Export agent templates to Claude Code format via MCP command.

        Args:
            product_path: Path to product's .claude/agents directory
            personal: Export to user's personal ~/.claude/agents
            product_id: Optional specific product ID (uses active product if not specified)

        Returns:
            Export result dictionary
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            from .claude_export import export_agents_command, get_product_for_tenant

            # If product_path not provided and not personal, try to get from product
            if not product_path and not personal:
                product = await get_product_for_tenant(self.db_manager, tenant_key, product_id)
                if product and product.project_path:
                    product_path = str(Path(product.project_path) / ".claude" / "agents")
                else:
                    return {
                        "success": False,
                        "error": "No product path configured. Set product project_path or use --personal",
                    }

            # Call export command
            result = await export_agents_command(
                db_manager=self.db_manager,
                tenant_key=tenant_key,
                product_path=product_path,
                personal=personal,
            )

            return result

        except Exception as e:
            logger.exception(f"Failed to export agents: {e}")
            return {"success": False, "error": str(e)}

    async def set_product_path(
        self,
        project_path: str,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Set or update product's project path for agent export.

        Args:
            project_path: File system path to product folder
            product_id: Optional specific product ID (uses active product if not specified)

        Returns:
            Update result dictionary
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            from .claude_export import get_product_for_tenant, validate_product_path

            # Get product
            product = await get_product_for_tenant(self.db_manager, tenant_key, product_id)
            if not product:
                return {"success": False, "error": "Product not found"}

            # Validate and update path
            result = await validate_product_path(
                db_manager=self.db_manager,
                tenant_key=tenant_key,
                product_id=str(product.id),
                project_path=project_path,
            )

            return result

        except Exception as e:
            logger.exception(f"Failed to set product path: {e}")
            return {"success": False, "error": str(e)}

    async def get_product_path(
        self,
        product_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Get product's current project path.

        Args:
            product_id: Optional specific product ID (uses active product if not specified)

        Returns:
            Product path information
        """
        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No tenant context available"}

            from .claude_export import get_product_for_tenant

            # Get product
            product = await get_product_for_tenant(self.db_manager, tenant_key, product_id)
            if not product:
                return {"success": False, "error": "Product not found"}

            return {
                "success": True,
                "product_id": str(product.id),
                "product_name": product.name,
                "project_path": product.project_path,
                "has_path": bool(product.project_path),
            }

        except Exception as e:
            logger.exception(f"Failed to get product path: {e}")
            return {"success": False, "error": str(e)}

    # Orchestration Tools

    async def health_check(self) -> dict[str, Any]:
        """MCP server health check"""
        from giljo_mcp.tools.orchestration import health_check

        return await health_check()

    async def get_orchestrator_instructions(self, orchestrator_id: str, tenant_key: str) -> dict[str, Any]:
        """Fetch orchestrator mission with 70% token reduction"""
        # Delegate to orchestration module but use our db_manager
        try:
            async with self.db_manager.get_session_async() as session:
                from sqlalchemy import and_

                from giljo_mcp.mission_planner import MissionPlanner
                from giljo_mcp.models import AgentTemplate, MCPAgentJob, Product, Project

                # Validate inputs
                if not orchestrator_id or not orchestrator_id.strip():
                    return {"error": "VALIDATION_ERROR", "message": "Orchestrator ID is required"}

                if not tenant_key or not tenant_key.strip():
                    return {"error": "VALIDATION_ERROR", "message": "Tenant key is required"}

                # Get orchestrator job with tenant isolation
                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(
                            MCPAgentJob.job_id == orchestrator_id,
                            MCPAgentJob.tenant_key == tenant_key,
                            MCPAgentJob.agent_type == "orchestrator",
                        )
                    )
                )
                orchestrator = result.scalar_one_or_none()

                if not orchestrator:
                    return {"error": "NOT_FOUND", "message": f"Orchestrator {orchestrator_id} not found"}

                # Get project and product
                result = await session.execute(
                    select(Project).where(and_(Project.id == orchestrator.project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": "NOT_FOUND", "message": "Project not found"}

                product = None
                if project.product_id:
                    result = await session.execute(
                        select(Product).where(and_(Product.id == project.product_id, Product.tenant_key == tenant_key))
                    )
                    product = result.scalar_one_or_none()

                # Generate condensed mission
                planner = MissionPlanner(self.db_manager)
                metadata = orchestrator.job_metadata or {}
                field_priorities = metadata.get("field_priorities", {})
                user_id = metadata.get("user_id")

                condensed_mission = await planner._build_context_with_priorities(
                    product=product, project=project, field_priorities=field_priorities, user_id=user_id
                )

                # FIX: Add fallback mission generation if mission is empty
                if not condensed_mission or condensed_mission.strip() == "":
                    mission_parts = []

                    # Include product vision if available
                    if product and product.vision_summary:
                        mission_parts.append(f"Vision: {product.vision_summary}")

                    # Include project description if available
                    if project.description:
                        mission_parts.append(f"Project Goal: {project.description}")

                    # Include tech stack from product context if available
                    if product and product.product_context:
                        context = product.product_context or {}
                        if context.get("tech_stack"):
                            mission_parts.append(f"Tech Stack: {context['tech_stack']}")

                    # Build fallback mission from collected parts
                    if mission_parts:
                        condensed_mission = "\n\n".join(mission_parts)
                    else:
                        # Final fallback: use project description or a minimal message
                        condensed_mission = project.description or "No mission defined"

                # Get agent templates
                result = await session.execute(
                    select(AgentTemplate)
                    .where(and_(AgentTemplate.tenant_key == tenant_key, AgentTemplate.is_active == True))
                    .limit(8)
                )
                templates = result.scalars().all()

                template_list = [
                    {"name": t.name, "role": t.role, "description": t.description[:200] if t.description else ""}
                    for t in templates
                ]

                estimated_tokens = len(condensed_mission) // 4

                return {
                    "orchestrator_id": orchestrator_id,
                    "project_id": str(project.id),
                    "project_name": project.name,
                    "project_description": project.description or "",
                    "mission": condensed_mission,
                    "context_budget": orchestrator.context_budget or 150000,
                    "context_used": orchestrator.context_used or 0,
                    "agent_templates": template_list,
                    "field_priorities": field_priorities,
                    "token_reduction_applied": bool(field_priorities),
                    "estimated_tokens": estimated_tokens,
                    "instance_number": orchestrator.instance_number or 1,
                    "thin_client": True,
                }

        except Exception as e:
            logger.exception(f"Failed to get orchestrator instructions: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}

    async def spawn_agent_job(
        self,
        agent_type: str,
        agent_name: str,
        mission: str,
        project_id: str,
        tenant_key: str,
        parent_job_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Create an agent job with thin client architecture"""
        try:
            async with self.db_manager.get_session_async() as session:
                from datetime import datetime, timezone

                from sqlalchemy import and_

                from giljo_mcp.models import MCPAgentJob, Project

                # Get project for context
                result = await session.execute(
                    select(Project).where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": "NOT_FOUND", "message": "Project not found"}

                # Create agent job with mission STORED in database
                agent_job_id = str(uuid4())
                agent_job = MCPAgentJob(
                    job_id=agent_job_id,
                    project_id=project_id,
                    tenant_key=tenant_key,
                    agent_type=agent_type,
                    agent_name=agent_name,
                    mission=mission,  # STORED HERE, not in prompt
                    spawned_by=parent_job_id,
                    status="waiting",  # Fixed: was "pending" but constraint only allows "waiting"
                    metadata={
                        "created_via": "thin_client_spawn",
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "thin_client": True,
                    },
                )

                session.add(agent_job)
                await session.commit()
                await session.refresh(agent_job)

                # Generate THIN agent prompt (~10 lines)
                thin_agent_prompt = f"""I am {agent_name} (Agent {agent_type}) for Project "{project.name}".

IDENTITY:
- Agent ID: {agent_job_id}
- Agent Type: {agent_type}
- Project ID: {project_id}
- Parent Orchestrator: {parent_job_id or "None"}

INSTRUCTIONS:
1. Fetch mission: get_agent_mission(agent_job_id='{agent_job_id}', tenant_key='{tenant_key}')
2. Execute mission
3. Report progress: update_job_progress('{agent_job_id}', percent, message)
4. Coordinate via: send_message(to_agent_id, content)

Begin by fetching your mission.
"""

                # Calculate token estimates
                prompt_tokens = len(thin_agent_prompt) // 4  # ~50 tokens
                mission_tokens = len(mission) // 4  # ~2000 tokens

                # Broadcast agent creation via WebSocket HTTP bridge
                logger.info(f"[WEBSOCKET DEBUG] About to broadcast agent:created for {agent_name} ({agent_type})")
                try:
                    import httpx
                    
                    logger.info(f"[WEBSOCKET DEBUG] httpx imported for agent creation broadcast")

                    # Use HTTP bridge to emit WebSocket event (MCP runs in separate process)
                    async with httpx.AsyncClient() as client:
                        bridge_url = "http://localhost:7272/api/v1/ws-bridge/emit"
                        logger.info(f"[WEBSOCKET DEBUG] Sending POST to {bridge_url} for agent:created")
                        
                        response = await client.post(
                            bridge_url,
                            json={
                                "event_type": "agent:created",
                                "tenant_key": tenant_key,
                                "data": {
                                    "project_id": project_id,
                                    "agent_id": agent_job_id,
                                    "agent_job_id": agent_job_id,
                                    "agent_type": agent_type,
                                    "agent_name": agent_name,
                                    "status": "waiting",
                                    "thin_client": True,
                                    "prompt_tokens": prompt_tokens,
                                    "mission_tokens": mission_tokens,
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                            },
                            timeout=5.0,
                        )
                        logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response for agent:created: {response.status_code}")
                        logger.info(f"[WEBSOCKET] Broadcasted agent:created for {agent_name} ({agent_type}) via HTTP bridge")
                except Exception as ws_error:
                    logger.error(f"[WEBSOCKET ERROR] Failed to broadcast agent:created via HTTP bridge: {ws_error}", exc_info=True)

                return {
                    "success": True,
                    "agent_job_id": agent_job_id,
                    "agent_prompt": thin_agent_prompt,  # ~10 lines
                    "prompt_tokens": prompt_tokens,  # ~50
                    "mission_stored": True,
                    "mission_tokens": mission_tokens,  # ~2000
                    "total_tokens": prompt_tokens + mission_tokens,
                    "thin_client": True,
                }

        except Exception as e:
            logger.exception(f"Failed to spawn agent job: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Failed to spawn agent: {e!s}", "severity": "ERROR"}

    async def get_agent_mission(self, agent_job_id: str, tenant_key: str) -> dict[str, Any]:
        """Get agent-specific mission"""
        try:
            async with self.db_manager.get_session_async() as session:
                from sqlalchemy import and_

                from giljo_mcp.models import MCPAgentJob

                result = await session.execute(
                    select(MCPAgentJob).where(
                        and_(MCPAgentJob.job_id == agent_job_id, MCPAgentJob.tenant_key == tenant_key)
                    )
                )
                agent_job = result.scalar_one_or_none()

                if not agent_job:
                    return {"error": "NOT_FOUND", "message": f"Agent job {agent_job_id} not found"}

                estimated_tokens = len(agent_job.mission or "") // 4

                return {
                    "success": True,
                    "agent_job_id": agent_job_id,
                    "agent_name": agent_job.agent_type,
                    "agent_type": agent_job.agent_type,
                    "mission": agent_job.mission or "",
                    "project_id": str(agent_job.project_id),
                    "parent_job_id": str(agent_job.spawned_by) if agent_job.spawned_by else None,
                    "estimated_tokens": estimated_tokens,
                    "status": agent_job.status,
                    "thin_client": True,
                }

        except Exception as e:
            logger.exception(f"Failed to get agent mission: {e}")
            return {"error": "INTERNAL_ERROR", "message": f"Unexpected error: {e!s}"}

    async def orchestrate_project(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """Full project orchestration workflow"""
        from giljo_mcp.orchestrator import ProjectOrchestrator

        try:
            async with self.db_manager.get_session_async() as session:
                from giljo_mcp.models import Project

                # Get project with tenant isolation
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project '{project_id}' not found"}

                if not project.product_id:
                    return {"error": f"Project '{project_id}' has no associated product"}

                # Initialize orchestrator and run workflow
                orchestrator = ProjectOrchestrator()
                result_dict = await orchestrator.process_product_vision(
                    tenant_key=tenant_key, product_id=project.product_id, project_requirements=project.mission
                )

                return result_dict

        except Exception as e:
            logger.exception(f"Failed to orchestrate project: {e}")
            return {"error": f"Orchestration failed: {e!s}"}

    async def get_workflow_status(self, project_id: str, tenant_key: str) -> dict[str, Any]:
        """Get workflow status for a project"""
        try:
            async with self.db_manager.get_session_async() as session:
                from giljo_mcp.models import Job, Project

                # Verify project exists
                result = await session.execute(
                    select(Project).where(Project.id == project_id, Project.tenant_key == tenant_key)
                )
                project = result.scalar_one_or_none()

                if not project:
                    return {"error": f"Project '{project_id}' not found"}

                # Get all Jobs for this tenant
                jobs_result = await session.execute(select(Job).where(Job.tenant_key == tenant_key))
                jobs = jobs_result.scalars().all()

                # Count by status
                active_count = sum(1 for job in jobs if job.status == "active")
                completed_count = sum(1 for job in jobs if job.status == "completed")
                failed_count = sum(1 for job in jobs if job.status == "failed")
                pending_count = sum(1 for job in jobs if job.status == "pending")
                total_count = len(jobs)

                # Calculate progress
                progress_percent = (completed_count / total_count * 100.0) if total_count > 0 else 0.0

                # Determine current stage
                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == total_count:
                    current_stage = "Completed"
                elif failed_count > 0:
                    current_stage = f"In Progress (with {failed_count} failure(s))"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                return {
                    "active_agents": active_count,
                    "completed_agents": completed_count,
                    "failed_agents": failed_count,
                    "pending_agents": pending_count,
                    "current_stage": current_stage,
                    "progress_percent": round(progress_percent, 2),
                    "total_agents": total_count,
                }

        except Exception as e:
            logger.exception(f"Failed to get workflow status: {e}")
            return {"error": f"Failed to get workflow status: {e!s}"}

    # Agent Coordination Tools

    async def get_pending_jobs(self, agent_type: str, tenant_key: str) -> dict[str, Any]:
        """Get pending jobs for agent type"""
        try:
            # Validate inputs
            if not agent_type or not agent_type.strip():
                return {"status": "error", "error": "agent_type cannot be empty", "jobs": [], "count": 0}

            if not tenant_key or not tenant_key.strip():
                return {"status": "error", "error": "tenant_key cannot be empty", "jobs": [], "count": 0}

            # Get pending jobs with tenant isolation (async)
            async with self.db_manager.get_session_async() as session:
                from giljo_mcp.models import MCPAgentJob

                result = await session.execute(
                    select(MCPAgentJob)
                    .where(
                        MCPAgentJob.tenant_key == tenant_key,
                        MCPAgentJob.agent_type == agent_type,
                        MCPAgentJob.status == "waiting",
                    )
                    .limit(10)
                )
                jobs = result.scalars().all()

                # Format jobs for response
                formatted_jobs = []
                for job in jobs:
                    formatted_jobs.append(
                        {
                            "job_id": job.job_id,
                            "agent_type": job.agent_type,
                            "mission": job.mission,
                            "context_chunks": job.context_chunks or [],
                            "priority": "normal",
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                        }
                    )

                return {"status": "success", "jobs": formatted_jobs, "count": len(formatted_jobs)}

        except Exception as e:
            logger.exception(f"Failed to get pending jobs: {e}")
            return {"status": "error", "error": str(e), "jobs": [], "count": 0}

    async def acknowledge_job(self, job_id: str, agent_id: str) -> dict[str, Any]:
        """Acknowledge job assignment"""
        from giljo_mcp.agent_job_manager import AgentJobManager

        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            # Validate inputs
            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}

            if not agent_id or not agent_id.strip():
                return {"status": "error", "error": "agent_id cannot be empty"}

            job_manager = AgentJobManager(self.db_manager)
            job = job_manager.acknowledge_job(tenant_key=tenant_key, job_id=job_id)

            # Agent status sync removed (Handover 0116) - Agent model eliminated
            # Previously synced job acknowledgment to legacy agents table
            # MCPAgentJob status is authoritative and updated via AgentJobManager

            return {
                "status": "success",
                "job": {
                    "job_id": job.job_id,
                    "agent_type": job.agent_type,
                    "mission": job.mission,
                    "status": job.status,
                    "started_at": job.started_at.isoformat() if job.started_at else None,
                },
                "next_instructions": "Begin executing your mission",
            }

        except Exception as e:
            logger.exception(f"Failed to acknowledge job: {e}")
            return {"status": "error", "error": str(e)}

    async def report_progress(self, job_id: str, progress: dict[str, Any]) -> dict[str, Any]:
        """Report job progress"""
        from giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            # Validate inputs
            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}

            if not progress or not isinstance(progress, dict):
                return {"status": "error", "error": "progress must be a non-empty dict"}

            comm_queue = AgentCommunicationQueue(self.db_manager)

            # Send progress message
            comm_queue.send_message(
                tenant_key=tenant_key,
                from_job_id=job_id,
                to_job_id="orchestrator",
                message_type="progress",
                content=progress,
            )

            return {"status": "success", "message": "Progress reported successfully"}

        except Exception as e:
            logger.exception(f"Failed to report progress: {e}")
            return {"status": "error", "error": str(e)}

    async def complete_job(self, job_id: str, result: dict[str, Any]) -> dict[str, Any]:
        """Mark job as complete"""
        from giljo_mcp.agent_job_manager import AgentJobManager

        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            # Validate inputs
            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}

            if not result or not isinstance(result, dict):
                return {"status": "error", "error": "result must be a non-empty dict"}

            job_manager = AgentJobManager(self.db_manager)
            job = job_manager.complete_job(tenant_key=tenant_key, job_id=job_id, result=result)

            # Agent status sync removed (Handover 0116) - Agent model eliminated
            # Previously synced job completion to legacy agents table
            # MCPAgentJob status is authoritative and updated via AgentJobManager

            return {"status": "success", "job_id": job.job_id, "message": "Job completed successfully"}

        except Exception as e:
            logger.exception(f"Failed to complete job: {e}")
            return {"status": "error", "error": str(e)}

    async def report_error(self, job_id: str, error: str) -> dict[str, Any]:
        """Report job error"""
        from giljo_mcp.agent_job_manager import AgentJobManager

        try:
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"status": "error", "error": "No tenant context available"}

            # Validate inputs
            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}

            if not error or not error.strip():
                return {"status": "error", "error": "error message cannot be empty"}

            job_manager = AgentJobManager(self.db_manager)
            job = job_manager.fail_job(tenant_key=tenant_key, job_id=job_id, error_message=error)

            # Agent status sync removed (Handover 0116) - Agent model eliminated
            # Previously synced job failure to legacy agents table
            # MCPAgentJob status is authoritative and updated via AgentJobManager
            try:
                pass
            except Exception as sync_error:
                logger.warning(f"Failed to sync Agent status: {sync_error}")

            return {"status": "success", "job_id": job.job_id, "message": "Error reported successfully"}

        except Exception as e:
            logger.exception(f"Failed to report error: {e}")
            return {"status": "error", "error": str(e)}

    async def get_next_instruction(self, job_id: str, agent_type: str, tenant_key: str) -> dict[str, Any]:
        """Get next instructions for agent from message queue"""
        from giljo_mcp.agent_communication_queue import AgentCommunicationQueue

        try:
            # Validate inputs
            if not job_id or not job_id.strip():
                return {"status": "error", "error": "job_id cannot be empty"}

            if not agent_type or not agent_type.strip():
                return {"status": "error", "error": "agent_type cannot be empty"}

            if not tenant_key or not tenant_key.strip():
                return {"status": "error", "error": "tenant_key cannot be empty"}

            comm_queue = AgentCommunicationQueue(self.db_manager)

            # Get unread messages for this job
            async with self.db_manager.get_session_async() as session:
                result = comm_queue.get_messages(
                    session=session, job_id=job_id, tenant_key=tenant_key, to_agent=agent_type, unread_only=True
                )

                if result.get("status") != "success":
                    return result

                messages = result.get("messages", [])
                has_updates = len(messages) > 0

                # Extract and categorize instructions
                instructions = []
                handoff_requested = False
                context_warning = False

                for msg in messages:
                    msg_type = msg.get("type")
                    content = msg.get("content")

                    if msg_type == "user_feedback":
                        instructions.append(f"USER FEEDBACK: {content}")
                    elif msg_type == "orchestrator_instruction":
                        instructions.append(f"ORCHESTRATOR: {content}")
                    elif msg_type == "handoff_request":
                        handoff_requested = True
                        instructions.append("HANDOFF REQUESTED: Prepare comprehensive summary and context handoff")
                    elif msg_type == "context_warning":
                        context_warning = True
                        instructions.append(f"CONTEXT WARNING: {content} - Plan completion or handoff")
                    elif msg_type == "error_recovery":
                        instructions.append(f"ERROR RECOVERY GUIDANCE: {content}")

                return {
                    "status": "success",
                    "has_updates": has_updates,
                    "instructions": instructions,
                    "handoff_requested": handoff_requested,
                    "context_warning": context_warning,
                    "message_count": len(messages),
                }

        except Exception as e:
            logger.exception(f"Failed to get next instruction: {e}")
            return {"status": "error", "error": str(e)}

    # Succession Tools (Handover 0080)

    async def create_successor_orchestrator(
        self, current_job_id: str, tenant_key: str, reason: str = "context_limit"
    ) -> dict[str, Any]:
        """Create successor orchestrator for context handover (Handover 0080)"""
        try:
            from giljo_mcp.models import MCPAgentJob
            from giljo_mcp.orchestrator_succession import OrchestratorSuccessionManager

            async with self.db_manager.get_session_async() as session:
                # Retrieve current orchestrator job
                result = await session.execute(
                    select(MCPAgentJob).where(
                        MCPAgentJob.job_id == current_job_id, MCPAgentJob.tenant_key == tenant_key
                    )
                )
                orchestrator = result.scalar_one_or_none()

                if not orchestrator:
                    return {
                        "success": False,
                        "error": f"Orchestrator job {current_job_id} not found for tenant {tenant_key}",
                    }

                # Verify agent type is orchestrator
                if orchestrator.agent_type != "orchestrator":
                    return {
                        "success": False,
                        "error": f"Job {current_job_id} is not an orchestrator (type: {orchestrator.agent_type})",
                    }

                # Verify orchestrator is not already complete
                if orchestrator.status == "complete":
                    return {"success": False, "error": f"Orchestrator {current_job_id} is already complete"}

                # Initialize succession manager
                manager = OrchestratorSuccessionManager(session, tenant_key)

                # Create successor
                successor = manager.create_successor(orchestrator, reason=reason)

                # Generate handover summary
                handover_summary = manager.generate_handover_summary(orchestrator)

                # Complete handover
                manager.complete_handover(orchestrator, successor, handover_summary, reason)

                # Commit changes
                await session.commit()

                # Refresh objects
                await session.refresh(orchestrator)
                await session.refresh(successor)

                logger.info(
                    f"Succession completed: {orchestrator.job_id} → {successor.job_id}, "
                    f"instance {orchestrator.instance_number} → {successor.instance_number}, "
                    f"reason: {reason}"
                )

                return {
                    "success": True,
                    "successor_id": successor.job_id,
                    "instance_number": successor.instance_number,
                    "status": successor.status,
                    "handover_summary": handover_summary,
                    "message": (
                        f"Successor orchestrator created (instance {successor.instance_number}). "
                        f"Original orchestrator marked complete. "
                        f"Launch successor manually from dashboard."
                    ),
                }

        except Exception as e:
            logger.exception(f"Failed to create successor orchestrator: {e}")
            return {"success": False, "error": str(e)}

    async def check_succession_status(self, job_id: str, tenant_key: str) -> dict[str, Any]:
        """Check if orchestrator should trigger succession (Handover 0080)"""
        try:
            from giljo_mcp.models import MCPAgentJob

            async with self.db_manager.get_session_async() as session:
                # Retrieve orchestrator job
                result = await session.execute(
                    select(MCPAgentJob).where(MCPAgentJob.job_id == job_id, MCPAgentJob.tenant_key == tenant_key)
                )
                orchestrator = result.scalar_one_or_none()

                if not orchestrator:
                    return {"should_trigger": False, "error": f"Job {job_id} not found"}

                # Calculate context usage percentage
                context_used = orchestrator.context_used or 0
                context_budget = orchestrator.context_budget or 200000
                usage_percentage = (context_used / context_budget) * 100 if context_budget > 0 else 0

                # Determine if succession should be triggered (90% threshold)
                should_trigger = usage_percentage >= 90.0

                recommendation = ""
                if usage_percentage < 70:
                    recommendation = "Context usage healthy. Continue normal operation."
                elif usage_percentage < 85:
                    recommendation = "Monitor context usage. Begin planning for potential succession."
                elif usage_percentage < 90:
                    recommendation = "Context usage high. Prepare for succession soon."
                else:
                    recommendation = "Trigger succession now to avoid context overflow."

                return {
                    "should_trigger": should_trigger,
                    "context_used": context_used,
                    "context_budget": context_budget,
                    "usage_percentage": round(usage_percentage, 2),
                    "threshold_reached": should_trigger,
                    "recommendation": recommendation,
                }

        except Exception as e:
            logger.exception(f"Failed to check succession status: {e}")
            return {"should_trigger": False, "error": str(e)}

    # Slash Command Setup Tool (Handover 0093)

    async def setup_slash_commands(
        self, platform: str = None, _api_key: str = None, _server_url: str = None
    ) -> dict[str, Any]:
        """
        Generate one-time download link for slash commands installation.

        Returns download URL instead of executing file operations on server.
        Client downloads and extracts files locally for proper installation.

        Args:
            platform: Optional platform hint (ignored, kept for compatibility)
            _api_key: API key for HTTP authentication (injected by MCP HTTP handler)
            _server_url: Server URL from HTTP request (injected by MCP HTTP handler)

        Returns:
            dict with success, download_url, message, expires_minutes, one_time_use, error (optional)
        """
        try:
            from giljo_mcp.config_manager import get_config
            from giljo_mcp.downloads.token_manager import TokenManager
            from giljo_mcp.file_staging import FileStaging

            # 1. Verify API key (injected by MCP HTTP handler)
            if not _api_key:
                return {
                    "success": False,
                    "error": "API key not provided",
                    "instructions": [
                        "This tool is called via MCP HTTP and requires authentication",
                        "Ensure you are connected to GiljoAI MCP server with valid API key",
                    ],
                }

            # 2. Get tenant context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            # 3. Generate token FIRST and stage with SAME token (single-token flow)
            async with self.db_manager.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                download_token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type="slash_commands",
                    filename="slash_commands.zip",
                )
                file_staging = FileStaging()
                staging_path = await file_staging.create_staging_directory(tenant_key, download_token)
                zip_path, message = await file_staging.stage_slash_commands(staging_path)
                if not zip_path:
                    await token_manager.mark_failed(download_token, message)
                    await file_staging.cleanup(tenant_key, download_token)
                    logger.error(f"Staging failed for token {download_token}: {message}")
                    return {"success": False, "error": f"File staging failed: {message}"}
                await token_manager.mark_ready(download_token)
                logger.info(f"Staged slash commands ZIP for token {download_token}: {zip_path}")

            # 5. Build download URL (use dynamically detected server URL)
            if not _server_url:
                config = get_config()

                # Read external_host from config.yaml for public IP
                config_path = Path.cwd() / "config.yaml"
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)

                host = config_data.get("services", {}).get("external_host", "localhost")
                _server_url = f"http://{host}:{config.server.api_port}"
                logger.warning(f"Server URL not provided, using fallback: {_server_url}")

            download_url = f"{_server_url}/api/download/temp/{download_token}/slash_commands.zip"

            # 6. Return natural language instructions for AI agents
            return {
                "success": True,
                "instructions": f"Download the slash commands from {download_url}, extract the zip file, and install the contents to your ~/.claude/commands/ folder (create the folder if it doesn't exist). The download link expires in 15 minutes but can be used multiple times within that window.",
                "download_url": download_url,
                "expires_minutes": 15,
                "unlimited_downloads": True,
                "technical_details": {
                    "filename": "slash_commands.zip",
                    "install_location": "~/.claude/commands/",
                    "windows_location": "%USERPROFILE%\\.claude\\commands\\",
                },
            }

        except Exception as e:
            logger.exception(f"Failed to generate slash commands download: {e}")
            return {"success": False, "error": str(e)}

    # Slash Command Handler Wrappers (Handover 0084b)

    async def gil_import_productagents(
        self, project_id: str = None, _api_key: str = None, _server_url: str = None
    ) -> dict[str, Any]:
        """
        Generate one-time download link for product agent templates.

        Returns download URL instead of executing file operations on server.
        Client downloads and extracts files locally to .claude/agents directory.

        Args:
            project_id: Optional project ID
            _api_key: API key for HTTP authentication (injected by MCP HTTP handler)
            _server_url: Server URL from HTTP request (injected by MCP HTTP handler)

        Returns:
            dict with success, download_url, message, expires_minutes, one_time_use, error (optional)
        """
        try:
            from giljo_mcp.config_manager import get_config
            from giljo_mcp.downloads.token_manager import TokenManager
            from giljo_mcp.file_staging import FileStaging

            # 1. Verify API key (injected by MCP HTTP handler)
            if not _api_key:
                return {
                    "success": False,
                    "error": "API key not provided",
                    "instructions": [
                        "This tool is called via MCP HTTP and requires authentication",
                        "Ensure you are connected to GiljoAI MCP server with valid API key",
                    ],
                }

            # 2. Get tenant context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            # 3. Generate token FIRST and stage with SAME token
            async with self.db_manager.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type="agent_templates",
                    filename="agent_templates.zip",
                )

            # 4. Stage files in temp directory
            file_staging = FileStaging(db_session=None)
            async with self.db_manager.get_session_async() as session:
                file_staging.db_session = session
                staging_path = await file_staging.create_staging_directory(tenant_key, token)
                zip_path, message = await file_staging.stage_agent_templates(
                    staging_path, tenant_key, db_session=session
                )

                if not zip_path:
                    await token_manager.mark_failed(token, message)
                    await file_staging.cleanup(tenant_key, token)
                    return {"success": False, "error": f"File staging failed: {message}"}

                await token_manager.mark_ready(token)

            logger.info(f"Staged agent templates ZIP for product download: {zip_path}")

            # 5. Build download URL (use dynamically detected server URL)
            if not _server_url:
                config = get_config()

                # Read external_host from config.yaml for public IP
                config_path = Path.cwd() / "config.yaml"
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)

                host = config_data.get("services", {}).get("external_host", "localhost")
                _server_url = f"http://{host}:{config.server.api_port}"
                logger.warning(f"Server URL not provided, using fallback: {_server_url}")

            download_url = f"{_server_url}/api/download/temp/{token}/agent_templates.zip"

            return {
                "success": True,
                "download_url": download_url,
                "message": "Download and extract to .claude/agents/ in your project directory",
                "expires_minutes": 15,
                "one_time_use": True,
                "instructions": [
                    f'1. Download: curl -H "X-API-Key: $GILJO_API_KEY" "{download_url}" -o templates.zip',
                    '2. Extract: unzip -o templates.zip -d .claude/agents/ (Linux/macOS) or 7z x templates.zip -o".\\claude\\agents\\" (Windows)',
                    "Templates will be available in your project's .claude/agents directory",
                ],
            }

        except Exception as e:
            logger.exception(f"Failed to generate product agent templates download: {e}")
            return {"success": False, "error": str(e)}

    async def gil_import_personalagents(
        self, project_id: str = None, _api_key: str = None, _server_url: str = None
    ) -> dict[str, Any]:
        """
        Generate one-time download link for personal agent templates.

        Returns download URL instead of executing file operations on server.
        Client downloads and extracts files locally to ~/.claude/agents directory.

        Args:
            project_id: Optional project ID (not used for personal agents)
            _api_key: API key for HTTP authentication (injected by MCP HTTP handler)
            _server_url: Server URL from HTTP request (injected by MCP HTTP handler)

        Returns:
            dict with success, download_url, message, expires_minutes, one_time_use, error (optional)
        """
        try:
            from giljo_mcp.config_manager import get_config
            from giljo_mcp.downloads.token_manager import TokenManager
            from giljo_mcp.file_staging import FileStaging

            # 1. Verify API key (injected by MCP HTTP handler)
            if not _api_key:
                return {
                    "success": False,
                    "error": "API key not provided",
                    "instructions": [
                        "This tool is called via MCP HTTP and requires authentication",
                        "Ensure you are connected to GiljoAI MCP server with valid API key",
                    ],
                }

            # 2. Get tenant context
            tenant_key = self.tenant_manager.get_current_tenant()
            if not tenant_key:
                return {"success": False, "error": "No active tenant"}

            # 3. Generate token FIRST and stage with SAME token
            async with self.db_manager.get_session_async() as session:
                token_manager = TokenManager(db_session=session)
                token = await token_manager.generate_token(
                    tenant_key=tenant_key,
                    download_type="agent_templates",
                    filename="agent_templates.zip",
                )

            # 4. Stage files in temp directory
            file_staging = FileStaging(db_session=None)
            async with self.db_manager.get_session_async() as session:
                file_staging.db_session = session
                staging_path = await file_staging.create_staging_directory(tenant_key, token)
                zip_path, message = await file_staging.stage_agent_templates(
                    staging_path, tenant_key, db_session=session
                )

                if not zip_path:
                    await token_manager.mark_failed(token, message)
                    await file_staging.cleanup(tenant_key, token)
                    return {"success": False, "error": f"File staging failed: {message}"}

                await token_manager.mark_ready(token)

            logger.info(f"Staged agent templates ZIP for personal download: {zip_path}")

            # 5. Build download URL (use dynamically detected server URL)
            if not _server_url:
                config = get_config()

                # Read external_host from config.yaml for public IP
                config_path = Path.cwd() / "config.yaml"
                with open(config_path) as f:
                    config_data = yaml.safe_load(f)

                host = config_data.get("services", {}).get("external_host", "localhost")
                _server_url = f"http://{host}:{config.server.api_port}"
                logger.warning(f"Server URL not provided, using fallback: {_server_url}")

            download_url = f"{_server_url}/api/download/temp/{token}/agent_templates.zip"

            return {
                "success": True,
                "download_url": download_url,
                "message": "Download and extract to ~/.claude/agents/ (or %USERPROFILE%\\.claude\\agents\\ on Windows)",
                "expires_minutes": 15,
                "one_time_use": True,
                "instructions": [
                    f'1. Download: curl -H "X-API-Key: $GILJO_API_KEY" "{download_url}" -o templates.zip',
                    '2. Extract: unzip -o templates.zip -d ~/.claude/agents/ (Linux/macOS) or 7z x templates.zip -o"%USERPROFILE%\\.claude\\agents\\" (Windows)',
                    "Templates will be available across all your projects",
                ],
            }

        except Exception as e:
            logger.exception(f"Failed to generate personal agent templates download: {e}")
            return {"success": False, "error": str(e)}

    async def gil_handover(self, current_job_id: str = None, reason: str = "manual") -> dict[str, Any]:
        """
        Trigger orchestrator succession for context handover

        Wrapper for slash command handler that executes via MCP tool call.

        Args:
            current_job_id: Current orchestrator job UUID
            reason: Succession reason (context_limit, manual, phase_transition)

        Returns:
            dict with success, message, successor_id, launch_prompt, error (optional)
        """
        try:
            from ..slash_commands import get_slash_command

            handler = get_slash_command("gil_handover")
            if not handler:
                return {"success": False, "message": "Slash command handler not found", "error": "HANDLER_NOT_FOUND"}

            # Get database session (synchronous context manager)
            with self.db_manager.get_session() as session:
                result = await handler(
                    db_session=session,
                    tenant_key=self.tenant_manager.get_current_tenant(),
                    project_id=None,  # Not used by handover
                    job_id=current_job_id,
                    reason=reason,
                )

            return result

        except Exception as e:
            logger.exception(f"Failed to trigger handover: {e}")
            return {"success": False, "message": f"Failed to trigger handover: {e!s}", "error": "UNEXPECTED_ERROR"}
