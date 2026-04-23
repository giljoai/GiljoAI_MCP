# Copyright (c) 2024-2026 GiljoAI LLC. All rights reserved.
# Licensed under the GiljoAI Community License v1.1.
# See LICENSE in the project root for terms.
# [CE] Community Edition — source-available, single-user use only.

"""
ProductAgentAssignment model - lightweight per-product agent toggle.

Templates belong to the tenant; products reference which ones are active.
Think Spotify: songs exist once, playlists point to them.

This junction table lets each product independently choose which agent
templates are active without duplicating template data.
"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class ProductAgentAssignment(Base):
    """
    Junction table linking products to agent templates.

    Each row represents a product's reference to a tenant-wide template,
    with an is_active toggle to enable/disable per product.

    Tenant isolation: Every query MUST filter by tenant_key.
    """

    __tablename__ = "product_agent_assignments"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    product_id = Column(
        String(36),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
    )
    template_id = Column(
        String(36),
        ForeignKey("agent_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    is_active = Column(Boolean, default=True, nullable=False)
    tenant_key = Column(String(36), nullable=False)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    product = relationship("Product", back_populates="agent_assignments")
    template = relationship("AgentTemplate", backref="product_assignments")

    __table_args__ = (
        UniqueConstraint("product_id", "template_id", name="uq_product_template_assignment"),
        Index("idx_assignment_tenant", "tenant_key"),
        Index("idx_assignment_product", "product_id"),
        Index("idx_assignment_template", "template_id"),
        Index("idx_assignment_active", "is_active"),
    )

    def __repr__(self) -> str:
        return (
            f"<ProductAgentAssignment(id={self.id}, product_id='{self.product_id}', "
            f"template_id='{self.template_id}', is_active={self.is_active})>"
        )
