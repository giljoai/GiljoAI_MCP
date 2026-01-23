# Testing Strategy & Patterns

**Version**: v3.1+ (Post-Remediation)
**Last Updated**: 2025-11-15
**Coverage Target**: >80% across all services and endpoints

## Overview

GiljoAI MCP uses a comprehensive testing strategy with **unit tests** for business logic, **integration tests** for workflows, and **E2E tests** for critical user journeys. All tests are written in pytest with async support.

**Coverage**: >80% achieved after Handover 0510 (test suite restoration)

---

## Test Structure

```
tests/
├── services/          # Unit tests for service layer
│   ├── test_product_service.py
│   ├── test_project_service.py
│   ├── test_orchestration_service_full.py  # Comprehensive orchestration tests (Handover 0452)
│   └── test_settings_service.py
├── integration/       # Integration tests (DB + services + endpoints)
│   ├── test_product_workflows.py
│   ├── test_project_lifecycle.py
│   ├── test_orchestration_e2e.py           # E2E orchestration workflow tests (Handover 0453)
│   └── test_multi_tenant_isolation.py
├── tools/             # MCP tool delegation tests
│   └── test_tool_accessor_delegation.py    # Verify delegation to OrchestrationService (Handover 0453)
├── endpoints/         # API endpoint tests
│   ├── test_products_api.py
│   ├── test_projects_api.py
│   └── test_settings_api.py
├── conftest.py        # Shared fixtures
└── pytest.ini         # pytest configuration
```

**Note**: As of Handover 0452 (Jan 2026), 30+ orchestrator test files were deleted (~13,500 lines) after consolidating orchestration logic into OrchestrationService. The new test structure focuses on testing the service layer directly.

---

## Unit Tests (`tests/services/`)

**Purpose**: Test business logic in isolation (mock database, no real I/O)

### **ProductService Tests**

```python
# tests/services/test_product_service.py

import pytest
from src.giljo_mcp.services.product_service import ProductService

@pytest.mark.asyncio
async def test_vision_upload_chunking(mock_session, test_tenant):
    """Test vision upload with automatic chunking (<25K tokens)"""
    service = ProductService(mock_session, test_tenant)

    # Large vision document (60K tokens)
    large_vision = "x" * 60000

    result = await service.upload_vision_document(
        product_id=1,
        content=large_vision
    )

    # Verify chunking
    assert result['chunks'] == 3  # 60K / 25K = 2.4 → 3 chunks
    assert all(len(chunk) <= 25000 for chunk in result['chunk_data'])


@pytest.mark.asyncio
async def test_config_data_persistence(mock_session, test_tenant):
    """Test config_data JSONB field persistence"""
    service = ProductService(mock_session, test_tenant)

    config = {
        "theme": "dark",
        "language": "en",
        "features": ["auth", "billing"]
    }

    product = await service.create_product({
        "name": "Test Product",
        "config_data": config
    })

    # Verify JSONB storage
    assert product.config_data == config
    assert product.config_data['theme'] == "dark"
```

### **ProjectService Tests**

```python
# tests/services/test_project_service.py

@pytest.mark.asyncio
async def test_single_active_project_constraint(db_session, test_tenant):
    """Test Single Active Project constraint enforcement"""
    service = ProjectService(db_session, test_tenant)

    # Create two projects
    project1 = await service.create_project({"name": "Project 1"})
    project2 = await service.create_project({"name": "Project 2"})

    # Activate project 1
    await service.activate_project(project1.id)
    active = await service.get_active_project()
    assert active.id == project1.id

    # Activate project 2 (should deactivate project 1)
    await service.activate_project(project2.id)
    active = await service.get_active_project()
    assert active.id == project2.id

    # Verify project 1 deactivated
    await db_session.refresh(project1)
    assert project1.status == "paused"


@pytest.mark.asyncio
async def test_project_summary_generation(db_session, test_tenant):
    """Test project summary generation"""
    service = ProjectService(db_session, test_tenant)

    project = await service.create_project({"name": "Test Project"})

    # Create some agent jobs for this project
    # ... (mock agent jobs) ...

    summary = await service.get_project_summary(project.id)

    assert summary['total_agents'] >= 0
    assert summary['completed_agents'] >= 0
    assert 0.0 <= summary['success_rate'] <= 1.0
    assert summary['time_spent_hours'] >= 0
```

