# Handover 0424f: Add User.org_id Column (Schema)

**Status:** 🟢 Ready for Execution
**Color:** `#4CAF50` (Green - Foundation)
**Prerequisites:** 0424e (Migration & Testing)
**Spawns:** 0424g (AuthService Update)
**Chain:** 0424 Organization Hierarchy Series

---

## Overview

Add direct `org_id` foreign key column to User model, establishing the Organization → User relationship at the schema level.

**Architecture Change:**
- User model gets `org_id` FK (direct relationship to Organization)
- OrgMemberships kept for ROLE tracking only
- User.org_id starts nullable (for migration), later becomes NOT NULL
- Fresh install: Create Org FIRST → then Admin user with org_id set

**What This Accomplishes:**
- User directly belongs to Organization (no join through OrgMembership for org access)
- OrgMembership.user_id + User.org_id = redundant but intentional (role data vs ownership)
- Simplifies queries: `user.organization` instead of `user.org_memberships[0].organization`
- Prepares for migration in 0424j

**Impact:**
- Foundation for auth flow changes (0424g) and API updates (0424h)
- All users will have direct org access via FK relationship
- OrgMembership remains authoritative for role data

---

## Prerequisites

**Required Handovers:**
- ✅ 0424a: Core Organization models and schema
- ✅ 0424b: Service layer (OrgService)
- ✅ 0424c: API endpoints
- ✅ 0424d: Frontend components
- ✅ 0424e: Migration script and E2E tests

**Verify Before Starting:**
```powershell
# Check Organization and OrgMembership tables exist
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d organizations"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d org_memberships"

# Check User model exists
cat src/giljo_mcp/models/auth.py | grep "class User"
```

---

## Implementation Phases

### 🔴 RED PHASE: Failing Tests

**1. Model Tests - User.org_id Relationship**

Create: `tests/models/test_user_org_relationship.py`

```python
"""
Tests for User.org_id direct relationship to Organization.
"""
import pytest
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from src.giljo_mcp.models import User, Organization


@pytest.mark.asyncio
async def test_user_org_id_column_exists(db_session):
    """Test User model has org_id column."""
    from sqlalchemy import inspect

    inspector = inspect(User)
    column_names = [c.name for c in inspector.columns]

    assert "org_id" in column_names


@pytest.mark.asyncio
async def test_user_org_id_nullable(db_session):
    """Test User.org_id is nullable (for migration)."""
    from sqlalchemy import inspect

    inspector = inspect(User)
    org_id_col = [c for c in inspector.columns if c.name == "org_id"][0]

    assert org_id_col.nullable is True


@pytest.mark.asyncio
async def test_user_organization_relationship(db_session, test_org):
    """Test User.organization relationship loads Organization."""
    # Create user with org_id
    user = User(
        username="testuser",
        email="test@example.com",
        tenant_key=test_org.tenant_key,
        org_id=test_org.id
    )
    db_session.add(user)
    await db_session.commit()

    # Load user with organization
    stmt = select(User).options(selectinload(User.organization)).where(User.id == user.id)
    result = await db_session.execute(stmt)
    loaded_user = result.scalar_one()

    # Assert relationship works
    assert loaded_user.organization is not None
    assert loaded_user.organization.id == test_org.id
    assert loaded_user.organization.name == test_org.name


@pytest.mark.asyncio
async def test_user_without_org(db_session):
    """Test User can exist without org_id (nullable)."""
    user = User(
        username="orphan_user",
        email="orphan@example.com",
        tenant_key="test_tenant"
        # No org_id
    )
    db_session.add(user)
    await db_session.commit()

    # Load user
    stmt = select(User).options(selectinload(User.organization)).where(User.id == user.id)
    result = await db_session.execute(stmt)
    loaded_user = result.scalar_one()

    # Assert org_id is None and relationship is None
    assert loaded_user.org_id is None
    assert loaded_user.organization is None


@pytest.mark.asyncio
async def test_organization_users_backref(db_session, test_org):
    """Test Organization.users backref returns users."""
    # Create 3 users with org_id
    for i in range(3):
        user = User(
            username=f"user{i}",
            email=f"user{i}@example.com",
            tenant_key=test_org.tenant_key,
            org_id=test_org.id
        )
        db_session.add(user)
    await db_session.commit()

    # Load org with users
    stmt = select(Organization).options(selectinload(Organization.users)).where(Organization.id == test_org.id)
    result = await db_session.execute(stmt)
    loaded_org = result.scalar_one()

    # Assert backref works
    assert len(loaded_org.users) == 3
    assert all(u.org_id == test_org.id for u in loaded_org.users)


@pytest.mark.asyncio
async def test_user_org_id_fk_constraint(db_session, test_org):
    """Test org_id FK constraint enforces referential integrity."""
    from sqlalchemy.exc import IntegrityError

    # Try to create user with invalid org_id
    user = User(
        username="baduser",
        email="bad@example.com",
        tenant_key="test_tenant",
        org_id="00000000-0000-0000-0000-000000000000"  # Non-existent
    )
    db_session.add(user)

    with pytest.raises(IntegrityError):
        await db_session.commit()
```

