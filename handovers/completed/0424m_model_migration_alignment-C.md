# Handover 0424m: Model-Migration Alignment & Test Fixture Fix

**Status:** Ready for Execution
**Color:** `#E91E63` (Pink - Critical Alignment)
**Prerequisites:** 0424l (Fresh Install Verification - COMPLETE)
**Spawns:** 0424n (Org Hierarchy Comprehensive Testing)
**Chain:** 0424 Organization Hierarchy Series (Extended - Final Fixes)

---

## Overview

Post-0424l analysis revealed **10 critical mismatches** between SQLAlchemy models and Alembic baseline migration. These mismatches cause:
- Fresh install failures (NOT NULL tenant_key with no model column)
- Runtime errors when inserting organizations
- 19 test failures due to fixture org_id issues
- Multi-tenant isolation risks

**What This Accomplishes:**
- Aligns Organization and OrgMembership models with database schema
- Fixes User.org_id nullable mismatch (model vs migration)
- Updates OrgService and AuthService to use tenant_key
- Fixes all test fixtures to provide required org_id
- Achieves 100% model-migration alignment for customer deployment

**Impact:**
- All 10 identified mismatches resolved
- All 19 failing tests pass
- Fresh install fully functional
- Multi-tenant isolation restored

---

## Prerequisites

**Required Handovers:**
- 0424l: COMPLETE (Fresh install verified, issues documented)

**Verify Before Starting:**
```powershell
# Confirm migration has tenant_key
grep -n "tenant_key" migrations/versions/baseline_v32_unified.py | head -5

# Confirm model MISSING tenant_key
grep -n "tenant_key" src/giljo_mcp/models/organizations.py
# Should return NO RESULTS

# Check current test status
pytest tests/models/test_organizations.py -v --co | head -10
```

---

## Identified Mismatches (10 Total)

| # | Mismatch | Model | Migration | Severity | Fix |
|---|----------|-------|-----------|----------|-----|
| 1 | Organization.tenant_key | MISSING | String(36) NOT NULL | CRITICAL | Add to model |
| 2 | OrgMembership.tenant_key | MISSING | String(36) NOT NULL | CRITICAL | Add to model |
| 3 | User.org_id nullable | False | True | CRITICAL | Change to True |
| 4 | Organization.slug length | 100 | 255 | HIGH | Change to 255 |
| 5 | OrgMembership.role length | 20 | 32 | LOW | Change to 32 |
| 6 | Organization indexes | Different names | idx_org_* | LOW | Match migration |
| 7 | OrgMembership indexes | Different names | idx_membership_* | LOW | Match migration |
| 8 | UniqueConstraint name | uq_org_membership_user | uq_org_user | LOW | Match migration |
| 9 | CheckConstraint name | ck_org_membership_role | ck_membership_role | LOW | Match migration |
| 10 | Organization.updated_at | onupdate=now() | NULL allowed | MEDIUM | Remove onupdate |

---

## Implementation Phases

### Phase 1: Fix Organization Model (CRITICAL)

**Edit:** `src/giljo_mcp/models/organizations.py`

**Current (lines 40-48):**
```python
id = Column(String(36), primary_key=True, default=generate_uuid)
name = Column(String(255), nullable=False)
slug = Column(String(100), nullable=False, unique=True, index=True)
```

**Replace with:**
```python
id = Column(String(36), primary_key=True, default=generate_uuid)
tenant_key = Column(String(36), nullable=False, index=True)  # ADDED: Multi-tenant isolation
name = Column(String(255), nullable=False)
slug = Column(String(255), nullable=False, unique=True, index=True)  # FIXED: 100 -> 255
```

**Also update `__table_args__` (lines 75-78):**
```python
__table_args__ = (
    Index("idx_org_tenant", "tenant_key"),  # Match migration name
    Index("idx_org_slug", "slug", unique=True),  # Match migration name
    Index("idx_org_active", "is_active"),  # Match migration name
)
```

