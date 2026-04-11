# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductMemoryEntry Repository (Handover 0390a)

CRUD operations for 360 memory entries with tenant isolation.
"""

import logging
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models.product_memory_entry import ProductMemoryEntry


logger = logging.getLogger(__name__)


class ProductMemoryRepository:
    """Repository for ProductMemoryEntry CRUD operations."""

    async def create_entry(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: UUID,
        sequence: int,
        entry_type: str,
        source: str,
        timestamp: datetime,
        project_id: UUID | None = None,
        project_name: str | None = None,
        summary: str | None = None,
        key_outcomes: list[str | None] = None,
        decisions_made: list[str | None] = None,
        git_commits: list[dict[str, Any | None]] = None,
        deliverables: list[str | None] = None,
        metrics: dict[str, Any | None] = None,
        priority: int = 3,
        significance_score: float = 0.5,
        token_estimate: int | None = None,
        tags: list[str | None] = None,
        author_job_id: UUID | None = None,
        author_name: str | None = None,
        author_type: str | None = None,
    ) -> ProductMemoryEntry:
        """
        Create a new 360 memory entry.

        Args:
            session: Database session
            tenant_key: Tenant isolation key
            product_id: Parent product ID
            sequence: Sequence number (must be unique per product)
            entry_type: Entry type (project_closeout, project_completion, handover_closeout)
            source: Source tool identifier
            timestamp: When the entry was created
            project_id: Source project ID (optional)
            ... (other fields)

        Returns:
            Created ProductMemoryEntry instance

        Raises:
            IntegrityError: If sequence is duplicate for product
        """
        entry = ProductMemoryEntry(
            tenant_key=tenant_key,
            product_id=str(product_id),  # Convert UUID to string (column is String(36))
            project_id=str(project_id) if project_id else None,  # Convert UUID to string
            sequence=sequence,
            entry_type=entry_type,
            source=source,
            timestamp=timestamp,
            project_name=project_name,
            summary=summary,
            key_outcomes=key_outcomes or [],
            decisions_made=decisions_made or [],
            git_commits=git_commits or [],
            deliverables=deliverables or [],
            metrics=metrics or {},
            priority=priority,
            significance_score=significance_score,
            token_estimate=token_estimate,
            tags=tags or [],
            author_job_id=str(author_job_id) if author_job_id else None,  # Convert UUID to string
            author_name=author_name,
            author_type=author_type,
        )
        session.add(entry)
        await session.flush()
        await session.refresh(entry)

        logger.info(
            f"Created memory entry {entry.id} for product {product_id} (seq={sequence})",
            extra={"tenant_key": tenant_key, "entry_type": entry_type},
        )
        return entry

    async def get_entries_by_product(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        limit: int | None = None,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> list[ProductMemoryEntry]:
        """
        Get 360 memory entries for a product with pagination.

        Args:
            session: Database session
            product_id: Product ID to query
            tenant_key: Tenant isolation key
            limit: Maximum entries to return (None = all)
            offset: Number of entries to skip
            include_deleted: Include soft-deleted entries

        Returns:
            List of ProductMemoryEntry in descending sequence order
        """
        stmt = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == str(product_id),
                ProductMemoryEntry.tenant_key == tenant_key,
            )
            .order_by(ProductMemoryEntry.sequence.desc())
            .offset(offset)
        )

        if not include_deleted:
            stmt = stmt.where(ProductMemoryEntry.deleted_by_user == False)  # noqa: E712

        if limit:
            stmt = stmt.limit(limit)

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_entries_by_last_n_projects(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        last_n_projects: int,
        offset: int = 0,
        include_deleted: bool = False,
    ) -> tuple[list[ProductMemoryEntry], int]:
        """
        Get 360 memory entries for the last N distinct projects.

        Unlike get_entries_by_product which limits by entry count, this limits
        by distinct project_id count. A project with 3 entries returns all 3
        within a single project slot.

        Args:
            session: Database session
            product_id: Product ID to query
            tenant_key: Tenant isolation key
            last_n_projects: Number of distinct projects to include
            offset: Number of distinct projects to skip
            include_deleted: Include soft-deleted entries

        Returns:
            Tuple of (entries list in descending sequence order, total distinct project count)
        """
        # Base filter shared by both queries
        base_filter = [
            ProductMemoryEntry.product_id == str(product_id),
            ProductMemoryEntry.tenant_key == tenant_key,
            ProductMemoryEntry.project_id.isnot(None),
        ]
        if not include_deleted:
            base_filter.append(ProductMemoryEntry.deleted_by_user == False)  # noqa: E712

        # Count total distinct projects
        count_stmt = select(func.count(func.distinct(ProductMemoryEntry.project_id))).where(*base_filter)
        count_result = await session.execute(count_stmt)
        total_distinct_projects = count_result.scalar() or 0

        # Get the N most recent distinct project_ids (by max sequence)
        project_ids_stmt = (
            select(ProductMemoryEntry.project_id)
            .where(*base_filter)
            .group_by(ProductMemoryEntry.project_id)
            .order_by(func.max(ProductMemoryEntry.sequence).desc())
            .offset(offset)
            .limit(last_n_projects)
        )
        project_ids_result = await session.execute(project_ids_stmt)
        project_ids = [row[0] for row in project_ids_result.all()]

        if not project_ids:
            return [], total_distinct_projects

        # Fetch all entries for those projects
        entries_stmt = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == str(product_id),
                ProductMemoryEntry.tenant_key == tenant_key,
                ProductMemoryEntry.project_id.in_(project_ids),
            )
            .order_by(ProductMemoryEntry.sequence.desc())
        )
        if not include_deleted:
            entries_stmt = entries_stmt.where(
                ProductMemoryEntry.deleted_by_user == False  # noqa: E712
            )

        result = await session.execute(entries_stmt)
        return list(result.scalars().all()), total_distinct_projects

    async def get_entry_by_id(
        self,
        session: AsyncSession,
        entry_id: UUID,
        tenant_key: str,
    ) -> ProductMemoryEntry | None:
        """
        Get a single entry by ID with tenant isolation.

        Args:
            session: Database session
            entry_id: Entry UUID
            tenant_key: Tenant isolation key

        Returns:
            ProductMemoryEntry or None if not found
        """
        stmt = select(ProductMemoryEntry).where(
            ProductMemoryEntry.id == entry_id,
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_next_sequence(
        self,
        session: AsyncSession,
        product_id: UUID,
    ) -> int:
        """
        Get the next available sequence number for a product.

        Uses SELECT MAX(sequence) + 1, returns 1 if no entries exist.

        Args:
            session: Database session
            product_id: Product ID

        Returns:
            Next sequence number (1-based)
        """
        stmt = select(func.max(ProductMemoryEntry.sequence)).where(
            ProductMemoryEntry.product_id == str(product_id),
        )
        result = await session.execute(stmt)
        max_seq = result.scalar_one_or_none()
        return (max_seq or 0) + 1

    async def mark_entries_deleted(
        self,
        session: AsyncSession,
        project_id: UUID,
        tenant_key: str,
    ) -> int:
        """
        Soft-delete all entries associated with a project.

        Called when a project is deleted - marks entries as deleted
        but preserves them for historical reference.

        Args:
            session: Database session
            project_id: Project ID to mark entries for
            tenant_key: Tenant isolation key

        Returns:
            Number of entries marked as deleted
        """
        stmt = (
            update(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.project_id == str(project_id),
                ProductMemoryEntry.tenant_key == tenant_key,
            )
            .values(
                deleted_by_user=True,
                user_deleted_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await session.execute(stmt)
        await session.flush()

        count = result.rowcount
        if count > 0:
            logger.info(
                f"Marked {count} memory entries as deleted for project {project_id}",
                extra={"tenant_key": tenant_key},
            )
        return count

    async def get_entries_for_context(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Get entries formatted for context (mission planning).

        Returns lightweight dicts suitable for agent context injection.

        Args:
            session: Database session
            product_id: Product ID
            tenant_key: Tenant isolation key
            limit: Max entries to return

        Returns:
            List of entry dicts
        """
        entries = await self.get_entries_by_product(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            limit=limit,
            include_deleted=False,
        )
        return [entry.to_dict() for entry in entries]

    async def get_git_history(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        """
        Get aggregated git commits from all entries.

        Args:
            session: Database session
            product_id: Product ID
            tenant_key: Tenant isolation key
            limit: Max commits to return

        Returns:
            List of git commit dicts
        """
        entries = await self.get_entries_by_product(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            include_deleted=False,
        )

        all_commits = []
        for entry in entries:
            if entry.git_commits:
                all_commits.extend(entry.git_commits)

        # Sort by date descending, limit
        all_commits.sort(key=lambda c: c.get("date", ""), reverse=True)
        return all_commits[:limit]
