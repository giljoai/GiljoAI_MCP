# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
WorkflowStatusService - Project workflow status queries.

Sprint 002e: Extracted from OrchestrationService to reduce god-class size.
get_workflow_status is completely self-contained (162 lines) -- pure read query.
"""

import logging
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import DatabaseError, ResourceNotFoundError
from giljo_mcp.repositories.agent_job_repository import AgentJobRepository
from giljo_mcp.repositories.agent_operations_repository import AgentOperationsRepository
from giljo_mcp.schemas.service_responses import (
    AgentTodoCounts,
    AgentWorkflowDetail,
    WorkflowStatus,
)
from giljo_mcp.tenant import TenantManager


logger = logging.getLogger(__name__)


class WorkflowStatusService:
    """Service for querying project workflow status.

    Extracted from OrchestrationService (Sprint 002e).
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_manager: TenantManager,
        test_session: AsyncSession | None = None,
    ):
        self.db_manager = db_manager
        self.tenant_manager = tenant_manager
        self._test_session = test_session
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """Get a session, preferring an injected test session when provided."""
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()
        return self.db_manager.get_session_async()

    async def get_workflow_status(
        self,
        project_id: str,
        tenant_key: str,
        exclude_job_id: str | None = None,
    ) -> WorkflowStatus:
        """Get workflow status for a project.

        Handover 0491: Simplified status model.
        - Counts execution statuses (waiting, working, complete, blocked, silent, decommissioned)
        - Job status comes from AgentJob (active, completed, cancelled)
        - Execution status from AgentExecution (execution progress)

        Args:
            project_id: Project UUID
            tenant_key: Tenant key for isolation
            exclude_job_id: Optional job_id to exclude from the query

        Returns:
            WorkflowStatus with agent counts, progress, and current stage

        Raises:
            ResourceNotFoundError: Project not found
            DatabaseError: Database operation failed
        """
        try:
            job_repo = AgentJobRepository(None)
            ops_repo = AgentOperationsRepository()
            async with self._get_session() as session:
                project = await job_repo.get_project_by_id(session, tenant_key, project_id)

                if not project:
                    raise ResourceNotFoundError(
                        message=f"Project '{project_id}' not found",
                        context={"project_id": project_id, "tenant_key": tenant_key},
                    )

                rows = await ops_repo.get_workflow_executions(session, tenant_key, project_id, exclude_job_id)

                executions = [row[0] for row in rows]
                job_type_map = {row[1].job_id: row[1].job_type or "" for row in rows}
                active_count = sum(1 for ex in executions if ex.status == "working")
                completed_count = sum(1 for ex in executions if ex.status == "complete")
                pending_count = sum(1 for ex in executions if ex.status == "waiting")
                blocked_count = sum(1 for ex in executions if ex.status == "blocked")
                silent_count = sum(1 for ex in executions if ex.status == "silent")
                decommissioned_count = sum(1 for ex in executions if ex.status == "decommissioned")
                total_count = len(executions)

                actionable_count = total_count - decommissioned_count
                progress_percent = (completed_count / actionable_count * 100.0) if actionable_count > 0 else 0.0

                if total_count == 0:
                    current_stage = "Not started"
                elif completed_count == actionable_count:
                    current_stage = "Completed"
                elif blocked_count > 0 and silent_count > 0:
                    current_stage = f"In Progress ({blocked_count} blocked, {silent_count} silent)"
                elif blocked_count > 0:
                    current_stage = f"In Progress ({blocked_count} blocked)"
                elif silent_count > 0:
                    current_stage = f"In Progress ({silent_count} silent)"
                elif active_count > 0:
                    current_stage = "In Progress"
                elif pending_count > 0:
                    current_stage = "Pending"
                else:
                    current_stage = "Unknown"

                if exclude_job_id:
                    caller_note = "Your job was excluded from these counts."
                else:
                    caller_note = "Note: You (the calling agent) are included in the active count above."

                agent_details: list[AgentWorkflowDetail] = []
                if executions:
                    job_ids = [ex.job_id for ex in executions]
                    todo_map = await ops_repo.get_todo_counts_by_job(session, tenant_key, job_ids)

                    for execution in executions:
                        counts = todo_map.get(execution.job_id, {})
                        agent_details.append(
                            AgentWorkflowDetail(
                                job_id=execution.job_id,
                                agent_id=execution.agent_id,
                                agent_name=execution.agent_name or "",
                                display_name=execution.agent_display_name or "",
                                status=execution.status or "",
                                job_type=job_type_map.get(execution.job_id, ""),
                                unread_messages=execution.messages_waiting_count or 0,
                                todos=AgentTodoCounts(
                                    completed=counts.get("completed", 0),
                                    in_progress=counts.get("in_progress", 0),
                                    pending=counts.get("pending", 0),
                                    skipped=counts.get("skipped", 0),
                                ),
                            )
                        )

                return WorkflowStatus(
                    active_agents=active_count,
                    completed_agents=completed_count,
                    pending_agents=pending_count,
                    blocked_agents=blocked_count,
                    silent_agents=silent_count,
                    decommissioned_agents=decommissioned_count,
                    current_stage=current_stage,
                    progress_percent=round(progress_percent, 2),
                    total_agents=total_count,
                    caller_note=caller_note,
                    agents=agent_details,
                )

        except ResourceNotFoundError:
            raise
        except Exception as e:
            self._logger.exception("Failed to get workflow status")
            raise DatabaseError(
                message=f"Failed to get workflow status: {e!s}",
                context={"project_id": project_id, "tenant_key": tenant_key},
            ) from e
