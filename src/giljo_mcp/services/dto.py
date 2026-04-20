# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Parameter dataclasses for service methods with many arguments.

These group related parameters into a single object, reducing method signatures
and improving readability without changing behaviour.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class BroadcastMessageContext:
    """Groups the parameters of MessageRoutingService._broadcast_message_events."""

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


@dataclass
class MemoryEntryCreateParams:
    """Groups parameters for ProductMemoryRepository.create_entry().

    Required fields are positional. Optional fields have defaults matching
    the current method signature defaults.

    Sprint 002e: Extracted from 23-parameter method signature.
    """

    # Required
    tenant_key: str
    product_id: UUID
    sequence: int
    entry_type: str
    source: str
    timestamp: datetime

    # Optional (defaults match current repository signature)
    project_id: Optional[UUID] = None
    project_name: Optional[str] = None
    summary: Optional[str] = None
    key_outcomes: Optional[list[str]] = None
    decisions_made: Optional[list[str]] = None
    git_commits: Optional[list[dict[str, Any]]] = None
    deliverables: Optional[list[str]] = None
    metrics: Optional[dict[str, Any]] = None
    priority: int = 3
    significance_score: float = 0.5
    token_estimate: Optional[int] = None
    tags: Optional[list[str]] = field(default=None)
    author_job_id: Optional[UUID] = None
    author_name: Optional[str] = None
    author_type: Optional[str] = None
