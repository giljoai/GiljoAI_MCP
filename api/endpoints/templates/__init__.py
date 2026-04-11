# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Templates Module - Handover 0126

Consolidated template endpoints using TemplateService.

Module Structure:
- crud.py: CRUD operations (create, list, get, update, delete, stats)
- history.py: History management (history, restore, reset)
- preview.py: Preview and diff operations

All routers use /api/v1/templates prefix and templates tag.
"""

from fastapi import APIRouter

from . import crud, history, preview


# Create main router for templates module
router = APIRouter(prefix="/api/v1/templates", tags=["templates"])

# Include all sub-routers
router.include_router(crud.router)
router.include_router(history.router)
router.include_router(preview.router)

__all__ = ["router"]
