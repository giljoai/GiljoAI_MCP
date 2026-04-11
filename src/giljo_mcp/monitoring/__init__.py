# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent Health Monitoring System.

Provides background monitoring of agent job health with automatic detection
of waiting timeouts, stalled jobs, and heartbeat failures.

Components:
- HealthCheckConfig: Configurable monitoring thresholds
- AgentHealthStatus: Health status data structure
- AgentHealthMonitor: Background monitoring service
"""

from src.giljo_mcp.monitoring.agent_health_monitor import AgentHealthMonitor
from src.giljo_mcp.monitoring.health_config import AgentHealthStatus, HealthCheckConfig


__all__ = ["AgentHealthMonitor", "AgentHealthStatus", "HealthCheckConfig"]
