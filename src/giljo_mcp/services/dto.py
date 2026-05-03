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
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class BroadcastMessageContext:
    """Groups the parameters of MessageRoutingService._broadcast_message_events."""

    session: AsyncSession
    messages: list
    message_id: str | None
    project: Any
    tenant_key: str
    to_agents: list[str]
    resolved_to_agents: list[str]
    from_agent: str | None
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
    phase: int | None
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
    project_id: UUID | None = None
    project_name: str | None = None
    summary: str | None = None
    key_outcomes: list[str] | None = None
    decisions_made: list[str] | None = None
    git_commits: list[dict[str, Any]] | None = None
    deliverables: list[str] | None = None
    metrics: dict[str, Any] | None = None
    priority: int = 3
    significance_score: float = 0.5
    token_estimate: int | None = None
    tags: list[str] | None = field(default=None)
    author_job_id: UUID | None = None
    author_name: str | None = None
    author_type: str | None = None
