# Test Fixtures for E2E Closeout Workflow

This directory contains test fixtures for E2E closeout workflow testing.

## E2E Closeout Fixtures

The `e2e_closeout_fixtures.py` module provides comprehensive test data for testing the closeout workflow end-to-end.

### What Gets Created

The fixture creates:

1. **Test User**
   - Email: `test@example.com`
   - Password: `testpassword`
   - Username: `testuser`
   - Role: `developer`
   - Status: Active

2. **Test Product**
   - Name: "Test Product"
   - Status: Active
   - Product memory initialized (GitHub integration, sequential history, context)

3. **Test Project**
   - Name: "Mock Project"
   - Description: "E2E test project for closeout workflow"
   - Status: `active`
   - Linked to test product

4. **Test Agents** (3 agents)
   - Agent 1: Orchestrator (completed, 100% progress)
   - Agent 2: Implementer (completed, 100% progress)
   - Agent 3: Tester (completed, 100% progress)

All data is **multi-tenant isolated** using a unique `tenant_key` generated for each test run.

### Usage in Tests

#### Pytest Fixture Usage

```python
import pytest

@pytest.mark.asyncio
async def test_closeout_workflow(e2e_closeout_fixtures):
    """Test closeout workflow with E2E fixtures."""
    fixtures = e2e_closeout_fixtures

    # Access fixtures
    user = fixtures["user"]
    product = fixtures["product"]
    project = fixtures["project"]
    agents = fixtures["agents"]
    tenant_key = fixtures["tenant_key"]

    # Use in your test
    assert user.email == "test@example.com"
    assert project.status == "active"
    assert len(agents) == 3
```

#### Standalone Script Usage

You can also run the fixture creator as a standalone script to populate the database:

```bash
# Create fixtures
python tests/fixtures/e2e_closeout_fixtures.py

# Output:
# === E2E Closeout Workflow Fixtures ===
# Creating test data for E2E closeout workflow testing...
#
# [OK] Created test user: test@example.com
#   - Username: testuser
#   - Password: testpassword
#   - Tenant: tk_xxxxx...
#   - Role: developer
# ...
```

### Fixture Properties

#### Test User Properties

```python
user = fixtures["user"]

user.email          # "test@example.com"
user.username       # "testuser"
user.password_hash  # Bcrypt hash of "testpassword"
user.role           # "developer"
user.is_active      # True
user.tenant_key     # Generated tenant key
```

#### Test Product Properties

```python
product = fixtures["product"]

product.name        # "Test Product"
product.is_active   # True
product.tenant_key  # Same as user tenant_key
product.config_data # {"test_mode": True, "e2e_fixture": True}
```

#### Test Project Properties

```python
project = fixtures["project"]

project.name            # "Mock Project"
project.status          # "active"
project.tenant_key      # Same as user tenant_key
project.product_id      # References test product
project.context_budget  # 150000
project.context_used    # 0
```

#### Test Agents Properties

```python
agents = fixtures["agents"]  # List of 3 MCPAgentJob instances

for agent in agents:
    agent.status         # "complete"
    agent.progress       # 100
    agent.tenant_key     # Same as user tenant_key
    agent.project_id     # References test project
    agent.health_status  # "healthy"
    agent.tool_type      # "claude-code"
```

### Multi-Tenant Isolation

All fixtures are created with a unique `tenant_key` to ensure:

- **Test isolation**: Each test run gets its own tenant namespace
- **No cross-tenant data leakage**: Data is properly filtered by tenant
- **Parallel test execution**: Multiple tests can run simultaneously without conflicts

```python
@pytest.mark.asyncio
async def test_tenant_isolation(e2e_closeout_fixtures, db_session):
    from sqlalchemy import select
    from src.giljo_mcp.models import Project

    tenant_key = e2e_closeout_fixtures["tenant_key"]

    # Query should only return projects for this tenant
    stmt = select(Project).where(Project.tenant_key == tenant_key)
    result = await db_session.execute(stmt)
    projects = result.scalars().all()

    # All projects belong to this tenant
    assert all(p.tenant_key == tenant_key for p in projects)
```

