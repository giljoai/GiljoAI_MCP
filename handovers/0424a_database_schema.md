# Handover 0424a: Organization Database Schema

**Date:** 2026-01-19
**From Agent:** Planning Session
**To Agent:** database-expert / tdd-implementor
**Priority:** HIGH
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation
**Parent:** 0424_org_hierarchy_overview.md

---

## Summary

Create database schema for Organization hierarchy:
- `organizations` table (governance entity)
- `org_memberships` table (user-org-role junction)
- Add `org_id` FK columns to products, templates, tasks

---

## TDD Discipline

Follow RED -> GREEN -> REFACTOR for all implementation.

### RED Phase (Write Failing Tests First)

```bash
# Create test file
touch tests/models/test_organizations.py

# Write failing tests
pytest tests/models/test_organizations.py -v
# MUST SEE: FAILED (RED)
```

### GREEN Phase (Minimal Implementation)

```bash
# Implement models
# Edit: src/giljo_mcp/models/organizations.py

pytest tests/models/test_organizations.py -v
# MUST SEE: PASSED (GREEN)
```

### REFACTOR Phase

```bash
# Add indexes, constraints, docstrings
pytest tests/models/test_organizations.py -v
# MUST STAY: GREEN
```

---

## Implementation Plan

### Step 1: Create Test File (tests/models/test_organizations.py)

```python
"""Tests for Organization and OrgMembership models."""
import pytest
from sqlalchemy import select
from src.giljo_mcp.models.organizations import Organization, OrgMembership
from src.giljo_mcp.models.base import generate_uuid


@pytest.mark.asyncio
async def test_organization_creation(db_session):
    """Test Organization can be created with required fields."""
    org = Organization(
        name="Test Organization",
        slug="test-org"
    )
    db_session.add(org)
    await db_session.commit()

    assert org.id is not None
    assert org.name == "Test Organization"
    assert org.slug == "test-org"
    assert org.is_active is True  # Default


@pytest.mark.asyncio
async def test_organization_slug_unique(db_session):
    """Test Organization slug must be unique."""
    org1 = Organization(name="Org 1", slug="same-slug")
    org2 = Organization(name="Org 2", slug="same-slug")

    db_session.add(org1)
    await db_session.commit()

    db_session.add(org2)
    with pytest.raises(Exception):  # IntegrityError
        await db_session.commit()


@pytest.mark.asyncio
async def test_org_membership_creation(db_session, test_user):
    """Test OrgMembership links user to organization with role."""
    org = Organization(name="Test Org", slug="test-membership")
    db_session.add(org)
    await db_session.commit()

    membership = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="owner"
    )
    db_session.add(membership)
    await db_session.commit()

    assert membership.id is not None
    assert membership.org_id == org.id
    assert membership.user_id == test_user.id
    assert membership.role == "owner"
    assert membership.is_active is True


@pytest.mark.asyncio
async def test_org_membership_role_constraint(db_session, test_user):
    """Test OrgMembership role must be valid."""
    org = Organization(name="Test Org", slug="test-role")
    db_session.add(org)
    await db_session.commit()

    membership = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="invalid_role"  # Not in allowed roles
    )
    db_session.add(membership)

    with pytest.raises(Exception):  # CheckConstraint violation
        await db_session.commit()


@pytest.mark.asyncio
async def test_org_members_relationship(db_session, test_user):
    """Test Organization.members relationship returns memberships."""
    org = Organization(name="Test Org", slug="test-rel")
    db_session.add(org)
    await db_session.commit()

    membership = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="admin"
    )
    db_session.add(membership)
    await db_session.commit()

    # Refresh to load relationships
    await db_session.refresh(org)

    assert len(org.members) == 1
    assert org.members[0].role == "admin"


@pytest.mark.asyncio
async def test_user_unique_per_org(db_session, test_user):
    """Test user can only have one membership per org."""
    org = Organization(name="Test Org", slug="test-unique")
    db_session.add(org)
    await db_session.commit()

    membership1 = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="owner"
    )
    db_session.add(membership1)
    await db_session.commit()

    membership2 = OrgMembership(
        org_id=org.id,
        user_id=test_user.id,
        role="admin"  # Same user, same org, different role
    )
    db_session.add(membership2)

    with pytest.raises(Exception):  # UniqueConstraint violation
        await db_session.commit()
```

