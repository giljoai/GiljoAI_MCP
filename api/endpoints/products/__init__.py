"""
Products Module - Handover 0126

Consolidated product endpoints.

NOTE: ProductService does not exist yet. Most operations currently use direct
database access. Future work: Create ProductService and refactor endpoints.

Module Structure:
- crud.py: CRUD operations (create, list, get, update, list deleted)
- lifecycle.py: Lifecycle management (activate, deactivate, delete, restore, cascade impact, token estimate)
- vision.py: Vision document operations (upload, get chunks)
- github.py: GitHub integration settings (Handover 0137 - DEPRECATED)
- git_integration.py: Simplified Git integration (Handover 013B - ACTIVE)

All routers use /api/v1/products prefix and Products tag.
"""

from fastapi import APIRouter

from . import crud, git_integration, github, lifecycle, vision


# Create main router for products module
router = APIRouter(prefix="/api/v1/products", tags=["Products"])

# Include all sub-routers
router.include_router(crud.router)
router.include_router(lifecycle.router)
router.include_router(vision.router)
router.include_router(github.router)  # DEPRECATED - kept for backward compatibility
router.include_router(git_integration.router)  # NEW - Handover 013B

__all__ = ["router"]
