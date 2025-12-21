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
from giljo_mcp.models import Project, Session
from giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from giljo_mcp.tenant import TenantManager, current_tenant


logger = logging.getLogger(__name__)


# Module-level variables for test injection (Handover 0366c)
_db_manager_instance: Optional[DatabaseManager] = None
_test_session: Optional[Any] = None


def init_for_testing(db_manager: DatabaseManager, db_session) -> None:
    """
    Initialize module for testing with shared session (Handover 0366c).

    This allows project tools to use the same database session as test fixtures,
    preventing session isolation issues during testing.

    Args:
        db_manager: DatabaseManager instance for tests
        db_session: Shared AsyncSession for test transaction isolation

    Usage:
        @pytest_asyncio.fixture(scope="function", autouse=True)
        async def setup_project_tools(db_manager, db_session):
            from src.giljo_mcp.tools import project
            project.init_for_testing(db_manager, db_session)
            yield
    """
    global _db_manager_instance, _test_session
    _db_manager_instance = db_manager
    _test_session = db_session


class _SessionWrapper:
    """
    Wrapper for database session that intercepts commit() in test mode.

    In tests: Converts commit() to flush() for transaction isolation
    In production: Passes through to real session
    """

    def __init__(self, session, test_mode=False):
        self._session = session
        self._test_mode = test_mode

    async def commit(self):
        """Commit in production, flush in tests."""
        if self._test_mode:
            await self._session.flush()
            # Don't expire all - let SQLAlchemy's session manage object state
            # Objects will be refreshed when accessed if needed
        else:
            await self._session.commit()

    async def flush(self):
        """Always flush."""
        await self._session.flush()

    async def refresh(self, *args, **kwargs):
        """Delegate to session."""
        return await self._session.refresh(*args, **kwargs)

    def add(self, *args, **kwargs):
        """Delegate to session."""
        return self._session.add(*args, **kwargs)

    async def execute(self, *args, **kwargs):
        """Delegate to session."""
        return await self._session.execute(*args, **kwargs)

    def __getattr__(self, name):
        """Delegate all other attributes to the wrapped session."""
        return getattr(self._session, name)


class _SessionContext:
    """
    Context manager for database sessions that handles both test and production modes.

    In tests: Uses injected test session (no commit, uses flush)
    In production: Creates new session via db_manager (commits)
    """

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager
        self.test_mode = _test_session is not None
        self.session = None
        self.context_manager = None

    async def __aenter__(self):
        if self.test_mode:
            # Test mode - use injected session with wrapper
            self.session = _SessionWrapper(_test_session, test_mode=True)
        else:
            # Production mode - create new session
            self.context_manager = self.db_manager.get_session_async()
            real_session = await self.context_manager.__aenter__()
            self.session = _SessionWrapper(real_session, test_mode=False)
        return self.session

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if not self.test_mode and self.context_manager:
            # Production mode - let context manager handle cleanup
            return await self.context_manager.__aexit__(exc_type, exc_val, exc_tb)
        # Test mode - do nothing, test fixture handles cleanup
        return False


