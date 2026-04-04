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
from typing import Any, Optional
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.exceptions import (
    BaseGiljoError,
    ContextError,
    DatabaseError,
    GiljoFileNotFoundError,
    ResourceNotFoundError,
    ValidationError,
)
from src.giljo_mcp.models import Product, Project, Task, VisionDocument
from src.giljo_mcp.models.agent_identity import AgentJob
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
    VisionUploadResult,
)
from src.giljo_mcp.tools.chunking import VISION_MAX_INGEST_TOKENS


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
        product_memory: dict[str, Any] | None = None,  # Handover 0135
        target_platforms: list[str] | None = None,  # Handover 0425
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

        Example:
            >>> product = await service.create_product(
            ...     name="MyApp",
            ...     description="Mobile application",
            ...     project_path="/projects/myapp",
            ...     tech_stack={"programming_languages": "Python 3.12"},
            ...     target_platforms=["windows", "linux"]
            ... )
            >>> print(product.id)
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
                    product_memory=validated_memory,  # Handover 0135
                    target_platforms=target_platforms or ["all"],  # Handover 0425
                    is_active=False,  # Products start inactive
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

                # Handover 0731b: Return Product ORM model directly
                return product

        except ValidationError:
            # Re-raise validation errors as-is
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

        Example:
            >>> product = await service.get_product("abc-123")
            >>> print(product.name)
        """
        try:
            async with self._get_session() as session:
                # Eagerly load vision_documents and config tables to prevent lazy-loading
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
                await self._ensure_product_memory_initialized(session, product)

                # Handover 0412: Force refresh to ensure we have latest DB data
                # Handover 0840h: Include relationships so refresh doesn't discard eager loads
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                # Handover 0731b: Return Product ORM model directly
                return product

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
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

        Example:
            >>> products = await service.list_products()
            >>> for product in products:
            ...     print(product.name)
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
                    await self._ensure_product_memory_initialized(session, product)

                self._logger.debug(f"Found {len(products)} products for tenant {self.tenant_key}")

                # Handover 0731b: Return list of Product ORM models directly
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

        Example:
            >>> product = await service.update_product(
            ...     "abc-123",
            ...     description="Updated description",
            ...     tech_stack={"programming_languages": "Python 3.12"},
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

                # Apply remaining updates
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
                    product_memory = await self._build_product_memory_response(session, product)
                    await self._emit_websocket_event(
                        event_type="product:memory:updated",
                        data={"product_id": product_id, "product_memory": product_memory},
                    )

                # Handover 0731b: Return Product ORM model directly
                return product

        except (ResourceNotFoundError, ValidationError):
            # Re-raise our custom errors as-is
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to update product")
            raise BaseGiljoError(
                message=f"Failed to update product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    # ============================================================================
    # Lifecycle Management
    # ============================================================================

    async def activate_product(self, product_id: str) -> Product:
        """
        Activate a product (deactivates other products for tenant).

        Only one product can be active at a time per tenant.

        Args:
            product_id: Product UUID to activate

        Returns:
            Product ORM model after activation

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoError: If database operation fails

        Example:
            >>> product = await service.activate_product("abc-123")
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
                    # Enforces non-negotiable rule: one active product -> one active project
                    deactivated_product_ids = [p.id for p in products_to_deactivate]

                    # Bulk update: Set all active projects in deactivated products to inactive
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
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Activated product {product_id} (deactivated {len(products_to_deactivate)} others)")

                # Handover 0731b: Return Product ORM model directly
                return product

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to activate product")
            raise BaseGiljoError(
                message=f"Failed to activate product: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def deactivate_product(self, product_id: str) -> Product:
        """
        Deactivate a product.

        Args:
            product_id: Product UUID to deactivate

        Returns:
            Product ORM model after deactivation

        Raises:
            ResourceNotFoundError: If product not found
            BaseGiljoError: If database operation fails

        Example:
            >>> product = await service.deactivate_product("abc-123")
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

                # Handover 0731b: Return Product ORM model directly
                return product

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
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

        Example:
            >>> result = await service.delete_product("abc-123")
            >>> assert result.deleted is True
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

                # Handover 0731b: Return DeleteResult Pydantic model
                return DeleteResult(deleted=True, deleted_at=product.deleted_at)

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
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

        Example:
            >>> product = await service.restore_product("abc-123")
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
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Restored product {product_id}")

                # Handover 0731b: Return Product ORM model directly
                return product

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
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
        List soft-deleted products.

        Returns:
            List of Product ORM models (soft-deleted)

        Raises:
            BaseGiljoError: If database operation fails

        Example:
            >>> products = await service.list_deleted_products()
            >>> for product in products:
            ...     print(f"{product.name} deleted at {product.deleted_at}")
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

                # Handover 0731b: Return list of Product ORM models directly
                # Purge date computation moved to endpoint layer
                return list(deleted_products)

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to list deleted products")
            raise BaseGiljoError(
                message=f"Failed to list deleted products: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

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

        Example:
            >>> product = await service.get_active_product()
            >>> if product:
            ...     print(f"Active: {product.name}")
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

                # Handover 0731b: Return Product or None directly
                return product

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get active product")
            raise BaseGiljoError(
                message=f"Failed to get active product: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

    # ============================================================================
    # Metrics & Statistics
    # ============================================================================

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

        Example:
            >>> stats = await service.get_product_statistics("abc-123")
            >>> print(f"Projects: {stats.project_count}")
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

                # Handover 0731b: Return ProductStatistics Pydantic model
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
            # Re-raise resource not found errors as-is
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

        Example:
            >>> impact = await service.get_cascade_impact("abc-123")
            >>> print(f"Will affect {impact.total_projects} projects")
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

                # Handover 0731b: Return CascadeImpact Pydantic model
                return CascadeImpact(
                    product_id=product_id,
                    product_name=product.name,
                    total_projects=project_count.scalar() or 0,
                    total_tasks=task_count.scalar() or 0,
                    total_vision_documents=vision_count.scalar() or 0,
                    warning="Deleting this product will soft-delete all related entities",
                )

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get cascade impact")
            raise BaseGiljoError(
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
        Git operations are handled by AI coding agents (Claude Code, Codex, Gemini).

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

                # Validate the full product_memory after mutation
                product.product_memory = validate_product_memory(product.product_memory)

                product.updated_at = datetime.now(timezone.utc)

                # Force SQLAlchemy to detect JSONB change
                try:
                    from sqlalchemy.orm.attributes import flag_modified

                    flag_modified(product, "product_memory")
                except AttributeError:
                    # Mock object in tests - flag_modified will fail
                    pass

                await session.commit()
                await session.refresh(
                    product,
                    attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
                )

                self._logger.info(f"Updated git integration for product {product_id}: enabled={enabled}")

                # Handover 013B: Emit WebSocket event for git settings change
                await self._emit_websocket_event(
                    event_type="product:git:settings:changed",
                    data={"product_id": product_id, "settings": product.product_memory["git_integration"]},
                )

                # Handover 0731b: Return settings dict directly (no wrapper)
                return product.product_memory["git_integration"]

        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to update git integration")
            raise BaseGiljoError(
                message=f"Failed to update git integration: {e!s}",
                context={"product_id": product_id, "tenant_key": self.tenant_key},
            ) from e

    async def upload_vision_document(
        self,
        product_id: str,
        content: str,
        filename: str,
        auto_chunk: bool = True,
        max_tokens: int = VISION_MAX_INGEST_TOKENS,
    ) -> VisionUploadResult:
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
            VisionUploadResult Pydantic model with document_id, document_name,
            chunks_created, and total_tokens

        Raises:
            ValidationError: If product not found or validation fails
            ResourceNotFoundError: If product not found
            BaseGiljoError: If upload fails

        Example:
            >>> result = await service.upload_vision_document(
            ...     product_id="abc-123",
            ...     content="# Vision\\n...",
            ...     filename="vision.md"
            ... )
            >>> print(f"Created {result.chunks_created} chunks")
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
                        doc.summary_light = summaries.light.summary
                        doc.summary_medium = summaries.medium.summary
                        doc.summary_light_tokens = summaries.light.tokens
                        doc.summary_medium_tokens = summaries.medium.tokens
                        doc.is_summarized = True
                        doc.original_token_count = summaries.original_tokens

                        # Backward compatibility: set summary_text to medium summary
                        doc.summary_text = summaries.medium.summary
                        doc.compression_ratio = (
                            (summaries.original_tokens - summaries.medium.tokens) / summaries.original_tokens
                            if summaries.original_tokens > 0
                            else 0.0
                        )

                        await session.commit()

                        self._logger.info(
                            f"Vision document {doc.id} summarized: "
                            f"Light={summaries.light.tokens} tokens, "
                            f"Medium={summaries.medium.tokens} tokens "
                            f"(from {summaries.original_tokens} tokens) "
                            f"in {summaries.processing_time_ms}ms"
                        )
                    except (ImportError, ValueError, KeyError) as e:
                        # Summarization failed but document created - log warning and continue
                        self._logger.warning(f"Document {doc.id} created but summarization failed: {e}")

                # Auto-chunk if enabled
                chunks_created = 0
                chunk_total_tokens = 0  # Track chunker's token count separately

                if auto_chunk:
                    chunker = VisionDocumentChunker(target_chunk_size=max_tokens)

                    try:
                        # Chunk the document
                        chunk_result = await chunker.chunk_vision_document(
                            session=session, tenant_key=self.tenant_key, vision_document_id=str(doc.id)
                        )

                        await session.commit()

                        chunks_created = chunk_result["chunks_created"]
                        chunk_total_tokens = chunk_result["total_tokens"]
                        # Update total_tokens for return value (use chunker's accurate count)
                        total_tokens = chunk_total_tokens

                        self._logger.info(f"Chunked document {doc.id}: {chunks_created} chunks, {total_tokens} tokens")
                    except (ContextError, GiljoFileNotFoundError, OSError) as e:
                        # Chunking failed but document created
                        self._logger.warning(f"Document {doc.id} created but chunking failed: {e}")

                # Handover 0493: Auto-consolidation after upload
                # Ensures light/medium summaries are always available
                try:
                    from src.giljo_mcp.services.consolidation_service import ConsolidatedVisionService

                    consolidation_service = ConsolidatedVisionService()
                    await consolidation_service.consolidate_vision_documents(
                        product_id=product_id,
                        session=session,
                        tenant_key=self.tenant_key,
                        force=True,
                    )
                    self._logger.info(f"Auto-consolidated vision documents for product {product_id}")
                except (ValidationError, ResourceNotFoundError, ValueError, KeyError) as e:
                    # Consolidation failure should not fail the upload
                    self._logger.warning(f"Auto-consolidation failed for product {product_id}: {e}")

                # Handover 0731b: Return VisionUploadResult Pydantic model
                return VisionUploadResult(
                    document_id=str(doc.id),
                    document_name=doc.document_name,
                    chunks_created=chunks_created,
                    total_tokens=total_tokens,
                )

        except ValueError as e:
            self._logger.exception("Validation error uploading vision document")
            raise ValidationError(
                message=f"Validation error uploading vision document: {e!s}",
                context={"product_id": product_id, "filename": filename},
            ) from e
        except ResourceNotFoundError:
            # Re-raise resource not found errors as-is
            raise
        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to upload vision document")
            raise BaseGiljoError(
                message=f"Failed to upload vision document: {e!s}",
                context={"product_id": product_id, "filename": filename, "tenant_key": self.tenant_key},
            ) from e

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
            # Handover 0840h: Include relationships so refresh doesn't discard eager loads
            await session.refresh(
                product,
                attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
            )
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
        # Count projects (defense-in-depth: explicit tenant_key on all child queries)
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

        # Count unfinished projects
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

        # Count tasks
        tasks_result = await session.execute(
            select(func.count(Task.id)).where(and_(Task.product_id == product_id, Task.tenant_key == self.tenant_key))
        )
        task_count = tasks_result.scalar() or 0

        # Count unresolved tasks
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

        # Count vision documents
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

    async def purge_expired_deleted_products(self, days_before_purge: int = 10) -> PurgeResult:
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
            PurgeResult Pydantic model with purged_count and purged_ids

        Raises:
            DatabaseError: If database not available
            BaseGiljoError: If purge operation fails

        Example:
            >>> result = await service.purge_expired_deleted_products()
            >>> print(f"Purged {result.purged_count} expired products")
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
                    return PurgeResult(purged_count=0, purged_ids=[])

                # Hard delete each expired product (cascade handles children)
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

                # Handover 0731b: Return PurgeResult Pydantic model
                return PurgeResult(purged_count=len(purged_ids), purged_ids=purged_ids)

        except DatabaseError:
            # Re-raise database errors as-is
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
