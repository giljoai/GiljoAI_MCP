# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
OrchestrationService - Facade for orchestration and job management.

Handover 0769: Facade delegating to sub-services.
Handover 0950j: Agent state methods extracted to OrchestrationAgentStateService.
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    DatabaseError,
    ValidationError,
)
from giljo_mcp.mission_planner import MissionPlanner
from giljo_mcp.repositories.agent_operations_repository import AgentOperationsRepository
from giljo_mcp.schemas.service_responses import (
    CompleteJobResult,
    JobListResult,
    MissionResponse,
    MissionUpdateResult,
    PendingJobsResult,
    ProgressResult,
    SpawnResult,
    WorkflowStatus,
)
from giljo_mcp.services.job_lifecycle_service import JobLifecycleService
from giljo_mcp.services.mission_service import MissionService
from giljo_mcp.services.orchestration_agent_state_service import OrchestrationAgentStateService
from giljo_mcp.services.progress_service import ProgressService
from giljo_mcp.tenant import TenantManager


if TYPE_CHECKING:
    from giljo_mcp.services.message_service import MessageService


logger = logging.getLogger(__name__)


class OrchestrationService:
    """Facade for orchestration and agent jobs (Handover 0769).

    Delegates to JobLifecycleService, MissionService, ProgressService.
    Retains: workflow status, pending jobs, listing, completion, error, reactivation.
    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: Optional[AsyncSession] = None,
        message_service: Optional["MessageService"] = None,
        websocket_manager: Optional[Any] = None,
    ):
        """
        Initialize OrchestrationService with database and tenant management.

        Args:
            db_manager: Database manager for async database operations
            tenant_manager: Tenant manager for multi-tenancy support
            test_session: Optional AsyncSession for tests to share the same transaction
            message_service: Optional MessageService for WebSocket-enabled messaging
        """
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._message_service = message_service
        self._websocket_manager = websocket_manager or getattr(message_service, "_websocket_manager", None)
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        # Handover 0406: Track todo_items warning timestamps (throttle 1 per 5 min per job)
        self._todo_warning_timestamps: dict[str, datetime] = {}

        # Handover 0450: Initialize orchestration components (from orchestrator.py)
        # Initialize lazily to avoid initialization errors in tests with mocked dependencies
        self._mission_planner = None
        self._template_generator = None

        # Handover 0769: Facade sub-services
        self._job_lifecycle = JobLifecycleService(
            db_manager, tenant_manager, test_session, message_service, websocket_manager
        )
        self._mission = MissionService(db_manager, tenant_manager, test_session, message_service, websocket_manager)
        self._progress = ProgressService(db_manager, tenant_manager, test_session, message_service, websocket_manager)
        # Handover 0950j: Agent state management (reactivate, dismiss, set_agent_status)
        self._agent_state = OrchestrationAgentStateService(
            db_manager, tenant_manager, test_session, message_service, websocket_manager
        )

        # Sprint 002e: Extracted sub-services
        from giljo_mcp.services.job_completion_service import JobCompletionService
        from giljo_mcp.services.job_query_service import JobQueryService
        from giljo_mcp.services.workflow_status_service import WorkflowStatusService

        self._workflow_status = WorkflowStatusService(db_manager, tenant_manager, test_session)
        self._job_completion = JobCompletionService(
            db_manager, tenant_manager, test_session, message_service, websocket_manager, self._agent_state
        )
        self._job_query = JobQueryService(db_manager, tenant_manager, test_session)

    @property
    def mission_planner(self):
        """Lazy initialization of MissionPlanner."""
        if self._mission_planner is None:
            self._mission_planner = MissionPlanner(self.db_manager)
        return self._mission_planner

    @mission_planner.setter
    def mission_planner(self, value):
        """Allow setting mission_planner for tests."""
        self._mission_planner = value

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

    def _can_warn_missing_todos(self, job_id: str, cooldown_minutes: int = 5) -> bool:
        """
        Check if we can send a todo_items warning (throttle: 1 per N minutes per job).

        Args:
            job_id: Job UUID
            cooldown_minutes: Minimum minutes between warnings (default: 5)

        Returns:
            True if we can warn, False if throttled
        """
        last_warning = self._todo_warning_timestamps.get(job_id)
        if not last_warning:
            return True
        elapsed = (datetime.now(timezone.utc) - last_warning).total_seconds()
        return elapsed >= (cooldown_minutes * 60)

    def _record_todo_warning(self, job_id: str) -> None:
        """
        Record that a todo_items warning was sent for this job.

        Args:
            job_id: Job UUID
        """
        self._todo_warning_timestamps[job_id] = datetime.now(timezone.utc)

    # ============================================================================
    # Project Orchestration
    # ============================================================================

    async def get_workflow_status(
        self,
        project_id: str,
        tenant_key: str,
        exclude_job_id: Optional[str] = None,
    ) -> WorkflowStatus:
        """Facade: delegates to WorkflowStatusService."""
        return await self._workflow_status.get_workflow_status(project_id, tenant_key, exclude_job_id)

    # ============================================================================
    # Agent Job Management — Facade Delegations (Handover 0769)
    # ============================================================================

    async def spawn_job(self, *a, **kw) -> SpawnResult:
        """Facade: delegates to JobLifecycleService."""
        return await self._job_lifecycle.spawn_job(*a, **kw)

    # ============================================================================
    # Mission & Orchestrator Instructions — Facade Delegations (Handover 0769)
    # ============================================================================

    async def get_agent_mission(self, job_id, tenant_key) -> MissionResponse:
        """Facade: delegates to MissionService."""
        return await self._mission.get_agent_mission(job_id, tenant_key)

    async def update_agent_mission(self, job_id: str, tenant_key: str, mission: str) -> MissionUpdateResult:
        """Facade: delegates to MissionService."""
        return await self._mission.update_agent_mission(job_id=job_id, tenant_key=tenant_key, mission=mission)

    # ============================================================================
    # Progress Reporting — Facade Delegation (Handover 0769)
    # ============================================================================

    async def report_progress(self, *a, **kw) -> ProgressResult:
        """Facade: delegates to ProgressService."""
        return await self._progress.report_progress(*a, **kw)

    # ============================================================================
    # Pending Jobs
    # ============================================================================

    async def get_pending_jobs(self, tenant_key: str, agent_display_name: Optional[str] = None) -> PendingJobsResult:
        """
        Get pending jobs, optionally filtered by agent display name.

        Handover 0358b: Migrated to dual-model (AgentJob + AgentExecution).
        - Queries AgentExecution.status for execution state (waiting, working, etc.)
        - Mission comes from AgentJob via join
        - Returns both job_id (work order) and agent_id (executor)

        Args:
            tenant_key: Tenant key for isolation
            agent_display_name: Optional display name of agent to filter by

        Returns:
            Dict with list of pending jobs

        """
        try:
            # Validate inputs

            if not tenant_key or not tenant_key.strip():
                raise ValidationError(
                    message="tenant_key cannot be empty",
                    context={"agent_display_name": agent_display_name, "tenant_key": tenant_key},
                )

            # Get pending executions with their jobs (dual-model)
            repo = AgentOperationsRepository()
            async with self._get_session() as session:
                rows = await repo.get_pending_executions_with_jobs(session, tenant_key, agent_display_name)

                # Format jobs for response
                formatted_jobs = []
                for execution, job in rows:
                    formatted_jobs.append(
                        {
                            "job_id": job.job_id,  # Work order ID
                            "agent_id": execution.agent_id,  # Executor ID
                            "execution_id": str(execution.id) if hasattr(execution, "id") else None,  # Unique row ID
                            "tenant_key": execution.tenant_key,  # For job_to_response
                            "project_id": job.project_id,  # From AgentJob
                            "agent_display_name": execution.agent_display_name,
                            "agent_name": execution.agent_name,
                            "mission": job.mission,  # Mission from AgentJob
                            "status": execution.status,  # Execution status
                            "progress": execution.progress if hasattr(execution, "progress") else 0,
                            "context_chunks": [],  # Context chunks removed in 0366a (stored in job_metadata)
                            "created_at": job.created_at.isoformat() if job.created_at else None,
                            "started_at": execution.started_at.isoformat() if execution.started_at else None,
                            "priority": "normal",
                        }
                    )

                return PendingJobsResult(jobs=formatted_jobs, count=len(formatted_jobs))

        except ValidationError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get pending jobs")
            raise DatabaseError(
                message=f"Failed to get pending jobs: {e!s}",
                context={"agent_display_name": agent_display_name, "tenant_key": tenant_key},
            ) from e

    # ============================================================================
    # Job Completion, Error Reporting, Reactivation
    # ============================================================================

    async def complete_job(
        self,
        job_id: str,
        result: dict[str, Any],
        tenant_key: Optional[str] = None,
        acknowledge_closeout_todo: bool = False,
        acknowledge_messages_on_complete: bool = False,
    ) -> CompleteJobResult:
        """Facade: delegates to JobCompletionService."""
        return await self._job_completion.complete_job(
            job_id,
            result,
            tenant_key,
            acknowledge_closeout_todo=acknowledge_closeout_todo,
            acknowledge_messages_on_complete=acknowledge_messages_on_complete,
        )

    async def get_agent_result(self, job_id: str, tenant_key: str | None = None) -> dict | None:
        """Fetch the completion result for a given job's latest execution.

        Args:
            job_id: Job UUID
            tenant_key: Tenant key for isolation

        Returns:
            Result dict or None if no completed execution found
        """
        if not tenant_key:
            tenant_key = self.tenant_manager.get_current_tenant()
        if not tenant_key:
            return None

        repo = AgentOperationsRepository()
        async with self._get_session() as session:
            return await repo.get_completed_execution_result(session, tenant_key, job_id)

    async def set_agent_status(self, job_id, status, reason="", wake_in_minutes=None, tenant_key=None):
        """Facade: delegates to OrchestrationAgentStateService."""
        return await self._agent_state.set_agent_status(job_id, status, reason, wake_in_minutes, tenant_key)

    async def list_jobs(
        self,
        tenant_key: str,
        project_id: Optional[str] = None,
        status_filter: Optional[str] = None,
        agent_display_name: Optional[str] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> JobListResult:
        """Facade: delegates to JobQueryService."""
        return await self._job_query.list_jobs(tenant_key, project_id, status_filter, agent_display_name, limit, offset)

    # NOTE: update_context_usage(), estimate_message_tokens(), _trigger_auto_succession(),
    # and trigger_succession() were removed in Handover 0422/0700d - the MCP server is passive
    # and cannot track external CLI tool context usage.
    # Manual succession via UI button (simple-handover REST endpoint).

    @staticmethod
    async def health_check() -> dict[str, Any]:
        """MCP server health check."""
        from giljo_mcp.tools.slash_command_templates import SKILLS_VERSION

        return {
            "status": "healthy",
            "server": "giljo_mcp",
            "version": "1.0.0",
            "skills_version": SKILLS_VERSION,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "database": "connected",
            "message": "GiljoAI MCP server is operational",
        }

    # Succession methods removed (0391/0461/0700d)
    # Session refresh is handled by:
    #   - REST: POST /api/agent-jobs/{job_id}/simple-handover (UI button)
    # Agents cannot self-detect context exhaustion (passive HTTP architecture).