### Step 2: Create Organization Models (src/giljo_mcp/models/organizations.py)

```python
"""
Organization and OrgMembership Models.

Handover 0424a: Implements organization hierarchy layer.

Design Philosophy:
- Organization: Governance entity that owns products
- OrgMembership: Junction table linking users to organizations with roles
- Roles: owner, admin, member, viewer (hierarchical permissions)

Relationships:
- Organization -> Many OrgMemberships (members)
- Organization -> Many Products (ownership)
- User -> Many OrgMemberships (multi-org capable)
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Boolean,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from .base import Base, generate_uuid


class Organization(Base):
    """
    Organization entity - governance layer for products.

    Represents a company, team, or personal workspace.
    Products, templates, and tasks belong to organizations.

    Handover 0424a: Foundation for multi-user access.
    """

    __tablename__ = "organizations"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    name = Column(String(255), nullable=False, comment="Organization display name")
    slug = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True,
        comment="URL-friendly identifier (e.g., 'acme-corp')"
    )

    # Lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Settings (org-level configuration)
    settings = Column(
        JSONB,
        default=dict,
        nullable=False,
        comment="Org-level settings (branding, defaults, etc.)"
    )

    # Relationships
    members = relationship(
        "OrgMembership",
        back_populates="organization",
        cascade="all, delete-orphan",
        order_by="OrgMembership.joined_at"
    )
    products = relationship(
        "Product",
        back_populates="organization",
        order_by="Product.created_at.desc()"
    )
    templates = relationship(
        "AgentTemplate",
        back_populates="organization",
        order_by="AgentTemplate.name"
    )

    __table_args__ = (
        Index("idx_organizations_slug", "slug"),
        Index("idx_organizations_active", "is_active"),
    )

    def __repr__(self):
        return f"<Organization(id={self.id}, name={self.name}, slug={self.slug})>"


class OrgMembership(Base):
    """
    Organization membership - links users to organizations with roles.

    Roles (hierarchical):
    - owner: Full control, can delete org, transfer ownership
    - admin: CRUD on all resources, can invite members
    - member: Read access, can create products (org-owned)
    - viewer: Read-only access to all resources

    Handover 0424a: Junction table for multi-user org access.
    """

    __tablename__ = "org_memberships"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Organization this membership belongs to"
    )
    user_id = Column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="User who has this membership"
    )

    # Role-based access
    role = Column(
        String(20),
        nullable=False,
        default="member",
        comment="Membership role: owner, admin, member, viewer"
    )

    # Lifecycle
    is_active = Column(Boolean, default=True, nullable=False)
    joined_at = Column(DateTime(timezone=True), server_default=func.now())

    # Invitation tracking
    invited_by = Column(
        String(36),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who invited this member"
    )

    # Relationships
    organization = relationship("Organization", back_populates="members")
    user = relationship(
        "User",
        foreign_keys=[user_id],
        backref="org_memberships"
    )
    inviter = relationship(
        "User",
        foreign_keys=[invited_by]
    )

    __table_args__ = (
        # User can only have one membership per org
        UniqueConstraint("org_id", "user_id", name="uq_org_membership_user"),
        # Role must be valid
        CheckConstraint(
            "role IN ('owner', 'admin', 'member', 'viewer')",
            name="ck_org_membership_role"
        ),
        Index("idx_org_memberships_org", "org_id"),
        Index("idx_org_memberships_user", "user_id"),
        Index("idx_org_memberships_role", "role"),
        Index("idx_org_memberships_active", "is_active"),
    )

    def __repr__(self):
        return (
            f"<OrgMembership(id={self.id}, org_id={self.org_id}, "
            f"user_id={self.user_id}, role={self.role})>"
        )
```

### Step 3: Update Models __init__.py

```python
# Add to src/giljo_mcp/models/__init__.py

from .organizations import Organization, OrgMembership

__all__ = [
    # ... existing exports ...
    "Organization",
    "OrgMembership",
]
```

### Step 4: Add org_id FK to Products (src/giljo_mcp/models/products.py)

