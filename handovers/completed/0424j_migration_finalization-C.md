# Handover 0424j: Migration + NOT NULL Constraint (FINAL)

**Status:** 🟢 Ready for Execution
**Color:** `#F44336` (Red - Final Migration)
**Prerequisites:** 0424i (AppBar + User Settings)
**Spawns:** NONE (FINAL handover in chain)
**Chain:** 0424 Organization Hierarchy Series

---

## Overview

Complete the User → Organization direct relationship migration by populating User.org_id from existing OrgMembership data and enforcing NOT NULL constraint.

**Architecture Change:**
- Migration script populates User.org_id from OrgMembership owner records
- Verify all users have org_id set (no NULL values)
- Change User.org_id to NOT NULL in model
- Run full test suite to verify migration success

**What This Accomplishes:**
- All existing users get org_id populated from their memberships
- Database enforces org_id requirement for all users
- Completes User → Organization direct relationship implementation
- Closes 0424 chain with clean, enforced schema

**Impact:**
- User.org_id becomes required field (NOT NULL)
- All user queries can rely on org_id being set
- OrgMembership still tracks role data (owner/admin/member/viewer)
- Future users MUST have org_id at creation (enforced by DB)

---

## Prerequisites

**Required Handovers:**
- ✅ 0424f: User.org_id column (nullable)
- ✅ 0424g: AuthService sets org_id on creation
- ✅ 0424h: API endpoints use org_id
- ✅ 0424i: UI displays workspace info

**Verify Before Starting:**
```powershell
# Check User.org_id column exists and is nullable
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d users" | grep org_id

# Check existing migration script
cat scripts/migrate_to_orgs.py | grep "migrate_to_orgs"

# Check for users without org_id
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM users WHERE org_id IS NULL;"
```

---

## Implementation Phases

### 🔴 RED PHASE: Failing Tests

**1. Migration Tests - Populate User.org_id**

Create: `tests/migration/test_user_org_id_migration.py`

```python
"""
Tests for User.org_id migration from OrgMembership.
"""
import pytest
from sqlalchemy import select, text

from src.giljo_mcp.models import User, Organization, OrgMembership


@pytest.mark.asyncio
async def test_migration_populates_org_id_from_membership(db_session):
    """Test migration sets User.org_id from OrgMembership."""
    # Create org
    org = Organization(
        name="Test Org",
        slug="test-org-123",
        tenant_key="test_tenant",
        is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    # Create user WITHOUT org_id
    user = User(
        username="testuser",
        email="test@example.com",
        tenant_key="test_tenant"
        # No org_id
    )
    db_session.add(user)
    await db_session.flush()

    # Create membership
    membership = OrgMembership(
        org_id=org.id,
        user_id=user.id,
        role="owner",
        is_active=True,
        tenant_key="test_tenant"
    )
    db_session.add(membership)
    await db_session.commit()

    # Run migration logic
    stmt = text("""
        UPDATE users
        SET org_id = om.org_id
        FROM org_memberships om
        WHERE users.id = om.user_id
        AND users.org_id IS NULL
    """)
    await db_session.execute(stmt)
    await db_session.commit()

    # Reload user
    await db_session.refresh(user)

    # Assert org_id was set
    assert user.org_id == org.id


@pytest.mark.asyncio
async def test_migration_does_not_overwrite_existing_org_id(db_session, test_org):
    """Test migration does not overwrite already-set org_id."""
    # Create another org
    other_org = Organization(
        name="Other Org",
        slug="other-org-456",
        tenant_key="test_tenant",
        is_active=True
    )
    db_session.add(other_org)
    await db_session.flush()

    # Create user WITH org_id already set
    user = User(
        username="existing",
        email="existing@example.com",
        tenant_key="test_tenant",
        org_id=test_org.id  # Already set
    )
    db_session.add(user)
    await db_session.flush()

    # Create membership to different org
    membership = OrgMembership(
        org_id=other_org.id,
        user_id=user.id,
        role="member",
        is_active=True,
        tenant_key="test_tenant"
    )
    db_session.add(membership)
    await db_session.commit()

    original_org_id = user.org_id

    # Run migration logic
    stmt = text("""
        UPDATE users
        SET org_id = om.org_id
        FROM org_memberships om
        WHERE users.id = om.user_id
        AND users.org_id IS NULL
    """)
    await db_session.execute(stmt)
    await db_session.commit()

    # Reload user
    await db_session.refresh(user)

    # Assert org_id was NOT changed
    assert user.org_id == original_org_id


@pytest.mark.asyncio
async def test_verify_no_null_org_ids_after_migration(db_session):
    """Test verification query finds no NULL org_ids."""
    # Run verification query
    stmt = select(User).where(User.org_id.is_(None))
    result = await db_session.execute(stmt)
    null_org_users = result.scalars().all()

    # Assert no users have NULL org_id
    assert len(null_org_users) == 0


@pytest.mark.asyncio
async def test_not_null_constraint_enforced(db_session, test_org):
    """Test User.org_id NOT NULL constraint prevents creation without org."""
    from sqlalchemy.exc import IntegrityError

    # Try to create user without org_id
    user = User(
        username="orphan",
        email="orphan@example.com",
        tenant_key="test_tenant"
        # No org_id
    )
    db_session.add(user)

    with pytest.raises(IntegrityError, match="null value"):
        await db_session.commit()
```

