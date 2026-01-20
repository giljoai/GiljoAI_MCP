# Handover 0019: Agent Job Management System - Testing Guide for Developers

**Version**: 1.0
**Date**: 2025-10-19
**Status**: Complete

## Table of Contents

1. [Overview](#overview)
2. [Running Tests](#running-tests)
3. [Test Organization](#test-organization)
4. [Adding New Tests](#adding-new-tests)
5. [Debugging Tests](#debugging-tests)
6. [Test Coverage](#test-coverage)
7. [CI/CD Integration](#cicd-integration)

## Overview

This guide provides comprehensive information for developers working with the Agent Job Management System test suite. The system includes:

- **Unit Tests**: `tests/test_agent_job_manager.py` (AgentJobManager, AgentCommunicationQueue, JobCoordinator)
- **API Tests**: `tests/test_agent_jobs_api.py` (13 REST endpoints)
- **Integration Tests**: `tests/integration/test_agent_job_websocket_events.py` (WebSocket events)

### Test Coverage Goals

- **Unit Tests**: 100% coverage for manager classes
- **API Tests**: All 13 endpoints tested with success/error scenarios
- **Integration Tests**: End-to-end workflows with WebSocket validation
- **Multi-Tenant Isolation**: Comprehensive cross-tenant access tests

## Running Tests

### Prerequisites

```bash
# PostgreSQL 18 running
psql -U postgres -l

# Python 3.11+ with test dependencies
pip install -r requirements.txt
pip install pytest pytest-asyncio pytest-cov httpx websockets
```

### Test Database Setup

Tests use a separate test database to avoid polluting production data:

```python
# tests/helpers/test_db_helper.py
class PostgreSQLTestHelper:
    @staticmethod
    def get_test_db_url(async_driver=True):
        """Get test database URL."""
        driver = "postgresql+asyncpg" if async_driver else "postgresql+psycopg2"
        return f"{driver}://postgres:***@localhost:5432/giljo_mcp_test"
```

Create the test database:

```bash
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"
```

### Run All Tests

```bash
# Run all tests
pytest tests/

# Run with verbose output
pytest tests/ -v

# Run with coverage report
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Run with output capturing disabled (see print statements)
pytest tests/ -s
```

### Run Specific Test Categories

```bash
# Unit tests only
pytest tests/test_agent_job_manager.py -v

# API tests only
pytest tests/test_agent_jobs_api.py -v

# Integration tests only
pytest tests/integration/test_agent_job_websocket_events.py -v
```

### Run Specific Test Classes or Functions

```bash
# Run specific test class
pytest tests/test_agent_job_manager.py::TestAgentJobManagerCreation -v

# Run specific test function
pytest tests/test_agent_job_manager.py::TestAgentJobManagerCreation::test_create_job_with_all_parameters -v

# Run tests matching pattern
pytest tests/ -k "create_job" -v
pytest tests/ -k "multi_tenant" -v
pytest tests/ -k "websocket" -v
```

### Run Tests with Markers

```bash
# Run only fast tests
pytest tests/ -m "not slow"

# Run only integration tests
pytest tests/ -m integration

# Run only API tests
pytest tests/ -m api
```

## Test Organization

### Directory Structure

```
tests/
├── helpers/
│   └── test_db_helper.py           # Test database utilities
├── integration/
│   └── test_agent_job_websocket_events.py  # WebSocket integration tests
├── test_agent_job_manager.py       # AgentJobManager unit tests
└── test_agent_jobs_api.py          # API endpoint tests
```

### Test File Organization

Each test file follows this structure:

```python
"""
Module docstring explaining what is tested.
"""

import sys
from pathlib import Path
import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Imports
from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.models import MCPAgentJob

# Fixtures
@pytest.fixture
def db_manager():
    """Create database manager for testing."""
    pass

# Test classes organized by feature
class TestJobCreation:
    """Tests for job creation operations."""

    def test_create_job_with_all_parameters(self):
        """Test creating a job with all parameters."""
        pass

class TestJobStatusTransitions:
    """Tests for job status transitions."""

    def test_acknowledge_job(self):
        """Test acknowledging a job."""
        pass
```

### Test Categories

#### 1. Unit Tests - AgentJobManager

**File**: `tests/test_agent_job_manager.py`

**Test Classes**:
- `TestAgentJobManagerCreation` - Job creation operations
- `TestAgentJobManagerStatusTransitions` - Status lifecycle (pending → active → completed)
- `TestAgentJobManagerRetrieval` - Job queries and filtering
- `TestAgentJobManagerMultiTenant` - Tenant isolation verification
- `TestAgentJobManagerHierarchy` - Parent-child relationships
- `TestAgentJobManagerValidation` - Input validation and error handling

**Key Tests**:
```python
def test_create_job_with_all_parameters()
def test_create_job_batch()
def test_acknowledge_job()
def test_complete_job()
def test_fail_job()
def test_invalid_status_transition()
def test_get_pending_jobs()
def test_get_job_hierarchy()
def test_multi_tenant_isolation()
```

#### 2. API Tests - REST Endpoints

**File**: `tests/test_agent_jobs_api.py`

**Test Classes**:
- `TestJobCRUD` - Create, Read, Update, Delete operations
- `TestJobStatusManagement` - Status transition endpoints
- `TestJobCommunication` - Message endpoints
- `TestJobCoordination` - Hierarchy and spawning
- `TestJobPermissions` - Role-based access control
- `TestJobMultiTenant` - Cross-tenant isolation

**Endpoints Tested** (13 total):
```
POST   /api/agent-jobs                          # Create job
GET    /api/agent-jobs                          # List jobs
GET    /api/agent-jobs/{job_id}                 # Get job
PATCH  /api/agent-jobs/{job_id}                 # Update job
DELETE /api/agent-jobs/{job_id}                 # Delete job (admin only)
POST   /api/agent-jobs/{job_id}/acknowledge     # Acknowledge job
POST   /api/agent-jobs/{job_id}/complete        # Complete job
POST   /api/agent-jobs/{job_id}/fail            # Fail job
POST   /api/agent-jobs/{job_id}/messages        # Send message
GET    /api/agent-jobs/{job_id}/messages        # Get messages
POST   /api/agent-jobs/{job_id}/messages/{id}/acknowledge  # Ack message
POST   /api/agent-jobs/{job_id}/spawn-children  # Spawn children
GET    /api/agent-jobs/{job_id}/hierarchy       # Get hierarchy
```

#### 3. Integration Tests - WebSocket Events

**File**: `tests/integration/test_agent_job_websocket_events.py`

**Test Classes**:
- `TestWebSocketJobEvents` - Real-time event broadcasting
- `TestWebSocketMultiTenant` - Tenant-scoped event delivery

**Events Tested**:
```
agent_job:created      # Job creation event
agent_job:acknowledged # Job acknowledgment event
agent_job:completed    # Job completion event
agent_job:failed       # Job failure event
```

### Fixtures

#### Database Fixtures

```python
@pytest.fixture
def db_manager():
    """Create synchronous database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    manager.create_tables()
    yield manager
    manager.close()

@pytest.fixture
def db_session(db_manager):
    """Get database session for testing."""
    with db_manager.get_session() as session:
        yield session
```

#### API Client Fixtures

```python
@pytest.fixture
async def async_client():
    """Create async HTTP client for API testing."""
    async with httpx.AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
async def admin_token(async_client, admin_user):
    """Get admin access token."""
    response = await async_client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]
```

#### Test Data Fixtures

```python
@pytest.fixture
def tenant_key():
    """Generate unique tenant key for test isolation."""
    return f"test-tenant-{uuid4()}"

@pytest.fixture
def sample_job(db_manager, tenant_key):
    """Create sample job for testing."""
    manager = AgentJobManager(db_manager)
    return manager.create_job(
        tenant_key=tenant_key,
        agent_type="implementer",
        mission="Test job"
    )
```

## Adding New Tests

### Test Template

Use this template when adding new tests:

```python
def test_feature_name_scenario(self, fixture1, fixture2):
    """
    Test description explaining:
    - What is being tested
    - Expected behavior
    - Edge cases covered
    """
    # ARRANGE - Set up test data
    tenant_key = str(uuid4())
    manager = AgentJobManager(db_manager)

    # ACT - Execute the operation
    result = manager.create_job(
        tenant_key=tenant_key,
        agent_type="implementer",
        mission="Test mission"
    )

    # ASSERT - Verify expectations
    assert result is not None
    assert result.tenant_key == tenant_key
    assert result.status == "pending"
```

### Naming Conventions

**Test Files**: `test_<module_name>.py`
- `test_agent_job_manager.py`
- `test_agent_jobs_api.py`

**Test Classes**: `Test<Feature><Aspect>`
- `TestAgentJobManagerCreation`
- `TestJobStatusManagement`

**Test Functions**: `test_<feature>_<scenario>`
- `test_create_job_with_all_parameters`
- `test_acknowledge_job_already_acknowledged`
- `test_multi_tenant_job_isolation`

### Coverage Requirements

All new code must meet these coverage standards:

- **Unit Tests**: 100% line coverage for manager classes
- **API Tests**: All endpoints with success + error scenarios
- **Integration Tests**: Critical workflows end-to-end

### Example: Adding a New Feature Test

Suppose we add a new feature to cancel jobs. Here's how to add tests:

```python
# tests/test_agent_job_manager.py

class TestAgentJobManagerCancellation:
    """Tests for job cancellation operations."""

    def test_cancel_pending_job(self, db_manager):
        """Test cancelling a pending job."""
        # ARRANGE
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Job to be cancelled"
        )

        # ACT
        cancelled_job = manager.cancel_job(tenant_key, job.job_id)

        # ASSERT
        assert cancelled_job.status == "cancelled"
        assert cancelled_job.completed_at is not None

    def test_cancel_active_job(self, db_manager):
        """Test cancelling an active job."""
        # ARRANGE
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Active job to cancel"
        )
        manager.acknowledge_job(tenant_key, job.job_id)

        # ACT
        cancelled_job = manager.cancel_job(tenant_key, job.job_id)

        # ASSERT
        assert cancelled_job.status == "cancelled"

    def test_cannot_cancel_completed_job(self, db_manager):
        """Test that completed jobs cannot be cancelled."""
        # ARRANGE
        tenant_key = str(uuid4())
        manager = AgentJobManager(db_manager)
        job = manager.create_job(
            tenant_key=tenant_key,
            agent_type="implementer",
            mission="Completed job"
        )
        manager.acknowledge_job(tenant_key, job.job_id)
        manager.complete_job(tenant_key, job.job_id)

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Cannot cancel completed job"):
            manager.cancel_job(tenant_key, job.job_id)

    def test_multi_tenant_cancel_isolation(self, db_manager):
        """Test that users cannot cancel jobs from other tenants."""
        # ARRANGE
        tenant1 = str(uuid4())
        tenant2 = str(uuid4())
        manager = AgentJobManager(db_manager)

        job1 = manager.create_job(
            tenant_key=tenant1,
            agent_type="implementer",
            mission="Tenant 1 job"
        )

        # ACT & ASSERT
        with pytest.raises(ValueError, match="Job .* not found for tenant"):
            manager.cancel_job(tenant2, job1.job_id)
```

```python
# tests/test_agent_jobs_api.py

@pytest.mark.asyncio
async def test_cancel_job_endpoint(async_client, admin_token, sample_job):
    """Test POST /api/agent-jobs/{job_id}/cancel endpoint."""
    # ACT
    response = await async_client.post(
        f"/api/agent-jobs/{sample_job.job_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # ASSERT
    assert response.status_code == 200
    data = response.json()
    assert data["job_id"] == sample_job.job_id
    assert data["status"] == "cancelled"
    assert data["completed_at"] is not None

@pytest.mark.asyncio
async def test_cancel_job_cross_tenant(async_client, admin_token, tenant_key):
    """Test that cancelling a job from another tenant returns 404."""
    # ARRANGE - Create job in different tenant
    other_tenant = str(uuid4())
    manager = AgentJobManager(db_manager)
    job = manager.create_job(
        tenant_key=other_tenant,
        agent_type="implementer",
        mission="Other tenant job"
    )

    # ACT
    response = await async_client.post(
        f"/api/agent-jobs/{job.job_id}/cancel",
        headers={"Authorization": f"Bearer {admin_token}"}
    )

    # ASSERT
    assert response.status_code == 404
    assert "Job not found" in response.json()["detail"]
```

## Debugging Tests

### Common Issues

#### Issue 1: Test Database Connection Error

**Error**: `psycopg2.OperationalError: could not connect to server`

**Solution**:
```bash
# Ensure PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS
sc query postgresql-x64-18  # Windows

# Ensure test database exists
psql -U postgres -c "CREATE DATABASE giljo_mcp_test;"

# Verify connection
psql -U postgres -d giljo_mcp_test -c "SELECT 1;"
```

#### Issue 2: Async Test Not Running

**Error**: `RuntimeError: Event loop is closed`

**Solution**:
```python
# Ensure @pytest.mark.asyncio decorator is present
@pytest.mark.asyncio
async def test_async_operation():
    result = await some_async_function()
    assert result is not None

# Install pytest-asyncio
pip install pytest-asyncio
```

#### Issue 3: Fixture Not Found

**Error**: `fixture 'db_manager' not found`

**Solution**:
```python
# Ensure fixture is defined in same file or conftest.py
# tests/conftest.py
@pytest.fixture
def db_manager():
    """Shared fixture across all tests."""
    pass

# Or define in test file before test class
@pytest.fixture
def db_manager():
    pass

class TestSomething:
    def test_feature(self, db_manager):
        pass
```

#### Issue 4: Test Isolation - Data from Previous Test

**Error**: Test fails because data from previous test exists

**Solution**:
```python
# Use unique tenant_key per test
@pytest.fixture
def tenant_key():
    return f"test-tenant-{uuid4()}"

# Or clean up in fixture teardown
@pytest.fixture
def db_manager():
    manager = DatabaseManager(test_db_url)
    manager.create_tables()
    yield manager
    # Cleanup
    with manager.get_session() as session:
        session.query(MCPAgentJob).delete()
        session.commit()
    manager.close()
```

### Debugging with Print Statements

```bash
# Run tests with output capturing disabled
pytest tests/test_agent_job_manager.py -s

# In your test:
def test_something(self):
    print(f"DEBUG: job_id = {job.job_id}")
    print(f"DEBUG: status = {job.status}")
    assert job.status == "pending"
```

### Debugging with PDB

```python
def test_something(self):
    import pdb; pdb.set_trace()

    result = manager.create_job(...)
    # Now in debugger, you can inspect variables:
    # (Pdb) print(result.job_id)
    # (Pdb) print(result.status)
    # (Pdb) continue
```

### Debugging with Logging

```python
import logging

# Configure logging in test
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_something(self):
    logger.debug(f"Creating job with tenant_key={tenant_key}")
    job = manager.create_job(tenant_key, "implementer", "Test")
    logger.debug(f"Created job: {job.job_id}")
```

### Viewing SQL Queries

```python
# Enable SQLAlchemy query logging
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

# Now run tests and see SQL queries
pytest tests/test_agent_job_manager.py -s
```

## Test Coverage

### Generate Coverage Report

```bash
# HTML report (most useful)
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Open in browser
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows

# Terminal report
pytest tests/ --cov=src/giljo_mcp --cov-report=term

# XML report (for CI/CD)
pytest tests/ --cov=src/giljo_mcp --cov-report=xml
```

### Coverage Report Example

```
Name                                    Stmts   Miss  Cover
-----------------------------------------------------------
src/giljo_mcp/agent_job_manager.py        245      0   100%
src/giljo_mcp/agent_communication_queue.py 180      5    97%
src/giljo_mcp/job_coordinator.py          210      8    96%
src/giljo_mcp/models.py                   150      0   100%
-----------------------------------------------------------
TOTAL                                     785     13    98%
```

### Coverage Goals

- **AgentJobManager**: 100% coverage
- **AgentCommunicationQueue**: 95%+ coverage
- **JobCoordinator**: 95%+ coverage
- **API Endpoints**: 100% coverage (all success + error paths)

### Identify Uncovered Lines

```bash
# Show missing lines
pytest tests/ --cov=src/giljo_mcp --cov-report=term-missing

# Output:
# Name                                    Stmts   Miss  Cover   Missing
# --------------------------------------------------------------------
# src/giljo_mcp/agent_job_manager.py        245      0   100%
# src/giljo_mcp/job_coordinator.py          210      8    96%   145-152
```

Then add tests to cover lines 145-152.

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: postgres:18
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
          pip install pytest pytest-asyncio pytest-cov httpx websockets

      - name: Run tests
        run: |
          pytest tests/ --cov=src/giljo_mcp --cov-report=xml

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
```

### Pre-Commit Hook

```bash
# .git/hooks/pre-commit
#!/bin/bash

echo "Running tests before commit..."
pytest tests/ --cov=src/giljo_mcp --cov-fail-under=95

if [ $? -ne 0 ]; then
    echo "Tests failed. Commit aborted."
    exit 1
fi

echo "All tests passed!"
```

Make it executable:
```bash
chmod +x .git/hooks/pre-commit
```

## Test Performance

### Run Tests in Parallel

```bash
# Install pytest-xdist
pip install pytest-xdist

# Run with 4 workers
pytest tests/ -n 4

# Auto-detect CPU count
pytest tests/ -n auto
```

### Measure Test Duration

```bash
# Show slowest 10 tests
pytest tests/ --durations=10

# Show all test durations
pytest tests/ --durations=0
```

### Skip Slow Tests

```python
# Mark slow tests
@pytest.mark.slow
def test_large_batch_creation():
    """Test creating 1000 jobs in batch."""
    pass

# Run without slow tests
pytest tests/ -m "not slow"
```

## Summary

You now know how to:

- Run all tests and specific test categories
- Understand test organization and fixtures
- Add new tests following naming conventions
- Debug test failures and isolation issues
- Generate and interpret coverage reports
- Integrate tests into CI/CD pipelines

### Quick Commands Reference

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ --cov=src/giljo_mcp --cov-report=html

# Run specific test file
pytest tests/test_agent_job_manager.py -v

# Run specific test class
pytest tests/test_agent_job_manager.py::TestAgentJobManagerCreation -v

# Run tests matching pattern
pytest tests/ -k "multi_tenant" -v

# Debug with print statements
pytest tests/ -s

# Show slowest tests
pytest tests/ --durations=10
```

## Next Steps

- Review [Validation Guide](../HANDOVER_0019_VALIDATION_GUIDE.md) for manual testing
- Review [API Reference](../api/AGENT_JOBS_API_REFERENCE.md) for endpoint documentation
- Review [Security Verification](../security/HANDOVER_0019_TENANT_ISOLATION_VERIFICATION.md) for multi-tenant testing
- Write tests for new features before implementing (TDD)

The test suite ensures the Agent Job Management System is production-ready and maintainable.
