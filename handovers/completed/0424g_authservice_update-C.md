# Handover 0424g: Update AuthService (Service Layer)

**Status:** 🟢 Ready for Execution
**Color:** `#2196F3` (Blue - Service Layer)
**Prerequisites:** 0424f (User.org_id Schema)
**Spawns:** 0424h (API Layer + Welcome Screen)
**Chain:** 0424 Organization Hierarchy Series

---

## Overview

Modify AuthService to set User.org_id during user creation, implementing the org-first flow where organizations are created before users.

**Architecture Change:**
- `_create_default_organization()` RETURNS org.id
- `_create_first_admin_impl()` creates org FIRST, then user WITH org_id
- `_register_user_impl()` accepts org_id parameter and sets it on user
- Add `create_user_in_org()` method for admin creating users

**What This Accomplishes:**
- Fresh install creates workspace → admin user (org-first flow)
- User registration sets org_id directly (no separate membership query needed)
- Admins can create users in their org with org_id pre-set
- OrgMembership still tracks role data (owner/admin/member/viewer)

**Impact:**
- All new users get org_id set at creation time
- Simplifies user queries (no OrgMembership join for org access)
- Maintains backwards compatibility (org_id nullable for existing users)

---

## Prerequisites

**Required Handovers:**
- ✅ 0424f: User.org_id column and relationship

**Verify Before Starting:**
```powershell
# Check User.org_id column exists
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c "\d users" | grep org_id

# Check AuthService exists
cat api/services/auth_service.py | grep "class AuthService"

# Check OrgService exists
cat api/services/organization_service.py | grep "class OrgService"
```

---

## Implementation Phases

### 🔴 RED PHASE: Failing Tests

**1. Service Tests - AuthService Sets org_id**

Create: `tests/services/test_authservice_org_integration.py`

```python
"""
Tests for AuthService setting User.org_id during creation.
"""
import pytest
from sqlalchemy import select

from api.services.auth_service import AuthService
from api.services.organization_service import OrgService
from src.giljo_mcp.models import User, Organization, OrgMembership


@pytest.mark.asyncio
async def test_create_first_admin_sets_org_id(db_session):
    """Test _create_first_admin_impl creates org FIRST then sets user.org_id."""
    # Create first admin
    user = await AuthService._create_first_admin_impl(
        db=db_session,
        username="admin",
        password="GiljoMCP",
        email="admin@example.com",
        org_name="My Workspace"  # Custom org name
    )

    # Assert user has org_id set
    assert user.org_id is not None

    # Load org and verify name
    org = await db_session.get(Organization, user.org_id)
    assert org is not None
    assert org.name == "My Workspace"

    # Load membership and verify owner role
    stmt = select(OrgMembership).where(
        OrgMembership.user_id == user.id,
        OrgMembership.org_id == user.org_id
    )
    result = await db_session.execute(stmt)
    membership = result.scalar_one()

    assert membership.role == "owner"


@pytest.mark.asyncio
async def test_register_user_sets_org_id(db_session, test_org):
    """Test _register_user_impl sets org_id when provided."""
    # Register user with org_id
    user = await AuthService._register_user_impl(
        db=db_session,
        username="newuser",
        password="password123",
        email="newuser@example.com",
        tenant_key=test_org.tenant_key,
        org_id=test_org.id,
        org_role="member"
    )

    # Assert user has org_id set
    assert user.org_id == test_org.id

    # Verify organization relationship works
    assert user.organization is not None
    assert user.organization.id == test_org.id


@pytest.mark.asyncio
async def test_create_user_in_org_by_admin(db_session, test_org, test_admin_user):
    """Test admin can create user in their org with org_id set."""
    # Admin creates user in their org
    new_user = await AuthService.create_user_in_org(
        db=db_session,
        admin_user_id=test_admin_user.id,
        username="teammember",
        email="teammember@example.com",
        role="member",
        initial_password="temp123"
    )

    # Assert new user has same org_id as admin
    assert new_user.org_id == test_admin_user.org_id

    # Verify membership created with correct role
    stmt = select(OrgMembership).where(OrgMembership.user_id == new_user.id)
    result = await db_session.execute(stmt)
    membership = result.scalar_one()

    assert membership.role == "member"
    assert membership.org_id == test_admin_user.org_id


@pytest.mark.asyncio
async def test_create_user_in_org_requires_admin_role(db_session, test_org, test_member_user):
    """Test only admins/owners can create users."""
    from api.exceptions import PermissionDeniedError

    # Member tries to create user
    with pytest.raises(PermissionDeniedError, match="Only admins and owners"):
        await AuthService.create_user_in_org(
            db=db_session,
            admin_user_id=test_member_user.id,
            username="unauthorized",
            email="unauthorized@example.com",
            role="member",
            initial_password="temp123"
        )


@pytest.mark.asyncio
async def test_default_organization_returns_org_id(db_session):
    """Test _create_default_organization returns org.id."""
    tenant_key = "test_tenant_123"
    org_name = "Default Workspace"

    # Create default org
    org_id = await AuthService._create_default_organization(
        db=db_session,
        tenant_key=tenant_key,
        org_name=org_name
    )

    # Assert returns UUID string
    assert org_id is not None
    assert isinstance(org_id, str)
    assert len(org_id) == 36

    # Verify org exists
    org = await db_session.get(Organization, org_id)
    assert org.name == org_name
    assert org.tenant_key == tenant_key
```

