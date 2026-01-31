"""
Organization-related models for GiljoAI MCP.

This module contains models for organizations and organization memberships.
Organizations provide a hierarchical tenant structure above products.

Handover 0424a: Organization Database Schema
"""

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class Organization(Base):
    """
    Organization model - hierarchical tenant structure above products.

    Organizations provide multi-user collaboration and resource sharing.
    Each organization can have multiple users (via memberships) and own
    multiple products, templates, and tasks.

    Handover 0424a: Organization Database Schema
    """

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False)
    slug = Column(String(100), nullable=False, unique=True, index=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    settings = Column(JSONB, default=dict, nullable=False)

    # Relationships
    members = relationship(
        "OrgMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
        order_by="OrgMembership.joined_at",
    )
    products = relationship(
        "Product",
        back_populates="organization",
        order_by="Product.created_at.desc()",
    )
    templates = relationship(
        "AgentTemplate",
        back_populates="organization",
        order_by="AgentTemplate.name",
    )
    # Direct User relationship (Handover 0424f)
    users = relationship(
        "User",
        back_populates="organization",
        foreign_keys="User.org_id",
        order_by="User.created_at.desc()",
    )

    __table_args__ = (
        Index("idx_organizations_slug", "slug"),
        Index("idx_organizations_active", "is_active"),
    )


class OrgMembership(Base):
    """
    Organization Membership model - links users to organizations with roles.

    Defines user roles within an organization:
    - owner: Full control, can delete organization
    - admin: Manage users, products, settings
    - member: Create and manage own products
    - viewer: Read-only access

    Handover 0424a: Organization Database Schema
    """

    __tablename__ = "org_memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        String(20), nullable=False, default="member"
    )  # owner, admin, member, viewer
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    invited_by = Column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship("User", foreign_keys=[user_id], backref="org_memberships")
    inviter = relationship("User", foreign_keys=[invited_by])

    __table_args__ = (
        UniqueConstraint("org_id", "user_id", name="uq_org_membership_user"),
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="ck_org_membership_role",
        ),
        Index("idx_org_memberships_org", "org_id"),
        Index("idx_org_memberships_user", "user_id"),
        Index("idx_org_memberships_role", "role"),
        Index("idx_org_memberships_active", "is_active"),
    )
