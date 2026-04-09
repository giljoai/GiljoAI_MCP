# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Agent Jobs Module - Handover 0124

Consolidated agent job endpoints using OrchestrationService.

Module Structure:
- lifecycle.py: Spawn, acknowledge, complete, error
- status.py: Get status, list pending, get mission
- progress.py: Progress reporting
- orchestration.py: Workflow status, launch project, launch implementation
- simple_handover.py: Simple 360 Memory-based handover (Handover 0461c)
- operations.py: Cancel, force-fail, health endpoints (Handover 0107)
- executions.py: Agent execution instances for job (Handover 0366d-1)
- messages.py: Message content for MessageAuditModal (Handover 0387g)

All routers are exported with /api/agent-jobs prefix and agent-jobs tag.
Operations router also exported separately with /api/jobs prefix for compatibility.

Note: succession.py removed in Handover 0700d - use simple_handover.py instead.
Note: table_view.py, filters.py removed in Handover 0729 (unused endpoints).
Note: regenerate-mission endpoint removed in Handover 0729 (never integrated).
"""

from fastapi import APIRouter

from . import (
    executions,
    lifecycle,
    messages,
    operations,
    orchestration,
    progress,
    simple_handover,
    status,
)

# Create main router for agent_jobs module
router = APIRouter(prefix="/api/agent-jobs", tags=["agent-jobs"])

# Include all sub-routers
router.include_router(lifecycle.router)
router.include_router(status.router)
router.include_router(progress.router)
router.include_router(orchestration.router)
router.include_router(simple_handover.router)  # Handover 0461c (authoritative handover mechanism)
router.include_router(executions.router)  # Handover 0366d-1
router.include_router(messages.router)  # Handover 0387g

# Create separate router for job operations (Handover 0107)
# Using /api/jobs prefix for compatibility with existing tools
jobs_router = APIRouter(prefix="/api/jobs", tags=["job-operations"])
jobs_router.include_router(operations.router)

__all__ = ["jobs_router", "router"]
