# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the Elastic License 2.0.
# See LICENSE in the project root for terms.
# [CE] Community Edition.

"""Task Statuses API endpoint (FE-5041 Phase 1).

Routes
------
- ``GET /`` -- return the canonical :class:`TaskStatus` metadata in
  declaration order.

The endpoint is read-only (no DB query -- the metadata is produced from
the in-memory :data:`TASK_STATUS_META` dict). Tenant isolation still
applies via the standard auth dependency: only authenticated users can
fetch the metadata. The payload is identical for every tenant.
"""

import logging

from fastapi import APIRouter, Depends

from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.domain.task_status import TASK_STATUS_META, TaskStatus
from giljo_mcp.models import User

from .schemas import TaskStatusResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[TaskStatusResponse])
async def list_task_statuses(
    current_user: User = Depends(get_current_active_user),
) -> list[TaskStatusResponse]:
    """Return the canonical task-status metadata in declaration order."""

    # Authentication-only gate: ``current_user`` is bound for that
    # purpose. The metadata payload is the same for every tenant, so we
    # don't filter by tenant_key here.
    del current_user

    return [
        TaskStatusResponse(
            value=member.value,
            label=TASK_STATUS_META[member].label,
            color_token=TASK_STATUS_META[member].color_token,
            is_lifecycle_finished=TASK_STATUS_META[member].is_lifecycle_finished,
        )
        for member in TaskStatus
    ]
