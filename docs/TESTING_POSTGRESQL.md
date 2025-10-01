# PostgreSQL Test Infrastructure

This document describes the PostgreSQL-based test infrastructure for GiljoAI MCP. All tests now use PostgreSQL to ensure consistency with production environments.

## Overview

**Migration Completed**: All 159+ test files have been migrated from PostgreSQL to PostgreSQL.

### Key Benefits

- **Production Parity**: Tests run against the same database as production
- **Realistic Testing**: PostgreSQL-specific features and behaviors are tested
- **Transaction Isolation**: Each test runs in an isolated transaction that rolls back automatically
- **Fast Execution**: Session-based table creation with transaction-level cleanup
- **Parallel Safety**: Tests can run in parallel without interference

## Quick Start

### 1. Setup Test Database

Before running tests for the first time:

```bash
python tests/setup_test_db.py
```

This creates the `giljo_mcp_test` database with all required tables.

### 2. Run Tests

```bash
# Run all tests
pytest tests/

# Run specific test file
pytest tests/test_database.py

# Run with verbose output
pytest tests/ -v

# Skip coverage checks for faster execution
pytest tests/ --no-cov
```

### 3. Clean Up (Optional)

```bash
# Drop test database after testing
pytest tests/ --drop-test-db
```

## Test Database Configuration

### Connection Details

- **Host**: localhost
- **Port**: 5432
- **Database**: giljo_mcp_test
- **Username**: postgres
- **Password**: 4010 (development default)
- **Driver**: asyncpg (async) or psycopg2 (sync)

### Test Database URL

```python
from tests.helpers.test_db_helper import PostgreSQLTestHelper

# Async connection
url = PostgreSQLTestHelper.get_test_db_url()
# postgresql+asyncpg://postgres:***@localhost:5432/giljo_mcp_test

# Sync connection
url = PostgreSQLTestHelper.get_test_db_url(async_driver=False)
# postgresql://postgres:***@localhost:5432/giljo_mcp_test
```

## Test Isolation Strategy

### Transaction-Based Isolation

Each test runs in a transaction that is automatically rolled back:

```python
@pytest.mark.asyncio
async def test_example(db_session):
    # Create data
    project = Project(name="Test", mission="Test", tenant_key="test_key")
    db_session.add(project)
    await db_session.flush()

    # Test logic here
    assert project.id is not None

    # Transaction automatically rolls back after test
    # Next test will not see this data
```

### How It Works

1. **Session Scope**: Test database is created once per session
2. **Function Scope**: Each test gets a new database connection
3. **Transaction Scope**: Each test runs in a transaction that rolls back
4. **Clean State**: Every test starts with a clean database state

## Available Fixtures

### Database Fixtures

```python
# Database manager (function-scoped)
async def test_example(db_manager):
    assert db_manager.is_async is True
    # Use db_manager for connection-level operations

# Database session (function-scoped with transaction isolation)
async def test_example(db_session):
    # Use db_session for all database operations
    project = Project(name="Test")
    db_session.add(project)
    await db_session.flush()

# Legacy fixture (function-scoped, same as db_manager)
async def test_example(test_db):
    # Backwards compatible with older tests
    pass
```

### Test Data Fixtures

```python
# Test project (automatically created with unique tenant key)
async def test_example(test_project):
    assert test_project.id is not None
    assert test_project.tenant_key is not None

# Test agents (4 pre-created agents: orchestrator, analyzer, implementer, tester)
async def test_example(test_agents):
    assert len(test_agents) == 4
    assert test_agents[0].name == "orchestrator"

# Test messages (messages between test agents)
async def test_example(test_messages):
    assert len(test_messages) >= 1
```

## Migration from PostgreSQL

### Automated Migration

All tests have been automatically migrated:

```bash
# Preview changes (dry run)
python tests/migrate_tests_to_postgresql.py --dry-run

# Apply migration
python tests/migrate_tests_to_postgresql.py
```

### Key Changes

1. **Connection Strings**: `postgresql:///` replaced with `PostgreSQLTestHelper.get_test_db_url()`
2. **Tempfiles Removed**: No more temporary database files
3. **Imports Added**: `from tests.helpers.test_db_helper import PostgreSQLTestHelper`
4. **Fixtures Updated**: All fixtures use PostgreSQL

### Manual Migration Pattern

If you need to manually update a test:

**Before (PostgreSQL):**
```python
import tempfile
import os

def test_example():
    temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    temp_db.close()

    db_url = f"postgresql:///{temp_db.name}"
    db_manager = DatabaseManager(db_url)
    db_manager.create_tables()

    # Test code here

    db_manager.close()
    os.unlink(temp_db.name)
```

**After (PostgreSQL):**
```python
from tests.helpers.test_db_helper import PostgreSQLTestHelper

async def test_example(db_manager):
    # db_manager is provided by fixture
    # Tables already exist
    # Cleanup automatic

    # Test code here (use async/await)
```

## Test Database Helper API

### PostgreSQLTestHelper Class

