"""
Silence detector startup module (Handover 0491 Phase 3).

Initializes and starts the SilenceDetector background service that
periodically scans for agents that have gone silent (no MCP activity
past the configurable threshold).
"""

import logging

from api.app import APIState


logger = logging.getLogger(__name__)


async def init_silence_detector(state: APIState) -> None:
    """Initialize the silence detector background service.

    Args:
        state: APIState instance to populate with silence_detector

    Note:
        Does not raise on failure - logs warning and continues startup.
        Follows the same pattern as init_health_monitor.
    """
    try:
        logger.info("Initializing silence detector...")

        from src.giljo_mcp.services.silence_detector import SilenceDetector

        state.silence_detector = SilenceDetector(
            db_manager=state.db_manager,
            ws_manager=state.websocket_manager,
            scan_interval_seconds=60,
        )

        await state.silence_detector.start()
        logger.info("Silence detector started (scan interval: 60s)")

    except Exception:
        logger.exception("Failed to start silence detector")
        logger.warning("Continuing without silence detection")
