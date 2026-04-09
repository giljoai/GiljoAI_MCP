# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProjectDeletionService - Extracted from ProjectService (Handover 0769).

Handles project deletion and purge operations:
- delete_project (soft delete)
- nuclear_delete_project (hard delete)
- purge_all_deleted_projects, purge_expired_deleted_projects
- restore_project
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.models.tasks import Message, Task
from src.giljo_mcp.schemas.service_responses import (
    NuclearDeleteResult,
    OperationResult,
    ProjectPurgeResult,
    SoftDeleteResult,
)
from src.giljo_mcp.tenant import TenantManager

logger = logging.getLogger(__name__)


class ProjectDeletionService:
    """Service for project deletion and purge operations."""

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
        websocket_manager: Any | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    async def delete_project(self, project_id: str) -> SoftDeleteResult:
        """
        Soft delete a project.

        Sets status='deleted' and deleted_at timestamp for the current tenant's project.
        Actual purge is handled separately by purge_expired_deleted_projects().

        Args:
            project_id: Project UUID

        Returns:
            Deletion result dictionary with deleted_at timestamp and cancelled_jobs count

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: Project not found or already deleted
        """
        # Get current tenant from context
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={"project_id": project_id})

        async with self._get_session() as session:
            stmt = select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                    Project.deleted_at.is_(None),
                )
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(
                    message="Project not found or already deleted",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

            now = datetime.now(timezone.utc)
            project.status = "deleted"
            project.deleted_at = now
            project.updated_at = now

            # Cascade soft delete to agent jobs - cancel all executions for this project (migrated to AgentExecution - Handover 0367a)
            executions_stmt = (
                select(AgentExecution)
                .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
                .where(
                    and_(
                        AgentJob.project_id == project_id,
                        AgentJob.tenant_key == tenant_key,
                        AgentExecution.status.notin_(["complete", "decommissioned"]),
                    )
                )
            )
            executions_result = await session.execute(executions_stmt)
            executions = executions_result.scalars().all()

            decommissioned_jobs_count = 0
            for execution in executions:
                execution.status = "decommissioned"
                execution.completed_at = now
                decommissioned_jobs_count += 1

            await session.commit()

            self._logger.info(
                f"Soft deleted project {project_id} for tenant {tenant_key} "
                f"at {project.deleted_at.isoformat() if project.deleted_at else 'unknown time'}. "
                f"Decommissioned {decommissioned_jobs_count} agent jobs."
            )

            return SoftDeleteResult(
                message="Project deleted successfully",
                deleted_at=project.deleted_at.isoformat() if project.deleted_at else None,
                decommissioned_jobs=decommissioned_jobs_count,
            )

    async def nuclear_delete_project(
        self, project_id: str, websocket_manager: Any | None = None
    ) -> NuclearDeleteResult:
        """
        Immediately and permanently delete a project and ALL related data (nuclear delete).

        This method performs complete cascade deletion of:
        - Agent jobs (AgentJob + AgentExecution)
        - Tasks
        - Messages
        - 360 memory entries (marked as deleted)
        - The project itself

        Special handling:
        - Deactivates project if it's currently active
        - Broadcasts WebSocket events for real-time UI cleanup
        - Ensures multi-tenant isolation (only deletes for current tenant)
        - Fully transactional (rollback on error)

        Args:
            project_id: Project UUID
            websocket_manager: Optional WebSocket manager for real-time updates

        Returns:
            Deletion details dictionary:
            - message: str
            - deleted_counts: dict with counts of each deleted entity type
            - project_name: str (name of deleted project)

        Raises:
            ValidationError: No tenant context available
            ResourceNotFoundError: Project not found or access denied

        Example:
            >>> result = await service.nuclear_delete_project("abc-123")
            >>> print(result["deleted_counts"])
            {"agents": 5, "tasks": 12, "messages": 48, ...}
        """
        # Get current tenant from context
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={"project_id": project_id})

        async with self._get_session() as session:
            # Fetch project with tenant validation
            stmt = select(Project).where(
                and_(
                    Project.id == project_id,
                    Project.tenant_key == tenant_key,
                )
            )
            result = await session.execute(stmt)
            project = result.scalar_one_or_none()

            if not project:
                raise ResourceNotFoundError(
                    message="Project not found or access denied",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

            project_name = project.name

            # Deactivate project if it's active (to avoid constraint issues)
            if project.status == "active":
                project.status = "inactive"
                project.updated_at = datetime.now(timezone.utc)
                await session.flush()  # Flush deactivation before deleting
                self._logger.info(f"Deactivated project {project_id} before nuclear delete")

            # Initialize deletion counters
            deleted_counts = {
                "agent_jobs": 0,
                "tasks": 0,
                "messages": 0,
            }

            # Delete agent jobs (migrated to AgentJob - Handover 0367a)
            # Note: AgentExecution records will cascade delete via FK relationship
            agent_job_stmt = select(AgentJob).where(
                and_(
                    AgentJob.project_id == project_id,
                    AgentJob.tenant_key == tenant_key,
                )
            )
            agent_jobs = (await session.execute(agent_job_stmt)).scalars().all()
            for job in agent_jobs:
                await session.delete(job)
            deleted_counts["agent_jobs"] = len(agent_jobs)

            # Delete tasks
            task_stmt = select(Task).where(
                and_(
                    Task.project_id == project_id,
                    Task.tenant_key == tenant_key,
                )
            )
            tasks = (await session.execute(task_stmt)).scalars().all()
            for task in tasks:
                await session.delete(task)
            deleted_counts["tasks"] = len(tasks)

            # Delete messages
            message_stmt = select(Message).where(
                and_(
                    Message.project_id == project_id,
                    Message.tenant_key == tenant_key,
                )
            )
            messages = (await session.execute(message_stmt)).scalars().all()
            for message in messages:
                await session.delete(message)
            deleted_counts["messages"] = len(messages)

            # Mark 360 memory entries as deleted by user (preserve historical reference)
            # Handover 0390b: Use repository instead of JSONB mutation
            memory_entries_marked = 0
            if project.product_id:
                from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

                repo = ProductMemoryRepository()
                memory_entries_marked = await repo.mark_entries_deleted(
                    session=session,
                    project_id=project_id,
                    tenant_key=tenant_key,
                )

                if memory_entries_marked > 0:
                    self._logger.info(
                        f"Marked {memory_entries_marked} 360 memory entries as deleted for project {project_id}"
                    )

            deleted_counts["memory_entries_marked"] = memory_entries_marked

            # Finally, delete the project itself
            await session.delete(project)

            # Commit transaction
            await session.commit()

            self._logger.info(
                f"Nuclear delete completed for project {project_id} ({project_name}): "
                f"{deleted_counts['agent_jobs']} agents, "
                f"{deleted_counts['tasks']} tasks, "
                f"{deleted_counts['messages']} messages, "
                f"{deleted_counts['memory_entries_marked']} 360 memory entries marked"
            )

            # Broadcast WebSocket event for real-time UI cleanup
            if websocket_manager:
                try:
                    await websocket_manager.broadcast_project_update(
                        project_id=project_id,
                        update_type="deleted",
                        project_data={
                            "name": project_name,
                            "deleted_counts": deleted_counts,
                        },
                    )
                except Exception as ws_error:  # noqa: BLE001 - WebSocket resilience: non-critical broadcast
                    self._logger.warning(f"WebSocket broadcast failed: {ws_error}")

            return NuclearDeleteResult(
                message=f"Project '{project_name}' permanently deleted",
                deleted_counts=deleted_counts,
                project_name=project_name,
            )

    async def _purge_project_records(self, session: AsyncSession, project: Project) -> dict[str, Any]:
        """Cascade delete a soft-deleted project and its child records."""
        project_info = {
            "id": project.id,
            "name": project.name,
            "tenant_key": project.tenant_key,
            "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
        }

        # Mark 360 memory entries as deleted by user (preserve historical reference)
        # Uses ProductMemoryRepository for table-based operations (Handover 0390c)
        if project.product_id:
            from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

            repo = ProductMemoryRepository()
            deleted_count = await repo.mark_entries_deleted(
                session=session,
                project_id=project.id,
                tenant_key=project.tenant_key,
            )
            if deleted_count > 0:
                self._logger.info(f"Marked {deleted_count} memory entries as deleted for project {project.id}")

        # TENANT ISOLATION: All cascade deletes filter by tenant_key
        tenant_key = project.tenant_key

        # Delete agent jobs (migrated to AgentJob - Handover 0367a)
        agent_job_stmt = select(AgentJob).where(
            and_(AgentJob.project_id == project.id, AgentJob.tenant_key == tenant_key)
        )
        agent_jobs = (await session.execute(agent_job_stmt)).scalars().all()
        for job in agent_jobs:
            await session.delete(job)

        task_stmt = select(Task).where(and_(Task.project_id == project.id, Task.tenant_key == tenant_key))
        tasks = (await session.execute(task_stmt)).scalars().all()
        for task in tasks:
            await session.delete(task)

        message_stmt = select(Message).where(and_(Message.project_id == project.id, Message.tenant_key == tenant_key))
        messages = (await session.execute(message_stmt)).scalars().all()
        for message in messages:
            await session.delete(message)

        await session.delete(project)
        return project_info

    async def purge_all_deleted_projects(self) -> ProjectPurgeResult:
        """
        Nuclear delete all soft-deleted projects for the current tenant.

        Uses nuclear_delete_project for each project to ensure complete removal.
        Called when user clicks "Delete All" button in deleted projects modal.

        Returns:
            Purge result dictionary with purged_count and project details list

        Raises:
            ValidationError: No tenant context available
        """
        tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            raise ValidationError(message="No tenant context available", context={})

        async with self._get_session() as session:
            stmt = select(Project).where(
                and_(Project.tenant_key == tenant_key, Project.status == "deleted", Project.deleted_at.isnot(None))
            )
            result = await session.execute(stmt)
            deleted_projects = result.scalars().all()

            if not deleted_projects:
                return ProjectPurgeResult(purged_count=0, projects=[])

        # Use nuclear delete for each project
        purged_projects = []
        for project in deleted_projects:
            try:
                await self.nuclear_delete_project(project.id)
                purged_projects.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "tenant_key": project.tenant_key,
                        "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                    }
                )
            except Exception:  # noqa: PERF203 - Nuclear delete resilience: continue on failures
                self._logger.exception("Failed to nuclear delete project {project.id}")

        self._logger.info(
            "[Nuclear Purge] Permanently deleted %s project(s) for tenant %s",
            len(purged_projects),
            tenant_key,
        )

        return ProjectPurgeResult(purged_count=len(purged_projects), projects=purged_projects)

    async def purge_expired_deleted_projects(self, days_before_purge: int = 10) -> ProjectPurgeResult:
        """
        Nuclear delete projects deleted more than specified days ago.

        Uses nuclear_delete_project to ensure complete removal of expired projects.
        This function performs COMPLETE cascade deletion:
        1. Deactivates if active
        2. Deletes ALL child agents (AgentJob + AgentExecution)
        3. Deletes ALL tasks
        4. Deletes ALL messages
        5. Deletes ALL context indexes
        6. Deletes ALL large document indexes
        7. Deletes ALL sessions
        8. Deletes ALL vision documents
        9. Deletes the project record

        Called from startup.py on server start for automatic cleanup.

        Args:
            days_before_purge: Number of days before permanent deletion (default: 10)

        Returns:
            ProjectPurgeResult: Pydantic model with:
                - purged_count: int - Number of projects purged
                - projects: list[dict] - Details of purged projects

        Raises:
            BaseGiljoError: Database not available

        Example:
            >>> result = await service.purge_expired_deleted_projects()
            >>> print(f"Nuclear purged {result.purged_count} expired projects")
        """
        from datetime import timedelta, timezone

        if not self.db_manager:
            self._logger.error("[Nuclear Purge] Cannot purge - database manager not available")
            raise BaseGiljoError(message="Database not available", context={})

        async with self._get_session() as session:
            # Find projects deleted more than specified days ago
            cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_before_purge)

            stmt = select(Project).where(
                Project.deleted_at.isnot(None),
                Project.status == "deleted",
                Project.deleted_at < cutoff_date,
            )

            result = await session.execute(stmt)
            expired_projects = result.scalars().all()

            if not expired_projects:
                self._logger.info(
                    f"[Nuclear Purge] No expired deleted projects to purge (cutoff: {days_before_purge} days)"
                )
                return ProjectPurgeResult(purged_count=0, projects=[])

        # Use nuclear delete for each expired project
        purged_projects = []
        for project in expired_projects:
            try:
                await self.nuclear_delete_project(project.id)
                purged_projects.append(
                    {
                        "id": project.id,
                        "name": project.name,
                        "tenant_key": project.tenant_key,
                        "deleted_at": project.deleted_at.isoformat() if project.deleted_at else None,
                    }
                )
                self._logger.info(
                    f"[Nuclear Purge] Auto-purged expired project {project.id} "
                    f"(deleted {(datetime.now(timezone.utc) - project.deleted_at).days} days ago)"
                )
            except Exception:  # noqa: PERF203 - Nuclear delete resilience: continue on failures
                self._logger.exception("Failed to nuclear delete expired project {project.id}")

        self._logger.info(f"[Nuclear Purge] Successfully purged {len(purged_projects)} expired deleted projects")

        return ProjectPurgeResult(purged_count=len(purged_projects), projects=purged_projects)

    async def restore_project(self, project_id: str, tenant_key: str) -> OperationResult:
        """
        Restore a completed, cancelled, or soft-deleted project to inactive status.

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for multi-tenant isolation

        Returns:
            Success message dictionary

        Raises:
            ResourceNotFoundError: Project not found or access denied

        Example:
            >>> result = await service.restore_project("abc-123", "tenant-key-456")
        """
        async with self._get_session() as session:
            # TENANT ISOLATION: Filter by both project_id AND tenant_key
            result = await session.execute(
                update(Project)
                .where(and_(Project.id == project_id, Project.tenant_key == tenant_key))
                .values(
                    status="inactive",
                    completed_at=None,
                    deleted_at=None,
                    updated_at=datetime.now(timezone.utc),
                )
            )

            if result.rowcount == 0:
                raise ResourceNotFoundError(
                    message="Project not found or access denied",
                    context={"project_id": project_id, "tenant_key": tenant_key},
                )

            await session.commit()

            self._logger.info(f"Restored project {project_id}")

            return OperationResult(
                message=f"Project {project_id} restored successfully",
            )