**Run Tests (should FAIL):**
```powershell
pytest tests/models/test_user_org_relationship.py -v
```

---

### 🟢 GREEN PHASE: Make Tests Pass

**1. Update User Model**

Edit: `src/giljo_mcp/models/auth.py`

Add `org_id` column and `organization` relationship to User class:

```python
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,  # Add this import
    Index,
    Integer,
    String,
    Text,
)

class User(Base):
    """
    User model - user accounts for authentication (LAN/WAN modes).

    ... (existing docstring) ...

    Handover 0424f: Organization Direct Relationship
    - org_id: Direct FK to organization (nullable for migration)
    - organization: Direct relationship to Organization model
    - User.organization replaces User.org_memberships[0].organization pattern
    - OrgMembership still tracks role (owner/admin/member/viewer)
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Organization (Handover 0424f)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=True,  # Nullable for migration; becomes NOT NULL in 0424j
        index=True,
        comment="Direct FK to organization (Handover 0424f)"
    )

    # Credentials
    username = Column(String(64), unique=True, nullable=False, index=True)
    # ... (rest of existing columns) ...

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="users",
        foreign_keys=[org_id]
    )
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    # ... (rest of existing relationships) ...

    __table_args__ = (
        Index("idx_user_tenant", "tenant_key"),
        Index("idx_user_username", "username"),
        Index("idx_user_email", "email"),
        Index("idx_user_active", "is_active"),
        Index("idx_user_system", "is_system_user"),
        Index("idx_user_pin_lockout", "pin_lockout_until"),
        Index("idx_user_org", "org_id"),  # Add index for org queries
        CheckConstraint("role IN ('admin', 'developer', 'viewer')", name="ck_user_role"),
        CheckConstraint("failed_pin_attempts >= 0", name="ck_user_pin_attempts_positive"),
    )
```

**2. Update Organization Model**

Edit: `src/giljo_mcp/models/organizations.py`

Add `users` backref to Organization class:

```python
class Organization(Base):
    """
    Organization model - hierarchical tenant structure above products.

    ... (existing docstring) ...

    Handover 0424f: User Direct Relationship
    - users: Direct relationship to users (backref from User.organization)
    """

    __tablename__ = "organizations"

    # ... (existing columns) ...

    # Relationships
    users = relationship(
        "User",
        back_populates="organization",
        foreign_keys="User.org_id",
        order_by="User.created_at.desc()"
    )
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

    # ... (existing __table_args__) ...
```

**3. Create Database Column**

Run install.py to create column in both databases:

```powershell
# Create column in production database
python install.py

# Verify column exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d users"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test -c "\d users"
```

**Run Tests (should PASS):**
```powershell
pytest tests/models/test_user_org_relationship.py -v
```

---

### 🔵 REFACTOR PHASE: Optimize & Document

**1. Add Docstring to User.organization**

Update `src/giljo_mcp/models/auth.py`:

```python
class User(Base):
    # ... (existing code) ...

    # Relationships
    organization = relationship(
        "Organization",
        back_populates="users",
        foreign_keys=[org_id],
        doc="""
        Direct relationship to user's organization.

        Replaces the pattern: user.org_memberships[0].organization

        Usage:
            >>> user = await db.get(User, user_id)
            >>> org = user.organization  # Direct access
            >>> print(f"User belongs to: {org.name}")

        Note: OrgMembership still tracks role (owner/admin/member/viewer).
        This relationship is for organizational ownership, not role data.

        Handover: 0424f (Organization Direct Relationship)
        """
    )
```

