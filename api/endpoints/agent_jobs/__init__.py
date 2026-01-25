"""
Agent Jobs Module - Handover 0124

Consolidated agent job endpoints using OrchestrationService.

Module Structure:
- lifecycle.py: Spawn, acknowledge, complete, error
- status.py: Get status, list pending, get mission
- progress.py: Progress reporting
- orchestration.py: Orchestrate project, workflow status, regenerate mission, launch project
- succession.py: Orchestrator succession (Handover 0505)
- simple_handover.py: Simple 360 Memory-based handover (Handover 0461c)
- operations.py: Cancel, force-fail, health endpoints (Handover 0107)
- table_view.py: Optimized table view for status board (Handover 0226)
- filters.py: Quick filter options for status board (Handover 0226)
- executions.py: Agent execution instances for job (Handover 0366d-1)
- messages.py: Message content for MessageAuditModal (Handover 0387g)

All routers are exported with /api/agent-jobs prefix and agent-jobs tag.
Operations router also exported separately with /api/jobs prefix for compatibility.
"""

from fastapi import APIRouter

from . import executions, filters, lifecycle, messages, operations, orchestration, progress, simple_handover, status, succession, table_view


# Create main router for agent_jobs module
router = APIRouter(prefix="/api/agent-jobs", tags=["agent-jobs"])

# Include all sub-routers
router.include_router(lifecycle.router)
router.include_router(status.router)
router.include_router(progress.router)
router.include_router(orchestration.router)
router.include_router(succession.router)
router.include_router(simple_handover.router)  # Handover 0461c
router.include_router(table_view.router)  # Handover 0226
router.include_router(filters.router)  # Handover 0226
router.include_router(executions.router)  # Handover 0366d-1
router.include_router(messages.router)  # Handover 0387g

# Create separate router for job operations (Handover 0107)
# Using /api/jobs prefix for compatibility with existing tools
jobs_router = APIRouter(prefix="/api/jobs", tags=["job-operations"])
jobs_router.include_router(operations.router)

__all__ = ["router", "jobs_router"]
