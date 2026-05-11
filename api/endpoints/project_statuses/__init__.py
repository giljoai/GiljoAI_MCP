# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Project Statuses API package (BE-5039 Phase 2b).

Exposes the canonical :class:`giljo_mcp.domain.project_status.ProjectStatus`
metadata as a read-only endpoint at ``GET /api/v1/project-statuses/``.
The frontend ``StatusBadge.vue`` consumes this endpoint to render labels
and resolve color tokens, replacing the hardcoded literal at
``frontend/src/components/StatusBadge.vue:21``.

Mirrors the existing ``api/endpoints/taxonomy_types`` pattern.
"""

from fastapi import APIRouter

from . import routes


router = APIRouter(prefix="/api/v1/project-statuses", tags=["project-statuses"])
router.include_router(routes.router)

__all__ = ["router"]