**Run Tests (should FAIL):**
```powershell
pytest tests/services/test_authservice_org_integration.py -v
```

---

### 🟢 GREEN PHASE: Make Tests Pass

**1. Modify AuthService - Return org_id from _create_default_organization**

Edit: `api/services/auth_service.py`

```python
@staticmethod
async def _create_default_organization(
    db: AsyncSession,
    tenant_key: str,
    org_name: str = "My Organization"
) -> str:
    """
    Create default organization for new tenant.

    Args:
        db: Database session
        tenant_key: Tenant key
        org_name: Organization name (default: "My Organization")

    Returns:
        str: Organization UUID

    Handover 0424g: Now returns org.id for use in user creation
    """
    from src.giljo_mcp.models import Organization
    import secrets

    # Generate unique slug
    slug_base = org_name.lower().replace(" ", "-")
    slug_suffix = secrets.token_hex(3)
    slug = f"{slug_base}-{slug_suffix}"

    # Create organization
    org = Organization(
        name=org_name,
        slug=slug,
        tenant_key=tenant_key,
        is_active=True,
        settings={}
    )
    db.add(org)
    await db.flush()  # Get org.id

    return str(org.id)
```

**2. Modify AuthService - Update _create_first_admin_impl**

Edit: `api/services/auth_service.py`

```python
@staticmethod
async def _create_first_admin_impl(
    db: AsyncSession,
    username: str,
    password: str,
    email: str,
    org_name: str = "My Organization"
) -> User:
    """
    Create first admin user with organization (fresh install flow).

    Flow:
    1. Create organization FIRST
    2. Create user WITH org_id set
    3. Create owner membership

    Args:
        db: Database session
        username: Admin username
        password: Admin password
        email: Admin email
        org_name: Workspace name (default: "My Organization")

    Returns:
        User: Created admin user with org_id set

    Handover 0424g: Org-first flow - creates org before user
    """
    from src.giljo_mcp.models import User, OrgMembership
    import secrets

    # Generate tenant key
    tenant_key = secrets.token_hex(16)

    # Step 1: Create organization FIRST
    org_id = await AuthService._create_default_organization(
        db=db,
        tenant_key=tenant_key,
        org_name=org_name
    )

    # Step 2: Create user WITH org_id
    user = User(
        username=username,
        email=email,
        password_hash=AuthService._hash_password(password),
        tenant_key=tenant_key,
        role="admin",
        is_active=True,
        org_id=org_id,  # Set org_id directly
        must_change_password=False,
        must_set_pin=True
    )
    db.add(user)
    await db.flush()

    # Step 3: Create owner membership (for role tracking)
    membership = OrgMembership(
        org_id=org_id,
        user_id=user.id,
        role="owner",
        is_active=True,
        tenant_key=tenant_key,
        invited_by=None  # Self-created
    )
    db.add(membership)
    await db.commit()

    return user
```

**3. Modify AuthService - Update _register_user_impl**

Edit: `api/services/auth_service.py`

