# Handover 0424e: Migration and Integration Testing

**Date:** 2026-01-19
**From Agent:** Planning Session
**To Agent:** backend-integration-tester / database-expert
**Priority:** HIGH
**Estimated Complexity:** 4-6 hours
**Status:** Ready for Implementation
**Parent:** 0424_org_hierarchy_overview.md
**Depends On:** 0424a-d (All previous phases)

---

## Summary

Migrate existing users to organization model and verify end-to-end:
- Create personal organization for each existing user
- Assign existing products to user's organization
- Set org_id on templates and tasks
- Run comprehensive E2E tests
- Verify no data loss or regressions

---

## Migration Strategy

### Phase 1: Create Migration Script

**File:** `scripts/migrate_to_orgs.py`

```python
"""
Migration script: Create organizations for existing users.

Handover 0424e: Data migration for organization hierarchy.

This script:
1. Creates a personal organization for each existing user
2. Sets the user as owner of their organization
3. Assigns all user's products to their organization
4. Sets org_id on all user's templates
5. Sets org_id on all user's tasks

SAFE TO RUN MULTIPLE TIMES (idempotent)
"""

import asyncio
import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from src.giljo_mcp.models.auth import User
from src.giljo_mcp.models.organizations import Organization, OrgMembership
from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.templates import AgentTemplate
from src.giljo_mcp.models.tasks import Task
from src.giljo_mcp.config import get_database_url

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def create_org_for_user(session: AsyncSession, user: User) -> Organization:
    """Create personal organization for user if not exists."""

    # Check if user already has an org
    stmt = select(OrgMembership).where(
        OrgMembership.user_id == user.id,
        OrgMembership.role == "owner"
    )
    result = await session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing:
        # User already has an org, fetch and return it
        org_stmt = select(Organization).where(Organization.id == existing.org_id)
        org_result = await session.execute(org_stmt)
        return org_result.scalar_one()

    # Create new org
    slug = f"{user.username}-workspace"

    # Handle slug collision
    counter = 1
    original_slug = slug
    while True:
        check_stmt = select(Organization).where(Organization.slug == slug)
        check_result = await session.execute(check_stmt)
        if not check_result.scalar_one_or_none():
            break
        slug = f"{original_slug}-{counter}"
        counter += 1

    org = Organization(
        name=f"{user.username}'s Workspace",
        slug=slug
    )
    session.add(org)
    await session.flush()  # Get org.id

    # Create owner membership
    membership = OrgMembership(
        org_id=org.id,
        user_id=user.id,
        role="owner"
    )
    session.add(membership)

    logger.info(f"Created org '{org.slug}' for user '{user.username}'")

    return org


async def assign_products_to_org(
    session: AsyncSession,
    user: User,
    org: Organization
) -> int:
    """Assign user's products to their organization."""

    stmt = update(Product).where(
        Product.tenant_key == user.tenant_key,
        Product.org_id.is_(None)  # Only update if not already set
    ).values(org_id=org.id)

    result = await session.execute(stmt)
    count = result.rowcount

    if count > 0:
        logger.info(f"Assigned {count} products to org '{org.slug}'")

    return count


async def assign_templates_to_org(
    session: AsyncSession,
    user: User,
    org: Organization
) -> int:
    """Assign user's templates to their organization."""

    stmt = update(AgentTemplate).where(
        AgentTemplate.tenant_key == user.tenant_key,
        AgentTemplate.org_id.is_(None)
    ).values(org_id=org.id)

    result = await session.execute(stmt)
    count = result.rowcount

    if count > 0:
        logger.info(f"Assigned {count} templates to org '{org.slug}'")

    return count


async def assign_tasks_to_org(
    session: AsyncSession,
    user: User,
    org: Organization
) -> int:
    """Assign user's tasks to their organization."""

    stmt = update(Task).where(
        Task.tenant_key == user.tenant_key,
        Task.org_id.is_(None)
    ).values(org_id=org.id)

    result = await session.execute(stmt)
    count = result.rowcount

    if count > 0:
        logger.info(f"Assigned {count} tasks to org '{org.slug}'")

    return count


async def run_migration():
    """Run full migration for all users."""

    engine = create_async_engine(get_database_url())
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Get all users
        stmt = select(User)
        result = await session.execute(stmt)
        users = result.scalars().all()

        logger.info(f"Found {len(users)} users to migrate")

        stats = {
            "users_processed": 0,
            "orgs_created": 0,
            "products_assigned": 0,
            "templates_assigned": 0,
            "tasks_assigned": 0
        }

        for user in users:
            logger.info(f"Processing user: {user.username}")

            # Create org
            org = await create_org_for_user(session, user)
            stats["orgs_created"] += 1

            # Assign products
            stats["products_assigned"] += await assign_products_to_org(session, user, org)

            # Assign templates
            stats["templates_assigned"] += await assign_templates_to_org(session, user, org)

            # Assign tasks
            stats["tasks_assigned"] += await assign_tasks_to_org(session, user, org)

            stats["users_processed"] += 1

        await session.commit()

        logger.info("Migration complete!")
        logger.info(f"Stats: {stats}")

        return stats


if __name__ == "__main__":
    asyncio.run(run_migration())
```

