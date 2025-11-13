"""
Agent Jobs Module - Handover 0124

Consolidated agent job endpoints using OrchestrationService.

Module Structure:
- lifecycle.py: Spawn, acknowledge, complete, error
- status.py: Get status, list pending, get mission
- progress.py: Progress reporting
- orchestration.py: Orchestrate project, workflow status, regenerate mission, launch project
- succession.py: Orchestrator succession (Handover 0505)

All routers are exported with /api/agent-jobs prefix and agent-jobs tag.
"""

from fastapi import APIRouter

from . import lifecycle, orchestration, progress, status, succession


# Create main router for agent_jobs module
router = APIRouter(prefix="/api/agent-jobs", tags=["agent-jobs"])

# Include all sub-routers
router.include_router(lifecycle.router)
router.include_router(status.router)
router.include_router(progress.router)
router.include_router(orchestration.router)
router.include_router(succession.router)

__all__ = ["router"]
