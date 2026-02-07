"""
ProductService - Dedicated service for product domain logic

Handover 0127b: Extract product operations from direct database access
to follow established service layer pattern.

Responsibilities:
- CRUD operations for products
- Product lifecycle management (activate, deactivate, archive, restore)
- Product metrics and statistics
- Vision document management
- Cascade impact analysis

Design Principles:
- Single Responsibility: Only product domain logic
- Dependency Injection: Accepts DatabaseManager and tenant_key
- Async/Await: Full SQLAlchemy 2.0 async support
- Error Handling: Consistent exception handling and logging
- Testability: Can be unit tested independently
"""

import logging
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoException,
    DatabaseError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import Product, Project, Task, VisionDocument


logger = logging.getLogger(__name__)


class ProductService:
    """
    Service for managing product lifecycle and operations.

    This service handles all product-related operations including:
    - Creating, reading, updating, deleting products
    - Product activation/deactivation (single active product per tenant)
    - Product metrics and statistics
    - Vision document management
    - Quality standards updates (Handover 0316)
    - Cascade impact analysis for deletions

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
        Initialize ProductService with database and tenant isolation.

        Args:
            db_manager: Database manager for async database operations
            tenant_key: Tenant key for multi-tenant isolation
            websocket_manager: Optional WebSocket manager for event emission (Handover 0139a)
            test_session: Optional AsyncSession for tests to share the same transaction
        """
        self.db_manager = db_manager
        self.tenant_key = tenant_key
        self._test_session = test_session
        self._websocket_manager = websocket_manager  # Handover 0139a: WebSocket events
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.

        Returns:
            Context manager for database session
        """
        if self._test_session is not None:
            # For test sessions, wrap in a context manager that doesn't close
            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        # Return the context manager directly (no double-wrapping)
        return self.db_manager.get_session_async()

    def _validate_target_platforms(self, target_platforms: list[str]) -> tuple[bool, str | None]:
        """
        Validate target_platforms field (Handover 0425).

        Args:
            target_platforms: List of platform values

        Returns:
            Tuple of (is_valid, error_message)

        Validation Rules:
            - All values must be in ['windows', 'linux', 'macos', 'all']
            - If 'all' is present, it must be the only value
        """
        if not target_platforms:
            return False, "target_platforms cannot be empty"

        valid_platforms = {"windows", "linux", "macos", "all"}
        invalid_platforms = set(target_platforms) - valid_platforms

        if invalid_platforms:
            return False, f"Invalid platform values: {', '.join(invalid_platforms)}"

        if "all" in target_platforms and len(target_platforms) > 1:
            return False, "'all' platform cannot be combined with specific platforms"

        return True, None

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    async def create_product(
        self,
        name: str,
        description: str | None = None,
        project_path: str | None = None,
        config_data: dict[str, Any | None] = None,
        product_memory: dict[str, Any | None] = None,  # Handover 0135
        target_platforms: list[str | None] = None,  # Handover 0425
    ) -> dict[str, Any]:
        """
        Create a new product.

        Args:
            name: Product name (required)
            description: Product description
            project_path: File system path to product folder
            config_data: Rich configuration data (architecture, tech_stack, etc.)
            product_memory: 360 Memory data (GitHub, sequential_history, context) - Handover 0135
            target_platforms: Target OS platforms (windows, linux, macos, or all) - Handover 0425

        Returns:
            Dict with product details

        Raises:
            ValidationError: If target_platforms invalid or product name already exists
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.create_product(
            ...     name="MyApp",
            ...     description="Mobile application",
            ...     project_path="/projects/myapp",
            ...     target_platforms=["windows", "linux"]
            ... )
            >>> print(result["product_id"])
        """
        try:
            # Handover 0425: Validate target_platforms if provided
            if target_platforms is not None:
                is_valid, error_msg = self._validate_target_platforms(target_platforms)
                if not is_valid:
                    raise ValidationError(message=error_msg, context={"target_platforms": target_platforms})

            async with self._get_session() as session:
                # Check for duplicate name (excluding soft-deleted)
                stmt = select(Product).where(
                    and_(Product.tenant_key == self.tenant_key, Product.name == name, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValidationError(
                        message=f"Product '{name}' already exists",
                        context={"product_name": name, "tenant_key": self.tenant_key},
                    )

                # Create product
                # Handover 0135 + 0700c: Initialize product_memory (history in table)
                default_memory = {
                    "github": {},
                    "context": {},
                }

                product = Product(
                    id=str(uuid4()),
                    tenant_key=self.tenant_key,
                    name=name,
                    description=description,
                    project_path=project_path,
                    config_data=config_data or {},
                    product_memory=product_memory or default_memory,  # Handover 0135
                    target_platforms=target_platforms or ["all"],  # Handover 0425
                    is_active=False,  # Products start inactive
                    created_at=datetime.now(timezone.utc),
                )

                session.add(product)
                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Created product {product.id} for tenant {self.tenant_key}")

                # Handover 0390b: Build product_memory from table (will be empty for new product)
                product_memory = await self._build_product_memory_response(session, product)

                return {
                    "success": True,
                    "product_id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "is_active": product.is_active,
                    "product_memory": product_memory,  # Handover 0390b: From table
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                }

        except ValidationError:
            # Re-raise validation errors as-is
            raise
        except (ImportError, ValueError, KeyError) as e:
            self._logger.exception("Failed to create product")
            raise BaseGiljoException(
                message=f"Failed to create product: {e!s}",
                context={"product_name": name, "tenant_key": self.tenant_key},
            ) from e

    async def get_product(self, product_id: str, include_metrics: bool = True) -> dict[str, Any]:
        """
        Get a specific product by ID with optional metrics.

        Args:
            product_id: Product UUID
            include_metrics: Include project/task counts (default: True)

        Returns:
            Dict with product details

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.get_product("abc-123")
            >>> print(result["product"]["name"])
        """
        try:
            async with self._get_session() as session:
                # Eagerly load vision_documents to prevent lazy-loading issues
                stmt = (
                    select(Product)
                    .options(selectinload(Product.vision_documents))
                    .where(
                        and_(
                            Product.id == product_id,
                            Product.tenant_key == self.tenant_key,
                            Product.deleted_at.is_(None),
                        )
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                # Handover 0136: Ensure product_memory is initialized (backward compatibility)
                await self._ensure_product_memory_initialized(session, product)

                # Handover 0412: Force refresh to ensure we have latest DB data
                await session.refresh(product)

                # Handover 0390b: Build product_memory from table
                product_memory = await self._build_product_memory_response(session, product)
                self._logger.info(
                    f"Product {product_id}: product_memory with {len(product_memory.get('sequential_history', []))} entries"
                )

                # Normalize config_data so that an empty dict is treated as "no config"
                # for API consumers, while preserving the raw structure for internal use.
                config_data = product.config_data or None

                product_data = {
                    "id": str(product.id),
                    "name": product.name,
                    "description": product.description,
                    "vision_path": product.primary_vision_path,  # Using new VisionDocument relationship
                    "project_path": product.project_path,
                    "is_active": product.is_active,
                    "config_data": config_data,
                    "has_config_data": bool(config_data),
                    "product_memory": product_memory,  # Handover 0390b: From table
                    "created_at": product.created_at.isoformat() if product.created_at else None,
                    "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                }

                if include_metrics:
                    metrics = await self._get_product_metrics(session, product_id)
                    product_data.update(metrics)

                return {"success": True, "product": product_data}

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except (ImportError, ValueError, KeyError) as e:
            self._logger.exception("Failed to get product")
            raise BaseGiljoException(
                message=f"Failed to get product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def list_products(self, include_inactive: bool = False, include_metrics: bool = True) -> dict[str, Any]:
        """
        List all products for tenant with optional filtering.

        Args:
            include_inactive: Include inactive products (default: False)
            include_metrics: Include project/task counts (default: True)

        Returns:
            Dict with list of products

        Raises:
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.list_products()
            >>> for product in result["products"]:
            ...     print(product["name"])
        """
        try:
            async with self._get_session() as session:
                conditions = [Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None)]

                if not include_inactive:
                    conditions.append(Product.is_active)

                # Eagerly load vision_documents to avoid lazy loading in property access
                # Sort: active products first, then by creation date (newest first)
                stmt = (
                    select(Product)
                    .where(and_(*conditions))
                    .options(selectinload(Product.vision_documents))
                    .order_by(Product.is_active.desc(), Product.created_at.desc())
                )
                result = await session.execute(stmt)
                products = result.scalars().all()

                product_list = []
                for product in products:
                    # Handover 0136: Ensure product_memory is initialized (backward compatibility)
                    await self._ensure_product_memory_initialized(session, product)

                    # Handover 0390b: Build product_memory from table
                    product_memory = await self._build_product_memory_response(session, product)

                    config_data = product.config_data or None

                    product_data = {
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "vision_path": product.primary_vision_path,  # Using new VisionDocument relationship
                        "project_path": product.project_path,
                        "is_active": product.is_active,
                        "config_data": config_data,
                        "has_config_data": bool(config_data),
                        "product_memory": product_memory,  # Handover 0390b: From table
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                    }

                    if include_metrics:
                        metrics = await self._get_product_metrics(session, product.id)
                        product_data.update(metrics)

                    product_list.append(product_data)

                self._logger.debug(f"Found {len(product_list)} products for tenant {self.tenant_key}")

                return {"success": True, "products": product_list}

        except Exception as e:
            self._logger.exception("Failed to list products")
            raise BaseGiljoException(
                message=f"Failed to list products: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    async def update_product(self, product_id: str, **updates) -> dict[str, Any]:
        """
        Update a product.

        Args:
            product_id: Product UUID
            **updates: Fields to update (name, description, project_path, config_data, product_memory, target_platforms, etc.)

        Returns:
            Dict with updated product

        Raises:
            ResourceNotFoundError: If product not found
            ValidationError: If target_platforms invalid
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.update_product(
            ...     "abc-123",
            ...     description="Updated description",
            ...     config_data={"tech_stack": {"python": "3.11"}},
            ...     product_memory={"github": {"enabled": True}},  # Handover 0135
            ...     target_platforms=["windows", "linux"]  # Handover 0425
            ... )
        """
        try:
            # Handover 0425: Validate target_platforms if provided
            if "target_platforms" in updates:
                is_valid, error_msg = self._validate_target_platforms(updates["target_platforms"])
                if not is_valid:
                    raise ValidationError(message=error_msg, context={"target_platforms": updates["target_platforms"]})

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

                # Apply updates
                for field, value in updates.items():
                    if hasattr(product, field):
                        setattr(product, field, value)

                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Updated product {product_id}")

                # Handover 0139a: Emit WebSocket event if product_memory was updated
                # Handover 0390b: Build product_memory from table for WebSocket event
                if "product_memory" in updates:
                    product_memory = await self._build_product_memory_response(session, product)
                    await self._emit_websocket_event(
                        event_type="product:memory:updated",
                        data={"product_id": product_id, "product_memory": product_memory},
                    )

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                    },
                }

        except (ResourceNotFoundError, ValidationError):
            # Re-raise our custom errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to update product")
            raise BaseGiljoException(
                message=f"Failed to update product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def update_quality_standards(
        self,
        product_id: str,
        quality_standards: str,
        tenant_key: str,
    ) -> dict[str, Any]:
        """
        Update quality standards for a product.

        Handover 0316: Updates Product.quality_standards field (direct column, not JSONB).

        Args:
            product_id: Product UUID
            quality_standards: Quality standards text
            tenant_key: Tenant isolation key

        Returns:
            Updated product data:
            {
                "product_id": "uuid",
                "quality_standards": "80% coverage, zero bugs"
            }

        Raises:
            ValueError: If product not found or tenant mismatch

        Multi-Tenant Isolation:
            Verifies product.tenant_key matches provided tenant_key.

        WebSocket Events:
            Emits "product_updated" event to tenant for real-time UI sync.

        Example:
            >>> result = await product_service.update_quality_standards(
            ...     product_id="123e4567-e89b-12d3-a456-426614174000",
            ...     quality_standards="TDD required, 85% coverage, zero P0 bugs",
            ...     tenant_key="tenant_abc"
            ... )
        """
        self._logger.info(
            f"Updating quality_standards for product {product_id}",
            extra={
                "product_id": product_id,
                "tenant_key": tenant_key,
                "has_quality_standards": bool(quality_standards),
            },
        )

        async with self._get_session() as session:
            # Fetch product with multi-tenant isolation
            product = await session.get(Product, product_id)

            # Verify product exists and belongs to tenant
            if not product or product.tenant_key != tenant_key:
                self._logger.warning(
                    f"Product {product_id} not found or wrong tenant",
                    extra={"product_id": product_id, "tenant_key": tenant_key, "operation": "update_quality_standards"},
                )
                raise ValueError(f"Product {product_id} not found")

            # Update quality_standards field
            old_value = product.quality_standards
            product.quality_standards = quality_standards

            # Commit changes
            await session.commit()

            self._logger.info(
                f"Quality standards updated for product {product_id}",
                extra={
                    "product_id": product_id,
                    "tenant_key": tenant_key,
                    "old_value": old_value[:50] if old_value else None,
                    "new_value": quality_standards[:50] if quality_standards else None,
                },
            )

            # Emit WebSocket event for real-time UI updates
            await self._emit_websocket_event(
                event_type="product_updated",
                data={"product_id": product_id, "field": "quality_standards", "quality_standards": quality_standards},
            )

            return {"product_id": product_id, "quality_standards": quality_standards}

    # ============================================================================
    # Lifecycle Management
    # ============================================================================

    async def activate_product(self, product_id: str) -> dict[str, Any]:
        """
        Activate a product (deactivates other products for tenant).

        Only one product can be active at a time per tenant.

        Args:
            product_id: Product UUID to activate

        Returns:
            Dict with activated product

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.activate_product("abc-123")
        """
        try:
            async with self._get_session() as session:
                # Verify product exists
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

                # Flush deactivation to satisfy unique constraint before activating
                if products_to_deactivate:
                    await session.flush()

                    # CRITICAL FIX: Deactivate ALL projects in deactivated products
                    # Enforces non-negotiable rule: one active product → one active project
                    deactivated_product_ids = [p.id for p in products_to_deactivate]

                    # Bulk update: Set all active projects in deactivated products to inactive
                    project_deactivate_stmt = (
                        update(Project)
                        .where(Project.product_id.in_(deactivated_product_ids))
                        .where(Project.status == "active")
                        .values(status="inactive", updated_at=datetime.now(timezone.utc))
                    )
                    await session.execute(project_deactivate_stmt)
                    await session.flush()

                    # Emit WebSocket event for bulk project deactivation
                    await self._emit_websocket_event(
                        event_type="projects:bulk:deactivated",
                        data={
                            "product_ids": [str(pid) for pid in deactivated_product_ids],
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        },
                    )

                # NOW activate target product (after others are deactivated)
                product.is_active = True
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Activated product {product_id} (deactivated {len(products_to_deactivate)} others)")

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "is_active": product.is_active,
                    },
                    "deactivated_count": len(products_to_deactivate),
                }

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to activate product")
            raise BaseGiljoException(
                message=f"Failed to activate product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def deactivate_product(self, product_id: str) -> dict[str, Any]:
        """
        Deactivate a product.

        Args:
            product_id: Product UUID to deactivate

        Returns:
            Dict with deactivated product

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.deactivate_product("abc-123")
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

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Deactivated product {product_id}")

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "is_active": product.is_active,
                    },
                }

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to deactivate product")
            raise BaseGiljoException(
                message=f"Failed to deactivate product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def delete_product(self, product_id: str) -> dict[str, Any]:
        """
        Soft delete a product.

        Args:
            product_id: Product UUID to delete

        Returns:
            Dict with deletion status

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.delete_product("abc-123")
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

                # Soft delete
                product.deleted_at = datetime.now(timezone.utc)
                product.is_active = False  # Deactivate when deleting
                product.updated_at = datetime.now(timezone.utc)

                await session.commit()

                self._logger.info(f"Soft deleted product {product_id}")

                return {
                    "success": True,
                    "message": "Product deleted successfully",
                    "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
                }

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to delete product")
            raise BaseGiljoException(
                message=f"Failed to delete product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def restore_product(self, product_id: str) -> dict[str, Any]:
        """
        Restore a soft-deleted product.

        Args:
            product_id: Product UUID to restore

        Returns:
            Dict with restored product

        Raises:
            ResourceNotFoundError: If deleted product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.restore_product("abc-123")
        """
        try:
            async with self._get_session() as session:
                stmt = select(Product).where(
                    and_(
                        Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.isnot(None)
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Deleted product not found",
                        context={"product_id": product_id, "tenant_key": self.tenant_key},
                    )

                # Restore
                product.deleted_at = None
                product.updated_at = datetime.now(timezone.utc)
                # Note: Don't auto-activate on restore, let user explicitly activate

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Restored product {product_id}")

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "is_active": product.is_active,
                    },
                }

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to restore product")
            raise BaseGiljoException(
                message=f"Failed to restore product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def list_deleted_products(self) -> dict[str, Any]:
        """
        List soft-deleted products with purge information.

        Returns:
            Dict with list of deleted products

        Raises:
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.list_deleted_products()
            >>> for product in result["products"]:
            ...     print(f"{product['name']} - purge in {product['days_until_purge']} days")
        """
        try:
            purge_days = 10  # 10-day purge policy (matches purge_expired_deleted_products)

            async with self._get_session() as session:
                stmt = (
                    select(Product)
                    .where(and_(Product.tenant_key == self.tenant_key, Product.deleted_at.isnot(None)))
                    .order_by(Product.deleted_at.desc())
                )

                result = await session.execute(stmt)
                deleted_products = result.scalars().all()

                product_list = []
                for product in deleted_products:
                    # Calculate purge date
                    purge_date = product.deleted_at + timedelta(days=purge_days)
                    days_until_purge = max(0, (purge_date - datetime.now(timezone.utc)).days)

                    # Count related entities
                    project_count = await session.execute(
                        select(func.count(Project.id)).where(Project.product_id == product.id)
                    )
                    vision_count = await session.execute(
                        select(func.count(VisionDocument.id)).where(VisionDocument.product_id == product.id)
                    )

                    product_list.append(
                        {
                            "id": str(product.id),
                            "name": product.name,
                            "description": product.description,
                            "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
                            "days_until_purge": days_until_purge,
                            "purge_date": purge_date.isoformat(),
                            "project_count": project_count.scalar() or 0,
                            "vision_documents_count": vision_count.scalar() or 0,
                        }
                    )

                return {"success": True, "products": product_list}

        except Exception as e:
            self._logger.exception("Failed to list deleted products")
            raise BaseGiljoException(
                message=f"Failed to list deleted products: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    # ============================================================================
    # Active Product Management
    # ============================================================================

    async def get_active_product(self) -> dict[str, Any]:
        """
        Get the currently active product for the tenant.

        Returns:
            Dict with active product (or None if no active product)

        Raises:
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.get_active_product()
            >>> if result.get("product"):
            ...     print(f"Active: {result['product']['name']}")
        """
        try:
            async with self._get_session() as session:
                stmt = (
                    select(Product)
                    .options(selectinload(Product.vision_documents))
                    .where(
                        and_(
                            Product.tenant_key == self.tenant_key,
                            Product.is_active,
                            Product.deleted_at.is_(None),
                        )
                    )
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    return {"success": True, "product": None, "message": "No active product"}

                # Get metrics for active product
                metrics = await self._get_product_metrics(session, product.id)

                return {
                    "success": True,
                    "product": {
                        "id": str(product.id),
                        "name": product.name,
                        "description": product.description,
                        "vision_path": product.primary_vision_path,
                        "project_path": product.project_path,
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                        "config_data": product.config_data,
                        "has_config_data": bool(product.config_data),
                        "is_active": product.is_active,
                        **metrics,
                    },
                }

        except Exception as e:
            self._logger.exception("Failed to get active product")
            raise BaseGiljoException(
                message=f"Failed to get active product: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    # ============================================================================
    # Metrics & Statistics
    # ============================================================================

    async def get_product_statistics(self, product_id: str) -> dict[str, Any]:
        """
        Get comprehensive statistics for a product.

        Args:
            product_id: Product UUID

        Returns:
            Dict with statistics

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.get_product_statistics("abc-123")
            >>> print(f"Projects: {result['statistics']['total_projects']}")
        """
        try:
            async with self._get_session() as session:
                # Verify product exists
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

                return {
                    "success": True,
                    "statistics": {
                        "product_id": product_id,
                        "name": product.name,
                        "is_active": product.is_active,
                        **metrics,
                        "created_at": product.created_at.isoformat() if product.created_at else None,
                        "updated_at": product.updated_at.isoformat() if product.updated_at else None,
                    },
                }

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to get product statistics")
            raise BaseGiljoException(
                message=f"Failed to get product statistics: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def get_cascade_impact(self, product_id: str) -> dict[str, Any]:
        """
        Get cascade impact analysis for product deletion.

        Shows what entities would be affected by deleting this product.

        Args:
            product_id: Product UUID

        Returns:
            Dict with impact analysis

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.get_cascade_impact("abc-123")
            >>> print(f"Will affect {result['impact']['total_projects']} projects")
        """
        try:
            async with self._get_session() as session:
                # Verify product exists
                stmt = select(Product).where(
                    and_(Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                # Count related entities
                project_count = await session.execute(
                    select(func.count(Project.id)).where(
                        and_(
                            Project.product_id == product_id, or_(Project.status != "deleted", Project.status.is_(None))
                        )
                    )
                )

                task_count = await session.execute(select(func.count(Task.id)).where(Task.product_id == product_id))

                vision_count = await session.execute(
                    select(func.count(VisionDocument.id)).where(VisionDocument.product_id == product_id)
                )

                return {
                    "success": True,
                    "impact": {
                        "product_id": product_id,
                        "product_name": product.name,
                        "total_projects": project_count.scalar() or 0,
                        "total_tasks": task_count.scalar() or 0,
                        "total_vision_documents": vision_count.scalar() or 0,
                        "warning": "Deleting this product will soft-delete all related entities",
                    },
                }

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to get cascade impact")
            raise BaseGiljoException(
                message=f"Failed to get cascade impact: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def update_git_integration(
        self,
        product_id: str,
        enabled: bool,
        commit_limit: int = 20,
        default_branch: str = "main",
    ) -> dict[str, Any]:
        """
        Update Git integration settings for a product (Handover 013B - Simplified).

        Settings are stored in product_memory.git_integration field with structure:
        {
            "enabled": bool,
            "commit_limit": int,  # Max commits to show in prompts
            "default_branch": str  # Default branch name (e.g., "main", "master")
        }

        REMOVED: GitHub API integration, URL validation
        Git operations are handled by CLI agents (Claude Code, Codex, Gemini).

        Args:
            product_id: Product UUID
            enabled: Whether git integration is enabled
            commit_limit: Max commits to include in prompts (default: 20)
            default_branch: Default branch name (default: "main")

        Returns:
            Dict with settings

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoException: If database operation fails

        Example:
            >>> result = await service.update_git_integration(
            ...     product_id="abc-123",
            ...     enabled=True,
            ...     commit_limit=30,
            ...     default_branch="develop"
            ... )
        """
        try:
            async with self._get_session() as session:
                # Verify product exists
                stmt = select(Product).where(
                    and_(Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                # Ensure product_memory exists (history is in table, not JSONB)
                if not product.product_memory:
                    product.product_memory = {"git_integration": {}, "context": {}}

                # Update Git integration settings
                if enabled:
                    product.product_memory["git_integration"] = {
                        "enabled": True,
                        "commit_limit": commit_limit,
                        "default_branch": default_branch,
                    }
                else:
                    # Disable integration - clear all config
                    product.product_memory["git_integration"] = {
                        "enabled": False,
                    }

                product.updated_at = datetime.now(timezone.utc)

                # Force SQLAlchemy to detect JSONB change
                try:
                    from sqlalchemy.orm.attributes import flag_modified

                    flag_modified(product, "product_memory")
                except AttributeError:
                    # Mock object in tests - flag_modified will fail
                    pass

                await session.commit()
                await session.refresh(product)

                self._logger.info(f"Updated git integration for product {product_id}: enabled={enabled}")

                # Handover 013B: Emit WebSocket event for git settings change
                await self._emit_websocket_event(
                    event_type="product:git:settings:changed",
                    data={"product_id": product_id, "settings": product.product_memory["git_integration"]},
                )

                return {"success": True, "settings": product.product_memory["git_integration"]}

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to update git integration")
            raise BaseGiljoException(
                message=f"Failed to update git integration: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def upload_vision_document(
        self,
        product_id: str,
        content: str,
        filename: str,
        auto_chunk: bool = True,
        max_tokens: int = 25000,
    ) -> dict[str, Any]:
        """
        Upload and optionally chunk vision document for product.

        Uses VisionDocumentChunker for intelligent chunking at semantic boundaries.
        Documents exceeding max_tokens are automatically split into chunks.

        Args:
            product_id: Product UUID
            content: Document content (text/markdown)
            filename: Document filename
            auto_chunk: Auto-chunk if content exceeds max_tokens (default: True)
            max_tokens: Max tokens per chunk (default: 25000 for 32K models)

        Returns:
            Dict with success status and document/chunk details
            {
                "success": bool,
                "document_id": str,
                "document_name": str,
                "chunks_created": int,
                "total_tokens": int,
                "error": str (if failed)
            }

        Raises:
            ValueError: If product not found or user lacks access

        Example:
            >>> result = await service.upload_vision_document(
            ...     product_id="abc-123",
            ...     content="# Vision\\n...",
            ...     filename="vision.md"
            ... )
            >>> print(f"Created {result['chunks_created']} chunks")
        """
        try:
            from src.giljo_mcp.context_management.chunker import VisionDocumentChunker
            from src.giljo_mcp.repositories.vision_document_repository import VisionDocumentRepository

            async with self._get_session() as session:
                # Verify product exists and belongs to tenant
                stmt = select(Product).where(
                    and_(Product.id == product_id, Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                product = result.scalar_one_or_none()

                if not product:
                    raise ResourceNotFoundError(
                        message=f"Product {product_id} not found or access denied",
                        context={"product_id": product_id, "tenant_key": self.tenant_key},
                    )

                # Create vision document via repository
                vision_repo = VisionDocumentRepository(db_manager=self.db_manager)

                # Calculate file size
                file_size = len(content.encode("utf-8"))

                # Create document (inline storage)
                doc = await vision_repo.create(
                    session=session,
                    tenant_key=self.tenant_key,
                    product_id=product_id,
                    document_name=filename,
                    content=content,
                    document_type="vision",
                    storage_type="inline",
                    file_size=file_size,
                    is_active=True,
                    display_order=0,
                )

                await session.commit()

                self._logger.info(f"Created vision document {doc.id} for product {product_id}")

                # Multi-level summarization (Handover 0345e)
                # Always generate summaries for large documents (no toggle check)
                # Handover 0377: Summarize all documents (100 token minimum to skip empty/trivial files)
                # Light=33%, Medium=66%, Full=100% (original)
                total_tokens = len(content) // 4  # Rough estimate: 1 token ≈ 4 chars

                # Generate multi-level summaries if document exceeds threshold
                if total_tokens > 100:  # Summarize all non-trivial documents
                    try:
                        from src.giljo_mcp.services.vision_summarizer import VisionDocumentSummarizer

                        self._logger.info(f"Generating multi-level summaries for doc {doc.id}: {total_tokens} tokens")

                        summarizer = VisionDocumentSummarizer()
                        summaries = summarizer.summarize_multi_level(content)

                        # Re-attach doc to session after previous commit (fixes detached state)
                        session.add(doc)

                        # Store summary levels (Handover 0352: light and medium only)
                        doc.summary_light = summaries["light"]["summary"]
                        doc.summary_medium = summaries["medium"]["summary"]
                        doc.summary_light_tokens = summaries["light"]["tokens"]
                        doc.summary_medium_tokens = summaries["medium"]["tokens"]
                        doc.is_summarized = True
                        doc.original_token_count = summaries["original_tokens"]

                        # Backward compatibility: set summary_text to medium summary
                        doc.summary_text = summaries["medium"]["summary"]
                        doc.compression_ratio = (
                            (summaries["original_tokens"] - summaries["medium"]["tokens"])
                            / summaries["original_tokens"]
                            if summaries["original_tokens"] > 0
                            else 0.0
                        )

                        await session.commit()

                        self._logger.info(
                            f"Vision document {doc.id} summarized: "
                            f"Light={summaries['light']['tokens']} tokens, "
                            f"Medium={summaries['medium']['tokens']} tokens "
                            f"(from {summaries['original_tokens']} tokens) "
                            f"in {summaries['processing_time_ms']}ms"
                        )
                    except (ImportError, ValueError, KeyError) as e:
                        # Summarization failed but document created - log warning and continue
                        self._logger.warning(f"Document {doc.id} created but summarization failed: {e}")

                # Auto-chunk if enabled
                chunks_created = 0
                chunk_total_tokens = 0  # Track chunker's token count separately

                if auto_chunk:
                    chunker = VisionDocumentChunker(target_chunk_size=max_tokens)

                    # Chunk the document
                    chunk_result = await chunker.chunk_vision_document(
                        session=session, tenant_key=self.tenant_key, vision_document_id=str(doc.id)
                    )

                    await session.commit()

                    if chunk_result["success"]:
                        chunks_created = chunk_result["chunks_created"]
                        chunk_total_tokens = chunk_result["total_tokens"]
                        # Update total_tokens for return value (use chunker's accurate count)
                        total_tokens = chunk_total_tokens

                        self._logger.info(f"Chunked document {doc.id}: {chunks_created} chunks, {total_tokens} tokens")
                    else:
                        # Chunking failed but document created
                        self._logger.warning(
                            f"Document {doc.id} created but chunking failed: "
                            f"{chunk_result.get('error', 'Unknown error')}"
                        )

                return {
                    "success": True,
                    "document_id": str(doc.id),
                    "document_name": doc.document_name,
                    "chunks_created": chunks_created,
                    "total_tokens": total_tokens,
                }

        except ValueError as e:
            self._logger.exception("Validation error uploading vision document")
            raise ValidationError(
                message=f"Validation error uploading vision document: {e!s}",
                context={"product_id": product_id, "filename": filename},
            ) from e
        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:
            self._logger.exception("Failed to upload vision document")
            raise BaseGiljoException(
                message=f"Failed to upload vision document: {e!s}",
                context={"product_id": product_id, "filename": filename, "tenant_key": self.tenant_key},
            ) from e

    # ============================================================================
    # Validation Methods
    # ============================================================================

    @staticmethod
    def validate_project_path(project_path: str) -> bool:
        """
        Validate project path for agent export functionality (Handover 0084).

        Args:
            project_path: File system path to validate

        Returns:
            True if valid, raises HTTPException if invalid

        Raises:
            HTTPException: If path is invalid, doesn't exist, isn't a directory, or isn't writable

        Example:
            >>> ProductService.validate_project_path("/path/to/project")
            True
        """
        from pathlib import Path

        from fastapi import HTTPException

        if not project_path:
            return True  # Optional field

        try:
            # Expand user home directory if present
            path = Path(project_path).expanduser()

            # Check if path exists and is a directory
            if not path.exists():
                logger.warning(f"Project path validation failed - does not exist: {path}")
                raise HTTPException(status_code=400, detail="Project path does not exist")

            if not path.is_dir():
                logger.warning(f"Project path validation failed - not a directory: {path}")
                raise HTTPException(status_code=400, detail="Project path is not a directory")

            # Check if path is writable (for .claude/agents creation)
            try:
                test_dir = path / ".claude_test_write"
                test_dir.mkdir(exist_ok=True)
                test_dir.rmdir()
            except (PermissionError, OSError) as e:
                logger.warning(f"Project path validation failed - not writable: {path}")
                raise HTTPException(status_code=400, detail="Project path is not writable") from e

            return True

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(f"Project path validation failed - invalid path: {project_path}, error: {e}")
            raise HTTPException(status_code=400, detail="Invalid project path") from e

    # ============================================================================
    # WebSocket Event Emission (Handover 0139a)
    # ============================================================================

    async def _emit_websocket_event(self, event_type: str, data: dict[str, Any]) -> None:
        """
        Emit WebSocket event to tenant clients (Handover 0139a).

        This helper method provides graceful degradation - events are emitted
        if WebSocket manager is available, but operations don't fail if it's not.

        Args:
            event_type: Event type (e.g., "product:memory:updated")
            data: Event payload data

        Side Effects:
            - Broadcasts event to all tenant clients via WebSocket
            - Logs warning if WebSocket fails (doesn't crash operation)

        Example:
            >>> await self._emit_websocket_event(
            ...     "product:memory:updated",
            ...     {"product_id": "abc-123", "product_memory": {...}}
            ... )
        """
        if not self._websocket_manager:
            # No WebSocket manager - gracefully skip event emission
            self._logger.debug(f"No WebSocket manager available for event: {event_type}")
            return

        try:
            # Add timestamp to event data
            event_data_with_timestamp = {
                **data,
                "tenant_key": self.tenant_key,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }

            # Broadcast to tenant clients
            await self._websocket_manager.broadcast_to_tenant(
                tenant_key=self.tenant_key, event_type=event_type, data=event_data_with_timestamp
            )

            self._logger.debug(f"WebSocket event emitted: {event_type} for tenant {self.tenant_key}")

        except (RuntimeError, ValueError) as e:
            # Log error but don't fail the operation
            self._logger.warning(f"Failed to emit WebSocket event {event_type}: {e}", exc_info=True)

    # ============================================================================
    # Private Helper Methods
    # ============================================================================

    async def _build_product_memory_response(
        self, session: AsyncSession, product: Product, include_deleted: bool = False
    ) -> dict:
        """
        Build product_memory response with sequential_history from table (Handover 0390b).

        This method maintains backward compatibility by returning the same structure
        as before, but populates sequential_history from product_memory_entries table
        instead of the JSONB column.

        Args:
            session: Async database session
            product: Product instance
            include_deleted: Include soft-deleted memory entries (default: False)

        Returns:
            Dict with product_memory structure:
            {
                "git_integration": {...},
                "sequential_history": [...],  # From table
                "context": {...}
            }

        Example:
            >>> memory = await self._build_product_memory_response(session, product)
            >>> assert "sequential_history" in memory
        """
        from src.giljo_mcp.repositories.product_memory_repository import ProductMemoryRepository

        # Start with JSONB data (git_integration, context)
        base_memory = product.product_memory or {}
        git_integration = base_memory.get("git_integration", {})
        context = base_memory.get("context", {})

        # Fetch sequential_history from table
        repo = ProductMemoryRepository()
        entries = await repo.get_entries_by_product(
            session=session,
            product_id=product.id,
            tenant_key=self.tenant_key,
            include_deleted=include_deleted,
        )

        # Convert to dict format (maintains backward compatibility)
        sequential_history = [entry.to_dict() for entry in entries]

        # Build response
        return {
            "git_integration": git_integration,
            "sequential_history": sequential_history,
            "context": context,
        }

    async def _ensure_product_memory_initialized(self, session: AsyncSession, product: Product) -> None:
        """
        Ensure product_memory is initialized with default structure (Handover 0136).

        This method provides backward compatibility for products that may have:
        - NULL product_memory (edge case, shouldn't happen with migration)
        - Empty dict {} (incomplete initialization)
        - Partial memory structure (e.g., only "github" key)

        The method is idempotent - safe to call multiple times.

        Args:
            session: Async database session
            product: Product instance to check/initialize

        Side Effects:
            - Updates product.product_memory if incomplete
            - Commits changes to database if modifications made

        Example:
            >>> await self._ensure_product_memory_initialized(session, product)
            >>> assert product.product_memory == {"github": {}, "context": {}}
        """
        # Default structure per Handover 0135 + 0700c (history in table)
        default_structure = {
            "github": {},
            "context": {},
        }

        # Check if product_memory needs initialization
        needs_update = False

        if product.product_memory is None:
            # NULL case - replace with default
            product.product_memory = default_structure
            needs_update = True
            self._logger.debug(f"Product {product.id}: Initialized NULL product_memory")
        elif not isinstance(product.product_memory, dict):
            # Invalid type - replace with default
            product.product_memory = default_structure
            needs_update = True
            self._logger.warning(
                f"Product {product.id}: Replaced invalid product_memory type "
                f"({type(product.product_memory)}) with default structure"
            )
        elif not product.product_memory:
            # Empty dict - replace with default
            product.product_memory = default_structure
            needs_update = True
            self._logger.debug(f"Product {product.id}: Initialized empty dict product_memory")
        else:
            # Partial structure - ensure all required keys exist
            # Create a copy to ensure SQLAlchemy detects the change
            updated_memory = dict(product.product_memory)
            for key, default_value in default_structure.items():
                if key not in updated_memory:
                    updated_memory[key] = default_value
                    needs_update = True
                    self._logger.debug(f"Product {product.id}: Added missing '{key}' key to product_memory")

            if needs_update:
                product.product_memory = updated_memory

        # Commit changes if modifications were made
        if needs_update:
            product.updated_at = datetime.now(timezone.utc)
            await session.commit()
            await session.refresh(product)
            self._logger.info(f"Product {product.id}: Updated product_memory structure")

    async def _get_product_metrics(self, session: AsyncSession, product_id: str) -> dict[str, Any]:
        """
        Get metrics for a product (projects, tasks, vision documents).

        Args:
            session: Async database session
            product_id: Product UUID

        Returns:
            Dict with metric counts
        """
        # Count projects
        projects_result = await session.execute(
            select(func.count(Project.id)).where(
                and_(Project.product_id == product_id, or_(Project.status != "deleted", Project.status.is_(None)))
            )
        )
        project_count = projects_result.scalar() or 0

        # Count unfinished projects
        unfinished_result = await session.execute(
            select(func.count(Project.id)).where(
                and_(Project.product_id == product_id, Project.status.in_(["active", "inactive"]))
            )
        )
        unfinished_projects = unfinished_result.scalar() or 0

        # Count tasks
        tasks_result = await session.execute(select(func.count(Task.id)).where(Task.product_id == product_id))
        task_count = tasks_result.scalar() or 0

        # Count unresolved tasks
        unresolved_result = await session.execute(
            select(func.count(Task.id)).where(
                and_(Task.product_id == product_id, Task.status.in_(["pending", "in_progress"]))
            )
        )
        unresolved_tasks = unresolved_result.scalar() or 0

        # Count vision documents
        # Note: VisionDocument doesn't support soft delete (no deleted_at field)
        vision_result = await session.execute(
            select(func.count(VisionDocument.id)).where(VisionDocument.product_id == product_id)
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

    async def purge_expired_deleted_products(self, days_before_purge: int = 10) -> dict[str, Any]:
        """
        Hard delete products that were soft-deleted more than specified days ago.

        SQLAlchemy cascade="all, delete-orphan" handles child relationships:
        - Projects (and their children via ProjectService cascade)
        - Tasks
        - VisionDocuments

        Called from startup.py on server start for automatic cleanup.

        Args:
            days_before_purge: Number of days before permanent deletion (default: 10)

        Returns:
            dict: Purge results with count and details
                - success: bool - Operation success status
                - purged_count: int - Number of products purged
                - products: list - Details of purged products
                - error: str - Error message if failed

        Example:
            >>> result = await service.purge_expired_deleted_products()
            >>> print(f"Purged {result['purged_count']} expired products")
        """

        if not self.db_manager:
            self._logger.error("[Product Purge] Cannot purge - database manager not available")
            raise DatabaseError(
                message="Database not available",
                context={"operation": "purge_expired_deleted_products", "tenant_key": self.tenant_key},
            )

        try:
            async with self._get_session() as session:
                # Find products deleted more than specified days ago
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
                    return {"success": True, "purged_count": 0, "products": []}

                # Hard delete each expired product (cascade handles children)
                purged_products = []
                for product in expired_products:
                    purged_info = {
                        "id": product.id,
                        "name": product.name,
                        "tenant_key": product.tenant_key,
                        "deleted_at": product.deleted_at.isoformat() if product.deleted_at else None,
                    }
                    days_ago = (datetime.now(timezone.utc) - product.deleted_at).days

                    await session.delete(product)
                    purged_products.append(purged_info)

                    self._logger.info(
                        f"[Product Purge] Auto-purged expired product {product.id} (deleted {days_ago} days ago)"
                    )

                await session.commit()

                self._logger.info(
                    f"[Product Purge] Successfully purged {len(purged_products)} expired deleted products"
                )

                return {"success": True, "purged_count": len(purged_products), "products": purged_products}

        except DatabaseError:
            # Re-raise database errors as-is
            raise
        except Exception as e:
            self._logger.exception("[Product Purge] Failed to purge expired deleted products")
            raise BaseGiljoException(
                message=f"Failed to purge expired deleted products: {e!s}",
                context={
                    "operation": "purge_expired_deleted_products",
                    "tenant_key": self.tenant_key,
                    "days_before_purge": days_before_purge,
                },
            ) from e