### **OrchestrationService Tests**

**Location**: `tests/services/test_orchestration_service_full.py`

**Note**: As of Handovers 0450-0452 (Jan 2026), OrchestrationService contains all orchestration logic (previously in `orchestrator.py`). Tests are comprehensive and cover:
- Agent spawning and execution creation
- Multi-tenant isolation
- Succession management
- Vision processing
- Error handling

```python
# tests/services/test_orchestration_service_full.py

@pytest.mark.asyncio
async def test_spawn_creates_both_job_and_execution(db_session, test_tenant):
    """Test spawn_agent_job creates AgentJob and AgentExecution"""
    service = OrchestrationService(db_session, test_tenant)

    result = await service.spawn_agent_job(
        agent_display_name="backend-implementer",
        agent_name="Backend Developer",
        mission="Implement user auth",
        project_id=test_project.id
    )

    assert result["job_id"] is not None
    assert result["agent_id"] is not None
    assert result["thin_prompt"] is not None


@pytest.mark.asyncio
async def test_create_successor_creates_new_execution(db_session, test_tenant):
    """Test create_successor_orchestrator creates new AgentExecution"""
    service = OrchestrationService(db_session, test_tenant)

    # Create original orchestrator
    original = await service.create_orchestrator_job(...)

    # Create successor
    result = await service.create_successor_orchestrator(
        current_job_id=original.job_id,
        tenant_key=test_tenant,
        reason="context_limit"
    )

    assert result["successor_agent_id"] != original.agent_id
    assert result["thin_prompt"] is not None


@pytest.mark.asyncio
async def test_get_agent_mission_returns_full_protocol(db_session, test_tenant):
    """Test get_agent_mission returns mission with full protocol"""
    service = OrchestrationService(db_session, test_tenant)

    result = await service.spawn_agent_job(...)
    mission_result = await service.get_agent_mission(
        job_id=result["job_id"],
        tenant_key=test_tenant
    )

    assert mission_result["mission"] is not None
    assert mission_result["full_protocol"] is not None
    assert "EXPLORE" in mission_result["full_protocol"]
```

**Test Coverage** (as of Handover 0452):
- 11 tests in `test_orchestration_service_full.py`
- 9 passing, 2 skipped (process_product_vision pending implementation)
- Tests cover: spawning, succession, multi-tenant isolation, error handling
- Previous `test_orchestrator*.py` files deleted (30+ files, ~13,500 lines)

---

## Integration Tests (`tests/integration/`)

**Purpose**: Test complete workflows with real database and services

### **Product → Vision → Project → Orchestrator Workflow**

```python
# tests/integration/test_product_workflows.py

@pytest.mark.asyncio
async def test_complete_product_lifecycle(db_session, test_tenant):
    """Test full product lifecycle from creation to orchestrator launch"""

    # 1. Create product
    product_service = ProductService(db_session, test_tenant)
    product = await product_service.create_product({
        "name": "E-Commerce Platform",
        "description": "Build online store"
    })

    # 2. Upload vision document
    vision_content = "Build e-commerce platform with cart, checkout, payments..."
    vision_result = await product_service.upload_vision_document(
        product.id,
        vision_content
    )
    assert vision_result['success'] is True

    # 3. Activate product
    await product_service.activate_product(product.id)
    active_product = await product_service.get_active_product()
    assert active_product.id == product.id

    # 4. Create project
    project_service = ProjectService(db_session, test_tenant)
    project = await project_service.create_project({
        "name": "MVP Development",
        "product_id": product.id
    })

    # 5. Activate project
    await project_service.activate_project(project.id)

    # 6. Launch orchestrator
    orchestration_service = OrchestrationService(db_session, test_tenant)
    orchestrator = await orchestration_service.create_orchestrator_job(
        project_id=project.id,
        mission="Build MVP for e-commerce platform",
        context_budget=200000
    )

    # Verify orchestrator created
    assert orchestrator.status == "pending"
    assert orchestrator.context_budget == 200000
    assert orchestrator.instance_number == 1
```

### **Multi-Tenant Isolation Tests**