```python
@staticmethod
async def _register_user_impl(
    db: AsyncSession,
    username: str,
    password: str,
    email: str,
    tenant_key: str,
    org_id: str = None,
    org_role: str = "member"
) -> User:
    """
    Register new user with optional org assignment.

    Args:
        db: Database session
        username: Username
        password: Password
        email: Email
        tenant_key: Tenant key
        org_id: Organization UUID (optional)
        org_role: Role in org (default: "member")

    Returns:
        User: Created user with org_id set (if provided)

    Handover 0424g: Accepts org_id parameter and sets on user
    """
    from src.giljo_mcp.models import User, OrgMembership

    # Create user with org_id
    user = User(
        username=username,
        email=email,
        password_hash=AuthService._hash_password(password),
        tenant_key=tenant_key,
        role="developer",
        is_active=True,
        org_id=org_id,  # Set org_id if provided
        must_change_password=True,
        must_set_pin=True
    )
    db.add(user)
    await db.flush()

    # Create membership if org_id provided
    if org_id:
        membership = OrgMembership(
            org_id=org_id,
            user_id=user.id,
            role=org_role,
            is_active=True,
            tenant_key=tenant_key,
            invited_by=None
        )
        db.add(membership)

    await db.commit()
    return user
```

**4. Add AuthService.create_user_in_org Method**

Edit: `api/services/auth_service.py`

```python
@staticmethod
async def create_user_in_org(
    db: AsyncSession,
    admin_user_id: str,
    username: str,
    email: str,
    role: str,
    initial_password: str
) -> User:
    """
    Admin creates new user in their organization.

    Args:
        db: Database session
        admin_user_id: ID of admin creating the user
        username: New user's username
        email: New user's email
        role: New user's role (owner/admin/member/viewer)
        initial_password: Temporary password

    Returns:
        User: Created user with org_id set to admin's org

    Raises:
        PermissionDeniedError: If admin_user is not admin/owner
        UserExistsError: If username/email already exists

    Handover 0424g: Admin user creation with org_id inheritance
    """
    from src.giljo_mcp.models import User, OrgMembership
    from sqlalchemy import select
    from api.exceptions import PermissionDeniedError, UserExistsError

    # Load admin user with org and membership
    stmt = (
        select(User)
        .options(selectinload(User.org_memberships))
        .where(User.id == admin_user_id)
    )
    result = await db.execute(stmt)
    admin_user = result.scalar_one_or_none()

    if not admin_user:
        raise PermissionDeniedError("Admin user not found")

    # Verify admin has org
    if not admin_user.org_id:
        raise PermissionDeniedError("Admin user has no organization")

    # Verify admin has admin/owner role
    admin_membership = admin_user.org_memberships[0]
    if admin_membership.role not in ["owner", "admin"]:
        raise PermissionDeniedError("Only admins and owners can create users")

    # Check username/email not taken
    existing = await db.execute(
        select(User).where(
            (User.username == username) | (User.email == email)
        )
    )
    if existing.scalar_one_or_none():
        raise UserExistsError("Username or email already exists")

    # Create user in admin's org
    new_user = await AuthService._register_user_impl(
        db=db,
        username=username,
        password=initial_password,
        email=email,
        tenant_key=admin_user.tenant_key,
        org_id=admin_user.org_id,  # Inherit admin's org_id
        org_role=role
    )

    return new_user
```

**Run Tests (should PASS):**
```powershell
pytest tests/services/test_authservice_org_integration.py -v
```

---

### 🔵 REFACTOR PHASE: Optimize & Document

**1. Add Comprehensive Docstrings**

Update all modified methods with detailed docstrings explaining the org-first flow.

**2. Add Integration Test**

Create: `tests/integration/test_auth_org_flow.py`

```python
"""
Integration test for auth org-first flow.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from src.giljo_mcp.models import User, Organization, OrgMembership


@pytest.mark.asyncio
async def test_fresh_install_creates_org_first(client: AsyncClient, db_session):
    """Test fresh install creates org → admin user → membership."""
    # Simulate fresh install
    response = await client.post(
        "/api/auth/first-login",
        json={
            "username": "admin",
            "password": "GiljoMCP",
            "email": "admin@example.com",
            "workspace_name": "Test Workspace"
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Load user
    user = await db_session.get(User, data["user"]["id"])

    # Assert org_id is set
    assert user.org_id is not None

    # Load org
    org = await db_session.get(Organization, user.org_id)
    assert org.name == "Test Workspace"

    # Load membership
    stmt = select(OrgMembership).where(OrgMembership.user_id == user.id)
    result = await db_session.execute(stmt)
    membership = result.scalar_one()

    assert membership.role == "owner"


@pytest.mark.asyncio
async def test_admin_creates_user_in_org(client: AsyncClient, db_session, test_admin_user, auth_headers):
    """Test admin can create user in their org."""
    response = await client.post(
        "/api/users",
        headers=auth_headers,
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "role": "member",
            "initial_password": "temp123"
        }
    )

    assert response.status_code == 201
    data = response.json()

    # Load new user
    new_user = await db_session.get(User, data["id"])

    # Assert new user has same org_id as admin
    assert new_user.org_id == test_admin_user.org_id
```