### Phase 2: Run Migration

```bash
# Run migration script
python scripts/migrate_to_orgs.py

# Verify results
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM organizations;"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM org_memberships;"
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM products WHERE org_id IS NOT NULL;"
```

---

## Integration Tests

### Create Test File (tests/integration/test_org_lifecycle.py)

```python
"""Integration tests for complete organization lifecycle."""
import pytest
from httpx import AsyncClient


class TestOrgLifecycle:
    """End-to-end tests for organization operations."""

    @pytest.mark.asyncio
    async def test_complete_org_workflow(
        self,
        client: AsyncClient,
        auth_headers,
        other_user_id,
        other_user_headers
    ):
        """Test complete org lifecycle: create -> invite -> manage -> delete."""

        # Step 1: Create organization
        create_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Integration Test Org", "slug": "int-test-org"}
        )
        assert create_response.status_code == 201
        org = create_response.json()
        org_id = org["id"]

        # Step 2: Verify owner membership
        assert len(org["members"]) == 1
        assert org["members"][0]["role"] == "owner"

        # Step 3: Invite member
        invite_response = await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "admin"}
        )
        assert invite_response.status_code == 201

        # Step 4: Verify invited user can access org
        access_response = await client.get(
            f"/api/organizations/{org_id}",
            headers=other_user_headers
        )
        assert access_response.status_code == 200

        # Step 5: Change member role
        role_response = await client.put(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=auth_headers,
            json={"role": "viewer"}
        )
        assert role_response.status_code == 200
        assert role_response.json()["role"] == "viewer"

        # Step 6: Remove member
        remove_response = await client.delete(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=auth_headers
        )
        assert remove_response.status_code == 200

        # Step 7: Verify removed user cannot access
        denied_response = await client.get(
            f"/api/organizations/{org_id}",
            headers=other_user_headers
        )
        assert denied_response.status_code == 403

        # Step 8: Delete organization
        delete_response = await client.delete(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )
        assert delete_response.status_code == 200

        # Step 9: Verify org no longer accessible
        gone_response = await client.get(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )
        assert gone_response.status_code == 404


class TestOrgPermissions:
    """Tests for permission boundaries."""

    @pytest.mark.asyncio
    async def test_viewer_cannot_invite(
        self,
        client: AsyncClient,
        auth_headers,
        viewer_user_id,
        viewer_user_headers,
        third_user_id
    ):
        """Test that viewer role cannot invite members."""
        # Setup: Create org and add viewer
        org_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Perm Test", "slug": "perm-test-viewer"}
        )
        org_id = org_response.json()["id"]

        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": viewer_user_id, "role": "viewer"}
        )

        # Test: Viewer tries to invite
        response = await client.post(
            f"/api/organizations/{org_id}/members",
            headers=viewer_user_headers,
            json={"user_id": third_user_id, "role": "member"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_member_cannot_change_roles(
        self,
        client: AsyncClient,
        auth_headers,
        member_user_id,
        member_user_headers,
        other_user_id
    ):
        """Test that member role cannot change other members' roles."""
        # Setup: Create org with member and another user
        org_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Perm Test 2", "slug": "perm-test-member"}
        )
        org_id = org_response.json()["id"]

        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": member_user_id, "role": "member"}
        )
        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "viewer"}
        )

        # Test: Member tries to promote viewer
        response = await client.put(
            f"/api/organizations/{org_id}/members/{other_user_id}",
            headers=member_user_headers,
            json={"role": "admin"}
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_only_owner_can_delete_org(
        self,
        client: AsyncClient,
        auth_headers,
        admin_user_id,
        admin_user_headers
    ):
        """Test that only owner can delete organization."""
        # Setup: Create org with admin
        org_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Delete Test", "slug": "delete-test-perm"}
        )
        org_id = org_response.json()["id"]

        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": admin_user_id, "role": "admin"}
        )

        # Test: Admin tries to delete
        response = await client.delete(
            f"/api/organizations/{org_id}",
            headers=admin_user_headers
        )

        assert response.status_code == 403


class TestOrgOwnershipTransfer:
    """Tests for ownership transfer."""

    @pytest.mark.asyncio
    async def test_transfer_ownership(
        self,
        client: AsyncClient,
        auth_headers,
        other_user_id,
        other_user_headers
    ):
        """Test transferring org ownership."""
        # Create org
        org_response = await client.post(
            "/api/organizations",
            headers=auth_headers,
            json={"name": "Transfer Test", "slug": "transfer-test"}
        )
        org_id = org_response.json()["id"]

        # Add member as admin
        await client.post(
            f"/api/organizations/{org_id}/members",
            headers=auth_headers,
            json={"user_id": other_user_id, "role": "admin"}
        )

        # Transfer ownership
        transfer_response = await client.post(
            f"/api/organizations/{org_id}/transfer",
            headers=auth_headers,
            json={"new_owner_id": other_user_id}
        )
        assert transfer_response.status_code == 200

        # Verify: New owner can delete, old owner cannot
        old_owner_delete = await client.delete(
            f"/api/organizations/{org_id}",
            headers=auth_headers
        )
        assert old_owner_delete.status_code == 403

        new_owner_delete = await client.delete(
            f"/api/organizations/{org_id}",
            headers=other_user_headers
        )
        assert new_owner_delete.status_code == 200


class TestDataMigration:
    """Tests for data migration verification."""

    @pytest.mark.asyncio
    async def test_user_has_default_org_after_migration(
        self,
        client: AsyncClient,
        auth_headers
    ):
        """Test that user has a default organization after migration."""
        response = await client.get("/api/organizations", headers=auth_headers)

        assert response.status_code == 200
        orgs = response.json()

        # User should have at least one org (personal workspace)
        assert len(orgs) >= 1

        # At least one org should have user as owner
        owner_orgs = [o for o in orgs if any(
            m["role"] == "owner" for m in o.get("members", [])
        )]
        assert len(owner_orgs) >= 1

    @pytest.mark.asyncio
    async def test_products_have_org_id(self, db_session):
        """Test that all products have org_id after migration."""
        from sqlalchemy import select
        from src.giljo_mcp.models.products import Product

        stmt = select(Product).where(Product.org_id.is_(None))
        result = await db_session.execute(stmt)
        orphaned = result.scalars().all()

        # No products should be without org_id
        assert len(orphaned) == 0, f"Found {len(orphaned)} products without org_id"
```

