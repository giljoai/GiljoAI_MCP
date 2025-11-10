"""
Products Module - Handover 0126

Consolidated product endpoints.

NOTE: ProductService does not exist yet. Most operations currently use direct
database access. Future work: Create ProductService and refactor endpoints.

Module Structure:
- crud.py: CRUD operations (create, list, get, update, list deleted)
- lifecycle.py: Lifecycle management (activate, deactivate, delete, restore, cascade impact, token estimate)
- vision.py: Vision document operations (upload, get chunks)

All routers use /api/v1/products prefix and Products tag.
"""

from fastapi import APIRouter

from . import crud, lifecycle, vision


# Create main router for products module
router = APIRouter(prefix="/api/v1/products", tags=["Products"])

# Include all sub-routers
router.include_router(crud.router)
router.include_router(lifecycle.router)
router.include_router(vision.router)

__all__ = ["router"]
