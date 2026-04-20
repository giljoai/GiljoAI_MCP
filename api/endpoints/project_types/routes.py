# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Project Types API Endpoints - Handover 0440a Phase 2

Routes:
- GET    / - List project types (triggers lazy seeding)
- POST   / - Create custom project type
- PUT    /{type_id} - Update project type
- DELETE /{type_id} - Delete project type (protected)

All endpoints enforce tenant isolation via get_current_active_user dependency.
BE-5022a: All DB access routed through project_type_ops service functions.
"""

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.dependencies import get_db
from giljo_mcp.auth.dependencies import get_current_active_user
from giljo_mcp.models import User

from .crud_ops import (
    create_project_type,
    delete_project_type,
    ensure_default_types_seeded,
    get_project_count_for_type,
    list_project_types,
    update_project_type,
)
from .schemas import ProjectTypeCreate, ProjectTypeResponse, ProjectTypeUpdate


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=list[ProjectTypeResponse])
async def list_types(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> list[ProjectTypeResponse]:
    """List all project types for the current tenant.

    Triggers lazy seeding of default types on first access.
    """
    tenant_key = current_user.tenant_key

    await ensure_default_types_seeded(session, tenant_key)

    types = await list_project_types(session, tenant_key)
    return [
        ProjectTypeResponse(
            id=str(pt.id),
            tenant_key=pt.tenant_key,
            abbreviation=pt.abbreviation,
            label=pt.label,
            color=pt.color,
            sort_order=pt.sort_order,
            project_count=pt.project_count,
            created_at=pt.created_at,
            updated_at=pt.updated_at,
        )
        for pt in types
    ]


@router.post("/", response_model=ProjectTypeResponse, status_code=status.HTTP_201_CREATED)
async def create_type(
    data: ProjectTypeCreate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectTypeResponse:
    """Create a custom project type."""
    tenant_key = current_user.tenant_key

    try:
        pt = await create_project_type(
            session,
            tenant_key,
            abbreviation=data.abbreviation,
            label=data.label,
            color=data.color,
            sort_order=data.sort_order,
        )
    except ValueError:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Project type already exists.") from None

    return ProjectTypeResponse(
        id=str(pt.id),
        tenant_key=pt.tenant_key,
        abbreviation=pt.abbreviation,
        label=pt.label,
        color=pt.color,
        sort_order=pt.sort_order,
        project_count=0,
        created_at=pt.created_at,
        updated_at=pt.updated_at,
    )


@router.put("/{type_id}", response_model=ProjectTypeResponse)
async def update_type(
    type_id: str,
    data: ProjectTypeUpdate,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> ProjectTypeResponse:
    """Update a project type (label, color, sort_order only)."""
    tenant_key = current_user.tenant_key

    try:
        update_fields = data.model_dump(exclude_unset=True)
        pt = await update_project_type(session, tenant_key, type_id, **update_fields)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project type not found.") from None

    count = await get_project_count_for_type(session, tenant_key, type_id)

    return ProjectTypeResponse(
        id=str(pt.id),
        tenant_key=pt.tenant_key,
        abbreviation=pt.abbreviation,
        label=pt.label,
        color=pt.color,
        sort_order=pt.sort_order,
        project_count=count,
        created_at=pt.created_at,
        updated_at=pt.updated_at,
    )


@router.delete("/{type_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_type(
    type_id: str,
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_db),
) -> None:
    """Delete a project type (fails if projects are assigned)."""
    tenant_key = current_user.tenant_key

    try:
        await delete_project_type(session, tenant_key, type_id)
    except ValueError as e:
        error_msg = str(e)
        if "not found" in error_msg:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=error_msg) from None
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=error_msg) from None