---

## Verification Checklist

### Pre-Migration Checks
- [ ] Backup database before migration
- [ ] Count existing users
- [ ] Count existing products
- [ ] Count existing templates
- [ ] Count existing tasks

### Migration Execution
- [ ] Run migration script
- [ ] Verify all users have personal org
- [ ] Verify all products have org_id
- [ ] Verify all templates have org_id
- [ ] Verify all tasks have org_id

### Post-Migration Verification

```sql
-- Verify all users have org
SELECT u.id, u.username, o.slug as org_slug
FROM users u
LEFT JOIN org_memberships m ON u.id = m.user_id AND m.role = 'owner'
LEFT JOIN organizations o ON m.org_id = o.id
WHERE o.id IS NULL;
-- Should return 0 rows

-- Verify all products have org_id
SELECT COUNT(*) as orphaned_products FROM products WHERE org_id IS NULL;
-- Should return 0

-- Verify all templates have org_id
SELECT COUNT(*) as orphaned_templates FROM agent_templates WHERE org_id IS NULL;
-- Should return 0

-- Verify membership counts
SELECT role, COUNT(*) FROM org_memberships GROUP BY role;
-- Should show owner count = user count
```

---

## Test Execution

```bash
# Run all integration tests
pytest tests/integration/test_org_lifecycle.py -v

# Run with coverage
pytest tests/integration/test_org_lifecycle.py -v --cov=src/giljo_mcp

# Full test suite (ensure no regressions)
pytest tests/ -v
```

---

## Files to Create

### NEW Files:
```
□ scripts/migrate_to_orgs.py (~150 lines)
□ tests/integration/test_org_lifecycle.py (~250 lines)
```

---

## Rollback Plan

If migration fails:

```sql
-- Remove all org_id assignments (revert to NULL)
UPDATE products SET org_id = NULL;
UPDATE agent_templates SET org_id = NULL;
UPDATE tasks SET org_id = NULL;

-- Remove all memberships
DELETE FROM org_memberships;

-- Remove all organizations
DELETE FROM organizations;
```

---

## Success Criteria