**Run All Tests:**
```powershell
pytest tests/services/test_authservice_org_integration.py tests/integration/test_auth_org_flow.py -v --cov=api/services/auth_service --cov-report=term-missing
```

---

## Success Criteria

**Service Layer:**
- ✅ `_create_default_organization()` returns org.id
- ✅ `_create_first_admin_impl()` creates org FIRST, then user with org_id
- ✅ `_register_user_impl()` accepts org_id parameter
- ✅ `create_user_in_org()` allows admins to create users
- ✅ All 5 service tests pass

**Integration:**
- ✅ Fresh install flow creates org → user → membership
- ✅ Admin can create users in their org
- ✅ New users inherit admin's org_id
- ✅ Non-admins cannot create users

**Test Coverage:**
- ✅ >80% coverage on modified AuthService methods
- ✅ All edge cases tested (no org, permission denied, etc.)

---

## Chain Execution Instructions

**CRITICAL: This handover is part of the 0424 chain. You MUST update chain_log.json.**

### Step 1: Read Chain Context

```powershell
cat prompts/0424_chain/chain_log.json
```

Verify 0424f is complete.

### Step 2: Mark Session In Progress

Update `prompts/0424_chain/chain_log.json`:

```json
{
  "sessions": [
    {
      "session_id": "0424g",
      "title": "AuthService Update",
      "color": "#2196F3",
      "status": "in_progress",
      "started_at": "2026-01-31T<current-time>",
      "completed_at": null,
      "planned_tasks": [
        "Modify _create_default_organization to return org_id",
        "Update _create_first_admin_impl for org-first flow",
        "Update _register_user_impl to accept org_id",
        "Add create_user_in_org method",
        "Write 5 service tests - all passing"
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
  agent: 'tdd-implementor',
  instruction: 'Implement AuthService org integration per 0424g GREEN phase. Modify _create_default_organization, _create_first_admin_impl, _register_user_impl, and add create_user_in_org. Run tests until green.'
})

Task.create({
  agent: 'backend-integration-tester',
  instruction: 'Write integration tests per 0424g REFACTOR phase. Test fresh install flow and admin user creation. Verify org_id inheritance works correctly.'
})
```

### Step 4: Update Chain Log

After all tests pass:

```json
{
  "sessions": [
    {
      "session_id": "0424g",
      "title": "AuthService Update",
      "color": "#2196F3",
      "status": "complete",
      "started_at": "2026-01-31T<start-time>",
      "completed_at": "2026-01-31T<end-time>",
      "planned_tasks": [
        "Modify _create_default_organization to return org_id",
        "Update _create_first_admin_impl for org-first flow",
        "Update _register_user_impl to accept org_id",
        "Add create_user_in_org method",
        "Write 5 service tests - all passing"
      ],
      "tasks_completed": [
        "Modified _create_default_organization to return org.id",
        "Updated _create_first_admin_impl: org → user → membership flow",
        "Updated _register_user_impl to accept and set org_id",
        "Added create_user_in_org method for admin user creation",
        "Wrote 5 service tests - all passing",
        "Added 2 integration tests for fresh install and admin creation"
      ],
      "deviations": [],
      "blockers_encountered": [],
      "notes_for_next": "AuthService now sets org_id during user creation. API endpoints need to pass org_name to first-login (0424h). Welcome screen needs 'Workspace Name' field (0424h).",
      "summary": "Successfully implemented org-first auth flow. Fresh install creates org before user, new users get org_id at creation. All 7 tests passing."
    }
  ]
}
```

### Step 5: Commit Your Work

