"""
Background Health Monitoring for Agent Jobs (Handover 0107).

Provides continuous health monitoring for active agent jobs, detecting
stale jobs that haven't reported progress in configurable time windows.

Key Features:
- Periodic health checks every 5 minutes
- Detects jobs with no progress updates in last 10 minutes
- WebSocket broadcasts for stale job warnings
- Multi-tenant isolation
- No auto-fail (user decides when to force-stop)

Production-grade features:
- Comprehensive error handling
- Graceful degradation
- Logging for audit trail
- Configurable thresholds
"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select

from .database import DatabaseManager
from .models import MCPAgentJob


logger = logging.getLogger(__name__)


async def monitor_agent_health(
    check_interval: int = 300,  # 5 minutes
    stale_threshold: int = 600,  # 10 minutes
) -> None:
    """
    Background task for monitoring agent job health (Handover 0107).

    Runs continuously, checking for stale agent jobs that haven't reported
    progress within the stale_threshold. Broadcasts warnings via WebSocket
    but does NOT auto-fail jobs - that decision is left to the user.

    Args:
        check_interval: Seconds between health checks (default: 300 = 5 minutes)
        stale_threshold: Seconds without progress before warning (default: 600 = 10 minutes)

    Monitoring Criteria:
        - Job status is "working" or "preparing"
        - last_progress_at is NULL or older than stale_threshold
        - Job is not in terminal state (complete, failed)

    WebSocket Event:
        Broadcasts "job:stale_warning" with:
        - job_id
        - tenant_key
        - minutes_stale
        - last_progress_at (ISO format or NULL)
        - current_status

    Example:
        >>> # Start in api/app.py startup
        >>> asyncio.create_task(monitor_agent_health())
    """
    logger.info(
        f"[monitor_agent_health] Starting agent health monitor "
        f"(check_interval={check_interval}s, stale_threshold={stale_threshold}s)"
    )

    db_manager = DatabaseManager()

    while True:
        try:
            # Sleep first to allow system startup
            await asyncio.sleep(check_interval)

            logger.debug("[monitor_agent_health] Running health check cycle")

            async with db_manager.get_session_async() as session:
                # Calculate stale cutoff time
                now = datetime.now(timezone.utc)
                stale_cutoff = now - timedelta(seconds=stale_threshold)

                # Find active/working jobs with no recent progress
                # Query for jobs that are:
                # 1. In active states (working, preparing)
                # 2. Have NULL last_progress_at OR last_progress_at older than threshold
                stmt = select(MCPAgentJob).where(
                    MCPAgentJob.status.in_(["working", "preparing"]),
                    # Check for NULL or stale timestamp
                    (
                        (MCPAgentJob.last_progress_at.is_(None))
                        | (MCPAgentJob.last_progress_at < stale_cutoff)
                    ),
                )

                result = await session.execute(stmt)
                stale_jobs = result.scalars().all()

                if stale_jobs:
                    logger.info(f"[monitor_agent_health] Found {len(stale_jobs)} potentially stale jobs")

                    # Import websocket manager for broadcasting
                    try:
                        from api.websocket import websocket_manager

                        for job in stale_jobs:
                            # Calculate how stale the job is
                            if job.last_progress_at:
                                time_since_progress = now - job.last_progress_at
                                minutes_stale = int(time_since_progress.total_seconds() / 60)
                                last_progress_iso = job.last_progress_at.isoformat()
                            else:
                                # No progress ever reported - use job start time or creation time
                                if job.started_at:
                                    time_since_progress = now - job.started_at
                                else:
                                    time_since_progress = now - job.created_at
                                minutes_stale = int(time_since_progress.total_seconds() / 60)
                                last_progress_iso = None

                            # Only warn if significantly stale (avoid noise)
                            if minutes_stale >= (stale_threshold / 60):
                                # Broadcast stale warning
                                try:
                                    await websocket_manager.broadcast(
                                        {
                                            "type": "job:stale_warning",
                                            "job_id": job.job_id,
                                            "tenant_key": job.tenant_key,
                                            "minutes_stale": minutes_stale,
                                            "last_progress_at": last_progress_iso,
                                            "current_status": job.status,
                                            "agent_type": job.agent_type,
                                            "agent_name": job.agent_name,
                                            "timestamp": now.isoformat(),
                                        }
                                    )

                                    logger.warning(
                                        f"[monitor_agent_health] Job {job.job_id} is stale "
                                        f"(no progress for {minutes_stale} minutes), "
                                        f"status={job.status}, tenant={job.tenant_key}"
                                    )

                                except Exception as ws_error:
                                    logger.warning(
                                        f"Failed to broadcast stale warning for job {job.job_id}: {ws_error}"
                                    )
                                    # Non-critical - continue monitoring

                    except Exception as import_error:
                        logger.error(f"Failed to import WebSocket manager: {import_error}")
                        # Continue monitoring even if WebSocket unavailable

                else:
                    logger.debug("[monitor_agent_health] No stale jobs detected")

        except asyncio.CancelledError:
            logger.info("[monitor_agent_health] Health monitor task cancelled, shutting down gracefully")
            break

        except Exception as e:
            logger.error(f"[monitor_agent_health] Error during health check cycle: {e}", exc_info=True)
            # Continue monitoring despite errors - don't let one failure stop the monitor
            await asyncio.sleep(30)  # Short delay before retry on error


async def get_job_health_status(
    tenant_key: str,
    job_id: str,
    stale_threshold: int = 600,
) -> dict:
    """
    Get current health status for a specific job (Handover 0107).

    Useful for on-demand health checks or API endpoints.

    Args:
        tenant_key: Tenant key for isolation
        job_id: Job ID to check
        stale_threshold: Seconds without progress before considering stale (default: 600)

    Returns:
        dict: {
            "job_id": str,
            "status": str,
            "is_stale": bool,
            "minutes_since_progress": Optional[int],
            "last_progress_at": Optional[str] (ISO format),
            "health_status": str (healthy|warning|stale|terminal)
        }

    Raises:
        ValueError: If job not found
    """
    try:
        db_manager = DatabaseManager()

        async with db_manager.get_session_async() as session:
            # Get job with tenant isolation
            stmt = select(MCPAgentJob).where(
                MCPAgentJob.tenant_key == tenant_key,
                MCPAgentJob.job_id == job_id,
            )
            result = await session.execute(stmt)
            job = result.scalar_one_or_none()

            if not job:
                raise ValueError(f"Job {job_id} not found for tenant {tenant_key}")

            now = datetime.now(timezone.utc)

            # Terminal states are always "healthy" (no monitoring needed)
            if job.status in ("complete", "failed"):
                return {
                    "job_id": job_id,
                    "status": job.status,
                    "is_stale": False,
                    "minutes_since_progress": None,
                    "last_progress_at": job.last_progress_at.isoformat() if job.last_progress_at else None,
                    "health_status": "terminal",
                }

            # Calculate staleness
            if job.last_progress_at:
                time_since_progress = now - job.last_progress_at
                minutes_since_progress = int(time_since_progress.total_seconds() / 60)
                is_stale = time_since_progress.total_seconds() > stale_threshold
            else:
                # No progress reported - use started_at or created_at
                if job.started_at:
                    time_since_progress = now - job.started_at
                else:
                    time_since_progress = now - job.created_at
                minutes_since_progress = int(time_since_progress.total_seconds() / 60)
                is_stale = time_since_progress.total_seconds() > stale_threshold

            # Determine health status
            if is_stale:
                health_status = "stale"
            elif minutes_since_progress > (stale_threshold / 2 / 60):  # Half threshold
                health_status = "warning"
            else:
                health_status = "healthy"

            return {
                "job_id": job_id,
                "status": job.status,
                "is_stale": is_stale,
                "minutes_since_progress": minutes_since_progress,
                "last_progress_at": job.last_progress_at.isoformat() if job.last_progress_at else None,
                "health_status": health_status,
            }

    except ValueError:
        # Re-raise validation errors
        raise
    except Exception as e:
        logger.error(f"[get_job_health_status] Error checking health status: {e}", exc_info=True)
        raise ValueError(f"Failed to get job health status: {e!s}")