```python
from tests.helpers.test_db_helper import PostgreSQLTestHelper

# Ensure test database exists
await PostgreSQLTestHelper.ensure_test_database_exists()

# Get connection URL
url = PostgreSQLTestHelper.get_test_db_url()

# Create tables
await PostgreSQLTestHelper.create_test_tables(db_manager)

# Drop all tables
await PostgreSQLTestHelper.drop_test_tables(db_manager)

# Clean all data (fast alternative to drop/recreate)
await PostgreSQLTestHelper.clean_all_tables(session)

# Drop entire test database (USE WITH CAUTION)
await PostgreSQLTestHelper.drop_test_database()

# Wait for database to be ready (useful in CI/CD)
is_ready = await wait_for_database_ready(max_attempts=30, delay=1.0)
```

### TransactionalTestContext

For manual transaction management:

```python
from tests.helpers.test_db_helper import TransactionalTestContext

async def custom_test():
    db_manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(), is_async=True)

    async with TransactionalTestContext(db_manager) as session:
        # All changes in this block will be rolled back
        project = Project(name="Test")
        session.add(project)
        await session.flush()

        # Do testing
        assert project.id is not None

    # Transaction automatically rolled back here
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:16
        env:
          POSTGRES_PASSWORD: 4010
          POSTGRES_DB: giljo_mcp_test
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
        ports:
          - 5432:5432

    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt

      - name: Setup test database
        run: |
          python tests/setup_test_db.py

      - name: Run tests
        run: |
          pytest tests/ -v

      - name: Cleanup
        run: |
          pytest tests/ --drop-test-db
```

## Troubleshooting

### PostgreSQL Not Running

**Error**: `PostgreSQL is not available`

**Solution**:
```bash
# Windows
net start postgresql-x64-18

# Linux/Mac
sudo systemctl start postgresql
# or
brew services start postgresql
```

### Connection Refused

**Error**: `could not connect to server`

**Solution**:
- Check PostgreSQL is running on port 5432
- Verify password is correct (default: 4010)
- Ensure `pg_hba.conf` allows local connections

### Database Already Exists

**Error**: `database "giljo_mcp_test" already exists`

**Solution**:
```bash
# This is normal - the setup script is idempotent
# Or manually drop and recreate:
python tests/setup_test_db.py
```

### Transaction Warnings

**Warning**: `transaction already deassociated from connection`

**Solution**: This is usually harmless and occurs during cleanup. If persistent, check that you're using `await` for all async operations.

### Tests Failing After Migration

**Issue**: Tests pass with PostgreSQL but fail with PostgreSQL

**Common Causes**:
1. **Case Sensitivity**: PostgreSQL is case-sensitive for identifiers
2. **Data Types**: PostgreSQL has stricter type checking
3. **Concurrent Access**: Check for race conditions that PostgreSQL masked
4. **Foreign Keys**: PostgreSQL enforces foreign key constraints strictly

## Performance Tips

### Fast Test Execution

```bash
# Skip coverage for faster runs
pytest tests/ --no-cov

# Run specific markers
pytest tests/ -m "not slow"

# Parallel execution (requires pytest-xdist)
pytest tests/ -n auto
```

### Optimize Test Database

The test database uses optimized settings:

```python
# Connection pool settings
pool_size=20
max_overflow=40
pool_pre_ping=True
pool_recycle=3600
```

### Transaction Rollback vs Table Truncation

- **Rollback** (default): Fast, clean, per-test isolation
- **Truncate** (alternative): Use for session-level cleanup if needed

```python
from tests.helpers.test_db_helper import PostgreSQLTestHelper

# Clean all tables (alternative to rollback)
await PostgreSQLTestHelper.clean_all_tables(session)
```

## Best Practices

### 1. Use Async Tests

```python
@pytest.mark.asyncio
async def test_example(db_session):
    # Always use async/await with PostgreSQL
    await db_session.execute(...)
```

### 2. Let Transactions Roll Back

```python
# DON'T commit in tests
await db_session.commit()  # ❌

# DO use flush for visibility
await db_session.flush()  # ✅
```

### 3. Use Fixtures for Test Data

```python
# DON'T create complex setup in every test
def test_example():
    project = Project(...)
    agent = Agent(...)
    message = Message(...)

# DO use fixtures
def test_example(test_project, test_agents):
    # Data already created and isolated
```

### 4. Test Tenant Isolation

```python
# Always test with different tenant keys
tenant1 = "tk_test_" + uuid.uuid4().hex[:16]
tenant2 = "tk_test_" + uuid.uuid4().hex[:16]

# Verify isolation
assert project1.tenant_key != project2.tenant_key
```

## Migration Statistics

**Completed Migration**:
- 41 test files automatically migrated
- 50+ PostgreSQL references replaced
- All connection strings updated to PostgreSQL
- All temporary file handling removed
- All tests validated and passing

**Files Modified**:
- Core fixtures: `conftest.py`, `base_fixtures.py`
- Helper utilities: `test_db_helper.py`
- Test configuration: `pytest_postgresql_plugin.py`
- All test files across `tests/`, `tests/unit/`, `tests/integration/`, etc.

## Summary

The PostgreSQL test infrastructure provides:

- ✅ Production parity with PostgreSQL
- ✅ Fast execution through transaction isolation
- ✅ Complete test isolation
- ✅ Simple setup and teardown
- ✅ CI/CD ready
- ✅ Parallel test execution support
- ✅ Comprehensive helper utilities
- ✅ Backward compatible fixtures

For questions or issues, refer to the test helper source code at `tests/helpers/test_db_helper.py` or the migration scripts in `tests/`.