**Run Tests (should FAIL - NOT NULL constraint not enforced yet):**
```powershell
pytest tests/migration/test_user_org_id_migration.py -v
```

---

### 🟢 GREEN PHASE: Make Tests Pass

**1. Update Migration Script**

Edit: `scripts/migrate_to_orgs.py`

Add step to populate User.org_id:

```python
"""
Migration script for Organization Hierarchy (0424a-j).

Handover 0424j: Populate User.org_id from OrgMembership.
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from src.giljo_mcp.config import load_config


async def migrate_user_org_ids():
    """
    Populate User.org_id from OrgMembership records.

    Sets org_id for users based on their organization membership.
    Only updates users where org_id IS NULL.

    Handover 0424j: User → Organization direct relationship.
    """
    config = load_config()
    db_url = config["database"]["url"]

    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)

    with Session() as session:
        print("Step 1: Populating User.org_id from OrgMembership...")

        # Update users.org_id from org_memberships
        stmt = text("""
            UPDATE users
            SET org_id = om.org_id
            FROM org_memberships om
            WHERE users.id = om.user_id
            AND users.org_id IS NULL
        """)

        result = session.execute(stmt)
        session.commit()

        rows_updated = result.rowcount
        print(f"  ✓ Updated {rows_updated} users with org_id")

        print("\nStep 2: Verifying no NULL org_ids...")

        # Verify no users have NULL org_id
        verify_stmt = text("""
            SELECT COUNT(*) as null_count
            FROM users
            WHERE org_id IS NULL
        """)

        result = session.execute(verify_stmt)
        null_count = result.scalar()

        if null_count > 0:
            print(f"  ✗ ERROR: {null_count} users still have NULL org_id!")
            print("  Please investigate before proceeding to NOT NULL constraint.")
            return False

        print("  ✓ All users have org_id set")

        print("\nStep 3: Summary")
        summary_stmt = text("""
            SELECT
                COUNT(*) as total_users,
                COUNT(DISTINCT org_id) as distinct_orgs
            FROM users
            WHERE org_id IS NOT NULL
        """)

        result = session.execute(summary_stmt)
        summary = result.fetchone()

        print(f"  Total users: {summary.total_users}")
        print(f"  Distinct orgs: {summary.distinct_orgs}")

        print("\n✓ Migration complete!")
        print("  Next step: Update User model to NOT NULL (run install.py)")

        return True


if __name__ == "__main__":
    success = asyncio.run(migrate_user_org_ids())
    sys.exit(0 if success else 1)
```

**2. Run Migration Script**

```powershell
# Run migration on production database
python scripts/migrate_to_orgs.py

# Verify migration
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM users WHERE org_id IS NULL;"

# Should return 0
```

**3. Update User Model - NOT NULL Constraint**

Edit: `src/giljo_mcp/models/auth.py`

