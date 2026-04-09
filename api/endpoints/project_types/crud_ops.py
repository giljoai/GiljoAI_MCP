# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
CRUD operations for Project Types - Handover 0440a Phase 2

All functions accept an AsyncSession and tenant_key to enforce
multi-tenant isolation at the query level. Raises ValueError on
business rule violations (post-0480 pattern: exceptions, not dicts).
"""

import logging
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.projects import ProjectType

from .schemas import ProjectTypeCreate, ProjectTypeUpdate

logger = logging.getLogger(__name__)

DEFAULT_PROJECT_TYPES: list[dict[str, Any]] = [
    {"abbr": "BE", "label": "Backend", "color": "#4CAF50"},
    {"abbr": "FE", "label": "Frontend", "color": "#2196F3"},
    {"abbr": "DB", "label": "Database", "color": "#FF9800"},
    {"abbr": "UI", "label": "UI/UX", "color": "#9C27B0"},
    {"abbr": "API", "label": "API/Integration", "color": "#00BCD4"},
    {"abbr": "INF", "label": "Infrastructure", "color": "#795548"},
    {"abbr": "DOC", "label": "Documentation", "color": "#607D8B"},
    {"abbr": "SEC", "label": "Security", "color": "#F44336"},
]


async def ensure_default_types_seeded(session: AsyncSession, tenant_key: str) -> None:
    """Lazily seed default project types for a tenant if none exist.

    This is idempotent: if the tenant already has project types, no action is taken.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
    """
    result = await session.execute(
        select(func.count()).select_from(ProjectType).where(ProjectType.tenant_key == tenant_key)
    )
    count = result.scalar()
    if count and count > 0:
        return

    logger.info(f"Seeding {len(DEFAULT_PROJECT_TYPES)} default project types for tenant {tenant_key}")

    for i, pt_def in enumerate(DEFAULT_PROJECT_TYPES):
        project_type = ProjectType(
            tenant_key=tenant_key,
            abbreviation=pt_def["abbr"],
            label=pt_def["label"],
            color=pt_def["color"],
            sort_order=i,
        )
        session.add(project_type)

    await session.flush()


async def list_project_types(session: AsyncSession, tenant_key: str) -> list[Any]:
    """List all project types for a tenant, ordered by sort_order.

    Each returned object has a `project_count` attribute indicating how many
    projects are assigned to that type.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation

    Returns:
        List of ProjectType objects with project_count attribute
    """
    project_count_subq = (
        select(func.count(Project.id))
        .where(
            Project.project_type_id == ProjectType.id,
            Project.tenant_key == tenant_key,
        )
        .correlate(ProjectType)
        .scalar_subquery()
        .label("project_count")
    )

    stmt = (
        select(ProjectType, project_count_subq)
        .where(ProjectType.tenant_key == tenant_key)
        .order_by(ProjectType.sort_order, ProjectType.abbreviation)
    )

    result = await session.execute(stmt)
    rows = result.all()

    types_with_counts = []
    for row in rows:
        pt = row[0]
        pt.project_count = row[1] or 0
        types_with_counts.append(pt)

    return types_with_counts


async def create_project_type(session: AsyncSession, tenant_key: str, data: ProjectTypeCreate) -> ProjectType:
    """Create a new project type for a tenant.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        data: Validated creation data

    Returns:
        Created ProjectType instance

    Raises:
        ValueError: If abbreviation already exists for this tenant
    """
    existing = await session.execute(
        select(ProjectType).where(
            ProjectType.tenant_key == tenant_key,
            ProjectType.abbreviation == data.abbreviation,
        )
    )
    if existing.scalar_one_or_none():
        raise ValueError(f"Project type with abbreviation '{data.abbreviation}' already exists for this tenant")

    project_type = ProjectType(
        tenant_key=tenant_key,
        abbreviation=data.abbreviation,
        label=data.label,
        color=data.color,
        sort_order=data.sort_order,
    )
    session.add(project_type)
    await session.flush()
    await session.refresh(project_type)

    logger.info(f"Created project type '{data.abbreviation}' ({data.label}) for tenant {tenant_key}")
    return project_type


async def update_project_type(
    session: AsyncSession, tenant_key: str, type_id: str, data: ProjectTypeUpdate
) -> ProjectType:
    """Update an existing project type.

    Only label, color, and sort_order can be changed. Abbreviation is immutable.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: ID of the project type to update
        data: Validated partial update data

    Returns:
        Updated ProjectType instance

    Raises:
        ValueError: If type not found for this tenant
    """
    result = await session.execute(
        select(ProjectType).where(
            ProjectType.id == type_id,
            ProjectType.tenant_key == tenant_key,
        )
    )
    project_type = result.scalar_one_or_none()

    if not project_type:
        raise ValueError(f"Project type '{type_id}' not found for this tenant")

    update_fields = data.model_dump(exclude_unset=True)
    for field, value in update_fields.items():
        setattr(project_type, field, value)

    await session.flush()
    await session.refresh(project_type)

    logger.info(f"Updated project type '{project_type.abbreviation}' for tenant {tenant_key}")
    return project_type


async def delete_project_type(session: AsyncSession, tenant_key: str, type_id: str) -> None:
    """Delete a project type if no projects are assigned to it.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: ID of the project type to delete

    Raises:
        ValueError: If type not found or has projects assigned
    """
    result = await session.execute(
        select(ProjectType).where(
            ProjectType.id == type_id,
            ProjectType.tenant_key == tenant_key,
        )
    )
    project_type = result.scalar_one_or_none()

    if not project_type:
        raise ValueError(f"Project type '{type_id}' not found for this tenant")

    count_result = await session.execute(
        select(func.count(Project.id)).where(
            Project.project_type_id == type_id,
            Project.tenant_key == tenant_key,
        )
    )
    project_count = count_result.scalar() or 0

    if project_count > 0:
        raise ValueError(
            f"Cannot delete project type '{project_type.abbreviation}': "
            f"{project_count} project(s) assigned. Reassign or remove them first."
        )

    await session.delete(project_type)
    await session.flush()

    logger.info(f"Deleted project type '{project_type.abbreviation}' for tenant {tenant_key}")


async def get_next_series_number(session: AsyncSession, tenant_key: str, type_id: str) -> int:
    """Get the next available series number for a project type.

    Returns max(series_number) + 1, or 1 if no projects exist for this type.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: Project type ID

    Returns:
        Next available series number (1-based)
    """
    result = await session.execute(
        select(func.max(Project.series_number)).where(
            Project.project_type_id == type_id,
            Project.tenant_key == tenant_key,
            Project.deleted_at.is_(None),
        )
    )
    max_num = result.scalar()
    return (max_num or 0) + 1


async def get_available_series_numbers(
    session: AsyncSession, tenant_key: str, type_id: str, limit: int = 5
) -> list[int]:
    """Get available series numbers, prioritizing gaps in the sequence.

    Returns gap numbers first, then continues after the highest used number.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: Project type ID
        limit: Maximum number of suggestions to return

    Returns:
        List of available series numbers, gaps first
    """
    result = await session.execute(
        select(Project.series_number)
        .where(
            Project.project_type_id == type_id,
            Project.tenant_key == tenant_key,
            Project.series_number.is_not(None),
            Project.deleted_at.is_(None),
        )
        .order_by(Project.series_number)
    )
    used_numbers = set(result.scalars().all())

    if not used_numbers:
        return list(range(1, limit + 1))

    max_used = max(used_numbers)
    available: list[int] = []

    # Find gaps in the sequence first
    for num in range(1, max_used + 1):
        if num not in used_numbers:
            available.append(num)
            if len(available) >= limit:
                return available

    # Fill remaining with numbers after max
    next_num = max_used + 1
    while len(available) < limit:
        available.append(next_num)
        next_num += 1

    return available


async def check_series_available(
    session: AsyncSession,
    tenant_key: str,
    type_id: str | None,
    series_number: int,
    subseries: str | None = None,
    exclude_project_id: str | None = None,
) -> dict[str, Any]:
    """Check if a specific series number combination is available.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: Project type ID (None checks untyped projects)
        series_number: The series number to check
        subseries: Optional subseries letter (a-z)
        exclude_project_id: Exclude this project ID (for edit mode)

    Returns:
        {"available": bool}
    """
    query = select(Project.id).where(
        Project.tenant_key == tenant_key,
        Project.series_number == series_number,
        Project.deleted_at.is_(None),
    )
    if type_id:
        query = query.where(Project.project_type_id == type_id)
    else:
        query = query.where(Project.project_type_id.is_(None))

    if subseries is not None:
        query = query.where(Project.subseries == subseries)
    else:
        query = query.where(Project.subseries.is_(None))

    if exclude_project_id:
        query = query.where(Project.id != exclude_project_id)

    result = await session.execute(query)
    existing_id = result.scalar_one_or_none()
    return {"available": existing_id is None}


async def get_used_subseries(
    session: AsyncSession,
    tenant_key: str,
    type_id: str | None,
    series_number: int,
    exclude_project_id: str | None = None,
) -> dict[str, Any]:
    """Get all subseries letters already used for a type + series_number combo.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: Project type ID (None checks untyped projects)
        series_number: The series number to check
        exclude_project_id: Exclude this project ID (for edit mode)

    Returns:
        {"used_subseries": list[str]}
    """
    query = select(Project.subseries).where(
        Project.tenant_key == tenant_key,
        Project.series_number == series_number,
        Project.subseries.isnot(None),
        Project.deleted_at.is_(None),
    )
    if type_id:
        query = query.where(Project.project_type_id == type_id)
    else:
        query = query.where(Project.project_type_id.is_(None))

    if exclude_project_id:
        query = query.where(Project.id != exclude_project_id)

    result = await session.execute(query)
    used = sorted([row[0] for row in result.all()])
    return {"used_subseries": used}
