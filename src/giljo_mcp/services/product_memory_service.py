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

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import BaseGiljoError, ResourceNotFoundError
from src.giljo_mcp.models import Product, Project, Task, VisionDocument
from src.giljo_mcp.schemas.service_responses import CascadeImpact, ProductStatistics

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
                stmt = select(Product).where(
                    and_(Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

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
                stmt = select(Product).where(
                    and_(Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                # Count related entities (defense-in-depth: explicit tenant_key on all child queries)
                project_count = await session.execute(
                    select(func.count(Project.id)).where(
                        and_(
                            Project.product_id == product_id,
                            Project.tenant_key == self.tenant_key,
                            or_(Project.status != "deleted", Project.status.is_(None)),
                        )
                    )
                )

                task_count = await session.execute(
                    select(func.count(Task.id)).where(
                        and_(Task.product_id == product_id, Task.tenant_key == self.tenant_key)
                    )
                )

                vision_count = await session.execute(
                    select(func.count(VisionDocument.id)).where(
                        and_(VisionDocument.product_id == product_id, VisionDocument.tenant_key == self.tenant_key)
                    )
                )

                return CascadeImpact(
                    product_id=product_id,
                    product_name=product.name,
                    total_projects=project_count.scalar() or 0,
                    total_tasks=task_count.scalar() or 0,
                    total_vision_documents=vision_count.scalar() or 0,
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
        from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

        base_memory = product.product_memory or {}
        git_integration = base_memory.get("git_integration", {})
        context = base_memory.get("context", {})

        repo = ProductMemoryRepository()
        entries = await repo.get_entries_by_product(
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
            await session.commit()
            # Include relationships so refresh doesn't discard eager loads (Handover 0840h)
            await session.refresh(
                product,
                attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
            )
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
        projects_result = await session.execute(
            select(func.count(Project.id)).where(
                and_(
                    Project.product_id == product_id,
                    Project.tenant_key == self.tenant_key,
                    or_(Project.status != "deleted", Project.status.is_(None)),
                )
            )
        )
        project_count = projects_result.scalar() or 0

        unfinished_result = await session.execute(
            select(func.count(Project.id)).where(
                and_(
                    Project.product_id == product_id,
                    Project.tenant_key == self.tenant_key,
                    Project.status.in_(["active", "inactive"]),
                )
            )
        )
        unfinished_projects = unfinished_result.scalar() or 0

        tasks_result = await session.execute(
            select(func.count(Task.id)).where(and_(Task.product_id == product_id, Task.tenant_key == self.tenant_key))
        )
        task_count = tasks_result.scalar() or 0

        unresolved_result = await session.execute(
            select(func.count(Task.id)).where(
                and_(
                    Task.product_id == product_id,
                    Task.tenant_key == self.tenant_key,
                    Task.status.in_(["pending", "in_progress"]),
                )
            )
        )
        unresolved_tasks = unresolved_result.scalar() or 0

        vision_result = await session.execute(
            select(func.count(VisionDocument.id)).where(
                and_(VisionDocument.product_id == product_id, VisionDocument.tenant_key == self.tenant_key)
            )
        )
        vision_documents_count = vision_result.scalar() or 0

        return {
            "project_count": project_count,
            "unfinished_projects": unfinished_projects,
            "task_count": task_count,
            "unresolved_tasks": unresolved_tasks,
            "vision_documents_count": vision_documents_count,
            "has_vision": vision_documents_count > 0,
        }