**Remove `onupdate` from `updated_at` (lines 45-47):**
```python
updated_at = Column(
    DateTime(timezone=True), nullable=True  # FIXED: Remove server_default and onupdate
)
```

### Phase 2: Fix OrgMembership Model (CRITICAL)

**Edit:** `src/giljo_mcp/models/organizations.py`

**Add tenant_key after user_id (around line 108):**
```python
user_id = Column(
    String(36),
    ForeignKey("users.id", ondelete="CASCADE"),
    nullable=False,
    index=True,
)
tenant_key = Column(String(36), nullable=False, index=True)  # ADDED: Multi-tenant isolation
role = Column(
    String(32), nullable=False, default="member"  # FIXED: 20 -> 32
)
```

**Update `__table_args__` (lines 123-133):**
```python
__table_args__ = (
    UniqueConstraint("org_id", "user_id", name="uq_org_user"),  # FIXED: Match migration
    CheckConstraint(
        "role IN ('owner', 'admin', 'member', 'viewer')",
        name="ck_membership_role",  # FIXED: Match migration
    ),
    Index("idx_membership_org", "org_id"),  # FIXED: Match migration
    Index("idx_membership_user", "user_id"),  # FIXED: Match migration
    Index("idx_membership_tenant", "tenant_key"),  # ADDED: Match migration
)
```

### Phase 3: Fix User.org_id Nullable (CRITICAL)

**Edit:** `src/giljo_mcp/models/auth.py`

**Current (lines 60-66):**
```python
org_id = Column(
    String(36),
    ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=False,  # WRONG: Conflicts with ondelete="SET NULL"
    index=True,
    comment="Direct foreign key to organization (Handover 0424j - NOT NULL enforced)"
)
```

**Replace with:**
```python
org_id = Column(
    String(36),
    ForeignKey("organizations.id", ondelete="SET NULL"),
    nullable=True,  # FIXED: Must be True for ondelete="SET NULL" to work
    index=True,
    comment="Direct foreign key to organization (Handover 0424m - nullable for SET NULL)"
)
```

**Rationale:** The `ondelete="SET NULL"` clause requires the column to be nullable. When an Organization is deleted, PostgreSQL sets org_id to NULL. If nullable=False, this would fail with a constraint violation.

### Phase 4: Update OrgService for tenant_key

**Edit:** `src/giljo_mcp/services/org_service.py`

**Find `create_organization` method and add tenant_key parameter:**
```python
async def create_organization(
    self,
    name: str,
    owner_id: str,
    tenant_key: str,  # ADDED
    slug: str = None,
    settings: dict = None
) -> Organization:
    """Create a new organization with the given owner."""
    # ... existing validation ...

    org = Organization(
        name=name,
        tenant_key=tenant_key,  # ADDED
        slug=slug,
        settings=settings or {}
    )
    # ... rest of method ...
```

**Find `invite_member` method and add tenant_key:**
```python
async def invite_member(
    self,
    org_id: str,
    user_id: str,
    role: str,
    invited_by: str,
    tenant_key: str,  # ADDED
) -> OrgMembership:
    """Invite a user to an organization."""
    # ... existing code ...

    membership = OrgMembership(
        org_id=org_id,
        user_id=user_id,
        role=role,
        invited_by=invited_by,
        tenant_key=tenant_key,  # ADDED
    )
    # ... rest of method ...
```

### Phase 5: Update AuthService for tenant_key

**Edit:** `src/giljo_mcp/services/auth_service.py`

**Find `_create_default_organization` method (around line 180):**
```python
async def _create_default_organization(
    self, session: AsyncSession, tenant_key: str, org_name: str = "My Workspace"
) -> str:
    """Create a default organization for a new user."""
    slug = self._generate_org_slug(org_name)

    org = Organization(
        name=org_name,
        tenant_key=tenant_key,  # FIXED: Actually use the parameter
        slug=slug,
        settings={}
    )
    session.add(org)
    await session.flush()
    return org.id
```

