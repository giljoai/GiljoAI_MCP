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
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import Product
from src.giljo_mcp.models.products import (
    VALID_TARGET_PLATFORMS,
    ProductArchitecture,
    ProductTechStack,
    ProductTestConfig,
)
from src.giljo_mcp.schemas.jsonb_validators import validate_product_memory
from src.giljo_mcp.schemas.service_responses import (
    CascadeImpact,
    DeleteResult,
    ProductStatistics,
    PurgeResult,
)
from src.giljo_mcp.services.product_lifecycle_service import ProductLifecycleService
from src.giljo_mcp.services.product_memory_service import ProductMemoryService


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

    Lifecycle state changes are delegated to ProductLifecycleService.
    Statistics and memory helpers are delegated to ProductMemoryService.

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
        self._websocket_manager = websocket_manager
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

        self._lifecycle = ProductLifecycleService(
            db_manager=db_manager,
            tenant_key=tenant_key,
            websocket_manager=websocket_manager,
            test_session=test_session,
        )
        self._memory = ProductMemoryService(
            db_manager=db_manager,
            tenant_key=tenant_key,
            test_session=test_session,
        )

    def _get_session(self):
        """
        Get a session, preferring an injected test session when provided.
        This keeps service methods compatible with test transaction fixtures.

        Returns:
            Context manager for database session
        """
        if self._test_session is not None:

            @asynccontextmanager
            async def _test_session_wrapper():
                yield self._test_session

            return _test_session_wrapper()

        return self.db_manager.get_session_async()

    def _validate_target_platforms(self, target_platforms: list[str]) -> tuple[bool, str | None]:
        """
        Validate target_platforms field (Handover 0425).

        Args:
            target_platforms: List of platform values

        Returns:
            Tuple of (is_valid, error_message)

        Validation Rules:
            - All values must be in VALID_TARGET_PLATFORMS
            - If 'all' is present, it must be the only value
        """
        if not target_platforms:
            return False, "target_platforms cannot be empty"

        invalid_platforms = set(target_platforms) - VALID_TARGET_PLATFORMS

        if invalid_platforms:
            valid_list = ", ".join(sorted(VALID_TARGET_PLATFORMS))
            return False, f"Invalid platform values: {', '.join(sorted(invalid_platforms))}. Valid values: {valid_list}"

        if "all" in target_platforms and len(target_platforms) > 1:
            return False, "'all' platform cannot be combined with specific platforms"

        return True, None

    def _create_config_relations(self, session: AsyncSession, product_id: str, config_data: dict) -> None:
        """Create normalized config table rows from config data. Handover 0840i: canonical names only."""
        tech_stack = config_data.get("tech_stack")
        if tech_stack and isinstance(tech_stack, dict):
            ts = ProductTechStack(
                product_id=product_id,
                tenant_key=self.tenant_key,
                programming_languages=tech_stack.get("programming_languages", ""),
                frontend_frameworks=tech_stack.get("frontend_frameworks", ""),
                backend_frameworks=tech_stack.get("backend_frameworks", ""),
                databases_storage=tech_stack.get("databases_storage", ""),
                infrastructure=tech_stack.get("infrastructure", ""),
                dev_tools=tech_stack.get("dev_tools", ""),
            )
            session.add(ts)

        architecture = config_data.get("architecture")
        if architecture and isinstance(architecture, dict):
            arch = ProductArchitecture(
                product_id=product_id,
                tenant_key=self.tenant_key,
                primary_pattern=architecture.get("primary_pattern", ""),
                design_patterns=architecture.get("design_patterns", ""),
                api_style=architecture.get("api_style", ""),
                architecture_notes=architecture.get("architecture_notes", ""),
                coding_conventions=architecture.get("coding_conventions", ""),
            )
            session.add(arch)

        test_config = config_data.get("test_config")
        if test_config and isinstance(test_config, dict):
            tc = ProductTestConfig(
                product_id=product_id,
                tenant_key=self.tenant_key,
                quality_standards=test_config.get("quality_standards", ""),
                test_strategy=test_config.get("test_strategy", ""),
                coverage_target=test_config.get("coverage_target", 80),
                testing_frameworks=test_config.get("testing_frameworks", ""),
            )
            session.add(tc)

    async def _update_config_relations(self, session: AsyncSession, product: Product, config_data: dict) -> None:
        """Update normalized config table rows. Handover 0840i: canonical names only."""
        tech_stack = config_data.get("tech_stack")
        if tech_stack and isinstance(tech_stack, dict):
            ts = product.tech_stack
            if ts is None:
                ts = ProductTechStack(product_id=product.id, tenant_key=self.tenant_key)
                session.add(ts)
                product.tech_stack = ts
            ts.programming_languages = tech_stack.get("programming_languages", "")
            ts.frontend_frameworks = tech_stack.get("frontend_frameworks", "")
            ts.backend_frameworks = tech_stack.get("backend_frameworks", "")
            ts.databases_storage = tech_stack.get("databases_storage", "")
            ts.infrastructure = tech_stack.get("infrastructure", "")
            ts.dev_tools = tech_stack.get("dev_tools", "")

        architecture = config_data.get("architecture")
        if architecture and isinstance(architecture, dict):
            arch = product.architecture
            if arch is None:
                arch = ProductArchitecture(product_id=product.id, tenant_key=self.tenant_key)
                session.add(arch)
                product.architecture = arch
            arch.primary_pattern = architecture.get("primary_pattern", "")
            arch.design_patterns = architecture.get("design_patterns", "")
            arch.api_style = architecture.get("api_style", "")
            arch.architecture_notes = architecture.get("architecture_notes", "")
            arch.coding_conventions = architecture.get("coding_conventions", "")

        test_config = config_data.get("test_config")
        if test_config and isinstance(test_config, dict):
            tc = product.test_config
            if tc is None:
                tc = ProductTestConfig(product_id=product.id, tenant_key=self.tenant_key)
                session.add(tc)
                product.test_config = tc
            tc.quality_standards = test_config.get("quality_standards", "")
            tc.test_strategy = test_config.get("test_strategy", "")
            tc.coverage_target = test_config.get("coverage_target", 80)
            tc.testing_frameworks = test_config.get("testing_frameworks", "")

    # ============================================================================
    # CRUD Operations
    # ============================================================================

    async def create_product(
        self,
        name: str,
        description: str | None = None,
        project_path: str | None = None,
        tech_stack: dict[str, Any] | None = None,
        architecture: dict[str, Any] | None = None,
        test_config: dict[str, Any] | None = None,
        core_features: str | None = None,
        brand_guidelines: str | None = None,
        product_memory: dict[str, Any] | None = None,
        target_platforms: list[str] | None = None,
    ) -> Product:
        """
        Create a new product.

        Handover 0840i: Accepts normalized config fields directly instead of config_data dict.

        Args:
            name: Product name (required)
            description: Product description
            project_path: File system path to product folder
            tech_stack: Tech stack configuration dict
            architecture: Architecture configuration dict
            test_config: Test configuration dict
            core_features: Core product features string
            product_memory: 360 Memory data (GitHub, sequential_history, context) - Handover 0135
            target_platforms: Target platforms (windows, linux, macos, android, ios, web, or all) - Handover 0425

        Returns:
            Product ORM model after commit and refresh

        Raises:
            ValidationError: If target_platforms invalid or product name already exists
            BaseGiljoError: If database operation fails
        """
        try:
            if target_platforms is not None:
                is_valid, error_msg = self._validate_target_platforms(target_platforms)
                if not is_valid:
                    raise ValidationError(message=error_msg, context={"target_platforms": target_platforms})

            async with self._get_session() as session:
                stmt = select(Product).where(
                    and_(Product.tenant_key == self.tenant_key, Product.name == name, Product.deleted_at.is_(None))
                )
                result = await session.execute(stmt)
                if result.scalar_one_or_none():
                    raise ValidationError(
                        message=f"Product '{name}' already exists",
                        context={"product_name": name, "tenant_key": self.tenant_key},
                    )

                # Handover 0135 + 0700c: Initialize product_memory (history in table)
                default_memory = {
                    "github": {},
                    "context": {},
                }

                product_id = str(uuid4())

                validated_memory = validate_product_memory(product_memory) or default_memory
                product = Product(
                    id=product_id,
                    tenant_key=self.tenant_key,
                    name=name,
                    description=description,
                    project_path=project_path,
                    core_features=core_features,
                    brand_guidelines=brand_guidelines,
                    product_memory=validated_memory,
                    target_platforms=target_platforms or ["all"],
                    is_active=False,
                    created_at=datetime.now(timezone.utc),
                )

                session.add(product)

                # Handover 0840i: Create normalized config table rows from typed fields
                config_parts = {}
                if tech_stack:
                    config_parts["tech_stack"] = tech_stack
                if architecture:
                    config_parts["architecture"] = architecture
                if test_config:
                    config_parts["test_config"] = test_config
                if config_parts:
                    self._create_config_relations(session, product_id, config_parts)

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=[
                        "tech_stack",
                        "architecture",
                        "test_config",
                        "vision_documents",
                    ],
                )

                self._logger.info(f"Created product {product.id} for tenant {self.tenant_key}")

                return product

        except ValidationError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to create product")
            raise BaseGiljoError(
                message=f"Failed to create product: {e!s}",
                context={"product_name": name, "tenant_key": self.tenant_key},
            ) from e

    async def get_product(self, product_id: str) -> Product:
        """
        Get a specific product by ID.

        Args:
            product_id: Product UUID

        Returns:
            Product ORM model

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                stmt = (
                    select(Product)
                    .options(
                        selectinload(Product.vision_documents),
                        selectinload(Product.tech_stack),
                        selectinload(Product.architecture),
                        selectinload(Product.test_config),
                    )
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
                await self._memory._ensure_product_memory_initialized(session, product)

                # Handover 0412: Force refresh to ensure we have latest DB data
                # Handover 0840h: Include relationships so refresh doesn't discard eager loads
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                return product

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get product")
            raise BaseGiljoError(
                message=f"Failed to get product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def list_products(self, include_inactive: bool = False) -> list[Product]:
        """
        List all products for tenant with optional filtering.

        Args:
            include_inactive: Include inactive products (default: False)

        Returns:
            List of Product ORM models

        Raises:
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                conditions = [Product.tenant_key == self.tenant_key, Product.deleted_at.is_(None)]

                if not include_inactive:
                    conditions.append(Product.is_active)

                stmt = (
                    select(Product)
                    .where(and_(*conditions))
                    .options(
                        selectinload(Product.vision_documents),
                        selectinload(Product.tech_stack),
                        selectinload(Product.architecture),
                        selectinload(Product.test_config),
                    )
                    .order_by(Product.is_active.desc(), Product.created_at.desc())
                )
                result = await session.execute(stmt)
                products = result.scalars().all()

                for product in products:
                    # Handover 0136: Ensure product_memory is initialized (backward compatibility)
                    await self._memory._ensure_product_memory_initialized(session, product)

                self._logger.debug(f"Found {len(products)} products for tenant {self.tenant_key}")

                return list(products)

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list products")
            raise BaseGiljoError(
                message=f"Failed to list products: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    async def update_product(self, product_id: str, **updates) -> Product:
        """
        Update a product.

        Args:
            product_id: Product UUID
            **updates: Fields to update (name, description, project_path, tech_stack, architecture,
                test_config, core_features, product_memory, target_platforms, etc.)

        Returns:
            Product ORM model after commit and refresh

        Raises:
            ResourceNotFoundError: If product not found
            ValidationError: If target_platforms invalid
            BaseGiljoError: If database operation fails
        """
        try:
            if "target_platforms" in updates:
                is_valid, error_msg = self._validate_target_platforms(updates["target_platforms"])
                if not is_valid:
                    raise ValidationError(message=error_msg, context={"target_platforms": updates["target_platforms"]})

            async with self._get_session() as session:
                stmt = (
                    select(Product)
                    .options(
                        selectinload(Product.tech_stack),
                        selectinload(Product.architecture),
                        selectinload(Product.test_config),
                    )
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

                # Handover 0840i: Handle normalized config fields
                tech_stack = updates.pop("tech_stack", None)
                architecture_data = updates.pop("architecture", None)
                test_config = updates.pop("test_config", None)
                core_features = updates.pop("core_features", None)

                if core_features is not None:
                    product.core_features = core_features

                config_parts = {}
                if tech_stack and isinstance(tech_stack, dict):
                    config_parts["tech_stack"] = tech_stack
                if architecture_data and isinstance(architecture_data, dict):
                    config_parts["architecture"] = architecture_data
                if test_config and isinstance(test_config, dict):
                    config_parts["test_config"] = test_config
                if config_parts:
                    await self._update_config_relations(session, product, config_parts)

                for field, value in updates.items():
                    if hasattr(product, field):
                        setattr(product, field, value)

                product.updated_at = datetime.now(timezone.utc)

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Updated product {product_id}")

                # Handover 0139a: Emit WebSocket event if product_memory was updated
                # Handover 0390b: Build product_memory from table for WebSocket event
                if "product_memory" in updates:
                    product_memory = await self._memory._build_product_memory_response(session, product)
                    await self._lifecycle._emit_websocket_event(
                        event_type="product:memory:updated",
                        data={"product_id": product_id, "product_memory": product_memory},
                    )

                return product

        except (ResourceNotFoundError, ValidationError):
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to update product")
            raise BaseGiljoError(
                message=f"Failed to update product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    # ============================================================================
    # Lifecycle Management -- delegated to ProductLifecycleService
    # ============================================================================

    async def activate_product(self, product_id: str) -> Product:
        """Activate a product (deactivates other products for tenant). Delegated to ProductLifecycleService."""
        return await self._lifecycle.activate_product(product_id)

    async def deactivate_product(self, product_id: str) -> Product:
        """Deactivate a product. Delegated to ProductLifecycleService."""
        return await self._lifecycle.deactivate_product(product_id)

    async def delete_product(self, product_id: str) -> DeleteResult:
        """Soft delete a product. Delegated to ProductLifecycleService."""
        return await self._lifecycle.delete_product(product_id)

    async def restore_product(self, product_id: str) -> Product:
        """Restore a soft-deleted product. Delegated to ProductLifecycleService."""
        return await self._lifecycle.restore_product(product_id)

    async def purge_product(self, product_id: str) -> dict:
        """Permanently delete a product and ALL related data. Delegated to ProductLifecycleService."""
        return await self._lifecycle.purge_product(product_id)

    async def list_deleted_products(self) -> list[Product]:
        """List soft-deleted products. Delegated to ProductLifecycleService."""
        return await self._lifecycle.list_deleted_products()

    async def purge_expired_deleted_products(self, days_before_purge: int = 10) -> PurgeResult:
        """Hard delete products soft-deleted more than N days ago. Delegated to ProductLifecycleService."""
        return await self._lifecycle.purge_expired_deleted_products(days_before_purge)

    # ============================================================================
    # Active Product Management
    # ============================================================================

    async def get_active_product(self) -> Optional[Product]:
        """
        Get the currently active product for the tenant.

        Returns:
            Product ORM model if active product exists, None otherwise

        Raises:
            BaseGiljoError: If database operation fails
        """
        try:
            async with self._get_session() as session:
                stmt = (
                    select(Product)
                    .options(
                        selectinload(Product.vision_documents),
                        selectinload(Product.tech_stack),
                        selectinload(Product.architecture),
                        selectinload(Product.test_config),
                    )
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

                return product

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get active product")
            raise BaseGiljoError(
                message=f"Failed to get active product: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    # ============================================================================
    # Metrics & Statistics -- delegated to ProductMemoryService
    # ============================================================================

    async def get_product_statistics(self, product_id: str) -> ProductStatistics:
        """Get comprehensive statistics for a product. Delegated to ProductMemoryService."""
        return await self._memory.get_product_statistics(product_id)

    async def get_cascade_impact(self, product_id: str) -> CascadeImpact:
        """Get cascade impact analysis for product deletion. Delegated to ProductMemoryService."""
        return await self._memory.get_cascade_impact(product_id)

    # ============================================================================
    # Git Integration
    # ============================================================================

    async def update_git_integration(
        self,
        product_id: str,
        enabled: bool,
        commit_limit: int = 20,
        default_branch: str = "main",
    ) -> dict[str, Any]:
        """
        Update Git integration settings for a product (Handover 013B - Simplified).

        Settings are stored in product_memory.git_integration field.

        Args:
            product_id: Product UUID
            enabled: Whether git integration is enabled
            commit_limit: Max commits to include in prompts (default: 20)
            default_branch: Default branch name (default: "main")

        Returns:
            Git integration settings dict directly (no wrapper)

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

                if not product.product_memory:
                    product.product_memory = {"git_integration": {}, "context": {}}

                if enabled:
                    product.product_memory["git_integration"] = {
                        "enabled": True,
                        "commit_limit": commit_limit,
                        "default_branch": default_branch,
                    }
                else:
                    product.product_memory["git_integration"] = {
                        "enabled": False,
                    }

                product.product_memory = validate_product_memory(product.product_memory)

                product.updated_at = datetime.now(timezone.utc)

                try:
                    from sqlalchemy.orm.attributes import flag_modified

                    flag_modified(product, "product_memory")
                except AttributeError:
                    pass

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Updated git integration for product {product_id}: enabled={enabled}")

                # Handover 013B: Emit WebSocket event for git settings change
                await self._lifecycle._emit_websocket_event(
                    event_type="product:git:settings:changed",
                    data={"product_id": product_id, "settings": product.product_memory["git_integration"]},
                )

                return product.product_memory["git_integration"]

        except ResourceNotFoundError:
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to update git integration")
            raise BaseGiljoError(
                message=f"Failed to update git integration: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e
