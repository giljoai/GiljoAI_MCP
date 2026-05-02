# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Project Statuses API package (BE-5039 Phase 2b).

Exposes the canonical :class:`giljo_mcp.domain.project_status.ProjectStatus`
metadata as a read-only endpoint at ``GET /api/v1/project-statuses/``.
The frontend ``StatusBadge.vue`` consumes this endpoint to render labels
and resolve color tokens, replacing the hardcoded literal at
``frontend/src/components/StatusBadge.vue:21``.

Mirrors the existing ``api/endpoints/project_types`` pattern.
"""

from fastapi import APIRouter

from . import routes


router = APIRouter(prefix="/api/v1/project-statuses", tags=["project-statuses"])
router.include_router(routes.router)

__all__ = ["router"]
