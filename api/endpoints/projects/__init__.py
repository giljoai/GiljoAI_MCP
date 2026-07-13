# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""
Projects Module - Handover 0125

Consolidated project endpoints using ProjectService.

Module Structure:
- crud.py: CRUD operations (create, list, get, update)
- series.py: Series-number management (next/available/check/used-subseries)
- lifecycle.py: Lifecycle management (activate, cancel, restore, cancel-staging)
- status.py: Status queries (status, summary)
- completion.py: Completion workflow (complete, close-out, continue-working)

All routers use /api/v1/projects prefix and projects tag.
"""

from fastapi import APIRouter

from . import completion, crud, lifecycle, series, status


# Create main router for projects module
router = APIRouter(prefix="/api/v1/projects", tags=["projects"])

# Include all sub-routers. series.router is included BEFORE crud.router so its
# static /next-series, /available-series, /check-series, /used-subseries paths
# are matched ahead of crud's catch-all /{project_id} route (INF-6055).
router.include_router(series.router)
router.include_router(crud.router)
router.include_router(lifecycle.router)
router.include_router(status.router)
router.include_router(completion.router)

__all__ = ["router"]
