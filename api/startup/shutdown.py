"""Shutdown module

Handles graceful shutdown of all services and connections.
Extracted from api/app.py lifespan function (lines ~595-649).
"""

import asyncio
import logging

from api.app import APIState


logger = logging.getLogger(__name__)


async def shutdown(state: APIState) -> None:
    """Gracefully shutdown all services, tasks, and connections

    Args:
        state: APIState instance with active services and connections

    Note:
        Errors are logged but do not prevent shutdown from continuing
    """
    logger.info("Shutting down GiljoAI MCP API...")

    # Cancel background tasks
    try:
        logger.info("Canceling background tasks...")
        if state.heartbeat_task:
            state.heartbeat_task.cancel()
            try:
                await state.heartbeat_task
            except asyncio.CancelledError:
                pass
        if state.cleanup_task:
            state.cleanup_task.cancel()
            try:
                await state.cleanup_task
            except asyncio.CancelledError:
                pass
        if state.metrics_sync_task:
            state.metrics_sync_task.cancel()
            try:
                await state.metrics_sync_task
            except asyncio.CancelledError:
                pass
        logger.info("Background tasks canceled")
    except Exception as e:
        logger.error(f"Error canceling background tasks: {e}", exc_info=True)

    # Stop health monitoring gracefully
    if state.health_monitor:
        try:
            logger.info("Stopping agent health monitoring...")
            await state.health_monitor.stop()
            logger.info("Agent health monitoring stopped")
        except Exception as e:
            logger.error(f"Error stopping health monitor: {e}", exc_info=True)

    # Close all WebSocket connections
    try:
        logger.info("Closing WebSocket connections...")
        for ws in state.connections.values():
            await ws.close()
        logger.info("WebSocket connections closed")
    except Exception as e:
        logger.error(f"Error closing WebSocket connections: {e}", exc_info=True)

    # Close database
    if state.db_manager:
        try:
            logger.info("Closing database connection...")
            await state.db_manager.close_async()  # Use close_async() for async engine
            logger.info("Database connection closed")
        except Exception as e:
            logger.error(f"Error closing database: {e}", exc_info=True)