```python
# tests/integration/test_multi_tenant_isolation.py

@pytest.mark.asyncio
async def test_zero_cross_tenant_leakage(db_session):
    """Verify zero cross-tenant data leakage"""

    # Create data for tenant A
    service_a = ProductService(db_session, "tenant_a")
    product_a = await service_a.create_product({"name": "Product A"})

    # Create data for tenant B
    service_b = ProductService(db_session, "tenant_b")
    product_b = await service_b.create_product({"name": "Product B"})

    # Verify tenant A cannot see tenant B's data
    products_a = await service_a.get_products()
    assert len(products_a) == 1
    assert products_a[0].id == product_a.id

    # Verify tenant B cannot see tenant A's data
    products_b = await service_b.get_products()
    assert len(products_b) == 1
    assert products_b[0].id == product_b.id

    # Attempt to access cross-tenant (should fail)
    with pytest.raises(NotFoundError):
        await service_a.get_product(product_b.id)
```

### **Orchestrator Succession Tests**

```python
# tests/integration/test_orchestrator_succession.py

@pytest.mark.asyncio
async def test_succession_lineage_preservation(db_session, test_tenant):
    """Test full succession chain lineage tracking"""

    service = OrchestrationService(db_session, test_tenant)

    # Create orchestrator (instance 1)
    job1 = await service.create_orchestrator_job(
        project_id=1,
        mission="Build auth system",
        context_budget=100000
    )

    # Simulate context usage and trigger succession
    await service.update_context_usage(job1.id, 91000)
    job2 = await service.trigger_succession(job1.id, "context_limit")

    # Trigger another succession (instance 2 → 3)
    await service.update_context_usage(job2.id, 91000)
    job3 = await service.trigger_succession(job2.id, "context_limit")

    # Verify lineage chain
    assert job1.spawned_by is None  # First orchestrator
    assert job1.handover_to == job2.id

    assert job2.spawned_by == job1.id
    assert job2.handover_to == job3.id
    assert job2.instance_number == 2

    assert job3.spawned_by == job2.id
    assert job3.instance_number == 3

    # Verify all handover summaries preserved
    assert job1.handover_summary is not None
    assert job2.handover_summary is not None
```

---

## API Endpoint Tests (`tests/endpoints/`)

**Purpose**: Test HTTP endpoints with FastAPI TestClient

### **Product Endpoints**

```python
# tests/endpoints/test_products_api.py

from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

def test_create_product(test_user_token):
    """Test POST /api/products"""
    response = client.post(
        "/api/products",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={
            "name": "Test Product",
            "description": "Test description"
        }
    )

    assert response.status_code == 200
    data = response.json()
    assert data['name'] == "Test Product"
    assert 'id' in data


def test_vision_upload(test_user_token, test_product_id):
    """Test POST /api/products/{id}/vision"""
    response = client.post(
        f"/api/products/{test_product_id}/vision",
        headers={"Authorization": f"Bearer {test_user_token}"},
        json={"content": "Build authentication system..."}
    )

    assert response.status_code == 200
    data = response.json()
    assert data['success'] is True
    assert data['chunks'] > 0  # Vision chunked
```

---

## Test Commands

### **Run All Tests**
```bash
pytest tests/ --cov=src/giljo_mcp --cov-report=html
```

### **Run Specific Test Categories**
```bash
# Unit tests only (service layer)
pytest tests/services/ -v

# Integration tests only
pytest tests/integration/ -v

# Endpoint tests only
pytest tests/endpoints/ -v

# Specific test file
pytest tests/services/test_product_service.py -v

# Specific test function
pytest tests/services/test_product_service.py::test_vision_upload_chunking -v
```

### **Coverage Reports**
```bash
# Terminal coverage report
pytest tests/ --cov=src/giljo_mcp --cov-report=term

# HTML coverage report (opens in browser)
pytest tests/ --cov=src/giljo_mcp --cov-report=html
open htmlcov/index.html  # macOS/Linux
start htmlcov/index.html  # Windows
```

### **Run Tests with Verbose Output**
```bash
# Show print statements and detailed errors
pytest tests/ -v -s

# Show only failures
pytest tests/ --tb=short

# Stop on first failure
pytest tests/ -x
```

---

## Fixtures (`tests/conftest.py`)

### **Database Fixtures**

