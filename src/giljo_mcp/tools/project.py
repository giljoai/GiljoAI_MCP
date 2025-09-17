"""
Project Management Tools for GiljoAI MCP
Handles project lifecycle: create, list, switch, close
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional
from uuid import uuid4

from fastmcp import FastMCP
from sqlalchemy import select, update

from ..database import DatabaseManager
from ..tenant import TenantManager, current_tenant
from ..models import Project, Agent, Session

logger = logging.getLogger(__name__)


def register_project_tools(
    mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager
):
    """Register project management tools with the MCP server"""

    @mcp.tool()
    async def create_project(
        name: str, mission: str, agents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new project with mission and optional agent sequence

        Args:
            name: Project name
            mission: Project mission statement
            agents: Optional list of agent names to initialize

        Returns:
            Project creation details including ID and tenant key
        """
        try:
            async with db_manager.get_session() as session:
                # Generate unique tenant key
                tenant_key = f"tk_{uuid4().hex[:12]}"

                # Create project
                project = Project(
                    name=name,
                    mission=mission,
                    tenant_key=tenant_key,
                    status="active",
                    context_budget=150000,
                    context_used=0,
                    created_at=datetime.utcnow(),
                )

                session.add(project)
                await session.flush()

                # Create initial session
                initial_session = Session(
                    project_id=project.id, started_at=datetime.utcnow(), status="active"
                )
                session.add(initial_session)

                # Create agents if specified
                if agents:
                    for agent_name in agents:
                        agent = Agent(
                            project_id=project.id,
                            name=agent_name,
                            role=agent_name,
                            status="pending",
                            created_at=datetime.utcnow(),
                        )
                        session.add(agent)

                await session.commit()

                # Set as current project in tenant manager
                tenant_manager.set_current_tenant(tenant_key)

                logger.info(f"Created project '{name}' with ID {project.id}")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": name,
                    "tenant_key": tenant_key,
                    "agents_created": agents or [],
                    "session_id": str(initial_session.id),
                }

        except Exception as e:
            logger.error(f"Failed to create project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def list_projects(status: Optional[str] = None) -> Dict[str, Any]:
        """
        List all projects with optional status filter

        Args:
            status: Optional status filter (active, completed, cancelled)

        Returns:
            List of projects with details
        """
        try:
            async with db_manager.get_session() as session:
                query = select(Project)

                if status:
                    query = query.where(Project.status == status)

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    # Get agent count
                    agent_query = select(Agent).where(Agent.project_id == project.id)
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
                            "created_at": (
                                project.created_at.isoformat()
                                if project.created_at
                                else None
                            ),
                        }
                    )

                return {
                    "success": True,
                    "count": len(project_list),
                    "projects": project_list,
                }

        except Exception as e:
            logger.error(f"Failed to list projects: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def switch_project(project_id: str) -> Dict[str, Any]:
        """
        Switch to a different project

        Args:
            project_id: UUID of the project to switch to

        Returns:
            Project details and activation status
        """
        try:
            async with db_manager.get_session() as session:
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
                session_query = select(Session).where(
                    Session.project_id == project.id, Session.status == "active"
                )
                session_result = await session.execute(session_query)
                active_session = session_result.scalar_one_or_none()

                if not active_session:
                    active_session = Session(
                        project_id=project.id,
                        started_at=datetime.utcnow(),
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
            logger.error(f"Failed to switch project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def close_project(project_id: str, summary: str) -> Dict[str, Any]:
        """
        Close a completed project with summary

        Args:
            project_id: UUID of the project to close
            summary: Summary of project completion

        Returns:
            Closure confirmation
        """
        try:
            async with db_manager.get_session() as session:
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
                project.completed_at = datetime.utcnow()

                # Close all active sessions
                session_update = (
                    update(Session)
                    .where(Session.project_id == project.id, Session.status == "active")
                    .values(status="completed", ended_at=datetime.utcnow())
                )
                await session.execute(session_update)

                # Decommission all agents
                agent_update = (
                    update(Agent)
                    .where(
                        Agent.project_id == project.id,
                        Agent.status.in_(["active", "idle"]),
                    )
                    .values(status="decommissioned")
                )
                await session.execute(agent_update)

                await session.commit()

                # Trigger auto-commit if git is configured
                try:
                    from .git import commit_changes
                    from ..config_manager import get_config

                    config = get_config()
                    if hasattr(config, "git") and getattr(
                        config.git, "auto_commit_on_completion", True
                    ):
                        # Get product_id from config or use project's tenant_key as fallback
                        product_id = getattr(config, "product_id", project.tenant_key)

                        # Try to auto-commit with project summary
                        repo_path = getattr(config, "root_path", str(Path.cwd()))
                        commit_message = f"""feat: complete project {project.name}

{summary}

🤖 Generated with [Claude Code](https://claude.ai/code)
Project: {project.name}

Co-Authored-By: Claude <noreply@anthropic.com>"""

                        # Use the current tenant context for git operations
                        current_tenant.set(project.tenant_key)

                        auto_commit_result = await commit_changes(
                            product_id=product_id,
                            repo_path=repo_path,
                            message=commit_message,
                            project_id=project.id,
                            commit_type="project_completion",
                        )

                        if auto_commit_result.get("success"):
                            logger.info(
                                f"Auto-commit successful for project completion: {auto_commit_result.get('commit_hash')}"
                            )
                        else:
                            logger.warning(
                                f"Auto-commit failed for project completion: {auto_commit_result.get('error')}"
                            )

                except Exception as e:
                    # Don't fail project closure if git commit fails
                    logger.warning(f"Auto-commit failed for project completion: {e}")

                logger.info(f"Closed project '{project.name}' (ID: {project_id})")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": project.name,
                    "summary": summary,
                    "closed_at": project.completed_at.isoformat(),
                }

        except Exception as e:
            logger.error(f"Failed to close project: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def update_project_mission(project_id: str, mission: str) -> Dict[str, Any]:
        """
        Update the mission field after orchestrator analysis

        Args:
            project_id: UUID of the project
            mission: Updated mission statement

        Returns:
            Update confirmation
        """
        try:
            async with db_manager.get_session() as session:
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

                logger.info(f"Updated mission for project '{project.name}'")

                return {
                    "success": True,
                    "project_id": str(project.id),
                    "name": project.name,
                    "old_mission": old_mission,
                    "new_mission": mission,
                }

        except Exception as e:
            logger.error(f"Failed to update project mission: {e}")
            return {"success": False, "error": str(e)}

    @mcp.tool()
    async def project_status(project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get comprehensive project status

        Args:
            project_id: Optional project ID, uses current if not specified

        Returns:
            Detailed project status including agents, tasks, and messages
        """
        try:
            async with db_manager.get_session() as session:
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

                # Get agents
                agent_query = select(Agent).where(Agent.project_id == project.id)
                agent_result = await session.execute(agent_query)
                agents = agent_result.scalars().all()

                agent_list = []
                for agent in agents:
                    agent_list.append(
                        {
                            "name": agent.name,
                            "role": agent.role,
                            "status": agent.status,
                            "context_used": agent.context_used,
                        }
                    )

                return {
                    "success": True,
                    "project": {
                        "id": str(project.id),
                        "name": project.name,
                        "mission": project.mission,
                        "status": project.status,
                        "tenant_key": project.tenant_key,
                        "context_usage": f"{project.context_used}/{project.context_budget}",
                        "created_at": (
                            project.created_at.isoformat()
                            if project.created_at
                            else None
                        ),
                    },
                    "agents": agent_list,
                    "agent_count": len(agent_list),
                }

        except Exception as e:
            logger.error(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Project management tools registered")
