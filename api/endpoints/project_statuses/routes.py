# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition -- source-available, single-user use only.

"""Project Statuses API endpoint (BE-5039 Phase 2b).

Routes
------
- ``GET /`` -- return the canonical :class:`ProjectStatus` metadata in
  declaration order.

The endpoint is read-only (no DB query -- the metadata is produced from
the in-memory :data:`PROJECT_STATUS_META` dict). Tenant isolation still
applies via the standard auth dependency: only authenticated users can
fetch the metadata. The payload is identical for every tenant.
"""

import logging

from fastapi import APIRouter, Depends

from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.domain.project_status import PROJECT_STATUS_META, ProjectStatus
from giljo_mcp.models import User

from .schemas import ProjectStatusResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[ProjectStatusResponse])
async def list_project_statuses(
    current_user: User = Depends(get_current_active_user),
) -> list[ProjectStatusResponse]:
    """Return the canonical project-status metadata.

    Order matches :class:`ProjectStatus` declaration order so the
    frontend can render dropdowns / lists with a stable order without
    additional sorting.
    """

    # Authentication-only gate: ``current_user`` is bound for that
    # purpose. The metadata payload is the same for every tenant, so we
    # don't filter by tenant_key here.
    del current_user

    return [
        ProjectStatusResponse(
            value=member.value,
            label=PROJECT_STATUS_META[member].label,
            color_token=PROJECT_STATUS_META[member].color_token,
            is_lifecycle_finished=PROJECT_STATUS_META[member].is_lifecycle_finished,
            is_immutable=PROJECT_STATUS_META[member].is_immutable,
            is_user_mutable_via_mcp=PROJECT_STATUS_META[member].is_user_mutable_via_mcp,
        )
        for member in ProjectStatus
    ]