- [ ] Migration script runs without errors
- [ ] All users have personal organization
- [ ] All products assigned to org
- [ ] All templates assigned to org
- [ ] All tasks assigned to org
- [ ] All integration tests pass
- [ ] No regressions in existing functionality
- [ ] Manual E2E testing complete

---

## Manual E2E Test Scenarios

1. **New user registration** - Creates account, verify default org created
2. **Product creation** - Create product, verify belongs to user's org
3. **Invite flow** - Owner invites user, user sees org products
4. **Permission boundaries** - Verify viewer can't edit, member can't invite
5. **Ownership transfer** - Transfer org, verify permissions flip
6. **Multi-org user** (future) - User in multiple orgs sees all

---

## Post-0424 Series Cleanup

After successful migration and testing:

1. **Consider making org_id NOT NULL** (0425 follow-up):
   ```sql
   ALTER TABLE products ALTER COLUMN org_id SET NOT NULL;
   ALTER TABLE agent_templates ALTER COLUMN org_id SET NOT NULL;
   ALTER TABLE tasks ALTER COLUMN org_id SET NOT NULL;
   ```

2. **Deprecate tenant_key usage** (future handover):
   - Update queries to use org_id instead of tenant_key
   - Keep tenant_key for backward compatibility
   - Plan removal in v4.0

---

## Dependencies

- **Depends on:** 0424a-d (All code must be deployed)
- **Enables:** 0425 (Export/Import), 0426 (Multi-org)

---

## Notes for Implementing Agent

1. **Run migration in dev first** - Test on dev database
2. **Idempotent script** - Safe to run multiple times
3. **Check for existing orgs** - Don't duplicate if already migrated
4. **Handle slug collisions** - Add suffix if username-workspace exists
5. **Comprehensive verification** - SQL queries + integration tests

---

## Chain Execution Instructions

**This is the FINAL handover in the chain. Follow these instructions EXACTLY.**

### Step 1: Read Chain Log

Read `prompts/0424_chain/chain_log.json`:
- Review `0424d` session's `notes_for_next` for critical context
- Verify `0424d` status is `complete`
- If previous session is `blocked` or `failed`, STOP and report to user

### Step 2: Mark Session Started

Update chain_log.json session `0424e`:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover Tasks

**CRITICAL: Use Task tool subagents for ALL implementation work. Do NOT do work directly.**

Example:
```
Task(subagent_type="backend-tester", prompt="Read handover 0424e at F:\GiljoAI_MCP\handovers\0424e_migration_testing.md. Run E2E integration tests for the complete Organization Hierarchy feature.")
```

**Required subagents:**
- `backend-tester` - For E2E integration testing
- `database-expert` - For migration scripts and verification

### Step 4: Update Chain Log - FINAL SESSION

Update chain_log.json session `0424e`:
```json
{
  "status": "complete",
  "completed_at": "<current ISO timestamp>",
  "tasks_completed": ["<list what you actually did>"],
  "deviations": ["<any changes from plan, or empty>"],
  "blockers_encountered": ["<any issues, or empty>"],
  "notes_for_next": null,
  "summary": "<2-3 sentence summary>"
}
```

Also update the chain-level fields:
```json
{
  "chain_summary": "<summary of entire 0424 series accomplishments>",
  "final_status": "complete"
}
```

### Step 5: CHAIN COMPLETE - No Terminal to Spawn

**CRITICAL: DO NOT SPAWN ANY TERMINALS!**
- This is the FINAL handover in the chain
- Neither you NOR your subagents should spawn any new terminals
- Just commit, report completion, and archive handovers

This is the FINAL handover. Instead of spawning a new terminal:

1. **Commit all changes:**
   ```bash
   git add .
   git commit -m "feat(0424): Complete Organization Hierarchy series

   - 0424a: Database schema (organizations, org_memberships)
   - 0424b: Service layer (OrgService, OrgRepository)
   - 0424c: API endpoints (CRUD, membership)
   - 0424d: Frontend (settings page, member UI, org switcher)
   - 0424e: Migration and E2E testing

   ```

2. **Report completion to user** with summary of all 5 handovers

3. **Move handovers to completed:**
   ```bash
   mv handovers/0424a_database_schema.md handovers/completed/0424a_database_schema-C.md
   mv handovers/0424b_service_layer.md handovers/completed/0424b_service_layer-C.md
   mv handovers/0424c_api_endpoints.md handovers/completed/0424c_api_endpoints-C.md
   mv handovers/0424d_frontend.md handovers/completed/0424d_frontend-C.md
   mv handovers/0424e_migration_testing.md handovers/completed/0424e_migration_testing-C.md
   ```
