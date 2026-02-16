"""
Silent agent detection background service (Handover 0491 Phase 3).

Periodically scans for agents in 'working' status whose last_progress_at
has exceeded the configurable silence threshold, marking them as 'silent'.

Also provides:
- auto_clear_silent(): Resets silent agents to 'working' when they make MCP calls
- clear_silent_status(): REST endpoint helper to manually clear silent status
"""

import asyncio
import contextlib
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.models.settings import Settings


logger = logging.getLogger(__name__)

# Default silence threshold in minutes (used when no setting is configured)
DEFAULT_SILENCE_THRESHOLD_MINUTES = 10

# How often the detector runs its scan (seconds)
DEFAULT_SCAN_INTERVAL_SECONDS = 60


class SilenceDetector:
    """Background service that detects agents that have gone silent.

    Scans for agents in 'working' status whose last_progress_at timestamp
    is older than the configurable threshold, or is NULL. These agents
    are transitioned to 'silent' status with a WebSocket notification.

    Follows the same pattern as AgentHealthMonitor for lifecycle management.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        ws_manager,
        scan_interval_seconds: int = DEFAULT_SCAN_INTERVAL_SECONDS,
    ):
        """Initialize silence detector.

        Args:
            db_manager: Database manager for session creation
            ws_manager: WebSocket manager for broadcasting status changes
            scan_interval_seconds: How often to scan (default 60s)
        """
        self.db = db_manager
        self.ws = ws_manager
        self.scan_interval_seconds = scan_interval_seconds
        self.running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self) -> None:
        """Start the background monitoring loop."""
        if self.running:
            logger.warning("Silence detector already running")
            return

        self.running = True
        self._task = asyncio.create_task(self._monitoring_loop())
        logger.info("Silence detector started (scan interval: %ds)", self.scan_interval_seconds)

    async def stop(self) -> None:
        """Stop the monitoring loop gracefully."""
        self.running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("Silence detector stopped")

    async def _monitoring_loop(self) -> None:
        """Main monitoring loop - runs every scan_interval_seconds."""
        while self.running:
            try:
                await self._run_detection_cycle()
            except Exception:
                logger.exception("Silence detection cycle failed")

            await asyncio.sleep(self.scan_interval_seconds)

    async def _run_detection_cycle(self) -> None:
        """Execute one complete silence detection cycle."""
        async with self.db.get_session_async() as session:
            # Read threshold from settings (scan all tenants for the global setting)
            threshold = await _get_silence_threshold(session)

            count = await self._detect_silent_agents(session, threshold_minutes=threshold)

            if count > 0:
                logger.info("Silence detection cycle: marked %d agent(s) as silent", count)

    async def _detect_silent_agents(
        self,
        session: AsyncSession,
        threshold_minutes: int = DEFAULT_SILENCE_THRESHOLD_MINUTES,
    ) -> int:
        """Detect and mark silent agents.

        Finds agents where:
        - status == 'working'
        - last_progress_at < (now - threshold) OR last_progress_at IS NULL

        Args:
            session: Database session
            threshold_minutes: Minutes of inactivity before marking silent

        Returns:
            Number of agents marked as silent
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=threshold_minutes)

        # TENANT ISOLATION NOTE (Phase C audit, Feb 2026):
        # This query intentionally scans ALL tenants. The silence detector is a
        # system-wide background health monitor (like a database cleanup job), not
        # a tenant-facing operation. It runs on a server timer with no user/tenant
        # context. Cross-tenant scope is BY DESIGN.
        stmt = select(AgentExecution).where(
            AgentExecution.status == "working",
            or_(
                AgentExecution.last_progress_at < cutoff,
                AgentExecution.last_progress_at.is_(None),
            ),
        )

        result = await session.execute(stmt)
        stale_agents = result.scalars().all()

        count = 0
        for agent in stale_agents:
            old_status = agent.status
            agent.status = "silent"

            logger.info(
                "Agent marked silent: agent_id=%s, job_id=%s, display_name=%s, last_progress_at=%s",
                agent.agent_id,
                agent.job_id,
                agent.agent_display_name,
                agent.last_progress_at,
            )

            # Emit WebSocket event
            try:
                await _broadcast_status_change(
                    ws_manager=self.ws,
                    agent=agent,
                    old_status=old_status,
                    new_status="silent",
                )
            except Exception:
                logger.exception(
                    "Failed to broadcast silent status for agent %s",
                    agent.agent_id,
                )

            count += 1

        if count > 0:
            await session.flush()

        return count


