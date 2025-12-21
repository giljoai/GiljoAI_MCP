"""
Staging Rollback Manager for GiljoAI MCP Server

Handles database cleanup when user cancels project staging after orchestrator
has created mission and spawned agents.

CRITICAL: Multi-tenant isolation enforced on ALL queries.
APPROACH: Soft delete with metadata for audit trail and debugging.

Usage:
    rollback_mgr = StagingRollbackManager(db_manager)
    result = await rollback_mgr.rollback_staging(
        tenant_key="tenant_xyz",
        project_id="proj_123",
        orchestrator_job_id="orch_456",
        reason="User canceled staging"
    )
"""

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from .database import DatabaseManager
from .models import Project
from .models.agent_identity import AgentJob, AgentExecution

logger = logging.getLogger(__name__)


class StagingRollbackManager:
    """
    Manages database rollback for canceled staging operations.

    Responsibilities:
    - Delete spawned agents that haven't launched yet (status='waiting')
    - Clear project mission field (revert to empty/unstaged state)
    - Soft delete agents with metadata for audit trail
    - Enforce multi-tenant isolation (prevent cross-tenant deletions)
    - Return detailed rollback counts and statistics
    - Transaction safety (atomic operations)
    """

    # Agent statuses that are safe to delete (not yet launched)
    DELETABLE_STATUSES = {"waiting", "preparing"}

    # Agent statuses that should NOT be deleted (already launched/working)
    PROTECTED_STATUSES = {"active", "working", "review", "complete", "failed", "blocked", "cancelling"}

    def __init__(self, db_manager: DatabaseManager):
        """
        Initialize StagingRollbackManager.

        Args:
            db_manager: DatabaseManager instance for database operations
        """
        self.db_manager = db_manager

    async def rollback_staging(
        self,
        tenant_key: str,
        project_id: str,
        orchestrator_job_id: str,
        reason: str = "User canceled staging",
        hard_delete: bool = False,
    ) -> dict[str, Any]:
        """
        Rollback staging operation by deleting/soft-deleting spawned agents.

        This method performs the following operations in a transaction:
        1. Validate orchestrator exists and belongs to tenant
        2. Find all child agents spawned by this orchestrator (status='waiting' or 'preparing')
        3. Soft delete agents (or hard delete if specified)
        4. Clear project mission field (optional - configurable)
        5. Update orchestrator status to 'failed' with rollback reason

        CRITICAL: Multi-tenant isolation enforced - only affects specified tenant.

        Args:
            tenant_key: Tenant key for isolation (REQUIRED)
            project_id: Project ID to rollback staging for
            orchestrator_job_id: Orchestrator job_id that spawned the agents
            reason: Reason for rollback (for audit trail)
            hard_delete: If True, permanently delete agents. If False, soft delete
                        with status='cancelled' and metadata. Default: False (soft delete)

        Returns:
            dict: {
                "success": bool,
                "agents_deleted": int,           # Count of agents deleted/marked cancelled
                "agents_protected": int,         # Count of agents NOT deleted (already launched)
                "orchestrator_updated": bool,    # Whether orchestrator was updated
                "project_mission_cleared": bool, # Whether project mission was cleared
                "rollback_timestamp": str,       # ISO timestamp of rollback
                "rollback_reason": str,          # Reason for rollback
                "tenant_key": str,               # Tenant key (for verification)
                "deleted_agent_ids": list[str],  # Job IDs of deleted agents
                "protected_agent_ids": list[str],# Job IDs of protected agents
            }

        Raises:
            ValueError: If required parameters are invalid or orchestrator not found
            RuntimeError: If database transaction fails
        """
        # Validate required parameters
        if not tenant_key or not tenant_key.strip():
            raise ValueError("tenant_key cannot be empty")

        if not project_id or not project_id.strip():
            raise ValueError("project_id cannot be empty")

        if not orchestrator_job_id or not orchestrator_job_id.strip():
            raise ValueError("orchestrator_job_id cannot be empty")

        if not reason or not reason.strip():
            raise ValueError("reason cannot be empty")

        logger.info(
            f"[StagingRollback] Starting rollback for project={project_id}, "
            f"orchestrator={orchestrator_job_id}, tenant={tenant_key}, "
            f"hard_delete={hard_delete}"
        )

        async with self.db_manager.get_session_async() as session:
            try:
                # Step 1: Validate orchestrator exists and belongs to tenant
                orchestrator = await self._get_orchestrator_or_raise(
                    session=session,
                    tenant_key=tenant_key,
                    job_id=orchestrator_job_id,
                )

                logger.info(
                    f"[StagingRollback] Found orchestrator: agent_id={orchestrator.agent_id}, "
                    f"status={orchestrator.status}, agent_type={orchestrator.agent_type}"
                )

                # Step 2: Find all child agents spawned by this orchestrator
                child_agents = await self._get_child_agents(
                    session=session,
                    tenant_key=tenant_key,
                    orchestrator_job_id=orchestrator_job_id,
                )

                logger.info(f"[StagingRollback] Found {len(child_agents)} child agents")

                # Step 3: Separate agents into deletable and protected
                deletable_agents = [
                    agent for agent in child_agents if agent.status in self.DELETABLE_STATUSES
                ]
                protected_agents = [
                    agent for agent in child_agents if agent.status in self.PROTECTED_STATUSES
                ]

                logger.info(
                    f"[StagingRollback] Deletable: {len(deletable_agents)}, "
                    f"Protected: {len(protected_agents)}"
                )

                # Step 4: Delete or soft-delete agents
                deleted_agent_ids = []
                if hard_delete:
                    deleted_agent_ids = await self._hard_delete_agents(
                        session=session,
                        agents=deletable_agents,
                    )
                else:
                    deleted_agent_ids = await self._soft_delete_agents(
                        session=session,
                        agents=deletable_agents,
                        reason=reason,
                    )

                # Step 5: Clear project mission field (optional)
                project_mission_cleared = await self._clear_project_mission(
                    session=session,
                    tenant_key=tenant_key,
                    project_id=project_id,
                )

                # Step 6: Update orchestrator status to 'failed' with rollback metadata
                orchestrator_updated = await self._update_orchestrator_status(
                    session=session,
                    orchestrator=orchestrator,
                    reason=reason,
                    agents_deleted=len(deleted_agent_ids),
                )

                # Commit transaction
                await session.commit()

                rollback_timestamp = datetime.now(timezone.utc).isoformat()

                result = {
                    "success": True,
                    "agents_deleted": len(deleted_agent_ids),
                    "agents_protected": len(protected_agents),
                    "orchestrator_updated": orchestrator_updated,
                    "project_mission_cleared": project_mission_cleared,
                    "rollback_timestamp": rollback_timestamp,
                    "rollback_reason": reason,
                    "tenant_key": tenant_key,
                    "deleted_agent_ids": deleted_agent_ids,
                    "protected_agent_ids": [str(agent.agent_id) for agent in protected_agents],
                }

                logger.info(
                    f"[StagingRollback] SUCCESS: Deleted {len(deleted_agent_ids)} agents, "
                    f"Protected {len(protected_agents)} agents, "
                    f"Orchestrator updated: {orchestrator_updated}"
                )

                return result

            except ValueError as e:
                # Re-raise validation errors
                logger.error(f"[StagingRollback] Validation error: {e}")
                await session.rollback()
                raise

            except Exception as e:
                # Rollback transaction on any error
                logger.error(f"[StagingRollback] Transaction failed: {e}", exc_info=True)
                await session.rollback()
                raise RuntimeError(f"Staging rollback failed: {e!s}") from e

    async def _get_orchestrator_or_raise(
        self,
        session: AsyncSession,
        tenant_key: str,
        job_id: str,
    ) -> AgentExecution:
        """
        Get orchestrator execution or raise ValueError if not found.

        CRITICAL: Enforces multi-tenant isolation.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            job_id: Orchestrator job_id (UUID)

        Returns:
            AgentExecution instance (orchestrator)

        Raises:
            ValueError: If orchestrator not found for this tenant
        """
        from sqlalchemy.orm import joinedload

        # Query AgentExecution with eager-loaded job
        stmt = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.job_id == job_id,
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.agent_type == "orchestrator",
                )
            )
        )

        result = await session.execute(stmt)
        orchestrator = result.scalar_one_or_none()

        if not orchestrator:
            raise ValueError(
                f"Orchestrator {job_id} not found for tenant {tenant_key}"
            )

        return orchestrator

    async def _get_child_agents(
        self,
        session: AsyncSession,
        tenant_key: str,
        orchestrator_job_id: str,
    ) -> list[AgentExecution]:
        """
        Get all child agent executions spawned by orchestrator.

        CRITICAL: Enforces multi-tenant isolation.
        Filters by spawned_by field to only get direct children.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            orchestrator_job_id: Orchestrator job_id (UUID)

        Returns:
            List of AgentExecution instances (child agents)
        """
        from sqlalchemy.orm import joinedload

        stmt = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .where(
                and_(
                    AgentJob.tenant_key == tenant_key,
                    AgentExecution.spawned_by == orchestrator_job_id,
                )
            )
            .order_by(AgentExecution.created_at)
        )

        result = await session.execute(stmt)
        agents = result.scalars().all()

        return list(agents)

    async def _hard_delete_agents(
        self,
        session: AsyncSession,
        agents: list[AgentExecution],
    ) -> list[str]:
        """
        Permanently delete agent executions from database (HARD DELETE).

        WARNING: Cannot be undone. Only use when storage is critical.

        Args:
            session: Database session
            agents: List of AgentExecution instances to delete

        Returns:
            List of deleted agent_ids
        """
        deleted_ids = []

        for agent in agents:
            agent_id = str(agent.agent_id)
            await session.delete(agent)
            deleted_ids.append(agent_id)

            logger.info(
                f"[StagingRollback] HARD DELETE: agent={agent_id}, "
                f"status={agent.status}, type={agent.agent_type}"
            )

        return deleted_ids

    async def _soft_delete_agents(
        self,
        session: AsyncSession,
        agents: list[AgentExecution],
        reason: str,
    ) -> list[str]:
        """
        Soft delete agents by marking status='cancelled' with rollback metadata.

        RECOMMENDED: Maintains audit trail and allows potential recovery.

        Soft delete strategy:
        - Set status to 'cancelled' (one of 7 AgentExecution statuses)
        - Set failure_reason with rollback details
        - Set completed_at timestamp
        - Preserve all other data for debugging

        Args:
            session: Database session
            agents: List of AgentExecution instances to soft delete
            reason: Reason for deletion (stored in failure_reason)

        Returns:
            List of soft-deleted agent_ids
        """
        deleted_ids = []
        rollback_timestamp = datetime.now(timezone.utc)

        for agent in agents:
            agent_id = str(agent.agent_id)
            old_status = agent.status

            # Update status to 'cancelled' (AgentExecution has 7-value status)
            agent.status = "cancelled"
            agent.completed_at = rollback_timestamp

            # Set failure reason with rollback metadata
            agent.failure_reason = f"Rollback: {reason} (original_status={old_status})"

            deleted_ids.append(agent_id)

            logger.info(
                f"[StagingRollback] SOFT DELETE: agent={agent_id}, "
                f"old_status={old_status}, type={agent.agent_type}, "
                f"reason={reason}"
            )

        return deleted_ids

    async def _clear_project_mission(
        self,
        session: AsyncSession,
        tenant_key: str,
        project_id: str,
    ) -> bool:
        """
        Clear project mission field (revert to empty/unstaged state).

        Optional operation - can be disabled if you want to preserve mission.

        CRITICAL: Enforces multi-tenant isolation.

        Args:
            session: Database session
            tenant_key: Tenant key for isolation
            project_id: Project ID

        Returns:
            True if mission was cleared, False if project not found
        """
        stmt = (
            update(Project)
            .where(
                and_(
                    Project.tenant_key == tenant_key,
                    Project.id == project_id,
                )
            )
            .values(mission="")
        )

        result = await session.execute(stmt)

        if result.rowcount > 0:
            logger.info(
                f"[StagingRollback] Cleared mission for project={project_id}"
            )
            return True
        else:
            logger.warning(
                f"[StagingRollback] Project {project_id} not found, "
                f"mission not cleared"
            )
            return False

    async def _update_orchestrator_status(
        self,
        session: AsyncSession,
        orchestrator: AgentExecution,
        reason: str,
        agents_deleted: int,
    ) -> bool:
        """
        Update orchestrator status to 'cancelled' with rollback metadata.

        Marks orchestrator as cancelled so it doesn't continue executing.
        Stores rollback metadata in failure_reason field.

        Args:
            session: Database session
            orchestrator: AgentExecution instance (orchestrator)
            reason: Reason for failure
            agents_deleted: Count of agents deleted

        Returns:
            True if orchestrator was updated
        """
        rollback_timestamp = datetime.now(timezone.utc)

        # Update status to 'cancelled' (AgentExecution status)
        orchestrator.status = "cancelled"
        orchestrator.completed_at = rollback_timestamp

        # Set failure reason with rollback metadata
        orchestrator.failure_reason = (
            f"Rollback: {reason} (agents_deleted={agents_deleted}, "
            f"timestamp={rollback_timestamp.isoformat()})"
        )

        logger.info(
            f"[StagingRollback] Updated orchestrator: agent_id={orchestrator.agent_id}, "
            f"status=cancelled, agents_deleted={agents_deleted}"
        )

        return True