```powershell
git add .
git commit -m "feat(0424g): Implement org-first auth flow in AuthService

- Modify _create_default_organization to return org.id
- Update _create_first_admin_impl: org → user → membership flow
- Update _register_user_impl to accept org_id parameter
- Add create_user_in_org for admin creating users
- Add 5 service tests + 2 integration tests
- All tests passing (7/7)

Handover: 0424g
Chain: 0424 Organization Hierarchy
Tests: 7/7 passing
Coverage: >85% on AuthService

BREAKING: _create_first_admin_impl now requires org_name parameter.
Fresh install flow creates organization before admin user."
```

### Step 6: Spawn Next Terminal

**⚠️ WARNING: Check for duplicate terminals before spawning!**

```powershell
# Check for existing 0424h terminal
Get-Process powershell | Select-Object MainWindowTitle | Select-String "0424h"
```

If NOT spawned yet:

```powershell
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd F:\GiljoAI_MCP; Write-Host 'Handover 0424h: API Layer + Welcome Screen' -ForegroundColor Cyan; Write-Host 'Spawned from: 0424g (AuthService Update)' -ForegroundColor Gray; Write-Host ''; cat handovers/0424h_api_welcome_screen.md"
```

---

## Critical Subagent Instructions

**YOU MUST USE THE TASK TOOL TO SPAWN SUBAGENTS.**

```javascript
Task.create({
  agent: 'tdd-implementor',
  instruction: `Implement AuthService org integration per handover 0424g:

1. Modify api/services/auth_service.py:
   - _create_default_organization: return org.id
   - _create_first_admin_impl: org → user → membership
   - _register_user_impl: accept org_id, set on user
   - create_user_in_org: admin creates users

2. Run tests:
   pytest tests/services/test_authservice_org_integration.py -v

Follow RED → GREEN → REFACTOR from handover.`
})
```

---

## Dependencies

**Requires:**
- User.org_id column (0424f)
- User.organization relationship (0424f)
- OrgService (0424b)

**Provides:**
- Org-first auth flow (for 0424h API updates)
- Admin user creation (for 0424h frontend)
- org_id set at user creation (foundation for 0424i)

---

## Notes

**Design Decisions:**
- Org created FIRST ensures user always has org_id at creation
- OrgMembership still created for role tracking (owner/admin/member/viewer)
- Admin inheritance: new users get admin's org_id automatically
- Permission check: only admin/owner can create users

**Testing Strategy:**
- Service tests verify methods set org_id correctly
- Integration tests verify full flow from API to database
- Permission tests verify role enforcement

**Future Work (0424h):**
- API endpoints must pass org_name to first-login
- Welcome screen needs "Workspace Name" field
- User creation endpoint uses create_user_in_org

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0424_chain/chain_log.json` and check 0424f status is "complete".

### Step 2: Mark Session Started
Update your session entry: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Complete all implementation phases above using Task tool subagents.

### Step 4: Commit Your Work
```bash
git add -A && git commit -m "feat(0424g): Update AuthService for org-first user creation flow

- Modify _create_default_organization() to return org.id
- Update _create_first_admin_impl() to create org FIRST
- Update _register_user_impl() to accept and set org_id
- Add create_user_in_org() method for admin user creation

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

### Step 5: Update Chain Log
Update `prompts/0424_chain/chain_log.json`:
- Set your session status to "complete"
- Fill in tasks_completed, deviations, blockers_encountered
- Add notes_for_next for 0424h
- Add summary

### Step 6: Spawn Next Terminal

**CRITICAL: DO NOT SPAWN DUPLICATE TERMINALS!**
- Only ONE agent should spawn the next terminal
- If your subagent already spawned it, DO NOT spawn again
- Check if terminal 0424h is already running before executing

**Use Bash tool to EXECUTE this command:**
```powershell
powershell.exe -Command "Start-Process wt -ArgumentList '--title \"0424h - API + Welcome Screen\" --tabColor \"#9C27B0\" -d \"F:\GiljoAI_MCP\" cmd /k claude --dangerously-skip-permissions \"Execute handover 0424h. READ: F:\GiljoAI_MCP\handovers\0424h_api_welcome_screen.md - Update API and welcome screen. Use Task subagents. Check chain_log.json. When complete: commit, update chain_log, spawn 0424i.\"' -Verb RunAs"
```

---

**Next Handover:** 0424h (API Layer + Welcome Screen)
