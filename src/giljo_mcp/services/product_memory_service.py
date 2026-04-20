# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductMemoryService - Product metrics, statistics, and memory management

Handover 0950n: Extracted from ProductService to keep all files under 1000 lines.

Responsibilities:
- Product statistics (project/task/vision document counts)
- Cascade impact analysis for deletion previews
- Product memory JSONB initialization and backward-compat repair
- Building product_memory response structures from the table + JSONB
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import BaseGiljoError, ResourceNotFoundError
from giljo_mcp.models import Product
from giljo_mcp.models.product_memory_entry import ProductMemoryEntry
from giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository
from giljo_mcp.schemas.service_responses import CascadeImpact, ProductStatistics
from giljo_mcp.services.dto import MemoryEntryCreateParams


logger = logging.getLogger(__name__)


class ProductMemoryService:
    """
    Service for product statistics, cascade analysis, and memory management.

    Encapsulates read-heavy analytics and JSONB memory initialization logic
    that was previously co-located with lifecycle state management.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        test_session: AsyncSession | None = None,
    ):
        """
        Initialize ProductMemoryService.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            test_session: Optional AsyncSession for tests to share the same transaction
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._test_session = test_session
        self._repo = ProductMemoryRepository()
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.

        Returns:
            Context manager for database session
        """
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    async def get_product_statistics(self, product_id: str) -> ProductStatistics:
        """
        Get comprehensive statistics for a product.

        Args:
            product_id: Product UUID

        Returns:
            ProductStatistics Pydantic model

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                product = await self._repo.get_product_by_id(session, product_id, self.tenant_key)

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                metrics = await self._get_product_metrics(session, product_id)

                return ProductStatistics(
                    product_id=product_id,
                    name=product.name,
                    is_active=product.is_active,
                    project_count=metrics["project_count"],
                    unfinished_projects=metrics["unfinished_projects"],
                    task_count=metrics["task_count"],
                    unresolved_tasks=metrics["unresolved_tasks"],
                    vision_documents_count=metrics["vision_documents_count"],
                    has_vision=metrics["has_vision"],
                    created_at=product.created_at,
                    updated_at=product.updated_at,
                )

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get product statistics")
            raise BaseGiljoError(
                message=f"Failed to get product statistics: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def get_cascade_impact(self, product_id: str) -> CascadeImpact:
        """
        Get cascade impact analysis for product deletion.

        Shows what entities would be affected by deleting this product.

        Args:
            product_id: Product UUID

        Returns:
            CascadeImpact Pydantic model

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                product = await self._repo.get_product_by_id(session, product_id, self.tenant_key)

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                # Count related entities (defense-in-depth: explicit tenant_key on all child queries)
                total_projects = await self._repo.count_projects(session, product_id, self.tenant_key)
                total_tasks = await self._repo.count_tasks(session, product_id, self.tenant_key)
                total_vision_docs = await self._repo.count_vision_documents(session, product_id, self.tenant_key)

                return CascadeImpact(
                    product_id=product_id,
                    product_name=product.name,
                    total_projects=total_projects,
                    total_tasks=total_tasks,
                    total_vision_documents=total_vision_docs,
                    warning="Deleting this product will soft-delete all related entities",
                )

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get cascade impact")
            raise BaseGiljoError(
                message=f"Failed to get cascade impact: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def _build_product_memory_response(
        self, session: AsyncSession, product: Product, include_deleted: bool = False
    ) -> dict:
        """
        Build product_memory response with sequential_history from the table (Handover 0390b).

        Maintains backward compatibility by returning the same structure as before,
        but populates sequential_history from product_memory_entries table instead
        of the JSONB column.

        Args:
            session: Async database session
            product: Product instance
            include_deleted: Include soft-deleted memory entries (default: False)

        Returns:
            Dict with keys: git_integration, sequential_history, context
        """
        base_memory = product.product_memory or {}
        git_integration = base_memory.get("git_integration", {})
        context = base_memory.get("context", {})

        entries = await self._repo.get_entries_by_product(
            session=session,
            product_id=product.id,
            tenant_key=self.tenant_key,
            include_deleted=include_deleted,
        )

        sequential_history = [entry.to_dict() for entry in entries]

        return {
            "git_integration": git_integration,
            "sequential_history": sequential_history,
            "context": context,
        }

    async def _ensure_product_memory_initialized(self, session: AsyncSession, product: Product) -> None:
        """
        Ensure product_memory is initialized with default structure (Handover 0136).

        Provides backward compatibility for products that may have NULL, empty,
        or partial product_memory JSONB. The method is idempotent.

        Args:
            session: Async database session
            product: Product instance to check and initialize

        Side Effects:
            - Updates product.product_memory if incomplete
            - Commits changes to database when modifications are made
        """
        default_structure = {
            "github": {},
            "context": {},
        }

        needs_update = False

        if product.product_memory is None:
            product.product_memory = default_structure
            needs_update = True
            self._logger.debug(f"Product {product.id}: Initialized NULL product_memory")
        elif not isinstance(product.product_memory, dict):
            product.product_memory = default_structure
            needs_update = True
            self._logger.warning(
                f"Product {product.id}: Replaced invalid product_memory type "
                f"({type(product.product_memory)}) with default structure"
            )
        elif not product.product_memory:
            product.product_memory = default_structure
            needs_update = True
            self._logger.debug(f"Product {product.id}: Initialized empty dict product_memory")
        else:
            updated_memory = dict(product.product_memory)
            for key, default_value in default_structure.items():
                if key not in updated_memory:
                    updated_memory[key] = default_value
                    needs_update = True
                    self._logger.debug(f"Product {product.id}: Added missing '{key}' key to product_memory")

            if needs_update:
                product.product_memory = updated_memory

        if needs_update:
            product.updated_at = datetime.now(timezone.utc)
            await self._repo.commit(session)
            # Include relationships so refresh doesn't discard eager loads (Handover 0840h)
            await self._repo.refresh_product(session, product)
            self._logger.info(f"Product {product.id}: Updated product_memory structure")

    async def _get_product_metrics(self, session: AsyncSession, product_id: str) -> dict[str, Any]:
        """
        Get aggregated metrics for a product (projects, tasks, vision documents).

        All queries filter by tenant_key for defense-in-depth isolation.

        Args:
            session: Async database session
            product_id: Product UUID

        Returns:
            Dict with keys: project_count, unfinished_projects, task_count,
            unresolved_tasks, vision_documents_count, has_vision
        """
        project_count = await self._repo.count_projects(session, product_id, self.tenant_key)
        unfinished_projects = await self._repo.count_unfinished_projects(session, product_id, self.tenant_key)
        task_count = await self._repo.count_tasks(session, product_id, self.tenant_key)
        unresolved_tasks = await self._repo.count_unresolved_tasks(session, product_id, self.tenant_key)
        vision_documents_count = await self._repo.count_vision_documents(session, product_id, self.tenant_key)

        return {
            "project_count": project_count,
            "unfinished_projects": unfinished_projects,
            "task_count": task_count,
            "unresolved_tasks": unresolved_tasks,
            "vision_documents_count": vision_documents_count,
            "has_vision": vision_documents_count > 0,
        }

    async def get_memory_entries(
        self,
        product_id: str,
        project_id: str | None = None,
        limit: int = 10,
    ) -> dict[str, Any]:
        """Fetch 360 memory entries for a product from the normalized table.

        BE-5022a: Extracted from api/endpoints/products/memory.py to keep
        all DB access in the service layer.

        Args:
            product_id: Product UUID (already validated by caller)
            project_id: Optional project UUID filter
            limit: Maximum entries to return (1-100)

        Returns:
            Dict with entries list, total_count, and filtered_count

        Raises:
            ResourceNotFoundError: Product not found or not accessible
        """
        async with self._get_session() as session:
            # Verify product exists and belongs to tenant
            product = await self._repo.get_product_by_id(session, product_id, self.tenant_key)

            if not product:
                raise ResourceNotFoundError(
                    message=f"Product {product_id} not found or not accessible",
                    context={"product_id": product_id},
                )

            # Fetch entries with total count via repository
            entries, total_count = await self._repo.get_memory_entries_paginated(
                session=session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                project_id=project_id,
                limit=limit,
            )

            return {
                "entries": entries,
                "total_count": total_count,
                "filtered_count": len(entries),
            }

    # ---- BE-5022b: Service wrappers for ProductMemoryRepository methods ----

    async def get_entries_by_last_n_projects(
        self,
        product_id: str,
        last_n_projects: int = 3,
        offset: int = 0,
        include_deleted: bool = False,
        session: AsyncSession | None = None,
    ) -> tuple[list, int]:
        """Fetch memory entries grouped by last N distinct projects.

        BE-5022b: Service wrapper for ProductMemoryRepository.get_entries_by_last_n_projects().

        Args:
            product_id: Product UUID
            last_n_projects: Number of distinct projects to consider
            offset: Number of projects to skip (pagination)
            include_deleted: Include soft-deleted entries
            session: Optional existing session (for callers that manage their own)

        Returns:
            Tuple of (entries list, total_projects count)
        """
        if session is not None:
            return await self._repo.get_entries_by_last_n_projects(
                session=session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                last_n_projects=last_n_projects,
                offset=offset,
                include_deleted=include_deleted,
            )
        async with self._get_session() as new_session:
            return await self._repo.get_entries_by_last_n_projects(
                session=new_session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                last_n_projects=last_n_projects,
                offset=offset,
                include_deleted=include_deleted,
            )

    async def get_entries_by_tag_prefix(
        self,
        product_id: str,
        prefix: str,
        session: AsyncSession | None = None,
    ) -> list:
        """Fetch memory entries matching a tag prefix.

        BE-5022b: Service wrapper for ProductMemoryRepository.get_entries_by_tag_prefix().

        Args:
            product_id: Product UUID
            prefix: Tag prefix to match (e.g. "action_required")
            session: Optional existing session

        Returns:
            List of ProductMemoryEntry instances matching the tag prefix
        """
        if session is not None:
            return await self._repo.get_entries_by_tag_prefix(
                session=session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                prefix=prefix,
            )
        async with self._get_session() as new_session:
            return await self._repo.get_entries_by_tag_prefix(
                session=new_session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                prefix=prefix,
            )

    async def get_git_history(
        self,
        product_id: str,
        limit: int = 25,
        session: AsyncSession | None = None,
    ) -> list:
        """Fetch git commit history from memory entries.

        BE-5022b: Service wrapper for ProductMemoryRepository.get_git_history().

        Args:
            product_id: Product UUID
            limit: Max commits to return
            session: Optional existing session

        Returns:
            List of git commit dicts (newest first)
        """
        if session is not None:
            return await self._repo.get_git_history(
                session=session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                limit=limit,
            )
        async with self._get_session() as new_session:
            return await self._repo.get_git_history(
                session=new_session,
                product_id=product_id,
                tenant_key=self.tenant_key,
                limit=limit,
            )

    async def get_next_sequence(
        self,
        product_id: str | Any,
        session: AsyncSession | None = None,
    ) -> int:
        """Get the next sequence number for a product's memory entries.

        BE-5022b: Service wrapper for ProductMemoryRepository.get_next_sequence().

        Args:
            product_id: Product UUID (str or UUID)
            session: Optional existing session

        Returns:
            Next available sequence number
        """
        if session is not None:
            return await self._repo.get_next_sequence(
                session=session,
                product_id=product_id,
                tenant_key=self.tenant_key,
            )
        async with self._get_session() as new_session:
            return await self._repo.get_next_sequence(
                session=new_session,
                product_id=product_id,
                tenant_key=self.tenant_key,
            )

    async def create_entry(
        self,
        params: MemoryEntryCreateParams,
        session: AsyncSession | None = None,
    ) -> ProductMemoryEntry:
        """Create a new product memory entry.

        BE-5022b: Service wrapper for ProductMemoryRepository.create_entry().
        BE-5022f: Post-write hook creates tasks from action_required tags.

        Args:
            params: MemoryEntryCreateParams with all required fields
            session: Optional existing session

        Returns:
            Created ProductMemoryEntry instance
        """
        if session is not None:
            entry = await self._repo.create_entry(session=session, params=params)
            await self._create_action_required_tasks(params, session)
            return entry
        async with self._get_session() as new_session:
            entry = await self._repo.create_entry(session=new_session, params=params)
            await self._create_action_required_tasks(params, new_session)
            return entry

    async def _create_action_required_tasks(
        self,
        params: MemoryEntryCreateParams,
        session: AsyncSession,
    ) -> None:
        """Scan tags for action_required: prefix and create tasks idempotently.

        BE-5022f: Post-write hook. For each tag starting with 'action_required:',
        creates a task via TaskService if one doesn't already exist.

        Args:
            params: The memory entry params (contains tags, tenant_key, product_id)
            session: Active database session
        """
        if not params.tags:
            return

        action_tags = [t for t in params.tags if t.startswith("action_required:")]
        if not action_tags:
            return

        from giljo_mcp.repositories.task_repository import TaskRepository
        from giljo_mcp.services.task_service import TaskService

        task_repo = TaskRepository()
        task_svc = TaskService(
            db_manager=self.db_manager,
            tenant_manager=None,
            session=session,
        )
        product_id_str = str(params.product_id)
        project_name = params.project_name or "unknown"
        sequence = params.sequence

        for tag in action_tags:
            title = tag[len("action_required:") :].strip()
            if not title:
                continue
            title = title[:255]

            try:
                existing = await task_repo.find_by_category_and_title(
                    session=session,
                    tenant_key=params.tenant_key,
                    product_id=product_id_str,
                    category="360",
                    title=title,
                )
                if existing:
                    self._logger.debug("Skipping duplicate action_required task: %s", title)
                    continue

                description = (
                    f"Auto-created from 360 Memory action tag (project: {project_name}, sequence: {sequence})."
                )
                task_id = await task_svc.log_task(
                    content=title,
                    title=title,
                    description=description,
                    priority="medium",
                    category="360",
                    product_id=product_id_str,
                    tenant_key=params.tenant_key,
                )
                self._logger.info("Created action_required task %s: %s", task_id, title)
            except Exception:  # noqa: BLE001
                self._logger.warning(
                    "Failed to create action_required task: %s",
                    title,
                    exc_info=True,
                )
