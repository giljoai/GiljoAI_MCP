"""
Project Management Tools for GiljoAI MCP
Handles project lifecycle: create, list, switch, close
"""

import logging
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from fastmcp import FastMCP
from sqlalchemy import select, update

from giljo_mcp.database import DatabaseManager
from giljo_mcp.models import MCPAgentJob, Project, Session
from giljo_mcp.tenant import TenantManager, current_tenant


logger = logging.getLogger(__name__)


def register_project_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register project management tools with the MCP server"""

    @mcp.tool()
    async def create_project(
        name: str,
        mission: str,
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Create a new project with mission

        Args:
            name: Project name
            mission: Project mission statement
            product_id: Optional product ID to associate the project with
            tenant_key: Optional tenant key to use (generates new one if not provided)

        Returns:
            Project creation details including ID and tenant key
        """
        try:
            async with db_manager.get_session_async() as session:
                # Use provided tenant key or generate a new one
                if not tenant_key:
                    tenant_key = f"tk_{uuid4().hex}"

                # Create project
                project = Project(
                    name=name,
                    mission=mission,
                    tenant_key=tenant_key,
                    product_id=product_id,
                    status="inactive",
                    context_budget=150000,
                    context_used=0,
                    created_at=datetime.now(timezone.utc),
                )

                session.add(project)
                await session.flush()

                # Create initial session
                initial_session = Session(project_id=project.id, started_at=datetime.now(timezone.utc), status="active")
                session.add(initial_session)

                await session.commit()

                # Set as current project in tenant manager
                tenant_manager.set_current_tenant(tenant_key)

                logger.info(
                    f"Created project '{name}' with ID {project.id}"
                    + (f" under product {product_id}" if product_id else "")
                )

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": name,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "session_id": str(initial_session.id),
                }

        except Exception as e:
            logger.exception(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def list_projects(status: Optional[str] = None) -> dict[str, Any]:
        """
        List all projects with optional status filter

        Args:
            status: Optional status filter (active, completed, cancelled)

        Returns:
            List of projects with details
        """
        try:
            async with db_manager.get_session_async() as session:
                query = select(Project)

                if status:
                    query = query.where(Project.status == status)

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    # Get agent job count
                    agent_query = select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                    agent_result = await session.execute(agent_query)
                    agents = agent_result.scalars().all()

                    project_list.append(
                        {
                            "id": str(project.id),
                            "name": project.name,
                            "status": project.status,
                            "tenant_key": project.tenant_key,
                            "agent_count": len(agents),
                            "context_usage": f"{project.context_used}/{project.context_budget}",
                            "created_at": (project.created_at.isoformat() if project.created_at else None),
                        }
                    )

                return {
                    "success": True,
                    "count": len(project_list),
                    "projects": project_list,
                }

        except Exception as e:
            logger.exception(f"Failed to list projects: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def switch_project(project_id: str) -> dict[str, Any]:
        """
        Switch to a different project

        Args:
            project_id: UUID of the project to switch to

        Returns:
            Project details and activation status
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find project
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found",
                    }

                # Set tenant context
                tenant_manager.set_current_tenant(project.tenant_key)
                current_tenant.set(project.tenant_key)

                # Create new session if needed
                session_query = select(Session).where(Session.project_id == project.id, Session.status == "active")
                session_result = await session.execute(session_query)
                active_session = session_result.scalar_one_or_none()

                if not active_session:
                    active_session = Session(
                        project_id=project.id,
                        started_at=datetime.now(timezone.utc),
                        status="active",
                    )
                    session.add(active_session)
                    await session.commit()

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

    @mcp.tool()
    async def close_project(project_id: str, summary: str) -> dict[str, Any]:
        """
        Close a completed project with summary.

        Deprecated: use REST completion endpoints (`api/endpoints/projects/completion.py`)
        and the project closeout service for 360 memory updates. This MCP tool remains
        for backward compatibility only.

        Args:
            project_id: UUID of the project to close
            summary: Summary of project completion

        Returns:
            Closure confirmation
        """
        try:
            async with db_manager.get_session_async() as session:
                # Find project
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found",
                    }

                if project.status != "active":
                    return {
                        "success": False,
                        "error": f"Project is not active (status: {project.status})",
                    }

                # Update project status
                project.status = "completed"
                project.summary = summary
                project.completed_at = datetime.now(timezone.utc)

                # Close all active sessions
                session_update = (
                    update(Session)
                    .where(Session.project_id == project.id, Session.status == "active")
                    .values(status="completed", ended_at=datetime.now(timezone.utc))
                )
                await session.execute(session_update)

                # Decommission all agent jobs
                agent_update = (
                    update(MCPAgentJob)
                    .where(
                        MCPAgentJob.project_id == project.id,
                        MCPAgentJob.status.in_(["pending", "running", "waiting"]),
                    )
                    .values(status="decommissioned", decommissioned_at=datetime.now(timezone.utc))
                )
                await session.execute(agent_update)

                await session.commit()

                logger.info(f"Closed project '{project.name}' (ID: {project_id})")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": project.name,
                    "summary": summary,
                    "closed_at": project.completed_at.isoformat(),
                }

        except Exception as e:
            logger.exception(f"Failed to close project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def update_project_mission(project_id: str, mission: str, user_id: Optional[str] = None) -> dict[str, Any]:
        """
        PERSIST orchestrator-created mission plan to Project.mission field.

        PURPOSE: Save the OUTPUT of orchestrator's mission planning (PROJECT STAGING step).
        This is called AFTER the orchestrator has analyzed Project.description and created an execution plan.

        CRITICAL DISTINCTIONS:
        - Project.description = User-written requirements (INPUT - already exists, DO NOT MODIFY)
        - Project.mission = Orchestrator-generated plan (OUTPUT - THIS TOOL WRITES HERE)

        WHEN TO USE:
        - Called by orchestrator after creating mission plan (thin prompt Step 4)
        - The 'mission' parameter should be the orchestrator's GENERATED execution strategy
        - DO NOT pass user requirements here (those belong in Project.description)

        WHAT HAPPENS:
        - Updates Project.mission database field
        - Triggers WebSocket broadcast: 'project:mission_updated'
        - UI LaunchTab displays mission in "Orchestrator Created Mission" window

        Args:
            project_id: UUID of the project
            mission: Orchestrator-generated mission plan (YOUR OUTPUT after analysis)
            user_id: Optional user ID for field priority configuration (Handover 0086A Task 2.1)

        Returns:
            {
                'success': True,
                'message': 'Mission updated successfully',
                'project_id': 'uuid',
                'old_mission': '...',  # Previous mission (if any)
                'new_mission': '...'   # Your newly created mission
            }
        """
        try:
            # Log user_id propagation for debugging (Handover 0086A Task 2.1)
            logger.info(
                "update_project_mission called",
                extra={
                    "project_id": project_id,
                    "user_id": user_id,
                    "has_user_id": user_id is not None,
                },
            )

            async with db_manager.get_session_async() as session:
                # Find project
                query = select(Project).where(Project.id == project_id)
                result = await session.execute(query)
                project = result.scalar_one_or_none()

                if not project:
                    return {
                        "success": False,
                        "error": f"Project {project_id} not found",
                    }

                # Update mission
                old_mission = project.mission
                project.mission = mission

                await session.commit()

                # Broadcast WebSocket event via HTTP bridge (cross-process communication)
                logger.info(f"[WEBSOCKET DEBUG] About to broadcast mission_updated for project {project_id}")
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
                                    "project_id": str(project.id),
                                    "mission": mission,
                                    "user_config_applied": bool(user_id),
                                    "token_estimate": len(mission) // 4,
                                    "generated_by": "orchestrator",
                                    "timestamp": datetime.now(timezone.utc).isoformat(),
                                },
                            },
                            timeout=5.0,
                        )
                        logger.info(f"[WEBSOCKET DEBUG] HTTP bridge response: {response.status_code}")
                        logger.info(f"[WEBSOCKET] Broadcasted mission_updated for project {project_id} via HTTP bridge")
                except Exception as ws_error:
                    logger.error(f"[WEBSOCKET ERROR] Failed to broadcast mission_updated via HTTP bridge: {ws_error}", exc_info=True)

                logger.info(f"Updated mission for project '{project.name}'")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": project.name,
                    "old_mission": old_mission,
                    "new_mission": mission,
                }

        except Exception as e:
            logger.exception(f"Failed to update project mission: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def project_status(project_id: Optional[str] = None) -> dict[str, Any]:
        """
        Get comprehensive project status

        Args:
            project_id: Optional project ID, uses current if not specified

        Returns:
            Detailed project status including agents, tasks, and messages
        """
        try:
            async with db_manager.get_session_async() as session:
                # Get project ID from tenant context if not provided
                if not project_id:
                    tenant_key = tenant_manager.get_current_tenant()
                    if not tenant_key:
                        return {
                            "success": False,
                            "error": "No active project. Use switch_project first.",
                        }

                    # Find project by tenant key
                    query = select(Project).where(Project.tenant_key == tenant_key)
                    result = await session.execute(query)
                    project = result.scalar_one_or_none()
                else:
                    # Find project by ID
                    query = select(Project).where(Project.id == project_id)
                    result = await session.execute(query)
                    project = result.scalar_one_or_none()

                if not project:
                    return {"success": False, "error": "Project not found"}

                # Get agent jobs
                agent_query = select(MCPAgentJob).where(MCPAgentJob.project_id == project.id)
                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()

                agent_list = []
                for agent in agents:
                    agent_list.append(
                        {
                            "name": agent.agent_name,
                            "role": agent.agent_type,
                            "status": agent.status,
                            "context_used": 0,  # MCPAgentJob doesn't track context_used
                        }
                    )

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "description": project.description,
                        "mission": project.mission,
                        "status": project.status,
                        "tenant_key": project.tenant_key,
                        "context_usage": f"{project.context_used}/{project.context_budget}",
                        "created_at": (project.created_at.isoformat() if project.created_at else None),
                    },
                    "agents": agent_list,
                    "agent_count": len(agent_list),
                }

        except Exception as e:
            logger.exception(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Project management tools registered")