**2. Add Migration Notes**

Create: `docs/architecture/user_org_relationship.md`

```markdown
# User → Organization Direct Relationship

**Handover:** 0424f
**Date:** 2026-01-31

## Architecture Overview

Users now have a direct FK relationship to organizations via `User.org_id`.

### Before (0424a-e)
```python
# Access org via OrgMembership join
user = await db.get(User, user_id)
membership = user.org_memberships[0]  # Assumes one membership
org = membership.organization
role = membership.role
```

### After (0424f+)
```python
# Direct org access + separate role lookup
user = await db.get(User, user_id)
org = user.organization  # Direct FK relationship
role = user.org_memberships[0].role  # Still from OrgMembership
```

## Data Model

- `User.org_id`: FK to organizations.id (nullable initially, NOT NULL in 0424j)
- `User.organization`: SQLAlchemy relationship to Organization
- `Organization.users`: Backref to all users in org
- `OrgMembership`: Still authoritative for role data (owner/admin/member/viewer)

## Migration Strategy (0424j)

1. Add column as nullable (0424f) ✅
2. Populate org_id from OrgMembership owner records (0424j)
3. Verify no NULL org_ids (0424j)
4. Change column to NOT NULL (0424j)

## Design Rationale

**Why redundant relationships?**
- User.org_id: Fast org access without join
- OrgMembership.user_id: Role tracking (owner/admin/member/viewer)
- Separates ownership from permissions

**Why nullable initially?**
- Allows existing users to continue working during migration
- Migration script sets org_id from OrgMembership in 0424j
- Becomes NOT NULL after migration complete
```

**Run All Tests:**
```powershell
pytest tests/models/ -v --cov=src/giljo_mcp/models/auth --cov-report=term-missing
```

---

## Success Criteria

**Schema:**
- ✅ User model has `org_id` column (nullable, indexed)
- ✅ User model has `organization` relationship
- ✅ Organization model has `users` backref
- ✅ FK constraint enforces referential integrity
- ✅ Column created in both giljo_mcp and giljo_mcp_test databases

**Tests:**
- ✅ All 6 model tests pass
- ✅ User.organization relationship loads Organization
- ✅ Organization.users backref returns users
- ✅ Users can exist without org_id (nullable)
- ✅ FK constraint prevents invalid org_id

**Documentation:**
- ✅ Docstrings added to relationship
- ✅ Architecture doc explains before/after patterns
- ✅ Migration strategy documented

---

## Chain Execution Instructions

**CRITICAL: This handover is part of the 0424 chain. You MUST update chain_log.json.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Check `sessions` array. Verify 0424e is complete.

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json`:

```json
{
  "sessions": [
    {
      "session_id": "0424f",
      "title": "User.org_id Schema",
      "color": "#4CAF50",
      "status": "in_progress",
      "started_at": "2026-01-31T<current-time>",
      "completed_at": null,
      "planned_tasks": [
        "Add User.org_id column (nullable)",
        "Add User.organization relationship",
        "Add Organization.users backref",
        "Run install.py to create column",
        "Write 6 model tests - all passing"
      ],
      "tasks_completed": [],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": null,
      "summary": null
    }
  ]
}
```

### Step 3: Execute Handover

Follow RED → GREEN → REFACTOR phases above.

**CRITICAL: Use Subagents**

This handover requires database-expert and tdd-implementor:

```javascript
Task.create({
  agent: 'database-expert',
  instruction: 'Implement User.org_id schema changes per 0424f GREEN phase. Add org_id column to User model, organization relationship, and users backref to Organization. Run install.py to create column. Verify column exists in both databases.'
})