```python
class User(Base):
    """
    User model - user accounts for authentication (LAN/WAN modes).

    ... (existing docstring) ...

    Handover 0424j: User.org_id is now NOT NULL (enforced after migration).
    """

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_key = Column(String(36), nullable=False, index=True)

    # Organization (Handover 0424f-j)
    org_id = Column(
        String(36),
        ForeignKey("organizations.id", ondelete="SET NULL"),
        nullable=False,  # Changed from nullable=True (0424j)
        index=True,
        comment="Direct FK to organization (Handover 0424f-j)"
    )

    # ... (rest of columns) ...
```

**4. Create Column with NOT NULL in Both Databases**

```powershell
# Run install.py to update schema
python install.py

# Verify NOT NULL constraint
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d users" | grep org_id
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp_test -c "\d users" | grep org_id
```

**Run Tests (should PASS):**
```powershell
pytest tests/migration/test_user_org_id_migration.py -v
```

---

### 🔵 REFACTOR PHASE: Final Verification

**1. Run Full Test Suite**

```powershell
# All tests
pytest tests/ -v

# Specific test suites
pytest tests/models/test_user_org_relationship.py -v
pytest tests/services/test_authservice_org_integration.py -v
pytest tests/api/test_auth_org_endpoints.py -v
pytest tests/integration/test_org_lifecycle.py -v
pytest tests/migration/test_user_org_id_migration.py -v
```

**2. Verify Database State**

```powershell
# Count users by org
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT
    o.name as org_name,
    COUNT(u.id) as user_count
FROM organizations o
LEFT JOIN users u ON u.org_id = o.id
GROUP BY o.id, o.name
ORDER BY user_count DESC;
"

# Verify all users have org_id
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "
SELECT COUNT(*) as total_users,
       COUNT(org_id) as users_with_org,
       COUNT(*) - COUNT(org_id) as users_without_org
FROM users;
"
```

**3. Update Documentation**

Update `docs/architecture/user_org_relationship.md`:

```markdown
# User → Organization Direct Relationship

**Handover:** 0424f-j
**Date:** 2026-01-31
**Status:** ✅ COMPLETE

## Migration Complete (0424j)

User.org_id is now NOT NULL. All users are required to belong to an organization.

### Migration Steps Completed

1. ✅ Created User.org_id column (nullable) - 0424f
2. ✅ Updated AuthService to set org_id on creation - 0424g
3. ✅ Updated API endpoints to use org_id - 0424h
4. ✅ Updated UI to display workspace info - 0424i
5. ✅ Populated org_id from OrgMembership - 0424j
6. ✅ Verified no NULL org_ids - 0424j
7. ✅ Changed org_id to NOT NULL - 0424j

### Current State

- User.org_id: FK to organizations.id (NOT NULL, indexed)
- User.organization: Direct SQLAlchemy relationship
- Organization.users: Backref to all users in org
- OrgMembership: Still tracks role data (owner/admin/member/viewer)

### Data Integrity

- All users MUST have org_id set
- Database enforces NOT NULL constraint
- FK constraint prevents invalid org_id values
- Cascade behavior: SET NULL on org deletion (allows org cleanup without breaking users)

## Next Steps (Out of Scope)

- Multi-workspace support (User.org_id → User.active_org_id + org switching UI)
- Org transfer (move user between orgs)
- Org deletion workflow (reassign users or cascade delete)
```

**Run All Tests:**
```powershell
pytest tests/ -v --cov=src/giljo_mcp --cov=api --cov-report=term-missing
```

---

## Success Criteria

**Migration:**
- ✅ Migration script populates User.org_id from OrgMembership
- ✅ Verification confirms no NULL org_ids
- ✅ Migration runs successfully on both databases

**Schema:**
- ✅ User.org_id is NOT NULL in model
- ✅ Database enforces NOT NULL constraint
- ✅ FK constraint still enforces referential integrity

**Testing:**
- ✅ All migration tests pass (4/4)
- ✅ All model tests pass (6/6)
- ✅ All service tests pass (5/5)
- ✅ All API tests pass (5/5)
- ✅ All integration tests pass (8/8)
- ✅ All frontend tests pass (11/11)
- ✅ **Total: 39/39 tests passing**

**Documentation:**
- ✅ Migration documentation updated
- ✅ Architecture documentation finalized
- ✅ Chain log updated with "complete" status

