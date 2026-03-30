"""
Parameter dataclasses for service methods with many arguments.

These group related parameters into a single object, reducing method signatures
and improving readability without changing behaviour.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class BroadcastMessageContext:
    """Groups the parameters of MessageService._broadcast_message_events."""

    session: AsyncSession
    messages: list
    message_id: Optional[str]
    project: Any
    tenant_key: str
    to_agents: list[str]
    resolved_to_agents: list[str]
    from_agent: Optional[str]
    message_type: str
    content: str
    priority: str
    sender_execution: Any


@dataclass
class BroadcastAgentCreatedContext:
    """Groups the parameters of JobLifecycleService._broadcast_agent_created."""

    tenant_key: str
    project_id: str
    agent_execution: Any
    agent_id: str
    job_id: str
    agent_display_name: str
    agent_name: str
    mission: str
    phase: Optional[int]
    created_at: datetime
