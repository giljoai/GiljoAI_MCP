# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductRepository - Data access layer for Product CRUD and lifecycle operations.

BE-5022c: Extracted from ProductService and ProductLifecycleService to route all
database writes through the repository layer.

Responsibilities:
- Product CRUD (create, read, update, soft-delete, hard-delete)
- Product activation/deactivation with cascade logic
- Config relations management (tech_stack, architecture, test_config)
- Soft-delete restoration, expiry purge

Design Principles:
- Session-in pattern: all methods accept session as parameter
- tenant_key filtering on EVERY query — no exceptions
- No business logic — pure data access
"""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giljo_mcp.domain.project_status import ProjectStatus
from giljo_mcp.models import Product, Project
from giljo_mcp.models.agent_identity import AgentJob
from giljo_mcp.models.products import (
    ProductArchitecture,
    ProductTechStack,
    ProductTestConfig,
)


logger = logging.getLogger(__name__)


class ProductRepository:
    """
    Repository for Product database operations.

    All methods enforce tenant_key isolation.
    Session is passed in by the caller (service layer).
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    # ============================================================================
    # Read Operations
    # ============================================================================

    async def get_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
        *,
        include_deleted: bool = False,
        eager_load: bool = False,
    ) -> Product | None:
        """
        Get a product by ID with tenant isolation.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            product_id: Product UUID
            include_deleted: Include soft-deleted products
            eager_load: Eager-load relationships (vision_documents, tech_stack, etc.)

        Returns:
            Product instance or None
        """
        conditions = [Product.id == product_id, Product.tenant_key == tenant_key]
        if not include_deleted:
            conditions.append(Product.deleted_at.is_(None))

        stmt = select(Product).where(and_(*conditions))

        if eager_load:
            stmt = stmt.options(
                selectinload(Product.vision_documents),
                selectinload(Product.tech_stack),
                selectinload(Product.architecture),
                selectinload(Product.test_config),
            )

        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_name(
        self,
        session: AsyncSession,
        tenant_key: str,
        name: str,
    ) -> Product | None:
        """
        Get a non-deleted product by name.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            name: Product name

        Returns:
            Product instance or None
        """
        stmt = select(Product).where(
            and_(
                Product.tenant_key == tenant_key,
                Product.name == name,
                Product.deleted_at.is_(None),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_product(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> Product | None:
        """
        Get the currently active product for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            Active Product instance or None
        """
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
                    Product.tenant_key == tenant_key,
                    Product.is_active,
                    Product.deleted_at.is_(None),
                )
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_products(
        self,
        session: AsyncSession,
        tenant_key: str,
        *,
        include_inactive: bool = False,
    ) -> list[Product]:
        """
        List products for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            include_inactive: Include inactive products

        Returns:
            List of Product instances
        """
        conditions = [Product.tenant_key == tenant_key, Product.deleted_at.is_(None)]

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
        return list(result.scalars().all())

    async def list_deleted(
        self,
        session: AsyncSession,
        tenant_key: str,
    ) -> list[Product]:
        """
        List soft-deleted products for a tenant.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation

        Returns:
            List of soft-deleted Product instances
        """
        stmt = (
            select(Product)
            .where(
                and_(
                    Product.tenant_key == tenant_key,
                    Product.deleted_at.isnot(None),
                )
            )
            .order_by(Product.deleted_at.desc())
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def get_deleted_by_id(
        self,
        session: AsyncSession,
        tenant_key: str,
        product_id: str,
    ) -> Product | None:
        """
        Get a soft-deleted product by ID.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            product_id: Product UUID

        Returns:
            Soft-deleted Product instance or None
        """
        stmt = select(Product).where(
            and_(
                Product.id == product_id,
                Product.tenant_key == tenant_key,
                Product.deleted_at.isnot(None),
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def find_expired_deleted(
        self,
        session: AsyncSession,
        days_before_purge: int = 10,
    ) -> list[Product]:
        """
        Find products soft-deleted more than N days ago.

        Note: This is a cross-tenant operation used by startup purge.

        Args:
            session: Active database session
            days_before_purge: Days threshold

        Returns:
            List of expired Product instances
        """
        cutoff_date = datetime.now(UTC) - timedelta(days=days_before_purge)
        stmt = select(Product).where(
            Product.deleted_at.isnot(None),
            Product.deleted_at < cutoff_date,
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    # ============================================================================
    # Write Operations
    # ============================================================================

    async def add(self, session: AsyncSession, product: Product) -> None:
        """
        Add a product to the session.

        Args:
            session: Active database session
            product: Product instance to add
        """
        session.add(product)

    async def delete_hard(self, session: AsyncSession, product: Product) -> None:
        """
        Hard-delete a product (cascades via FK).

        Args:
            session: Active database session
            product: Product instance to delete
        """
        await session.delete(product)

    async def flush(self, session: AsyncSession) -> None:
        """
        Flush pending changes to the database.

        Args:
            session: Active database session
        """
        await session.flush()

    async def commit(self, session: AsyncSession) -> None:
        """
        Commit the current transaction.

        Args:
            session: Active database session
        """
        await session.commit()

    async def refresh(
        self,
        session: AsyncSession,
        product: Product,
        *,
        include_relations: bool = True,
    ) -> None:
        """
        Refresh a product from the database.

        Args:
            session: Active database session
            product: Product instance to refresh
            include_relations: Whether to refresh relationships
        """
        if include_relations:
            await session.refresh(
                product,
                attribute_names=["tech_stack", "architecture", "test_config", "vision_documents"],
            )
        else:
            await session.refresh(product)

    # ============================================================================
    # Config Relations
    # ============================================================================

    async def create_config_relations(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
        config_data: dict,
    ) -> None:
        """
        Create normalized config table rows from config data.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation
            config_data: Dict with optional keys: tech_stack, architecture, test_config
        """
        tech_stack = config_data.get("tech_stack")
        if tech_stack and isinstance(tech_stack, dict):
            ts = ProductTechStack(
                product_id=product_id,
                tenant_key=tenant_key,
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
                tenant_key=tenant_key,
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
                tenant_key=tenant_key,
                quality_standards=test_config.get("quality_standards", ""),
                test_strategy=test_config.get("test_strategy", ""),
                coverage_target=test_config.get("coverage_target", 80),
                testing_frameworks=test_config.get("testing_frameworks", ""),
            )
            session.add(tc)

    async def update_config_relations(
        self,
        session: AsyncSession,
        product: Product,
        tenant_key: str,
        config_data: dict,
    ) -> None:
        """
        Update normalized config table rows.

        Args:
            session: Active database session
            product: Product instance with loaded relationships
            tenant_key: Tenant key for isolation
            config_data: Dict with optional keys: tech_stack, architecture, test_config
        """
        tech_stack = config_data.get("tech_stack")
        if tech_stack and isinstance(tech_stack, dict):
            ts = product.tech_stack
            if ts is None:
                ts = ProductTechStack(product_id=product.id, tenant_key=tenant_key)
                session.add(ts)
                product.tech_stack = ts
            for field in (
                "programming_languages",
                "frontend_frameworks",
                "backend_frameworks",
                "databases_storage",
                "infrastructure",
                "dev_tools",
            ):
                if field in tech_stack:
                    setattr(ts, field, tech_stack[field])

        architecture = config_data.get("architecture")
        if architecture and isinstance(architecture, dict):
            arch = product.architecture
            if arch is None:
                arch = ProductArchitecture(product_id=product.id, tenant_key=tenant_key)
                session.add(arch)
                product.architecture = arch
            for field in (
                "primary_pattern",
                "design_patterns",
                "api_style",
                "architecture_notes",
                "coding_conventions",
            ):
                if field in architecture:
                    setattr(arch, field, architecture[field])

        test_config = config_data.get("test_config")
        if test_config and isinstance(test_config, dict):
            tc = product.test_config
            if tc is None:
                tc = ProductTestConfig(product_id=product.id, tenant_key=tenant_key)
                session.add(tc)
                product.test_config = tc
            for field in ("quality_standards", "test_strategy", "coverage_target", "testing_frameworks"):
                if field in test_config:
                    setattr(tc, field, test_config[field])

    # ============================================================================
    # Lifecycle Operations (ProductLifecycleService)
    # ============================================================================

    async def find_other_active_products(
        self,
        session: AsyncSession,
        tenant_key: str,
        exclude_product_id: str,
    ) -> list[Product]:
        """
        Find active products for tenant, excluding a specific product.

        Args:
            session: Active database session
            tenant_key: Tenant key for isolation
            exclude_product_id: Product ID to exclude

        Returns:
            List of other active products
        """
        stmt = select(Product).where(
            and_(
                Product.tenant_key == tenant_key,
                Product.is_active,
                Product.id != exclude_product_id,
            )
        )
        result = await session.execute(stmt)
        return list(result.scalars().all())

    async def bulk_deactivate_projects(
        self,
        session: AsyncSession,
        product_ids: list[str],
    ) -> None:
        """
        Bulk deactivate active projects under given products.

        Args:
            session: Active database session
            product_ids: List of product IDs
        """
        stmt = (
            update(Project)
            .where(Project.product_id.in_(product_ids))
            .where(Project.status == ProjectStatus.ACTIVE)
            .values(status=ProjectStatus.INACTIVE, updated_at=datetime.now(UTC))
        )
        await session.execute(stmt)

    async def bulk_cancel_jobs(
        self,
        session: AsyncSession,
        product_ids: list[str],
    ) -> None:
        """
        Bulk cancel active jobs under products' projects.

        Args:
            session: Active database session
            product_ids: List of product IDs
        """
        project_ids_stmt = select(Project.id).where(Project.product_id.in_(product_ids))
        stmt = (
            update(AgentJob)
            .where(AgentJob.project_id.in_(project_ids_stmt))
            .where(AgentJob.status == "active")
            .values(status="cancelled")
        )
        await session.execute(stmt)

    async def deactivate_product_projects(
        self,
        session: AsyncSession,
        product_id: str,
    ) -> None:
        """
        Deactivate active projects under a single product.

        Args:
            session: Active database session
            product_id: Product UUID
        """
        stmt = (
            update(Project)
            .where(Project.product_id == product_id)
            .where(Project.status == ProjectStatus.ACTIVE)
            .values(status=ProjectStatus.INACTIVE, updated_at=datetime.now(UTC))
        )
        await session.execute(stmt)

    async def cancel_product_jobs(
        self,
        session: AsyncSession,
        product_id: str,
    ) -> None:
        """
        Cancel active jobs under a single product's projects.

        Args:
            session: Active database session
            product_id: Product UUID
        """
        project_ids_stmt = select(Project.id).where(Project.product_id == product_id)
        stmt = (
            update(AgentJob)
            .where(AgentJob.project_id.in_(project_ids_stmt))
            .where(AgentJob.status == "active")
            .values(status="cancelled")
        )
        await session.execute(stmt)