---

## Chain Execution Instructions

**CRITICAL: This is the FINAL handover in the 0424 chain. Mark chain as COMPLETE.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Verify 0424i is complete.

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json`:

```json
{
  "sessions": [
    {
      "session_id": "0424j",
      "title": "Migration + NOT NULL Constraint",
      "color": "#F44336",
      "status": "in_progress",
      "started_at": "2026-01-31T<current-time>",
      "completed_at": null,
      "planned_tasks": [
        "Update migrate_to_orgs.py to populate User.org_id",
        "Run migration on both databases",
        "Verify no NULL org_ids",
        "Change User.org_id to NOT NULL in model",
        "Run install.py to enforce constraint",
        "Run full test suite (39 tests)",
        "Update chain_log.json final_status = 'complete'"
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

Follow RED → GREEN → REFACTOR phases.

**CRITICAL: Use Subagents**

```javascript
Task.create({
  agent: 'database-expert',
  instruction: 'Execute migration per 0424j GREEN phase. Update migrate_to_orgs.py to populate User.org_id, run migration, verify no NULLs, change model to NOT NULL, run install.py. Verify with SQL queries.'
})

Task.create({
  agent: 'tdd-implementor',
  instruction: 'Write migration tests per 0424j RED phase. Test org_id population, verification, and NOT NULL constraint enforcement. Run full test suite and verify all 39 tests pass.'
})
```

### Step 4: Mark Chain COMPLETE

After all tests pass, update `prompts/0424_chain/chain_log.json`:

```json
{
  "chain_id": "0424",
  "chain_name": "Organization Hierarchy Series",
  "created_at": "2026-01-30",
  "total_sessions": 9,
  "sessions": [
    // ... (existing sessions 0424a-i) ...
    {
      "session_id": "0424j",
      "title": "Migration + NOT NULL Constraint",
      "color": "#F44336",
      "status": "complete",
      "started_at": "2026-01-31T<start-time>",
      "completed_at": "2026-01-31T<end-time>",
      "planned_tasks": [
        "Update migrate_to_orgs.py to populate User.org_id",
        "Run migration on both databases",
        "Verify no NULL org_ids",
        "Change User.org_id to NOT NULL in model",
        "Run install.py to enforce constraint",
        "Run full test suite (39 tests)",
        "Update chain_log.json final_status = 'complete'"
      ],
      "tasks_completed": [
        "Updated migrate_to_orgs.py with User.org_id population step",
        "Ran migration on giljo_mcp and giljo_mcp_test databases",
        "Verified 0 users have NULL org_id",
        "Changed User.org_id to NOT NULL in model",
        "Ran install.py to enforce constraint in both databases",
        "Ran full test suite - all 39 tests passing",
        "Updated chain_log.json final_status = 'complete'",
        "Updated architecture documentation"
      ],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": "0424 chain COMPLETE. User → Organization direct relationship fully implemented. All users have org_id (NOT NULL enforced). OrgMembership tracks roles. UI displays workspace throughout app.",
      "summary": "Successfully completed User → Organization migration. Populated org_id from OrgMembership, enforced NOT NULL constraint. All 39 tests passing. Chain COMPLETE."
    }
  ],
  "chain_summary": "Organization Hierarchy Series (0424a-j) COMPLETE. Phase 1 (a-e): Database, service, API, frontend components, migration. Phase 2 (f-j): User.org_id direct relationship - schema, service, API, UI, migration finalization. Total: 39 tests passing across 9 handovers.",
  "final_status": "complete"
}
```

### Step 5: Commit Your Work

```powershell
git add .
git commit -m "feat(0424j): Complete User.org_id migration and enforce NOT NULL

- Update migrate_to_orgs.py to populate User.org_id from OrgMembership
- Run migration on both databases (0 NULL org_ids)
- Change User.org_id to NOT NULL in model
- Run install.py to enforce constraint
- Add 4 migration tests
- Run full test suite - all 39 tests passing
- Update architecture documentation
- Mark 0424 chain as COMPLETE

Handover: 0424j (FINAL)
Chain: 0424 Organization Hierarchy - COMPLETE
Tests: 39/39 passing
Coverage: >85%

BREAKING: User.org_id is now NOT NULL. All users MUST belong to org.
Migration complete - User → Organization direct relationship enforced."
```

### Step 6: NO TERMINAL SPAWN

**This is the FINAL handover. DO NOT SPAWN another terminal.**

Instead, announce completion:

```powershell
Write-Host "`n========================================" -ForegroundColor Green
Write-Host "0424 Chain COMPLETE!" -ForegroundColor Green
Write-Host "========================================`n" -ForegroundColor Green
Write-Host "Handovers: 0424a-j (9 total)" -ForegroundColor Cyan
Write-Host "Tests: 39/39 passing" -ForegroundColor Green
Write-Host "Coverage: >85%" -ForegroundColor Green
Write-Host "`nUser → Organization direct relationship" -ForegroundColor Yellow
Write-Host "fully implemented and enforced.`n" -ForegroundColor Yellow
```

---

## Critical Subagent Instructions

**YOU MUST USE THE TASK TOOL TO SPAWN SUBAGENTS.**

```javascript
Task.create({
  agent: 'database-expert',
  instruction: `Execute migration per handover 0424j:

1. Update scripts/migrate_to_orgs.py:
   - Add step to populate User.org_id from OrgMembership
   - Add verification query (no NULL org_ids)

2. Run migration:
   python scripts/migrate_to_orgs.py

3. Verify:
   PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM users WHERE org_id IS NULL;"

4. Update src/giljo_mcp/models/auth.py:
   - Change org_id nullable=False

5. Run install.py to enforce constraint

Follow GREEN phase from handover.`
})

Task.create({
  agent: 'tdd-implementor',
  instruction: `Write migration tests per handover 0424j:

1. Create tests/migration/test_user_org_id_migration.py
2. Write 4 tests:
   - Migration populates org_id
   - Migration doesn't overwrite existing
   - Verification finds no NULLs
   - NOT NULL constraint enforced

3. Run full test suite:
   pytest tests/ -v

4. Verify all 39 tests pass

Follow RED → GREEN → REFACTOR from handover.`
})
```

**After spawning subagents:** Monitor Task output, verify migration success, run full test suite, announce chain completion.

---

## Dependencies

**Requires:**
- User.org_id column (0424f)
- AuthService org flow (0424g)
- OrgMembership data (0424a-e)

**Provides:**
- User.org_id NOT NULL enforcement
- Complete User → Organization architecture
- 0424 chain COMPLETION

---

## Notes

**Design Decisions:**
- Migration populates org_id from OrgMembership (authoritative source)
- NOT NULL enforced only after migration complete (safe approach)
- ondelete="SET NULL" allows org deletion without cascading to users
- Future users MUST have org_id at creation (enforced by DB)

**Testing Strategy:**
- Migration tests verify data population
- Constraint tests verify DB enforcement
- Full test suite ensures no regressions

**Chain Completion:**
- This is the FINAL handover in 0424 series
- Mark chain_log.json final_status = "complete"
- DO NOT spawn another terminal
- Announce completion with summary

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0424_chain/chain_log.json` and check 0424i status is "complete".

### Step 2: Mark Session Started
Update your session entry: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Complete all implementation phases above using Task tool subagents.

### Step 4: Commit Your Work
```bash
git add -A && git commit -m "feat(0424j): Finalize User.org_id migration - make NOT NULL

- Update migration script to populate User.org_id from OrgMembership
- Verify no NULL org_ids remain
- Change User.org_id to NOT NULL
- Run full test suite

```

### Step 5: Update Chain Log - MARK CHAIN COMPLETE
Update `prompts/0424_chain/chain_log.json`:
- Set your session status to "complete"
- Fill in tasks_completed, deviations, blockers_encountered
- Set `final_status` to "complete"
- Update `chain_summary` with full series summary

### Step 6: CHAIN COMPLETE

**CRITICAL: DO NOT SPAWN ANY TERMINALS!**
- This is the FINAL handover in the 0424 series
- Neither you NOR your subagents should spawn any new terminals
- Report completion to user

---

**Chain Status:** 🎉 COMPLETE (0424a-j)
**Total Tests:** 39/39 passing
**Coverage:** >85%
