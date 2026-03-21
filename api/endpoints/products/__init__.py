"""
Products Module - Handover 0126

Consolidated product endpoints.

NOTE: ProductService does not exist yet. Most operations currently use direct
database access. Future work: Create ProductService and refactor endpoints.

Module Structure:
- crud.py: CRUD operations (create, list, get, update, list deleted)
- lifecycle.py: Lifecycle management (activate, deactivate, delete, restore, cascade impact)
- vision.py: Vision document operations (upload, get chunks)
- git_integration.py: Simplified Git integration (Handover 013B - ACTIVE)

All routers use /api/v1/products prefix and Products tag.
"""

from fastapi import APIRouter

from . import crud, git_integration, lifecycle, memory, tuning, vision


# Create main router for products module
router = APIRouter(prefix="/api/v1/products", tags=["Products"])

# Include all sub-routers
# IMPORTANT: Order matters! Routes with specific paths must come BEFORE
# routes with path parameters like /{product_id} to avoid incorrect matching.
# e.g., /refresh-active must match before /{product_id} treats it as a product ID.
router.include_router(lifecycle.router)  # Has /refresh-active, /deleted
router.include_router(crud.router)  # Has /{product_id} - must come after specific routes
router.include_router(vision.router)
router.include_router(git_integration.router)  # NEW - Handover 013B
router.include_router(memory.router)  # NEW - Handover 0490
router.include_router(tuning.router)  # NEW - Handover 0831

__all__ = ["router"]
