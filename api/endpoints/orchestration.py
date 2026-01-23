"""
Orchestration compatibility module.

Provides the symbols and routes expected by older tests that import
`api.endpoints.orchestration`, while delegating to the modern
agent_jobs orchestration endpoints and the OrchestrationService.

This keeps the modular design (agent_jobs package + services) while
preserving import paths and public APIs relied on by tests and tools.

Handover 0450: Removed ProjectOrchestrator re-export - methods moved to OrchestrationService.
"""

from __future__ import annotations

from fastapi import APIRouter

from .agent_jobs import orchestration as agent_jobs_orchestration


# Expose a router that mirrors the old /api/orchestration routes by
# including the agent_jobs orchestration endpoints under the expected
# prefix. The exact route shapes remain defined in the agent_jobs module.
router = APIRouter()

# Mount the existing orchestration endpoints under /api/orchestration/*
router.include_router(agent_jobs_orchestration.router, prefix="")


__all__ = ["router"]

