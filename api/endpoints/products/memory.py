# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
Product Memory Entries Endpoint - Handover 0490

Handles fetching 360 memory entries from the normalized product_memory_entries table.
"""

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select

from src.giljo_mcp.auth.dependencies import get_current_active_user
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry

from .dependencies import get_db_manager
from .models import MemoryEntriesResponse, MemoryEntryResponse


logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{product_id}/memory-entries", response_model=MemoryEntriesResponse)
async def get_memory_entries(
    product_id: str,
    project_id: Optional[str] = Query(None, description="Filter by specific project"),
    limit: int = Query(10, ge=1, le=100, description="Maximum entries to return (1-100)"),
    current_user: User = Depends(get_current_active_user),
    db_manager=Depends(get_db_manager),
) -> MemoryEntriesResponse:
    """
    Get 360 memory entries for a product.

    Fetches memory entries from the normalized product_memory_entries table.
    Entries are product-scoped but linked to projects for traceability.

    Query Parameters:
        project_id: Optional UUID to filter entries by specific project
        limit: Maximum number of entries to return (default: 10, max: 100)

    Returns:
        MemoryEntriesResponse with entries array and counts

    Raises:
        404: Product not found or not accessible to tenant
        422: Invalid UUID format
    """
    tenant_key = current_user.tenant_key

    try:
        UUID(product_id)  # Validate product_id format
        project_uuid = UUID(project_id) if project_id else None
    except ValueError as e:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid UUID format: {e!s}",
        ) from e

    async with db_manager.get_tenant_session_async(tenant_key) as session:
        # Verify product exists and belongs to tenant
        stmt = select(Product).where(
            Product.id == product_id,
            Product.tenant_key == tenant_key,
        )
        result = await session.execute(stmt)
        product = result.scalar_one_or_none()

        if not product:
            raise HTTPException(
                status_code=404,
                detail=f"Product {product_id} not found or not accessible",
            )

        # Build query for entries (direct SQLAlchemy query for better performance)
        query = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == product_id,
                ProductMemoryEntry.tenant_key == tenant_key,
                ~ProductMemoryEntry.deleted_by_user,  # Exclude deleted by default
            )
            .order_by(ProductMemoryEntry.sequence.desc())
        )

        # Apply project filter if provided
        if project_uuid:
            query = query.where(ProductMemoryEntry.project_id == str(project_uuid))

        # Apply limit
        query = query.limit(limit)

        # Execute query
        result = await session.execute(query)
        entries = result.scalars().all()

        # Get total count (all entries for product, including deleted)
        total_count_stmt = select(func.count(ProductMemoryEntry.id)).where(
            ProductMemoryEntry.product_id == product_id,
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        total_count_result = await session.execute(total_count_stmt)
        total_count = total_count_result.scalar_one()

        # Convert entries to response format
        entry_responses = []
        for entry in entries:
            entry_dict = entry.to_dict()
            entry_responses.append(
                MemoryEntryResponse(
                    id=entry_dict["id"],
                    sequence=entry_dict["sequence"],
                    entry_type=entry_dict["type"],
                    source=entry_dict["source"],
                    timestamp=entry_dict["timestamp"],
                    project_id=entry_dict["project_id"],
                    project_name=entry_dict["project_name"],
                    summary=entry_dict["summary"],
                    key_outcomes=entry_dict["key_outcomes"],
                    decisions_made=entry_dict["decisions_made"],
                    git_commits=entry_dict["git_commits"],
                    deliverables=entry_dict["deliverables"],
                    metrics=entry_dict["metrics"],
                    priority=entry_dict["priority"],
                    significance_score=entry_dict["significance_score"],
                    tags=entry_dict["tags"],
                    author_job_id=entry_dict["author_job_id"],
                    author_name=entry_dict["author_name"],
                    author_type=entry_dict["author_type"],
                    deleted_by_user=entry_dict["deleted_by_user"],
                )
            )

        logger.info(
            f"Fetched {len(entry_responses)} memory entries for product {product_id}",
            extra={
                "tenant_key": tenant_key,
                "product_id": product_id,
                "project_id": project_id,
                "limit": limit,
                "filtered_count": len(entry_responses),
            },
        )

        return MemoryEntriesResponse(
            success=True,
            entries=entry_responses,
            total_count=total_count,
            filtered_count=len(entry_responses),
        )