async def auto_clear_silent(
    session: AsyncSession,
    job_id: str,
    ws_manager,
) -> None:
    """Auto-clear silent status when an agent makes an MCP call.

    If the agent associated with the given job_id is currently 'silent',
    transitions it back to 'working' and updates last_progress_at.

    This is called from the MCP tool handler after successful tool execution.

    Args:
        session: Database session
        job_id: The job_id extracted from MCP tool arguments
        ws_manager: WebSocket manager for broadcasting
    """
    # TENANT ISOLATION NOTE (Phase C audit, Feb 2026):
    # This query filters by job_id (UUID) which uniquely identifies one agent's job.
    # MCP authentication resolves job_id from the authenticated tenant's context,
    # so a tenant cannot call this with another tenant's job_id. Cross-tenant risk
    # is mitigated by UUID uniqueness + MCP auth layer. System-level by design.
    stmt = select(AgentExecution).where(
        AgentExecution.job_id == job_id,
        AgentExecution.status == "silent",
    )
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        return

    old_status = agent.status
    agent.status = "working"
    agent.last_progress_at = datetime.now(timezone.utc)
    await session.flush()

    logger.info(
        "Auto-cleared silent status: agent_id=%s, job_id=%s, display_name=%s",
        agent.agent_id,
        agent.job_id,
        agent.agent_display_name,
    )

    try:
        await _broadcast_status_change(
            ws_manager=ws_manager,
            agent=agent,
            old_status=old_status,
            new_status="working",
        )
    except Exception:
        logger.exception(
            "Failed to broadcast auto-clear for agent %s",
            agent.agent_id,
        )


async def clear_silent_status(
    session: AsyncSession,
    agent_id: str,
    tenant_key: str,
    ws_manager,
) -> Optional[dict]:
    """Clear silent status for a specific agent (REST endpoint helper).

    Used by the dashboard when a user clicks the Silent badge to
    manually acknowledge and clear the status.

    Args:
        session: Database session
        agent_id: The agent execution ID
        tenant_key: Tenant key for isolation
        ws_manager: WebSocket manager for broadcasting

    Returns:
        Dict with updated agent info if cleared, None if agent not found or not silent
    """
    stmt = select(AgentExecution).where(
        AgentExecution.agent_id == agent_id,
        AgentExecution.tenant_key == tenant_key,
        AgentExecution.status == "silent",
    )
    result = await session.execute(stmt)
    agent = result.scalar_one_or_none()

    if agent is None:
        return None

    old_status = agent.status
    agent.status = "working"
    agent.last_progress_at = datetime.now(timezone.utc)
    await session.flush()

    logger.info(
        "Manually cleared silent status: agent_id=%s, tenant_key=%s, display_name=%s",
        agent.agent_id,
        tenant_key,
        agent.agent_display_name,
    )

    try:
        await _broadcast_status_change(
            ws_manager=ws_manager,
            agent=agent,
            old_status=old_status,
            new_status="working",
        )
    except Exception:
        logger.exception(
            "Failed to broadcast clear-silent for agent %s",
            agent.agent_id,
        )

    return {
        "agent_id": str(agent.agent_id),
        "job_id": str(agent.job_id),
        "status": agent.status,
        "last_progress_at": agent.last_progress_at.isoformat() if agent.last_progress_at else None,
    }


async def _get_silence_threshold(session: AsyncSession) -> int:
    """Get the silence threshold from system settings.

    Looks for `agent_silence_threshold_minutes` in the 'general' settings
    category across all tenants. Uses the first found value, or defaults.

    Args:
        session: Database session

    Returns:
        Silence threshold in minutes
    """
    try:
        stmt = select(Settings).where(Settings.category == "general").limit(1)
        result = await session.execute(stmt)
        settings = result.scalar_one_or_none()

        if settings and settings.settings_data:
            threshold = settings.settings_data.get("agent_silence_threshold_minutes")
            if threshold is not None and isinstance(threshold, (int, float)):
                return max(1, int(threshold))
    except Exception:
        logger.exception("Failed to read silence threshold from settings")

    return DEFAULT_SILENCE_THRESHOLD_MINUTES


async def _broadcast_status_change(
    ws_manager,
    agent: AgentExecution,
    old_status: str,
    new_status: str,
) -> None:
    """Broadcast an agent status change event via WebSocket.

    Uses the EventFactory.agent_status_changed pattern for consistency
    with other status change events in the system.

    Args:
        ws_manager: WebSocket manager
        agent: The agent execution object
        old_status: Previous status
        new_status: New status
    """
    from api.events.schemas import EventFactory

    event = EventFactory.agent_status_changed(
        job_id=str(agent.job_id),
        tenant_key=agent.tenant_key,
        old_status=old_status,
        new_status=new_status,
        agent_display_name=agent.agent_display_name or "unknown",
    )

    await ws_manager.broadcast_event_to_tenant(
        tenant_key=agent.tenant_key,
        event=event,
    )
