# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Project Type service-layer operations.

Extracted from api/endpoints/project_types/crud_ops.py (Sprint 003a)
to eliminate the backward import from src/giljo_mcp/services/project_service.py.

BE-5022a: All CRUD + query operations consolidated here so endpoints never
touch session directly.

These functions are pure data-access helpers with no api/ dependencies.
"""

import logging
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models.projects import ProjectType
from giljo_mcp.repositories.project_type_repository import ProjectTypeRepository
from giljo_mcp.utils.log_sanitizer import sanitize


logger = logging.getLogger(__name__)

_repo = ProjectTypeRepository()

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
    count = await _repo.count_for_tenant(session, tenant_key)
    if count and count > 0:
        return

    logger.info("Seeding %d default project types for tenant %s", len(DEFAULT_PROJECT_TYPES), sanitize(tenant_key))

    for i, pt_def in enumerate(DEFAULT_PROJECT_TYPES):
        project_type = ProjectType(
            tenant_key=tenant_key,
            abbreviation=pt_def["abbr"],
            label=pt_def["label"],
            color=pt_def["color"],
            sort_order=i,
        )
        await _repo.add_project_type(session, project_type)

    await _repo.flush(session)


async def list_project_types(session: AsyncSession, tenant_key: str) -> list[Any]:
    """List all project types for a tenant, ordered by sort_order.

    Each returned object has a ``project_count`` attribute indicating how many
    projects are assigned to that type.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation

    Returns:
        List of ProjectType objects with project_count attribute
    """
    rows = await _repo.list_with_project_counts(session, tenant_key)

    types_with_counts = []
    for row in rows:
        pt = row[0]
        pt.project_count = row[1] or 0
        types_with_counts.append(pt)

    return types_with_counts


# ---------------------------------------------------------------------------
# CRUD operations (BE-5022a: moved from api/endpoints/project_types/crud_ops.py)
# ---------------------------------------------------------------------------

UPDATABLE_FIELDS = {"label", "color", "sort_order"}


async def create_project_type(
    session: AsyncSession,
    tenant_key: str,
    *,
    abbreviation: str,
    label: str,
    color: str = "#607D8B",
    sort_order: int = 0,
) -> ProjectType:
    """Create a new project type for a tenant.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        abbreviation: 2-4 uppercase letter abbreviation
        label: Human-readable label
        color: Hex color for UI display
        sort_order: Display ordering in UI dropdowns

    Returns:
        Created ProjectType instance

    Raises:
        ValueError: If abbreviation already exists for this tenant
    """
    existing = await _repo.get_by_abbreviation(session, tenant_key, abbreviation)
    if existing:
        raise ValueError(f"Project type with abbreviation '{abbreviation}' already exists for this tenant")

    project_type = ProjectType(
        tenant_key=tenant_key,
        abbreviation=abbreviation,
        label=label,
        color=color,
        sort_order=sort_order,
    )
    await _repo.add_project_type(session, project_type)
    project_type = await _repo.flush_and_refresh(session, project_type)

    logger.info(
        "Created project type '%s' (%s) for tenant %s",
        sanitize(abbreviation),
        sanitize(label),
        sanitize(tenant_key),
    )
    return project_type


async def update_project_type(
    session: AsyncSession,
    tenant_key: str,
    type_id: str,
    **fields: Any,
) -> ProjectType:
    """Update an existing project type.

    Only label, color, and sort_order can be changed. Abbreviation is immutable.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: ID of the project type to update
        **fields: Field values to update (must be in UPDATABLE_FIELDS allowlist)

    Returns:
        Updated ProjectType instance

    Raises:
        ValueError: If type not found or invalid field supplied
    """
    project_type = await _repo.get_by_id(session, tenant_key, type_id)

    if not project_type:
        raise ValueError(f"Project type '{type_id}' not found for this tenant")

    for field, value in fields.items():
        if field not in UPDATABLE_FIELDS:
            raise ValueError(f"Field '{field}' is not updatable on ProjectType")
        setattr(project_type, field, value)

    project_type = await _repo.flush_and_refresh(session, project_type)

    logger.info("Updated project type '%s' for tenant %s", sanitize(project_type.abbreviation), sanitize(tenant_key))
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
    project_type = await _repo.get_by_id(session, tenant_key, type_id)

    if not project_type:
        raise ValueError(f"Project type '{type_id}' not found for this tenant")

    project_count = await get_project_count_for_type(session, tenant_key, type_id)

    if project_count > 0:
        raise ValueError(
            f"Cannot delete project type '{project_type.abbreviation}': "
            f"{project_count} project(s) assigned. Reassign or remove them first."
        )

    await _repo.delete_project_type(session, project_type)

    logger.info("Deleted project type '%s' for tenant %s", sanitize(project_type.abbreviation), sanitize(tenant_key))


async def get_project_count_for_type(session: AsyncSession, tenant_key: str, type_id: str) -> int:
    """Get the count of projects assigned to a project type.

    Args:
        session: Async database session
        tenant_key: Tenant identifier for isolation
        type_id: Project type ID

    Returns:
        Number of projects assigned to this type
    """
    return await _repo.get_project_count_for_type(session, tenant_key, type_id)


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
    return await _repo.get_next_series_number(session, tenant_key, type_id)


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
    used_numbers = await _repo.get_used_series_numbers(session, tenant_key, type_id)

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
    type_id: Optional[str],
    series_number: int,
    subseries: Optional[str] = None,
    exclude_project_id: Optional[str] = None,
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
    available = await _repo.check_series_available(
        session, tenant_key, type_id, series_number, subseries, exclude_project_id
    )
    return {"available": available}


async def get_used_subseries(
    session: AsyncSession,
    tenant_key: str,
    type_id: Optional[str],
    series_number: int,
    exclude_project_id: Optional[str] = None,
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
    used = await _repo.get_used_subseries(session, tenant_key, type_id, series_number, exclude_project_id)
    return {"used_subseries": used}
