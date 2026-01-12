"""
Health monitoring configuration and data structures.

Provides configurable thresholds for agent health monitoring and
data structures for tracking health status.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict


@dataclass
class HealthCheckConfig:
    """
    Configurable thresholds for health monitoring.

    Attributes:
        waiting_timeout_minutes: Timeout for jobs stuck in 'waiting' state
        active_no_progress_minutes: Timeout for active jobs without progress updates
        heartbeat_timeout_minutes: Default timeout for complete silence
        timeout_overrides: Agent-type-specific timeout overrides
        scan_interval_seconds: How often to scan for unhealthy jobs
        auto_fail_on_timeout: Whether to automatically fail timed-out jobs
        notify_orchestrator: Whether to notify orchestrator of health issues
    """

    # Timeout thresholds (minutes)
    waiting_timeout_minutes: int = 2
    active_no_progress_minutes: int = 5
    heartbeat_timeout_minutes: int = 10

    # Per-agent type overrides
    timeout_overrides: Dict[str, int] = field(default_factory=lambda: {
        "orchestrator": 15,  # Orchestrators get more time
        "analyzer": 5,
        "implementer": 10,
        "tester": 8,
        "reviewer": 6,
        "documenter": 5
    })

    # Monitoring behavior
    scan_interval_seconds: int = 300  # 5 minutes
    auto_fail_on_timeout: bool = False  # Conservative default
    notify_orchestrator: bool = True

    def get_timeout_for_agent(self, agent_display_name: str) -> int:
        """
        Get timeout for specific agent type.

        Args:
            agent_display_name: Type of agent (orchestrator, implementer, etc.)

        Returns:
            Timeout in minutes for this agent type
        """
        return self.timeout_overrides.get(agent_display_name, self.heartbeat_timeout_minutes)


@dataclass
class AgentHealthStatus:
    """
    Health status for a single agent job.

    Attributes:
        job_id: Unique job identifier
        agent_display_name: Type of agent (orchestrator, implementer, etc.)
        current_status: Current job status (waiting, active, etc.)
        health_state: Health state (healthy, warning, critical, timeout)
        last_update: Timestamp of last activity
        minutes_since_update: Minutes since last activity
        issue_description: Human-readable description of the issue
        recommended_action: Recommended remediation action
    """

    job_id: str
    agent_display_name: str
    current_status: str  # Job status (waiting, active, etc.)
    health_state: str  # Health state (healthy, warning, critical, timeout)
    last_update: datetime
    minutes_since_update: float
    issue_description: str
    recommended_action: str
