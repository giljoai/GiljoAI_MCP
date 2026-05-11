# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Task Statuses API package (FE-5041 Phase 1).

Exposes the canonical :class:`giljo_mcp.domain.task_status.TaskStatus`
metadata as a read-only endpoint at ``GET /api/v1/task-statuses/``.
The frontend ``TaskStatusBadge.vue`` consumes this endpoint to render
labels and resolve color tokens, replacing the hardcoded literals at
``frontend/src/components/TaskStatusBadge.vue:50-57``.

Mirrors the existing ``api/endpoints/project_statuses`` pattern.
"""

from fastapi import APIRouter

from . import routes


router = APIRouter(prefix="/api/v1/task-statuses", tags=["task-statuses"])
router.include_router(routes.router)

__all__ = ["router"]