Task.create({
  agent: 'tdd-implementor',
  instruction: 'Write model tests per 0424f RED phase. Test User.org_id column, relationship, backref, nullable constraint, and FK integrity. Run tests until all 6 pass.'
})
```

### Step 4: Update Chain Log

After all tests pass:

```json
{
  "sessions": [
    {
      "session_id": "0424f",
      "title": "User.org_id Schema",
      "color": "#4CAF50",
      "status": "complete",
      "started_at": "2026-01-31T<start-time>",
      "completed_at": "2026-01-31T<end-time>",
      "planned_tasks": [
        "Add User.org_id column (nullable)",
        "Add User.organization relationship",
        "Add Organization.users backref",
        "Run install.py to create column",
        "Write 6 model tests - all passing"
      ],
      "tasks_completed": [
        "Added User.org_id column with FK to organizations",
        "Added User.organization relationship (direct access)",
        "Added Organization.users backref",
        "Created column in both giljo_mcp and giljo_mcp_test databases",
        "Wrote 6 model tests - all passing",
        "Added architecture documentation"
      ],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": "User.org_id is nullable for migration. AuthService needs to set org_id when creating users (0424g). Migration script will populate org_id from OrgMembership (0424j).",
      "summary": "Successfully added User.org_id direct relationship to Organization. Column is nullable for migration, becomes NOT NULL in 0424j. All 6 model tests passing."
    }
  ]
}
```

### Step 5: Commit Your Work

```powershell
git add .
git commit -m "feat(0424f): Add User.org_id direct FK to Organization

- Add org_id column to User model (nullable for migration)
- Add User.organization relationship (direct access)
- Add Organization.users backref
- Create column in both databases via install.py
- Add 6 comprehensive model tests
- Document architecture and migration strategy

Handover: 0424f
Chain: 0424 Organization Hierarchy
Tests: 6/6 passing
Coverage: >95% on new code

BREAKING: User.organization is now direct FK, not via OrgMembership join.
OrgMembership still tracks role data (owner/admin/member/viewer)."
```

### Step 6: Spawn Next Terminal

**⚠️ WARNING: Check for duplicate terminals before spawning!**

Before spawning, verify no existing 0424g terminal:

```powershell
# List all PowerShell windows
Get-Process powershell | Select-Object MainWindowTitle
```

If you see "Handover 0424g" in the list, **DO NOT SPAWN**. That terminal already exists.

If NOT spawned yet:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd F:\GiljoAI_MCP; Write-Host 'Handover 0424g: AuthService Update' -ForegroundColor Cyan; Write-Host 'Spawned from: 0424f (User.org_id Schema)' -ForegroundColor Gray; Write-Host ''; cat handovers/0424g_authservice_update.md"
```

---

## Critical Subagent Instructions

**YOU MUST USE THE TASK TOOL TO SPAWN SUBAGENTS.**

```javascript
Task.create({
  agent: 'database-expert',
  instruction: `Implement User.org_id schema per handover 0424f:

1. Modify src/giljo_mcp/models/auth.py:
   - Add org_id column (nullable, FK to organizations.id)
   - Add organization relationship
   - Add index on org_id

2. Modify src/giljo_mcp/models/organizations.py:
   - Add users backref to Organization

3. Run install.py to create column in both databases

4. Verify:
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\\d users"

Follow GREEN phase from handover.`
})

Task.create({
  agent: 'tdd-implementor',
  instruction: `Write model tests per handover 0424f:

1. Create tests/models/test_user_org_relationship.py
2. Write 6 tests:
   - User.org_id column exists
   - User.org_id is nullable
   - User.organization relationship works
   - User without org_id (None)
   - Organization.users backref
   - FK constraint enforcement

3. Run tests:
   pytest tests/models/test_user_org_relationship.py -v

Follow RED → GREEN pattern from handover.`
})
```

**After spawning subagents:** Monitor Task output, review code, verify database changes.

---

## Dependencies

**Requires:**
- Organization model (0424a)
- OrgMembership model (0424a)
- install.py script for database changes

**Provides:**
- User.org_id column (foundation for 0424g AuthService changes)
- User.organization relationship (foundation for API updates in 0424h)
- Migration path for 0424j

---

## Notes

**Design Decisions:**
- org_id nullable initially to allow gradual migration
- OrgMembership still authoritative for role data (not redundant)
- ondelete="SET NULL" allows org deletion without cascading to users
- Separate relationships for ownership (User.org_id) vs permissions (OrgMembership.role)

**Testing Strategy:**
- Model tests verify schema constraints
- Relationship tests verify eager loading works
- FK tests verify referential integrity

**Future Work (0424g):**
- AuthService must set org_id when creating users
- Fresh install: Create org FIRST, then user with org_id
- Migration script (0424j) populates org_id from OrgMembership

---

**Next Handover:** 0424g (AuthService Update)