### Phase 6: Update API Endpoints for tenant_key

**Edit:** `api/endpoints/organizations/crud.py`

**Find create organization endpoint and pass tenant_key:**
```python
@router.post("/", response_model=OrganizationResponse)
async def create_organization(
    request: CreateOrganizationRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a new organization."""
    org_service = OrgService(db)
    org = await org_service.create_organization(
        name=request.name,
        owner_id=current_user.id,
        tenant_key=current_user.tenant_key,  # ADDED
        slug=request.slug,
        settings=request.settings,
    )
    return org
```

**Edit:** `api/endpoints/organizations/members.py`

**Find invite member endpoint and pass tenant_key:**
```python
@router.post("/{org_id}/members", response_model=MembershipResponse)
async def invite_member(
    org_id: str,
    request: InviteMemberRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """Invite a user to an organization."""
    org_service = OrgService(db)
    membership = await org_service.invite_member(
        org_id=org_id,
        user_id=request.user_id,
        role=request.role,
        invited_by=current_user.id,
        tenant_key=current_user.tenant_key,  # ADDED
    )
    return membership
```

### Phase 7: Fix Test Fixtures (19 Tests)

**Edit:** `tests/models/test_organizations.py`

**Replace `test_user` fixture (lines 22-37) with:**
```python
@pytest_asyncio.fixture(scope="function")
async def test_user(db_session, test_tenant_key):
    """Create a test user for organization membership tests."""
    from src.giljo_mcp.models.organizations import Organization

    # Create org first (0424m: tenant_key required)
    org = Organization(
        name=f"Test Org {generate_uuid()[:8]}",
        slug=f"test-org-{generate_uuid()[:8]}",
        tenant_key=test_tenant_key,  # ADDED
        is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=generate_uuid(),
        tenant_key=test_tenant_key,
        username=f"test_user_{generate_uuid()[:8]}",
        email=f"test_{generate_uuid()[:8]}@example.com",
        password_hash="hashed_password",
        role="developer",
        is_active=True,
        org_id=org.id,  # ADDED
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

**Edit:** `tests/services/test_org_service.py`

**Replace `test_user` fixture (lines 35-49):**
```python
@pytest_asyncio.fixture
async def test_user(db_session):
    """Create test user for organization testing"""
    from src.giljo_mcp.models.organizations import Organization

    # Create org first (0424m: tenant_key required)
    org = Organization(
        name=f"Test Org {uuid4().hex[:8]}",
        slug=f"test-org-{uuid4().hex[:8]}",
        tenant_key=f"tenant_{uuid4().hex[:8]}",  # ADDED
        is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        username=f"testuser_{uuid4().hex[:8]}",
        email=f"test_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
        is_active=True,
        org_id=org.id,  # ADDED
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

**Replace `test_user_2` fixture (lines 53-67) with same pattern:**
```python
@pytest_asyncio.fixture
async def test_user_2(db_session):
    """Create second test user for organization testing"""
    from src.giljo_mcp.models.organizations import Organization

    # Create org first (0424m: tenant_key required)
    org = Organization(
        name=f"Test Org 2 {uuid4().hex[:8]}",
        slug=f"test-org-2-{uuid4().hex[:8]}",
        tenant_key=f"tenant2_{uuid4().hex[:8]}",  # ADDED
        is_active=True
    )
    db_session.add(org)
    await db_session.flush()

    user = User(
        id=str(uuid4()),
        username=f"testuser2_{uuid4().hex[:8]}",
        email=f"test2_{uuid4().hex[:8]}@example.com",
        tenant_key=f"tenant2_{uuid4().hex[:8]}",
        role="developer",
        password_hash="hashed_password",
        is_active=True,
        org_id=org.id,  # ADDED
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
```

### Phase 8: Update OrgService Test Calls

**Edit:** `tests/services/test_org_service.py`

**Find all calls to `create_organization` and add `tenant_key`:**
```python
# Example fix for test_create_organization
result = await service.create_organization(
    name="Test Company",
    slug="test-company",
    owner_id=test_user.id,
    tenant_key=test_user.tenant_key,  # ADDED
)
```

**Find all calls to `invite_member` and add `tenant_key`:**
```python
# Example fix for test_invite_member
membership = await service.invite_member(
    org_id=org.id,
    user_id=test_user_2.id,
    role="member",
    invited_by=test_user.id,
    tenant_key=test_user.tenant_key,  # ADDED
)
```

---

## Success Criteria

**Model Alignment:**
- [ ] Organization model has `tenant_key` column (String(36), nullable=False)
- [ ] Organization model has `slug` as String(255)
- [ ] Organization model uses migration index names
- [ ] OrgMembership model has `tenant_key` column
- [ ] OrgMembership model has `role` as String(32)
- [ ] OrgMembership model uses migration constraint/index names
- [ ] User.org_id has `nullable=True`

**Service Layer:**
- [ ] OrgService.create_organization accepts and sets tenant_key
- [ ] OrgService.invite_member accepts and sets tenant_key
- [ ] AuthService._create_default_organization uses tenant_key

**API Endpoints:**
- [ ] Create organization endpoint passes tenant_key
- [ ] Invite member endpoint passes tenant_key

**Tests:**
- [ ] All 4 model tests pass
- [ ] All 15 service tests pass
- [ ] All 17 API tests pass
- [ ] All 8 integration tests pass
- [ ] All 4 migration tests pass

**Verification:**
```powershell
# Run all org tests
pytest tests/models/test_organizations.py -v
pytest tests/services/test_org_service.py -v
pytest tests/api/test_organizations_api.py -v
pytest tests/integration/test_org_lifecycle.py -v

# Total should be: 48 passed, 0 failed
```

---

## Chain Execution Instructions

**CRITICAL: This handover is part of the 0424 chain (extended). You MUST update chain_log.json.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json | Select-String -Pattern "0424l" -Context 0,5
```

Verify 0424l status is "complete".

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json` - add 0424m session entry and set:
```json
"status": "in_progress",
"started_at": "<current ISO timestamp>"
```

### Step 3: Execute Handover

**CRITICAL: Use Task Tool Subagents**

```javascript
Task.create({
  subagent_type: 'database-expert',
  prompt: `Execute handover 0424m Phases 1-3. Read F:\\GiljoAI_MCP\\handovers\\0424m_model_migration_alignment.md for full instructions.

Your tasks:
1. Phase 1: Fix Organization model (add tenant_key, fix slug length, update indexes)
2. Phase 2: Fix OrgMembership model (add tenant_key, fix role length, update constraints)
3. Phase 3: Fix User.org_id nullable (change to nullable=True)
4. Verify model changes compile: python -c "from src.giljo_mcp.models import *"

IMPORTANT:
- Organization.tenant_key MUST be String(36), nullable=False, indexed
- OrgMembership.tenant_key MUST be String(36), nullable=False, indexed
- User.org_id MUST be nullable=True (for ondelete=SET NULL)
- Match ALL index names to migration: idx_org_*, idx_membership_*`
})
```

```javascript
Task.create({
  subagent_type: 'tdd-implementor',
  prompt: `Execute handover 0424m Phases 4-6. Read F:\\GiljoAI_MCP\\handovers\\0424m_model_migration_alignment.md for full instructions.

Your tasks:
1. Phase 4: Update OrgService.create_organization to accept/set tenant_key
2. Phase 4: Update OrgService.invite_member to accept/set tenant_key
3. Phase 5: Update AuthService._create_default_organization to use tenant_key
4. Phase 6: Update API endpoints to pass tenant_key from current_user

Files to modify:
- src/giljo_mcp/services/org_service.py
- src/giljo_mcp/services/auth_service.py
- api/endpoints/organizations/crud.py
- api/endpoints/organizations/members.py

IMPORTANT:
- tenant_key should come from current_user.tenant_key in API endpoints
- Service methods MUST accept tenant_key as required parameter
- AuthService already has tenant_key parameter but doesn't use it`
})
```

```javascript
Task.create({
  subagent_type: 'backend-tester',
  prompt: `Execute handover 0424m Phases 7-8. Read F:\\GiljoAI_MCP\\handovers\\0424m_model_migration_alignment.md for full instructions.

Your tasks:
1. Phase 7: Fix test_user fixture in tests/models/test_organizations.py
2. Phase 7: Fix test_user and test_user_2 fixtures in tests/services/test_org_service.py
3. Phase 8: Update all create_organization/invite_member calls to include tenant_key
4. Run all org tests and verify 48 pass, 0 fail

Pattern for fixtures:
- Create Organization FIRST with tenant_key
- Flush to get org.id
- Create User with org_id=org.id
- Commit and refresh

Run after fixes:
pytest tests/models/test_organizations.py tests/services/test_org_service.py -v`
})
```

### Step 4: Commit Your Work

```bash
git add -A && git commit -m "fix(0424m): Align models with migration and fix test fixtures

