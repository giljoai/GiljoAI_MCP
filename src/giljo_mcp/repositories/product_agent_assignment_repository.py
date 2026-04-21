# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductAgentAssignmentRepository - Data access for product-template assignments.

Manages the junction table that links products to tenant-wide agent templates.
Every query filters by tenant_key for multi-tenant isolation.
"""

from __future__ import annotations

import logging

from sqlalchemy import and_, select
from sqlalchemy import delete as sql_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from giljo_mcp.models.product_agent_assignment import ProductAgentAssignment
from giljo_mcp.models.templates import AgentTemplate


logger = logging.getLogger(__name__)


class ProductAgentAssignmentRepository:
    """
    Repository for product-agent assignment operations.

    Methods accept an AsyncSession parameter (session-in pattern) so the
    calling service controls transaction boundaries.

    CRITICAL: Every query filters by tenant_key for tenant isolation.
    """

    def __init__(self) -> None:
        self._logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")

    async def get_assignments_for_product(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
        *,
        active_only: bool = False,
    ) -> list[ProductAgentAssignment]:
        """
        Get all assignments for a product with eager-loaded template info.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation
            active_only: If True, only return active assignments

        Returns:
            List of ProductAgentAssignment ORM instances with template relationship loaded
        """
        stmt = (
            select(ProductAgentAssignment)
            .options(joinedload(ProductAgentAssignment.template))
            .where(
                and_(
                    ProductAgentAssignment.product_id == product_id,
                    ProductAgentAssignment.tenant_key == tenant_key,
                )
            )
        )
        if active_only:
            stmt = stmt.where(ProductAgentAssignment.is_active.is_(True))

        result = await session.execute(stmt)
        return list(result.unique().scalars().all())

    async def get_assignment(
        self,
        session: AsyncSession,
        product_id: str,
        template_id: str,
        tenant_key: str,
    ) -> ProductAgentAssignment | None:
        """
        Get a specific assignment by product+template pair.

        Args:
            session: Active database session
            product_id: Product UUID
            template_id: Template UUID
            tenant_key: Tenant key for isolation

        Returns:
            ProductAgentAssignment or None
        """
        stmt = select(ProductAgentAssignment).where(
            and_(
                ProductAgentAssignment.product_id == product_id,
                ProductAgentAssignment.template_id == template_id,
                ProductAgentAssignment.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_assignment(
        self,
        session: AsyncSession,
        product_id: str,
        template_id: str,
        tenant_key: str,
        is_active: bool,
    ) -> ProductAgentAssignment:
        """
        Create or update a product-template assignment.

        If the assignment exists, updates is_active. Otherwise creates it.

        Args:
            session: Active database session
            product_id: Product UUID
            template_id: Template UUID
            tenant_key: Tenant key for isolation
            is_active: Whether the template is active for this product

        Returns:
            The created or updated ProductAgentAssignment
        """
        existing = await self.get_assignment(session, product_id, template_id, tenant_key)

        if existing:
            existing.is_active = is_active
            await session.flush()
            return existing

        assignment = ProductAgentAssignment(
            product_id=product_id,
            template_id=template_id,
            tenant_key=tenant_key,
            is_active=is_active,
        )
        session.add(assignment)
        await session.flush()
        return assignment

    async def bulk_assign_all_templates(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> list[ProductAgentAssignment]:
        """
        Assign all active tenant templates to a product (default: all active).

        Skips templates that already have an assignment for this product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            List of newly created ProductAgentAssignment instances
        """
        # Get all active templates for this tenant
        templates_stmt = select(AgentTemplate).where(
            and_(
                AgentTemplate.tenant_key == tenant_key,
                AgentTemplate.is_active.is_(True),
            )
        )
        templates_result = await session.execute(templates_stmt)
        all_templates = list(templates_result.scalars().all())

        if not all_templates:
            return []

        # Get existing assignments for this product
        existing_stmt = select(ProductAgentAssignment.template_id).where(
            and_(
                ProductAgentAssignment.product_id == product_id,
                ProductAgentAssignment.tenant_key == tenant_key,
            )
        )
        existing_result = await session.execute(existing_stmt)
        existing_template_ids = {row[0] for row in existing_result.all()}

        # Create assignments for templates not yet assigned
        new_assignments = []
        for template in all_templates:
            if template.id not in existing_template_ids:
                assignment = ProductAgentAssignment(
                    product_id=product_id,
                    template_id=template.id,
                    tenant_key=tenant_key,
                    is_active=True,
                )
                session.add(assignment)
                new_assignments.append(assignment)

        if new_assignments:
            await session.flush()

        return new_assignments

    async def remove_assignments_for_product(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> int:
        """
        Remove all assignments for a product.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Number of assignments removed
        """
        stmt = sql_delete(ProductAgentAssignment).where(
            and_(
                ProductAgentAssignment.product_id == product_id,
                ProductAgentAssignment.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return result.rowcount

    async def remove_assignments_for_template(
        self,
        session: AsyncSession,
        template_id: str,
        tenant_key: str,
    ) -> int:
        """
        Remove all assignments for a template (used when template is deleted).

        Note: FK CASCADE handles this at the DB level, but this method is
        available for explicit cleanup when needed.

        Args:
            session: Active database session
            template_id: Template UUID
            tenant_key: Tenant key for isolation

        Returns:
            Number of assignments removed
        """
        stmt = sql_delete(ProductAgentAssignment).where(
            and_(
                ProductAgentAssignment.template_id == template_id,
                ProductAgentAssignment.tenant_key == tenant_key,
            )
        )
        result = await session.execute(stmt)
        return result.rowcount

    async def get_active_template_ids_for_product(
        self,
        session: AsyncSession,
        product_id: str,
        tenant_key: str,
    ) -> set[str]:
        """
        Get the set of active template IDs assigned to a product.

        Useful for filtering template lists by product context.

        Args:
            session: Active database session
            product_id: Product UUID
            tenant_key: Tenant key for isolation

        Returns:
            Set of active template IDs
        """
        stmt = select(ProductAgentAssignment.template_id).where(
            and_(
                ProductAgentAssignment.product_id == product_id,
                ProductAgentAssignment.tenant_key == tenant_key,
                ProductAgentAssignment.is_active.is_(True),
            )
        )
        result = await session.execute(stmt)
        return {row[0] for row in result.all()}
