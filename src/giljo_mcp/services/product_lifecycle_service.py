# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductLifecycleService - Product lifecycle state management

Handover 0950n: Extracted from ProductService to keep all files under 1000 lines.

Responsibilities:
- Activate / deactivate products (single-active-per-tenant rule)
- Soft delete, restore, and hard-purge products
- Auto-purge expired soft-deleted products on startup
- WebSocket event emission for lifecycle state changes
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    DatabaseError,
    ResourceNotFoundError,
)
from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentJob
from src.giljo_mcp.schemas.service_responses import DeleteResult, PurgeResult


logger = logging.getLogger(__name__)


class ProductLifecycleService:
    """
    Service for product lifecycle state transitions.

    Handles activation, deactivation, soft delete, restore, hard purge,
    and automatic expiry purge. Emits WebSocket events for state changes.

    Thread Safety: Each instance is session-scoped. Do not share across requests.
    """

    def __init__(
        self,
        db_manager: DatabaseManager,
        tenant_key: str,
        websocket_manager=None,
        test_session: AsyncSession | None = None,
    ):
        """
        Initialize ProductLifecycleService.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            websocket_manager: Optional WebSocket manager for event emission
            test_session: Optional AsyncSession for tests to share the same transaction
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._test_session = test_session
        self._websocket_manager = websocket_manager
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

    async def _emit_websocket_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Emit WebSocket event to tenant clients.

        Provides graceful degradation - events are emitted if a WebSocket manager
        is available, but operations don't fail if it's absent.

        Args:
            event_type: Event type (e.g., "projects:bulk:deactivated")
            data: Event payload data
        """
        if not self._websocket_manager:
            self._logger.debug(f"No WebSocket manager available for event: {event_type}")
            return

        try:
            event_data_with_timestamp = {
                **data,
                "tenant_key": self.tenant_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=self.tenant_key, event_type=event_type, data=event_data_with_timestamp
            )

            self._logger.debug(f"WebSocket event emitted: {event_type} for tenant {self.tenant_key}")

        except (RuntimeError, ValueError) as e:
            self._logger.warning(f"Failed to emit WebSocket event {event_type}: {e}", exc_info=True)

    async def activate_product(self, product_id: str) -> Product:
        """
        Activate a product, deactivating all other products for the tenant.

        Only one product can be active at a time per tenant. Cascades project
        and job deactivation to previously active products.

        Args:
            product_id: Product UUID to activate

        Returns:
            Product ORM model after activation

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

                # Deactivate all other products for tenant FIRST
                # Must flush deactivation before activation due to unique constraint
                deactivate_stmt = select(Product).where(
                    and_(Product.tenant_key == self.tenant_key, Product.is_active, Product.id != product_id)
                )
                deactivate_result = await session.execute(deactivate_stmt)
                products_to_deactivate = deactivate_result.scalars().all()

                for p in products_to_deactivate:
                    p.is_active = False
                    p.updated_at = datetime.now(timezone.utc)

                if products_to_deactivate:
                    await session.flush()

                    deactivated_product_ids = [p.id for p in products_to_deactivate]

                    # Bulk deactivate projects in all deactivated products
                    project_deactivate_stmt = (
                        update(Project)
                        .where(Project.product_id.in_(deactivated_product_ids))
                        .where(Project.status == "active")
                        .values(status="inactive", updated_at=datetime.now(timezone.utc))
                    )
                    await session.execute(project_deactivate_stmt)

                    # Cascade: cancel active jobs under deactivated products
                    project_ids_stmt = select(Project.id).where(Project.product_id.in_(deactivated_product_ids))
                    job_cancel_stmt = (
                        update(AgentJob)
                        .where(AgentJob.project_id.in_(project_ids_stmt))
                        .where(AgentJob.status == "active")
                        .values(status="cancelled")
                    )
                    await session.execute(job_cancel_stmt)
                    await session.flush()

                    await self._emit_websocket_event(
                        event_type="projects:bulk:deactivated",
                        data={
                            "product_ids": [str(pid) for pid in deactivated_product_ids],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                product.is_active = True
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Activated product {product_id} (deactivated {len(products_to_deactivate)} others)")

                return product

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to activate product")
            raise BaseGiljoError(
                message=f"Failed to activate product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def deactivate_product(self, product_id: str) -> Product:
        """
        Deactivate a product and cascade to its active projects and jobs.

        Args:
            product_id: Product UUID to deactivate

        Returns:
            Product ORM model after deactivation

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

                product.is_active = False
                product.updated_at = datetime.now(timezone.utc)

                # Cascade: deactivate active projects under this product
                project_deactivate_stmt = (
                    update(Project)
                    .where(Project.product_id == product_id)
                    .where(Project.status == "active")
                    .values(status="inactive", updated_at=datetime.now(timezone.utc))
                )
                await session.execute(project_deactivate_stmt)

                # Cascade: cancel active jobs under this product's projects
                project_ids_stmt = select(Project.id).where(Project.product_id == product_id)
                job_cancel_stmt = (
                    update(AgentJob)
                    .where(AgentJob.project_id.in_(project_ids_stmt))
                    .where(AgentJob.status == "active")
                    .values(status="cancelled")
                )
                await session.execute(job_cancel_stmt)

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Deactivated product {product_id} (cascaded to projects and jobs)")

                return product

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to deactivate product")
            raise BaseGiljoError(
                message=f"Failed to deactivate product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def delete_product(self, product_id: str) -> DeleteResult:
        """
        Soft delete a product.

        Args:
            product_id: Product UUID to delete

        Returns:
            DeleteResult Pydantic model with deleted flag and timestamp

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

                product.deleted_at = datetime.now(timezone.utc)
                product.is_active = False
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()

                self._logger.info(f"Soft deleted product {product_id}")

                return DeleteResult(deleted=True, deleted_at=product.deleted_at)

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to delete product")
            raise BaseGiljoError(
                message=f"Failed to delete product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def restore_product(self, product_id: str) -> Product:
        """
        Restore a soft-deleted product.

        Args:
            product_id: Product UUID to restore

        Returns:
            Product ORM model after restoration

        Raises:
            ResourceNotFoundError: If deleted product not found
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id,
                        Product.tenant_key == self.tenant_key,
                        Product.deleted_at.isnot(None),
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Deleted product not found",
                        context={"product_id": product_id, "tenant_key": self.tenant_key},
                    )

                product.deleted_at = None
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Restored product {product_id}")

                return product

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to restore product")
            raise BaseGiljoError(
                message=f"Failed to restore product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def purge_product(self, product_id: str) -> dict:
        """
        Permanently delete a product and ALL related data (hard delete).

        Cascades via FK ondelete=CASCADE to: projects, tasks, tech_stacks,
        architectures, test_configs, vision_documents, product_memory_entries,
        context chunks.

        Args:
            product_id: Product UUID to permanently delete

        Returns:
            dict with product_name and message

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                stmt = select(Product).where(and_(Product.id == product_id, Product.tenant_key == self.tenant_key))
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found",
                        context={"product_id": product_id, "tenant_key": self.tenant_key},
                    )

                product_name = product.name
                await session.delete(product)
                await session.commit()

                self._logger.info(f"Permanently deleted product {product_id} ({product_name})")

                return {"product_name": product_name, "message": f"Product '{product_name}' permanently deleted"}

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps unexpected errors in BaseGiljoError
            self._logger.exception("Failed to purge product")
            raise BaseGiljoError(
                message=f"Failed to permanently delete product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def list_deleted_products(self) -> list[Product]:
        """
        List soft-deleted products for the tenant.

        Returns:
            List of Product ORM models (soft-deleted), ordered by deleted_at desc

        Raises:
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                stmt = (
                    select(Product)
                    .where(and_(Product.tenant_key == self.tenant_key, Product.deleted_at.isnot(None)))
                    .order_by(Product.deleted_at.desc())
                )

                result = await session.execute(stmt)
                deleted_products = result.scalars().all()

                return list(deleted_products)

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list deleted products")
            raise BaseGiljoError(
                message=f"Failed to list deleted products: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    async def purge_expired_deleted_products(self, days_before_purge: int = 10) -> PurgeResult:
        """
        Hard delete products that were soft-deleted more than the specified number of days ago.

        SQLAlchemy cascade="all, delete-orphan" handles child relationships:
        projects, tasks, vision documents, etc.

        Called from startup.py on server start for automatic cleanup.

        Args:
            days_before_purge: Number of days before permanent deletion (default: 10)

        Returns:
            PurgeResult Pydantic model with purged_count and purged_ids

        Raises:
            DatabaseError: If database not available
            BaseGiljoError: If purge operation fails
        """
        if not self.db_manager:
            self._logger.error("[Product Purge] Cannot purge - database manager not available")
            raise DatabaseError(
                message="Database not available",
                context={"operation": "purge_expired_deleted_products", "tenant_key": self.tenant_key},
            )

        try:
            async with self._get_session() as session:
                cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_before_purge)

                stmt = select(Product).where(
                    Product.deleted_at.isnot(None),
                    Product.deleted_at < cutoff_date,
                )

                result = await session.execute(stmt)
                expired_products = result.scalars().all()

                if not expired_products:
                    self._logger.info(
                        f"[Product Purge] No expired deleted products to purge (cutoff: {days_before_purge} days)"
                    )
                    return PurgeResult(purged_count=0, purged_ids=[])

                purged_ids = []
                for product in expired_products:
                    days_ago = (datetime.now(timezone.utc) - product.deleted_at).days
                    purged_ids.append(str(product.id))

                    await session.delete(product)

                    self._logger.info(
                        f"[Product Purge] Auto-purged expired product {product.id} (deleted {days_ago} days ago)"
                    )

                await session.commit()

                self._logger.info(f"[Product Purge] Successfully purged {len(purged_ids)} expired deleted products")

                return PurgeResult(purged_count=len(purged_ids), purged_ids=purged_ids)

        except DatabaseError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("[Product Purge] Failed to purge expired deleted products")
            raise BaseGiljoError(
                message=f"Failed to purge expired deleted products: {e!s}",
                context={
                    "operation": "purge_expired_deleted_products",
                    "tenant_key": self.tenant_key,
                    "days_before_purge": days_before_purge,
                },
            ) from e
