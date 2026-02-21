"""
Project Types Module - Handover 0440a Phase 2

Provides CRUD endpoints for project type taxonomy management.
All routers use /api/v1/project-types prefix and project-types tag.
"""

from fastapi import APIRouter

from . import routes


router = APIRouter(prefix="/api/v1/project-types", tags=["project-types"])
router.include_router(routes.router)

__all__ = ["router"]
