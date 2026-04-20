# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

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

from sqlalchemy.ext.asyncio import AsyncSession

from giljo_mcp.database import DatabaseManager
from giljo_mcp.exceptions import (
    BaseGiljoError,
    ResourceNotFoundError,
    ValidationError,
)
from giljo_mcp.models import Product
from giljo_mcp.models.products import VALID_TARGET_PLATFORMS
from giljo_mcp.repositories.product_repository import ProductRepository
from giljo_mcp.schemas.jsonb_validators import validate_product_memory
from giljo_mcp.services.product_lifecycle_service import ProductLifecycleService
from giljo_mcp.services.product_memory_service import ProductMemoryService


logger = logging.getLogger(__name__)


_ALLOWED_PRODUCT_FIELDS = {
    "name",
    "description",
    "project_path",
    "core_features",
    "brand_guidelines",
    "extraction_custom_instructions",
    "target_platforms",
}


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
        self._repo = ProductRepository()

        # Sprint 002f: Public sub-services for direct caller access (collapsed pass-throughs)
        self.lifecycle = ProductLifecycleService(
            db_manager=db_manager,
            tenant_key=tenant_key,
            websocket_manager=websocket_manager,
            test_session=test_session,
        )
        self.memory = ProductMemoryService(
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
                existing = await self._repo.get_by_name(session, self.tenant_key, name)
                if existing:
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

                await self._repo.add(session, product)

                # Handover 0840i: Create normalized config table rows from typed fields
                config_parts = {}
                if tech_stack:
                    config_parts["tech_stack"] = tech_stack
                if architecture:
                    config_parts["architecture"] = architecture
                if test_config:
                    config_parts["test_config"] = test_config
                if config_parts:
                    await self._repo.create_config_relations(session, product_id, self.tenant_key, config_parts)

                await self._repo.commit(session)
                await self._repo.refresh(session, product)

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
                product = await self._repo.get_by_id(session, self.tenant_key, product_id, eager_load=True)

                if not product:
                    raise ResourceNotFoundError(
                        message="Product not found", context={"product_id": product_id, "tenant_key": self.tenant_key}
                    )

                # Handover 0136: Ensure product_memory is initialized (backward compatibility)
                await self.memory._ensure_product_memory_initialized(session, product)

                # Handover 0412: Force refresh to ensure we have latest DB data
                # Handover 0840h: Include relationships so refresh doesn't discard eager loads
                await self._repo.refresh(session, product)

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
                products = await self._repo.list_products(session, self.tenant_key, include_inactive=include_inactive)

                for product in products:
                    # Handover 0136: Ensure product_memory is initialized (backward compatibility)
                    await self.memory._ensure_product_memory_initialized(session, product)

                self._logger.debug(f"Found {len(products)} products for tenant {self.tenant_key}")

                return products

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
                product = await self._repo.get_by_id(session, self.tenant_key, product_id, eager_load=True)

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
                    await self._repo.update_config_relations(session, product, self.tenant_key, config_parts)

                for field, value in updates.items():
                    if field in _ALLOWED_PRODUCT_FIELDS:
                        setattr(product, field, value)

                product.updated_at = datetime.now(timezone.utc)

                await self._repo.commit(session)
                await self._repo.refresh(session, product)

                self._logger.info(f"Updated product {product_id}")

                # Handover 0139a: Emit WebSocket event if product_memory was updated
                # Handover 0390b: Build product_memory from table for WebSocket event
                if "product_memory" in updates:
                    product_memory = await self.memory._build_product_memory_response(session, product)
                    await self.lifecycle._emit_websocket_event(
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
        return await self.lifecycle.activate_product(product_id)

    async def deactivate_product(self, product_id: str) -> Product:
        """Deactivate a product. Delegated to ProductLifecycleService."""
        return await self.lifecycle.deactivate_product(product_id)

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
                product = await self._repo.get_active_product(session, self.tenant_key)
                return product

        except Exception as e:  # Broad catch: service boundary, wraps in BaseGiljoError
            self._logger.exception("Failed to get active product")
            raise BaseGiljoError(
                message=f"Failed to get active product: {e!s}", context={"tenant_key": self.tenant_key}
            ) from e

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
                product = await self._repo.get_by_id(session, self.tenant_key, product_id)

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

                await self._repo.commit(session)
                await self._repo.refresh(session, product)

                self._logger.info(f"Updated git integration for product {product_id}: enabled={enabled}")

                # Handover 013B: Emit WebSocket event for git settings change
                await self.lifecycle._emit_websocket_event(
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