```python
# Add column (after tenant_key column):
org_id = Column(
    String(36),
    ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=True,  # Initially nullable for migration
    index=True,
    comment="Organization that owns this product (Handover 0424)"
)

# Add relationship:
organization = relationship("Organization", back_populates="products")

# Add index to __table_args__:
Index("idx_products_org", "org_id"),
```

### Step 5: Add org_id FK to Templates (src/giljo_mcp/models/templates.py)

```python
# Add column (after tenant_key column):
org_id = Column(
    String(36),
    ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=True,  # Initially nullable for migration
    index=True,
    comment="Organization for org-level templates (Handover 0424)"
)

# Add relationship:
organization = relationship("Organization", back_populates="templates")

# Add index to __table_args__:
Index("idx_agent_templates_org", "org_id"),
```

### Step 6: Add org_id FK to Tasks (src/giljo_mcp/models/tasks.py)

```python
# Add column (after tenant_key column):
org_id = Column(
    String(36),
    ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=True,  # Initially nullable for migration
    index=True,
    comment="Organization for org-level tasks (Handover 0424)"
)

# Add index to __table_args__:
Index("idx_tasks_org", "org_id"),
```

### Step 7: Run Migration

```bash
# Verify PostgreSQL running
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\dt"

# Run install.py to create tables
python install.py

# Verify tables created
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d organizations"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d org_memberships"
```

---

## Files to Modify/Create

### NEW Files:
```
□ src/giljo_mcp/models/organizations.py (~100 lines)
□ tests/models/test_organizations.py (~100 lines)
```

### MODIFIED Files:
```
□ src/giljo_mcp/models/__init__.py (2 lines - exports)
□ src/giljo_mcp/models/products.py (5 lines - org_id column + relationship)
□ src/giljo_mcp/models/templates.py (5 lines - org_id column + relationship)
□ src/giljo_mcp/models/tasks.py (4 lines - org_id column)
```

---

## Expected Test Results

After implementation:
```bash
pytest tests/models/test_organizations.py -v
# Expected: 6 tests passed (GREEN)

pytest tests/ -v
# Expected: All existing tests still pass (no regressions)
```

---

## Verification Checklist

- [ ] `organizations` table exists with correct schema
- [ ] `org_memberships` table exists with correct schema
- [ ] `products.org_id` column exists (nullable)
- [ ] `agent_templates.org_id` column exists (nullable)
- [ ] `tasks.org_id` column exists (nullable)
- [ ] All indexes created
- [ ] All constraints enforced (role check, unique membership)
- [ ] All tests pass
- [ ] No regressions in existing functionality

---

## Database Schema Verification

```sql
-- Verify organizations table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'organizations';

-- Verify org_memberships table
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'org_memberships';

-- Verify products.org_id added
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'products' AND column_name = 'org_id';

-- Verify indexes
SELECT indexname FROM pg_indexes WHERE tablename = 'organizations';
SELECT indexname FROM pg_indexes WHERE tablename = 'org_memberships';
```

---

## Rollback Plan

If issues discovered:
```sql
-- Drop new tables (clean slate)
DROP TABLE IF EXISTS org_memberships CASCADE;
DROP TABLE IF EXISTS organizations CASCADE;

-- Remove org_id columns
ALTER TABLE products DROP COLUMN IF EXISTS org_id;
ALTER TABLE agent_templates DROP COLUMN IF EXISTS org_id;
ALTER TABLE tasks DROP COLUMN IF EXISTS org_id;
```

---

## Dependencies

- **Depends on:** None (first in series)
- **Blocks:** 0424b (Service Layer needs models)

---

## Notes for Implementing Agent

1. **Test first** - Write test_organizations.py before any model code
2. **Nullable org_id** - Keep nullable initially for backward compatibility
3. **Keep tenant_key** - Don't remove, will be deprecated later
4. **Check relationships** - Verify back_populates work correctly
5. **Run full test suite** - Ensure no regressions

---

## Success Criteria

- [ ] All 6 model tests pass
- [ ] Organizations table created with proper schema
- [ ] OrgMemberships table created with constraints
- [ ] Products, Templates, Tasks have org_id FK
- [ ] No existing tests broken
- [ ] Manual verification via psql queries
