# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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
