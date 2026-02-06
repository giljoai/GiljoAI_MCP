"""
Agent Health Monitor - Background monitoring service for agent job health.

Provides automatic detection of:
- Waiting timeouts (jobs never acknowledged)
- Stalled jobs (active jobs without progress)
- Heartbeat failures (extended silence)

Implements three-tier escalation (warning → critical → timeout) and
WebSocket event integration for real-time alerting.
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models import Project
from sqlalchemy.orm import joinedload
from src.giljo_mcp.database import DatabaseManager
from api.websocket import WebSocketManager
from src.giljo_mcp.monitoring.health_config import HealthCheckConfig, AgentHealthStatus


logger = logging.getLogger(__name__)


class AgentHealthMonitor:
    """
    Background task for agent health monitoring.

    Continuously scans agent jobs for health issues and triggers
    alerts or auto-recovery actions based on configuration.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        ws_manager: WebSocketManager,
        config: Optional[HealthCheckConfig] = None
    ):
        """
        Initialize health monitor.

        Args:
            db_manager: Database manager for job queries
            ws_manager: WebSocket manager for broadcasting alerts
            config: Health check configuration (uses defaults if None)
        """
        self.db = db_manager
        self.ws = ws_manager
        self.config = config or HealthCheckConfig()
        self.running = False
        self._task: Optional[asyncio.Task] = None
        self._first_scan = True  # Suppress verbose logging on first scan

    async def start(self):
        """Start background monitoring loop."""
        if self.running:
            logger.warning("Health monitor already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Agent health monitor started")

    async def stop(self):
        """Stop monitoring loop gracefully."""
        self.running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Agent health monitor stopped")

    async def _monitoring_loop(self):
        """Main monitoring loop."""
        while self.running:
            try:
                await self._run_health_check_cycle()
            except Exception as e:
                logger.error(f"Health check cycle failed: {e}", exc_info=True)

            await asyncio.sleep(self.config.scan_interval_seconds)

    async def _run_health_check_cycle(self):
        """Execute one complete health check cycle."""
        logger.debug("Starting health check cycle")

        async with self.db.get_session_async() as session:
            # Get all tenants
            tenants = await self._get_all_tenants(session)

            for tenant_key in tenants:
                # Scan for unhealthy jobs per tenant
                unhealthy_jobs = await self._scan_tenant_jobs(session, tenant_key)

                # On first scan, just log a summary instead of individual alerts
                if self._first_scan and unhealthy_jobs:
                    logger.info(f"Initial health scan: Found {len(unhealthy_jobs)} stale jobs (alerts suppressed on first scan)")
                    self._first_scan = False
                    continue

                for health_status in unhealthy_jobs:
                    await self._handle_unhealthy_job(session, health_status, tenant_key)

        logger.debug("Health check cycle completed")

    async def _scan_tenant_jobs(
        self,
        session: AsyncSession,
        tenant_key: str
    ) -> List[AgentHealthStatus]:
        """
        Scan all jobs for a tenant and detect unhealthy states.

        Args:
            session: Database session
            tenant_key: Tenant to scan

        Returns:
            List of unhealthy job statuses
        """
        unhealthy = []

        # Detection 1: Waiting timeout (never acknowledged)
        waiting_timeouts = await self._detect_waiting_timeouts(session, tenant_key)
        unhealthy.extend(waiting_timeouts)

        # Detection 2: Active no progress (stalled execution)
        stalled_jobs = await self._detect_stalled_jobs(session, tenant_key)
        unhealthy.extend(stalled_jobs)

        # Detection 3: Heartbeat timeout (complete silence)
        heartbeat_failures = await self._detect_heartbeat_failures(session, tenant_key)
        unhealthy.extend(heartbeat_failures)

        return unhealthy

    async def _detect_waiting_timeouts(
        self,
        session: AsyncSession,
        tenant_key: str
    ) -> List[AgentHealthStatus]:
        """
        Find jobs stuck in 'waiting' state.

        Args:
            session: Database session
            tenant_key: Tenant to scan

        Returns:
            List of jobs with waiting timeouts
        """
        timeout_threshold = datetime.now(timezone.utc) - timedelta(
            minutes=self.config.waiting_timeout_minutes
        )

        # Filter out jobs from deleted projects and inactive projects using LEFT JOIN
        # Handover 0424: Only monitor jobs from active projects
        # Only check latest execution per job to avoid alerts on old executions
        from sqlalchemy import func

        # Subquery to get latest started_at per job_id
        latest_instance_subq = (
            select(
                AgentExecution.job_id,
                func.max(AgentExecution.started_at).label('latest_started')
            )
            .where(AgentExecution.tenant_key == tenant_key)
            .group_by(AgentExecution.job_id)
            .subquery()
        )

        query = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .join(
                latest_instance_subq,
                and_(
                    AgentExecution.job_id == latest_instance_subq.c.job_id,
                    AgentExecution.started_at == latest_instance_subq.c.latest_started
                )
            )
            .outerjoin(Project, AgentJob.project_id == Project.id)
            .where(
                and_(
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status == "waiting",
                    AgentJob.created_at < timeout_threshold,
                    or_(
                        AgentJob.project_id.is_(None),  # Jobs without project (orphaned)
                        and_(
                            Project.deleted_at.is_(None),
                            Project.status == "active"  # Only active projects
                        )
                    )
                )
            )
        )

        result = await session.execute(query)
        executions = result.unique().scalars().all()

        return [
            AgentHealthStatus(
                execution_id=execution.id,  # Primary key - guaranteed unique
                job_id=execution.job_id,
                agent_id=execution.agent_id,
                agent_display_name=execution.agent_display_name,
                current_status="waiting",
                health_state="critical",
                last_update=execution.job.created_at,
                minutes_since_update=(
                    (datetime.now(timezone.utc) - execution.job.created_at).total_seconds() / 60
                    if execution.job.created_at
                    else float(self.config.waiting_timeout_minutes)
                ),
                issue_description=f"Job never acknowledged after {self.config.waiting_timeout_minutes} minutes",
                recommended_action="Check if agent received job, manual intervention may be required"
            )
            for execution in executions
        ]

    async def _detect_stalled_jobs(
        self,
        session: AsyncSession,
        tenant_key: str
    ) -> List[AgentHealthStatus]:
        """
        Find active jobs without progress updates.

        Args:
            session: Database session
            tenant_key: Tenant to scan

        Returns:
            List of stalled jobs
        """
        timeout_threshold = datetime.now(timezone.utc) - timedelta(
            minutes=self.config.active_no_progress_minutes
        )

        # Query active jobs, filtering out jobs from deleted projects and inactive projects
        # Handover 0424: Only monitor jobs from active projects
        # Only check latest execution per job to avoid alerts on old executions
        from sqlalchemy import func

        # Subquery to get latest started_at per job_id
        latest_instance_subq = (
            select(
                AgentExecution.job_id,
                func.max(AgentExecution.started_at).label('latest_started')
            )
            .where(AgentExecution.tenant_key == tenant_key)
            .group_by(AgentExecution.job_id)
            .subquery()
        )

        query = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .join(
                latest_instance_subq,
                and_(
                    AgentExecution.job_id == latest_instance_subq.c.job_id,
                    AgentExecution.started_at == latest_instance_subq.c.latest_started
                )
            )
            .outerjoin(Project, AgentJob.project_id == Project.id)
            .where(
                and_(
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status == "working",
                    or_(
                        AgentJob.project_id.is_(None),  # Jobs without project (orphaned)
                        and_(
                            Project.deleted_at.is_(None),
                            Project.status == "active"  # Only active projects
                        )
                    )
                )
            )
        )

        result = await session.execute(query)
        executions = result.unique().scalars().all()

        stalled = []
        for execution in executions:
            last_progress = self._get_last_progress_time(execution)
            if last_progress < timeout_threshold:
                minutes_stalled = (datetime.now(timezone.utc) - last_progress).total_seconds() / 60

                # Determine health state based on duration
                if minutes_stalled >= self.config.heartbeat_timeout_minutes:
                    health_state = "timeout"
                elif minutes_stalled >= 7:
                    health_state = "critical"
                else:
                    health_state = "warning"

                stalled.append(AgentHealthStatus(
                    execution_id=execution.id,  # Primary key - guaranteed unique
                    job_id=execution.job_id,
                    agent_id=execution.agent_id,
                    agent_display_name=execution.agent_display_name,
                    current_status="active",
                    health_state=health_state,
                    last_update=last_progress,
                    minutes_since_update=minutes_stalled,
                    issue_description=f"No progress update for {minutes_stalled:.1f} minutes",
                    recommended_action="Check agent logs, may need manual restart"
                ))

        return stalled

    async def _detect_heartbeat_failures(
        self,
        session: AsyncSession,
        tenant_key: str
    ) -> List[AgentHealthStatus]:
        """
        Find jobs with extended silence (heartbeat timeout).

        Args:
            session: Database session
            tenant_key: Tenant to scan

        Returns:
            List of jobs with heartbeat failures
        """
        # Query waiting and active jobs, filtering out jobs from deleted projects and inactive projects
        # Handover 0424: Only monitor jobs from active projects
        # Only check latest execution per job to avoid alerts on old executions
        from sqlalchemy import func

        # Subquery to get latest started_at per job_id
        latest_instance_subq = (
            select(
                AgentExecution.job_id,
                func.max(AgentExecution.started_at).label('latest_started')
            )
            .where(AgentExecution.tenant_key == tenant_key)
            .group_by(AgentExecution.job_id)
            .subquery()
        )

        query = (
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .join(
                latest_instance_subq,
                and_(
                    AgentExecution.job_id == latest_instance_subq.c.job_id,
                    AgentExecution.started_at == latest_instance_subq.c.latest_started
                )
            )
            .outerjoin(Project, AgentJob.project_id == Project.id)
            .where(
                and_(
                    AgentExecution.tenant_key == tenant_key,
                    AgentExecution.status.in_(["waiting", "working"]),
                    or_(
                        AgentJob.project_id.is_(None),  # Jobs without project (orphaned)
                        and_(
                            Project.deleted_at.is_(None),
                            Project.status == "active"  # Only active projects
                        )
                    )
                )
            )
        )

        result = await session.execute(query)
        executions = result.unique().scalars().all()

        failures = []
        for execution in executions:
            # Apply agent-type-specific timeouts
            timeout_minutes = self.config.get_timeout_for_agent(execution.agent_display_name)
            threshold = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)
            last_activity = self._get_last_activity_time(execution)

            if last_activity < threshold:
                minutes_silent = (datetime.now(timezone.utc) - last_activity).total_seconds() / 60

                failures.append(AgentHealthStatus(
                    execution_id=execution.id,  # Primary key - guaranteed unique
                    job_id=execution.job_id,
                    agent_id=execution.agent_id,
                    agent_display_name=execution.agent_display_name,
                    current_status=execution.status,
                    health_state="timeout",
                    last_update=last_activity,
                    minutes_since_update=minutes_silent,
                    issue_description=f"Complete silence for {minutes_silent:.1f} minutes (timeout: {timeout_minutes}m)",
                    recommended_action="Auto-fail job or manual intervention required"
                ))

        return failures

    async def _handle_unhealthy_job(
        self,
        session: AsyncSession,
        health_status: AgentHealthStatus,
        tenant_key: str
    ):
        """
        Handle detected unhealthy job.

        Args:
            session: Database session
            health_status: Health status of unhealthy job
            tenant_key: Tenant key
        """
        logger.warning(
            f"Unhealthy execution detected: {health_status.execution_id} (job: {health_status.job_id})",
            extra={
                "execution_id": health_status.execution_id,
                "agent_id": health_status.agent_id,
                "job_id": health_status.job_id,
                "agent_display_name": health_status.agent_display_name,
                "health_state": health_status.health_state,
                "minutes_since_update": health_status.minutes_since_update
            }
        )

        # Get execution from database by primary key (guaranteed unique)
        # NOTE: Use execution_id (primary key) not agent_id which may have duplicates
        result = await session.execute(
            select(AgentExecution)
            .options(joinedload(AgentExecution.job))
            .where(AgentExecution.id == health_status.execution_id)
        )
        execution = result.unique().scalar_one_or_none()
        if not execution:
            logger.error(f"Execution {health_status.execution_id} not found in database")
            return

        # Update execution health fields
        execution.health_status = health_status.health_state
        execution.health_failure_count += 1
        execution.last_health_check = datetime.now(timezone.utc)

        # Auto-fail on timeout (if configured)
        if health_status.health_state == "timeout" and self.config.auto_fail_on_timeout:
            execution.status = "failed"
            execution.completed_at = datetime.now(timezone.utc)
            execution.result_summary = f"Auto-failed: {health_status.issue_description}"

            # Broadcast auto-fail event
            await self.ws.broadcast_agent_auto_failed(
                tenant_key=tenant_key,
                job_id=health_status.job_id,
                agent_display_name=health_status.agent_display_name,
                reason=health_status.issue_description
            )
        else:
            # Broadcast health alert
            await self.ws.broadcast_health_alert(
                tenant_key=tenant_key,
                job_id=health_status.job_id,
                agent_display_name=health_status.agent_display_name,
                health_status=health_status
            )

        await session.commit()

    def _get_last_progress_time(self, execution: AgentExecution) -> datetime:
        """
        Get last progress update time from execution.

        Args:
            execution: Agent execution to check

        Returns:
            Datetime of last progress update
        """
        # AgentExecution has last_progress_at as a direct field
        if execution.last_progress_at:
            return execution.last_progress_at

        # Fallback to started_at or job.created_at
        return execution.started_at or execution.job.created_at

    def _get_last_activity_time(self, execution: AgentExecution) -> datetime:
        """
        Get most recent activity timestamp.

        Args:
            execution: Agent execution to check

        Returns:
            Most recent activity timestamp
        """
        candidates = [
            execution.job.created_at,
            execution.started_at,
            execution.last_progress_at,
            execution.last_message_check_at,
            self._get_last_progress_time(execution)
        ]

        # Filter out None values and return max
        valid_timestamps = [ts for ts in candidates if ts is not None]
        return max(valid_timestamps) if valid_timestamps else datetime.now(timezone.utc)

    async def _get_all_tenants(self, session: AsyncSession) -> List[str]:
        """
        Get list of all tenant keys.

        Args:
            session: Database session

        Returns:
            List of unique tenant keys from active projects
        """
        # Only get tenant keys from executions that don't belong to deleted projects or inactive projects
        # Handover 0424: Only monitor jobs from active projects
        query = (
            select(AgentExecution.tenant_key)
            .distinct()
            .join(AgentJob, AgentExecution.job_id == AgentJob.job_id)
            .outerjoin(Project, AgentJob.project_id == Project.id)
            .where(
                or_(
                    AgentJob.project_id.is_(None),  # Jobs without project (orphaned)
                    and_(
                        Project.deleted_at.is_(None),
                        Project.status == "active"  # Only active projects
                    )
                )
            )
        )
        result = await session.execute(query)
        return [row[0] for row in result.fetchall()]
