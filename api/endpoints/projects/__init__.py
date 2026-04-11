# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Projects Module - Handover 0125

Consolidated project endpoints using ProjectService.

Module Structure:
- crud.py: CRUD operations (create, list, get, update)
- lifecycle.py: Lifecycle management (activate, cancel, restore, cancel-staging)
- status.py: Status queries (status, summary)
- completion.py: Completion workflow (complete, close-out, continue-working)

All routers use /api/v1/projects prefix and projects tag.
"""

from fastapi import APIRouter

from . import completion, crud, lifecycle, status


# Create main router for projects module
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Include all sub-routers
router.include_router(crud.router)
router.include_router(lifecycle.router)
router.include_router(status.router)
router.include_router(completion.router)

__all__ = ["router"]