### Fixture Idempotency

The fixture creator is **idempotent**:

- **Test user**: Reuses existing user if found, updates tenant_key and password
- **Test product**: Creates new product for each test run
- **Test project**: Creates new project for each test run
- **Test agents**: Creates new agents for each test run

This ensures:
- Fast test execution (no duplicate user creation)
- Clean state for each test (new project/agents)
- Consistent test data (password always matches expected value)

### Database Verification

After running the fixture script, you can verify data in the database:

```bash
# Verify test user
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT email, username, tenant_key, role FROM users WHERE email = 'test@example.com';"

# Verify test project
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT name, status FROM projects WHERE name = 'Mock Project';"

# Verify test agents
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -d giljo_mcp -c \
  "SELECT agent_name, agent_type, status, progress FROM mcp_agent_jobs \
   WHERE project_id IN (SELECT id FROM projects WHERE name = 'Mock Project');"
```

### Cleanup

The fixture provides a cleanup method (optional):

```python
from tests.fixtures.e2e_closeout_fixtures import E2ECloseoutFixtures

async def cleanup_test_data(db_manager, tenant_key):
    """Clean up test fixtures for a specific tenant."""
    fixture_creator = E2ECloseoutFixtures(db_manager)

    async with db_manager.get_session_async() as session:
        await fixture_creator.cleanup_fixtures(session, tenant_key)
```

**Note**: Cleanup is usually not necessary because:
- Tests use transaction rollback for isolation
- Each test run gets a new tenant_key
- Old test data doesn't interfere with new tests

### Integration with E2E Tests

Use these fixtures in your E2E tests for the closeout workflow:

```python
@pytest.mark.asyncio
async def test_closeout_workflow_e2e(e2e_closeout_fixtures):
    """
    E2E test for project closeout workflow.

    Prerequisites:
    - Backend API running on port 7272
    - PostgreSQL database running
    - Frontend dev server running on port 7274
    """
    fixtures = e2e_closeout_fixtures

    # Test user can login
    # (use fixtures["user"].email and "testpassword")

    # Navigate to project
    # (use fixtures["project"].name)

    # Verify agents are completed
    # (use fixtures["agents"])

    # Execute closeout workflow
    # ...
```

### Troubleshooting

#### Issue: User password doesn't match

**Symptom**: Login fails with `test@example.com` / `testpassword`

**Cause**: User was created manually with a different password

**Solution**: Delete user and run fixture script again:

```sql
DELETE FROM users WHERE email = 'test@example.com';
```

Or let the fixture update the password automatically (it does this by default).

#### Issue: No agents found

**Symptom**: Test expects 3 agents but finds 0

**Cause**: Agents belong to a different tenant or project

**Solution**: Verify tenant_key matches:

```sql
SELECT tenant_key, project_id, COUNT(*)
FROM mcp_agent_jobs
WHERE status = 'complete'
GROUP BY tenant_key, project_id;
```

#### Issue: Project not active

**Symptom**: Test expects active project but finds inactive

**Cause**: Project status was changed manually or by another test

**Solution**: Run fixture script to recreate project:

```bash
python tests/fixtures/e2e_closeout_fixtures.py
```

### Related Documentation

- **E2E Test Analysis**: `/f/GiljoAI_MCP/E2E_TEST_ANALYSIS_REPORT.md`
- **E2E Test Fixes**: `/f/GiljoAI_MCP/E2E_TEST_FIXES_REQUIRED.md`
- **Handover Report**: `/f/GiljoAI_MCP/HANDOVER_0249c_E2E_TESTING_REPORT.md`
- **Base Fixtures**: `tests/fixtures/base_fixtures.py`
- **Test Helpers**: `tests/helpers/test_db_helper.py`

### Examples

See `tests/integration/test_e2e_closeout_fixtures.py` for complete examples of:
- Basic fixture usage
- Multi-tenant isolation testing
- Idempotency testing
- Database verification

---

**Created**: November 26, 2025
**Author**: Backend Integration Tester Agent
**Purpose**: E2E closeout workflow testing support