```python
# tests/conftest.py

import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from src.giljo_mcp.models import Base

@pytest.fixture
async def db_session():
    """Provide async database session for tests"""
    engine = create_async_engine("postgresql+asyncpg://localhost/giljo_mcp_test")

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
def test_tenant():
    """Provide test tenant key"""
    return "test_tenant_123"


@pytest.fixture
async def test_product(db_session, test_tenant):
    """Provide test product"""
    from src.giljo_mcp.services.product_service import ProductService

    service = ProductService(db_session, test_tenant)
    product = await service.create_product({"name": "Test Product"})
    return product
```

### **Mock Fixtures**

```python
@pytest.fixture
def mock_session():
    """Provide mock database session (no real DB)"""
    from unittest.mock import AsyncMock
    return AsyncMock()


@pytest.fixture
def test_user_token():
    """Provide JWT token for authenticated endpoints"""
    from jose import jwt
    token = jwt.encode(
        {"sub": "test_user", "tenant_key": "test_tenant"},
        "secret_key",
        algorithm="HS256"
    )
    return token
```

---

## Best Practices

### **1. Use Async Tests for Async Code**
```python
@pytest.mark.asyncio
async def test_async_function():
    result = await my_async_function()
    assert result == expected
```

### **2. Mock External Dependencies**
```python
from unittest.mock import patch, AsyncMock

@pytest.mark.asyncio
@patch('src.giljo_mcp.services.product_service.websocket_manager')
async def test_with_mocked_websocket(mock_ws, db_session, test_tenant):
    mock_ws.broadcast_to_tenant = AsyncMock()

    service = ProductService(db_session, test_tenant)
    await service.activate_product(1)

    # Verify WebSocket called
    mock_ws.broadcast_to_tenant.assert_called_once()
```

### **3. Test Edge Cases**
```python
@pytest.mark.asyncio
async def test_product_not_found(db_session, test_tenant):
    """Test error handling for non-existent product"""
    service = ProductService(db_session, test_tenant)

    with pytest.raises(ProductNotFoundError):
        await service.get_product(999999)  # Non-existent ID
```

### **4. Test Multi-Tenant Isolation**
```python
@pytest.mark.asyncio
async def test_tenant_isolation(db_session):
    """Always verify tenant isolation in data access tests"""
    service_a = ProductService(db_session, "tenant_a")
    service_b = ProductService(db_session, "tenant_b")

    product_a = await service_a.create_product({"name": "Product A"})

    # Tenant B cannot access tenant A's data
    with pytest.raises(NotFoundError):
        await service_b.get_product(product_a.id)
```

### **5. Clean Up After Tests**
```python
@pytest.fixture
async def test_product(db_session, test_tenant):
    """Use fixtures for setup and automatic teardown"""
    service = ProductService(db_session, test_tenant)
    product = await service.create_product({"name": "Test"})

    yield product

    # Automatic cleanup after test
    await service.delete_product(product.id)
```

---

## Troubleshooting

### **Issue: Tests Failing with Database Connection Errors**

**Diagnosis**:
```bash
# Check PostgreSQL running
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -l
```

**Solution**: Ensure PostgreSQL is running and test database exists:
```bash
PGPASSWORD=$DB_PASSWORD /f/PostgreSQL/bin/psql.exe -U postgres -c "CREATE DATABASE giljo_mcp_test;"
```

### **Issue: Async Tests Not Running**

**Diagnosis**: Missing pytest-asyncio plugin

**Solution**:
```bash
pip install pytest-asyncio
```

Add to `pytest.ini`:
```ini
[pytest]
asyncio_mode = auto
```

### **Issue: Coverage Not Showing All Files**

**Diagnosis**: Missing `__init__.py` in directories

**Solution**: Add `__init__.py` to all Python package directories:
```bash
touch src/giljo_mcp/services/__init__.py
touch tests/services/__init__.py
```

---

## Related Documentation

- **Services**: [SERVICES.md](SERVICES.md) - Service layer architecture
- **Orchestrator**: [ORCHESTRATOR.md](ORCHESTRATOR.md) - Succession testing patterns
- **Architecture**: [SERVER_ARCHITECTURE_TECH_STACK.md](SERVER_ARCHITECTURE_TECH_STACK.md)

---

**Last Updated**: 2025-11-15 (Post-Remediation v3.1.1)
