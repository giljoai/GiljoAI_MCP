# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""Health monitor initialization module

Handles agent health monitoring service initialization from configuration.
Extracted from api/app.py lifespan function (lines ~414-459).
"""

import logging

from api.app import APIState

logger = logging.getLogger(__name__)


async def init_health_monitor(state: APIState) -> None:
    """Initialize agent health monitoring service if enabled in configuration

    Args:
        state: APIState instance to populate with health_monitor

    Note:
        Does not raise on failure - logs warning and continues startup
    """
    # Start agent health monitoring service (Handover 0107)
    try:
        logger.info("Initializing agent health monitoring...")

        # Load health_monitoring config from ConfigManager raw cache
        health_config_dict = state.config.get_nested("health_monitoring", {})

        # Only start if enabled in config
        if health_config_dict.get("enabled", True):
            from src.giljo_mcp.monitoring.agent_health_monitor import AgentHealthMonitor
            from src.giljo_mcp.monitoring.health_config import HealthCheckConfig

            # Build configuration from config.yaml
            timeout_config = health_config_dict.get("timeouts", {})
            health_config = HealthCheckConfig(
                waiting_timeout_minutes=timeout_config.get("waiting_timeout", 2),
                active_no_progress_minutes=timeout_config.get("active_no_progress", 5),
                heartbeat_timeout_minutes=timeout_config.get("heartbeat_timeout", 10),
                timeout_overrides={
                    "orchestrator": timeout_config.get("orchestrator", 15),
                    "implementer": timeout_config.get("implementer", 10),
                    "tester": timeout_config.get("tester", 8),
                    "analyzer": timeout_config.get("analyzer", 5),
                    "reviewer": timeout_config.get("reviewer", 6),
                    "documenter": timeout_config.get("documenter", 5),
                },
                scan_interval_seconds=health_config_dict.get("scan_interval_seconds", 300),
                auto_fail_on_timeout=health_config_dict.get("auto_fail_on_timeout", False),
                notify_orchestrator=health_config_dict.get("notify_orchestrator", True),
            )

            # Initialize monitor with dependencies
            state.health_monitor = AgentHealthMonitor(
                db_manager=state.db_manager,
                ws_manager=state.websocket_manager,
                config=health_config,
            )

            # Start monitoring service
            await state.health_monitor.start()
            logger.info(f"Agent health monitoring started (scan interval: {health_config.scan_interval_seconds}s)")
        else:
            logger.info("Agent health monitoring disabled in configuration")
    except Exception as e:  # Broad catch: startup resilience, non-fatal initialization
        logger.error(f"Failed to start agent health monitoring: {e}", exc_info=True)
        logger.warning("Continuing without health monitoring")
