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

from sqlalchemy import and_, func, or_, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.models import Product, Project, Task, VisionDocument
from giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from giljo_mcp.services.dto import MemoryEntryCreateParams


logger = logging.getLogger(__name__)


class ProductMemoryRepository:
    """Repository for ProductMemoryEntry CRUD operations."""

    async def create_entry(
        self,
        session: AsyncSession,
        params: MemoryEntryCreateParams,
    ) -> ProductMemoryEntry:
        """
        Create a new 360 memory entry.

        Args:
            session: Database session
            params: DTO containing all entry fields (tenant_key, product_id, sequence, etc.)

        Returns:
            Created ProductMemoryEntry instance

        Raises:
            IntegrityError: If sequence is duplicate for product
        """
        # Validate JSONB list columns at the write boundary
        from giljo_mcp.schemas.jsonb_validators import (
            validate_git_commits,
            validate_string_list,
        )

        validated_key_outcomes = validate_string_list(params.key_outcomes, "key_outcomes") or []
        validated_decisions = validate_string_list(params.decisions_made, "decisions_made") or []
        validated_deliverables = validate_string_list(params.deliverables, "deliverables") or []
        validated_tags = validate_string_list(params.tags, "tags", max_items=100, max_length=200) or []
        validated_git_commits = validate_git_commits(params.git_commits) or []

        entry = ProductMemoryEntry(
            tenant_key=params.tenant_key,
            product_id=str(params.product_id),  # Convert UUID to string (column is String(36))
            project_id=str(params.project_id) if params.project_id else None,
            sequence=params.sequence,
            entry_type=params.entry_type,
            source=params.source,
            timestamp=params.timestamp,
            project_name=params.project_name,
            summary=params.summary,
            key_outcomes=validated_key_outcomes,
            decisions_made=validated_decisions,
            git_commits=validated_git_commits,
            deliverables=validated_deliverables,
            metrics=params.metrics or {},
            priority=params.priority,
            significance_score=params.significance_score,
            token_estimate=params.token_estimate,
            tags=validated_tags,
            author_job_id=str(params.author_job_id) if params.author_job_id else None,
            author_name=params.author_name,
            author_type=params.author_type,
        )
        session.add(entry)
        await session.flush()
        await session.refresh(entry)

        logger.info(
            f"Created memory entry {entry.id} for product {params.product_id} (seq={params.sequence})",
            extra={"tenant_key": params.tenant_key, "entry_type": params.entry_type},
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
        tenant_key: str,
    ) -> int:
        """
        Get the next available sequence number for a product.

        Uses SELECT MAX(sequence) + 1, returns 1 if no entries exist.

        Args:
            session: Database session
            product_id: Product ID
            tenant_key: Tenant isolation key (required, no default)

        Returns:
            Next sequence number (1-based)
        """
        filters = [
            ProductMemoryEntry.product_id == str(product_id),
            ProductMemoryEntry.tenant_key == tenant_key,
        ]
        stmt = select(func.max(ProductMemoryEntry.sequence)).where(*filters)
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

    async def get_entries_by_tag_prefix(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        prefix: str = "action_required",
        include_deleted: bool = False,
    ) -> list[ProductMemoryEntry]:
        """
        Get entries that have at least one tag starting with the given prefix.

        Uses PostgreSQL jsonb_array_elements_text to check tag prefixes.

        Args:
            session: Database session
            product_id: Product ID to query
            tenant_key: Tenant isolation key
            prefix: Tag prefix to match (default: "action_required")
            include_deleted: Include soft-deleted entries

        Returns:
            List of entries with at least one matching tag
        """
        # Use EXISTS subquery with jsonb_array_elements_text
        tag_filter = text(
            "EXISTS (SELECT 1 FROM jsonb_array_elements_text(tags) elem WHERE elem LIKE :prefix_pattern)"
        ).bindparams(prefix_pattern=f"{prefix}:%")

        stmt = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == str(product_id),
                ProductMemoryEntry.tenant_key == tenant_key,
                tag_filter,
            )
            .order_by(ProductMemoryEntry.sequence.desc())
        )

        if not include_deleted:
            stmt = stmt.where(ProductMemoryEntry.deleted_by_user == False)  # noqa: E712

        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def resolve_action_tags(
        self,
        session: AsyncSession,
        product_id: UUID,
        tenant_key: str,
        resolved_items: list[str],
    ) -> int:
        """
        Remove matching action_required tags from entries.

        For each entry with action_required:* tags: if the tag description
        (after 'action_required:') matches any resolved item (case-insensitive
        substring match), remove that tag.

        Args:
            session: Database session
            product_id: Product ID to scope
            tenant_key: Tenant isolation key
            resolved_items: List of description strings to match against

        Returns:
            Count of tags removed
        """
        if not resolved_items:
            return 0

        # Fetch entries with action_required tags
        entries = await self.get_entries_by_tag_prefix(
            session=session,
            product_id=product_id,
            tenant_key=tenant_key,
            prefix="action_required",
            include_deleted=False,
        )

        resolved_lower = [item.lower() for item in resolved_items]
        total_removed = 0

        for entry in entries:
            original_tags = list(entry.tags) if entry.tags else []
            new_tags = []

            for tag in original_tags:
                if tag.startswith("action_required:"):
                    description = tag[len("action_required:") :].lower()
                    if any(resolved in description or description in resolved for resolved in resolved_lower):
                        total_removed += 1
                        continue
                new_tags.append(tag)

            if len(new_tags) != len(original_tags):
                # Reassign full list (not in-place mutation) to trigger SQLAlchemy dirty detection
                entry.tags = new_tags

        await session.flush()

        if total_removed > 0:
            logger.info(
                f"Resolved {total_removed} action tags for product {product_id}",
                extra={"tenant_key": tenant_key},
            )

        return total_removed

    # ========================================================================
    # Product lookups (BE-5022d: moved from product_memory_service.py)
    # ========================================================================

    async def get_product_by_id(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> Product | None:
        """
        Get a product by ID with tenant isolation (non-deleted only).

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Product ORM instance or None
        """
        stmt = select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_key == tenant_key,
                Product.deleted_at.is_(None),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    # ========================================================================
    # Cascade impact counts (BE-5022d: moved from product_memory_service.py)
    # ========================================================================

    async def count_projects(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Count non-deleted projects for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Count of non-deleted projects
        """
        stmt = select(func.count(Project.id)).where(
            and_(
                Project.product_id == product_id,
                Project.tenant_key == tenant_key,
                or_(Project.status != "deleted", Project.status.is_(None)),
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def count_tasks(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Count tasks for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Count of tasks
        """
        stmt = select(func.count(Task.id)).where(and_(Task.product_id == product_id, Task.tenant_key == tenant_key))
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def count_vision_documents(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Count vision documents for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Count of vision documents
        """
        stmt = select(func.count(VisionDocument.id)).where(
            and_(VisionDocument.product_id == product_id, VisionDocument.tenant_key == tenant_key)
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def count_unfinished_projects(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Count active or inactive projects for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Count of unfinished projects
        """
        stmt = select(func.count(Project.id)).where(
            and_(
                Project.product_id == product_id,
                Project.tenant_key == tenant_key,
                Project.status.in_(["active", "inactive"]),
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def count_unresolved_tasks(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Count pending or in-progress tasks for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Count of unresolved tasks
        """
        stmt = select(func.count(Task.id)).where(
            and_(
                Task.product_id == product_id,
                Task.tenant_key == tenant_key,
                Task.status.in_(["pending", "in_progress"]),
            )
        )
        result = await session.execute(stmt)
        return result.scalar() or 0

    async def get_memory_entries_paginated(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
        project_id: str | None = None,
        limit: int = 10,
    ) -> tuple[list[ProductMemoryEntry], int]:
        """
        Get memory entries with total count for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation
            project_id: Optional project filter
            limit: Maximum entries to return

        Returns:
            Tuple of (entries list, total count)
        """
        query = (
            select(ProductMemoryEntry)
            .where(
                ProductMemoryEntry.product_id == product_id,
                ProductMemoryEntry.tenant_key == tenant_key,
                ~ProductMemoryEntry.deleted_by_user,
            )
            .order_by(ProductMemoryEntry.sequence.desc())
        )

        if project_id:
            query = query.where(ProductMemoryEntry.project_id == project_id)

        query = query.limit(limit)

        result = await session.execute(query)
        entries = list(result.scalars().all())

        # Get total count
        total_count_stmt = select(func.count(ProductMemoryEntry.id)).where(
            ProductMemoryEntry.product_id == product_id,
            ProductMemoryEntry.tenant_key == tenant_key,
        )
        total_count_result = await session.execute(total_count_stmt)
        total_count = total_count_result.scalar_one()

        return entries, total_count

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()

    async def refresh_product(
        self,
        session: AsyncSession,
        product: Product,
    ) -> None:
        """
        Refresh a product with its relationships after commit.

        Args:
            session: Active database session
            product: Product ORM instance
        """
        await session.refresh(
            product,
            attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
        )