def register_project_tools(mcp: FastMCP, db_manager: DatabaseManager, tenant_manager: TenantManager):
    """Register project management tools with the MCP server"""

    @mcp.tool()
    async def create_project(
        name: str,
        mission: str,
        description: Optional[str] = None,
        product_id: Optional[str] = None,
        tenant_key: Optional[str] = None,
        auto_create_orchestrator_job: bool = False,
    ) -> dict[str, Any]:
        """
        Create a new project with mission

        Args:
            name: Project name
            mission: Project mission statement
            description: User-written project description (defaults to mission if not provided)
            product_id: Optional product ID to associate the project with
            tenant_key: Optional tenant key to use (generates new one if not provided)
            auto_create_orchestrator_job: If True, creates AgentJob and AgentExecution for orchestrator

        Returns:
            Project creation details including ID and tenant key.
            If auto_create_orchestrator_job=True, also includes job_id and agent_id.
        """
        try:
            async with _SessionContext(db_manager) as session:
                # Use provided tenant key or generate a new one
                if not tenant_key:
                    tenant_key = f"tk_{uuid4().hex}"

                # Use mission as description if not provided (for backward compatibility)
                if not description:
                    description = mission

                # Create project
                project = Project(
                    name=name,
                    description=description,
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

                # Create initial session (Session model doesn't have status field)
                initial_session = Session(
                    project_id=project.id,
                    tenant_key=tenant_key,
                    session_number=1,
                    title=f"Initial Session - {name}",
                    started_at=datetime.now(timezone.utc)
                )
                session.add(initial_session)

                result = {
                    "success": True,
                    "project_id": str(project.id),
                    "name": name,
                    "tenant_key": tenant_key,
                    "product_id": product_id,
                    "session_id": str(initial_session.id),
                }

                # Auto-create orchestrator job and execution if requested
                if auto_create_orchestrator_job:
                    # Create AgentJob
                    agent_job = AgentJob(
                        job_id=str(uuid4()),
                        tenant_key=tenant_key,
                        project_id=project.id,
                        mission=mission,
                        job_type="orchestrator",
                        status="active",
                        job_metadata={"auto_created": True},
                    )
                    session.add(agent_job)
                    await session.flush()

                    # Create AgentExecution
                    agent_execution = AgentExecution(
                        agent_id=str(uuid4()),
                        job_id=agent_job.job_id,
                        tenant_key=tenant_key,
                        agent_type="orchestrator",
                        instance_number=1,
                        status="waiting",
                        agent_name=f"{name} - Orchestrator #1",
                        context_used=0,
                        context_budget=150000,
                        tool_type="claude-code",
                    )
                    session.add(agent_execution)

                    # Add job and execution IDs to result
                    result["job_id"] = agent_job.job_id
                    result["agent_id"] = agent_execution.agent_id

                # Save project_id before commit (which expires objects in test mode)
                project_id_str = str(project.id)

                await session.commit()

                # Note: Not setting current tenant here since tenant may not exist in User table yet
                # Tenant context will be set when switching to this project via switch_project()

                logger.info(
                    f"Created project '{name}' with ID {project_id_str}"
                    + (f" under product {product_id}" if product_id else "")
                    + (f" with orchestrator job {result.get('job_id')}" if auto_create_orchestrator_job else "")
                )

                return result

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
            List of projects with details including execution-level aggregates
        """
        try:
            async with _SessionContext(db_manager) as session:
                query = select(Project)

                if status:
                    query = query.where(Project.status == status)

                result = await session.execute(query)
                projects = result.scalars().all()

                project_list = []
                for project in projects:
                    # Get job count (AgentJob records)
                    job_query = select(AgentJob).where(AgentJob.project_id == project.id)
                    job_result = await session.execute(job_query)
                    jobs = job_result.scalars().all()
                    job_count = len(jobs)

                    # Get execution count (AgentExecution records)
                    execution_count = 0
                    active_agents = 0
                    for job in jobs:
                        exec_query = select(AgentExecution).where(AgentExecution.job_id == job.job_id)
                        exec_result = await session.execute(exec_query)
                        executions = exec_result.scalars().all()
                        execution_count += len(executions)

                        # Count active agents (executions not completed/decommissioned)
                        for execution in executions:
                            if execution.status not in ["complete", "failed", "cancelled", "decommissioned"]:
                                active_agents += 1

                    project_list.append(
                        {
                            "id": str(project.id),
                            "name": project.name,
                            "status": project.status,
                            "tenant_key": project.tenant_key,
                            "job_count": job_count,
                            "execution_count": execution_count,
                            "active_agents": active_agents,
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
            async with _SessionContext(db_manager) as session:
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

                # Get the latest session or create new one if needed
                session_query = (
                    select(Session)
                    .where(Session.project_id == project.id)
                    .order_by(Session.session_number.desc())
                )
                session_result = await session.execute(session_query)
                latest_session = session_result.scalar_one_or_none()

                if not latest_session:
                    # Create first session
                    active_session = Session(
                        project_id=project.id,
                        tenant_key=project.tenant_key,
                        session_number=1,
                        title=f"Session 1 - {project.name}",
                        started_at=datetime.now(timezone.utc),
                    )
                    session.add(active_session)
                    await session.commit()
                else:
                    # Use latest session
                    active_session = latest_session

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
            async with _SessionContext(db_manager) as session:
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

                # Flush to persist project changes first
                await session.flush()

                # Save values for return (needed before commit in test mode)
                project_id_str = str(project.id)
                project_name = project.name
                project_completed_at = project.completed_at

                # Close all sessions without ended_at timestamp
                session_update = (
                    update(Session)
                    .where(Session.project_id == project.id, Session.ended_at.is_(None))
                    .values(ended_at=datetime.now(timezone.utc))
                )
                await session.execute(session_update)

                # Update all AgentJob records to completed
                job_update = (
                    update(AgentJob)
                    .where(
                        AgentJob.project_id == project.id,
                        AgentJob.status == "active",
                    )
                    .values(status="completed", completed_at=datetime.now(timezone.utc))
                    .execution_options(synchronize_session='fetch')
                )
                await session.execute(job_update)

                # Update all AgentExecution records to decommissioned
                # First, get all job IDs for this project
                job_query = select(AgentJob.job_id).where(AgentJob.project_id == project.id)
                job_result = await session.execute(job_query)
                job_ids = [row[0] for row in job_result.fetchall()]

                # Update all executions for these jobs
                if job_ids:
                    exec_update = (
                        update(AgentExecution)
                        .where(
                            AgentExecution.job_id.in_(job_ids),
                            AgentExecution.status.in_(["waiting", "working", "blocked"]),
                        )
                        .values(status="decommissioned", decommissioned_at=datetime.now(timezone.utc))
                        .execution_options(synchronize_session='fetch')
                    )
                    await session.execute(exec_update)

                await session.commit()

                logger.info(f"Closed project '{project_name}' (ID: {project_id_str})")

                return {
                    "success": True,
                    "project_id": project_id_str,
                    "name": project_name,
                    "summary": summary,
                    "closed_at": project_completed_at.isoformat(),
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
            Detailed project status including jobs and executions (nested structure)
        """
        try:
            async with _SessionContext(db_manager) as session:
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
                job_query = select(AgentJob).where(AgentJob.project_id == project.id)
                job_result = await session.execute(job_query)
                jobs = job_result.scalars().all()

                job_list = []
                total_execution_count = 0
                total_active_agents = 0

                for job in jobs:
                    # Get executions for this job
                    exec_query = select(AgentExecution).where(AgentExecution.job_id == job.job_id)
                    exec_result = await session.execute(exec_query)
                    executions = exec_result.scalars().all()

                    execution_list = []
                    for execution in executions:
                        execution_list.append(
                            {
                                "agent_id": str(execution.agent_id),
                                "instance_number": execution.instance_number,
                                "status": execution.status,
                                "agent_type": execution.agent_type,
                                "agent_name": execution.agent_name,
                                "progress": execution.progress,
                                "health_status": execution.health_status,
                                "context_used": execution.context_used,
                                "context_budget": execution.context_budget,
                                "started_at": (execution.started_at.isoformat() if execution.started_at else None),
                                "completed_at": (execution.completed_at.isoformat() if execution.completed_at else None),
                            }
                        )

                        total_execution_count += 1
                        if execution.status not in ["complete", "failed", "cancelled", "decommissioned"]:
                            total_active_agents += 1

                    job_list.append(
                        {
                            "job_id": str(job.job_id),
                            "job_type": job.job_type,
                            "status": job.status,
                            "mission": job.mission,
                            "created_at": (job.created_at.isoformat() if job.created_at else None),
                            "completed_at": (job.completed_at.isoformat() if job.completed_at else None),
                            "executions": execution_list,
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
                    "jobs": job_list,
                    "job_count": len(job_list),
                    "execution_count": total_execution_count,
                    "active_agents": total_active_agents,
                }

        except Exception as e:
            logger.exception(f"Failed to get project status: {e}")
            return {"success": False, "error": str(e)}

    logger.info("Project management tools registered")