# Convenience function for API endpoints
async def rollback_project_staging(
    tenant_key: str,
    project_id: str,
    orchestrator_job_id: str,
    reason: str = "User canceled staging",
    hard_delete: bool = False,
) -> dict[str, Any]:
    """
    Convenience function to rollback project staging.

    This is a standalone function that can be called directly from API endpoints
    without instantiating StagingRollbackManager.

    Args:
        tenant_key: Tenant key for isolation
        project_id: Project ID to rollback staging for
        orchestrator_job_id: Orchestrator job_id that spawned the agents
        reason: Reason for rollback (default: "User canceled staging")
        hard_delete: If True, permanently delete agents (default: False, soft delete)

    Returns:
        dict: Rollback result with counts and status

    Raises:
        ValueError: If required parameters are invalid or orchestrator not found
        RuntimeError: If database transaction fails

    Example:
        result = await rollback_project_staging(
            tenant_key="tenant_123",
            project_id="proj_456",
            orchestrator_job_id="orch_789",
            reason="User canceled during staging review",
        )
        print(f"Deleted {result['agents_deleted']} agents")
    """
    db_manager = DatabaseManager()
    rollback_mgr = StagingRollbackManager(db_manager)

    return await rollback_mgr.rollback_staging(
        tenant_key=tenant_key,
        project_id=project_id,
        orchestrator_job_id=orchestrator_job_id,
        reason=reason,
        hard_delete=hard_delete,
    )