CRITICAL FIXES:
- Add tenant_key column to Organization model (NOT NULL, indexed)
- Add tenant_key column to OrgMembership model (NOT NULL, indexed)
- Fix User.org_id to nullable=True (required for ondelete=SET NULL)
- Fix Organization.slug length 100 -> 255
- Fix OrgMembership.role length 20 -> 32
- Update index/constraint names to match migration

SERVICE UPDATES:
- OrgService.create_organization: accepts tenant_key parameter
- OrgService.invite_member: accepts tenant_key parameter
- AuthService._create_default_organization: uses tenant_key parameter
- API endpoints: pass current_user.tenant_key to services

TEST FIXES:
- Fixed 3 fixtures to create Organization before User
- Updated 15 service tests with tenant_key parameter
- All 48 org tests now passing

Handover: 0424m
Chain: 0424 Organization Hierarchy (Extended)
Impact: Model-migration alignment complete, multi-tenant isolation restored

```

### Step 5: Update Chain Log

Update `prompts/0424_chain/chain_log.json`:
- Set 0424m status to "complete"
- Fill in tasks_completed, deviations, blockers_encountered
- Add notes_for_next for 0424n
- Add summary

### Step 6: Spawn Next Terminal (Optional)

If comprehensive testing is needed:

```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424n - Comprehensive Testing\" --tabColor \"#00BCD4\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424n. READ: F:\GiljoAI_MCP\handovers\0424n_comprehensive_testing.md - Run full test suite, verify fresh install, document completion.\"' -Verb RunAs"
```

---

## Troubleshooting

**Model import fails:**
- Check syntax errors in organizations.py and auth.py
- Verify Column imports include String

**Tests still fail after fixture update:**
- Verify Organization creation includes tenant_key
- Verify User creation includes org_id
- Check db_session.flush() is called before using org.id

**Service method signature errors:**
- Update all callers (API endpoints, tests) to pass tenant_key
- Check function parameter order

**Fresh install still fails:**
- Verify model columns match migration exactly
- Run: `python -c "from src.giljo_mcp.models import *; print('OK')"`

---

## Notes

**Why nullable=True for User.org_id:**
The migration uses `ondelete="SET NULL"` which means when an Organization is deleted, all users' org_id will be set to NULL. This requires the column to be nullable. The business logic should prevent orphan users, but the database constraint must allow it.

**Multi-Tenant Isolation:**
With tenant_key on Organization and OrgMembership, the system can enforce multi-tenant isolation at the data layer. Organizations belong to tenants, and queries should filter by tenant_key for security.

**Index Naming Convention:**
- Organizations: `idx_org_*` (e.g., idx_org_tenant, idx_org_slug, idx_org_active)
- OrgMemberships: `idx_membership_*` (e.g., idx_membership_org, idx_membership_user)

---

**Next Handover:** 0424n (Comprehensive Testing - Optional)

