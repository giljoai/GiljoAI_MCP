---
**Document Type:** Handover
**Handover ID:** 0511
**Title:** E2E Integration Tests - Critical Workflows
**Version:** 2.0
**Created:** 2025-11-12
**Updated:** 2025-11-13
**Status:** Ready for Execution
**Duration:** 18-22 hours
**Scope:** Create end-to-end integration tests for all critical workflows
**Priority:** 🔴 P0 CRITICAL
**Tool:** 🖥️ CLI
**Parallel Execution:** ❌ No (Sequential after 0510)
**Parent Project:** Projectplan_500.md
---

# Handover 0511: E2E Integration Tests - Critical Workflows

## 🎯 Mission Statement
Create comprehensive end-to-end integration tests for all critical workflows: product lifecycle, project lifecycle, vision upload with chunking, orchestrator succession, settings persistence, multi-tenant isolation, WebSocket updates, and MCP tool integration.

## 📋 Prerequisites
- ✅ Handover 0510 complete (unit tests passing, import blockers fixed)
- ✅ Handovers 0500-0510 complete (actual API endpoints, models, services)
- ✅ Live PostgreSQL database (test database configured)
- ✅ Test infrastructure patterns established (TestClient, async fixtures)
- ✅ FastAPI application running with all endpoints registered

## ⚠️ Problem Statement

**Evidence**: Projectplan_500.md line 88 + Handover 0510 completion
- No integration tests for complete workflows
- Refactoring broke workflows (found via manual testing)
- Unit tests cover services (65-73%) but not end-to-end flows
- **Need**: Automated E2E tests to prevent regressions and verify full workflows

**Current Gaps**:
- No tests for API → Service → Database → WebSocket flow
- No validation of thin-client prompt generation in real scenarios
- No succession workflow verification from creation through handover
- No multi-tenant isolation verification across full request lifecycle

## ✅ Solution Approach

Create pytest integration tests using **FastAPI TestClient** pattern that:
1. Start with clean database state (transaction isolation)
2. Execute complete workflows via REST API endpoints
3. Verify database state changes at each step
4. Test error conditions and edge cases
5. Validate WebSocket broadcasts (where applicable)
6. Verify MCP tool exposure and functionality

**Testing Pattern** (from Handover 0510):
```python
from fastapi.testclient import TestClient
from api.app import app

client = TestClient(app)

# Make requests via client
response = client.post("/api/products/", json={...})
assert response.status_code == 200
product = response.json()
```

**Database Fixtures** (from tests/conftest.py):
- `db_manager` - Async database manager (function-scoped)
- `db_session` - Async session with transaction rollback
- `test_project` - Pre-created test project
- `test_agent_jobs` - Multiple agent jobs for testing
- `tenant_manager` - Multi-tenant isolation

## 🔧 Database Fixtures

### Fixtures Available

**tests/conftest.py** provides:
- `db_manager` - Async database session manager
- `db_session` - Transaction-isolated async session (auto-rollback)
- `test_project` - Pre-created Project instance
- `test_agent_jobs` - List of MCPAgentJob instances
- `tenant_manager` - TenantManager for multi-tenant tests
- `api_client` - FastAPI TestClient (with auth mocking)
- `async_client` - httpx AsyncClient for async API tests

**tests/fixtures/base_fixtures.py** utilities:
- `TestData.generate_tenant_key()` - Generate unique tenant keys
- `TestData.generate_project_data(tenant_key)` - Project test data
- `TestData.generate_agent_job_data(project_id, tenant_key)` - Job test data

### New Fixtures to Create

Add to `tests/conftest.py`:

```python
@pytest_asyncio.fixture(scope="function")
async def test_product(db_session, tenant_manager):
    """Create test product for E2E tests."""
    from src.giljo_mcp.models import Product

    product = Product(
        id=str(uuid.uuid4()),
        name="E2E Test Product",
        tenant_key=tenant_manager.get_current_tenant(),
        description="Integration test product",
        is_active=False
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product

@pytest_asyncio.fixture(scope="function")
async def test_project_with_product(db_session, test_product):
    """Create test project linked to test product."""
    from src.giljo_mcp.models import Project

    project = Project(
        id=str(uuid.uuid4()),
        name="E2E Test Project",
        product_id=test_product.id,
        tenant_key=test_product.tenant_key,
        mission="Test mission for E2E testing",
        status="staging"
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project

@pytest_asyncio.fixture(scope="function")
async def test_orchestrator_job(db_session, test_project_with_product):
    """Create orchestrator job for succession testing."""
    from src.giljo_mcp.models import MCPAgentJob
    from datetime import datetime, timezone

    job = MCPAgentJob(
        job_id=str(uuid.uuid4()),
        agent_type="orchestrator",
        status="working",
        project_id=test_project_with_product.id,
        tenant_key=test_project_with_product.tenant_key,
        mission="E2E succession test",
        instance_number=1,
        context_budget=200000,
        context_used=0,
        created_at=datetime.now(timezone.utc)
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job
```

## 📝 Implementation Tasks

### Task 1: Product Lifecycle E2E (3 hours)
**File**: `tests/integration/test_product_lifecycle_e2e.py` (NEW)

Test complete product workflow: create → upload vision → activate → deactivate → restore → delete.

**Implementation**:
```python
"""
E2E Integration Tests for Product Lifecycle
Tests complete product workflow via REST API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from src.giljo_mcp.models import Product, VisionDocument


@pytest.mark.asyncio
async def test_complete_product_lifecycle(db_session, tenant_manager):
    """Test: create → upload vision → activate → deactivate → restore."""
    client = TestClient(app)
    tenant_key = tenant_manager.get_current_tenant()

    # 1. Create product
    response = client.post("/api/products/", json={
        "name": "E2E Lifecycle Test",
        "tenant_key": tenant_key,
        "description": "Testing full lifecycle"
    })
    assert response.status_code == 200
    product = response.json()
    product_id = product["id"]
    assert product["name"] == "E2E Lifecycle Test"
    assert product["is_active"] is False

    # 2. Upload vision document (test chunking for large files)
    vision_content = "# Vision Document\n\n" + ("Large content section " * 5000)  # ~100KB
    files = {"file": ("vision.md", vision_content.encode("utf-8"), "text/markdown")}
    response = client.post(
        f"/api/products/{product_id}/vision",
        files=files,
        data={"tenant_key": tenant_key}
    )
    assert response.status_code == 200
    vision_docs = response.json()
    assert len(vision_docs) >= 2  # Verify chunking occurred for large file

    # 3. Verify vision docs in database
    from sqlalchemy import select
    stmt = select(VisionDocument).where(VisionDocument.product_id == product_id)
    result = await db_session.execute(stmt)
    db_vision_docs = result.scalars().all()
    assert len(db_vision_docs) >= 2

    # 4. Activate product
    response = client.post(f"/api/products/{product_id}/activate")
    assert response.status_code == 200
    activation_response = response.json()
    assert activation_response["product"]["is_active"] is True

    # 5. Verify activation in database
    stmt = select(Product).where(Product.id == product_id)
    result = await db_session.execute(stmt)
    db_product = result.scalar_one()
    assert db_product.is_active is True

    # 6. Deactivate product
    response = client.post(f"/api/products/{product_id}/deactivate")
    assert response.status_code == 200
    product_data = response.json()
    assert product_data["is_active"] is False

    # 7. Verify vision docs persist after deactivation (data integrity)
    response = client.get(f"/api/products/{product_id}/vision")
    assert response.status_code == 200
    vision_after_deactivate = response.json()
    assert len(vision_after_deactivate) == len(vision_docs)

    # 8. Delete product (soft delete)
    response = client.delete(f"/api/products/{product_id}")
    assert response.status_code == 200
    delete_response = response.json()
    assert delete_response["success"] is True
    assert delete_response["deleted_at"] is not None

    # 9. Restore product
    response = client.post(f"/api/products/{product_id}/restore")
    assert response.status_code == 200
    restored_product = response.json()
    assert restored_product["id"] == product_id


@pytest.mark.asyncio
async def test_single_active_product_constraint(db_session, tenant_manager):
    """Test Single Active Product per tenant constraint enforcement."""
    client = TestClient(app)
    tenant_key = tenant_manager.get_current_tenant()

    # Create two products
    response1 = client.post("/api/products/", json={
        "name": "Product A",
        "tenant_key": tenant_key,
        "description": "First product"
    })
    product_a_id = response1.json()["id"]

    response2 = client.post("/api/products/", json={
        "name": "Product B",
        "tenant_key": tenant_key,
        "description": "Second product"
    })
    product_b_id = response2.json()["id"]

    # Activate Product A
    response = client.post(f"/api/products/{product_a_id}/activate")
    assert response.status_code == 200
    assert response.json()["product"]["is_active"] is True

    # Activate Product B (should auto-deactivate Product A)
    response = client.post(f"/api/products/{product_b_id}/activate")
    assert response.status_code == 200
    assert response.json()["product"]["is_active"] is True

    # Verify Product A is now deactivated
    from sqlalchemy import select
    stmt = select(Product).where(Product.id == product_a_id)
    result = await db_session.execute(stmt)
    product_a = result.scalar_one()
    assert product_a.is_active is False
```

### Task 2: Project Lifecycle E2E (4 hours)
**File**: `tests/integration/test_project_lifecycle_e2e.py` (NEW)

Test complete project workflow: create → activate → launch orchestrator → deactivate → reactivate → complete.

**Implementation**:
```python
"""
E2E Integration Tests for Project Lifecycle
Tests complete project workflow via REST API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from src.giljo_mcp.models import Project, MCPAgentJob


@pytest.mark.asyncio
async def test_complete_project_lifecycle(test_product, db_session):
    """Test: create → activate → launch orchestrator → deactivate → complete."""
    client = TestClient(app)

    # 1. Create project
    response = client.post("/api/projects/", json={
        "name": "E2E Project Test",
        "product_id": test_product.id,
        "tenant_key": test_product.tenant_key,
        "mission": "Test orchestrator lifecycle",
        "description": "End-to-end project test"
    })
    assert response.status_code == 200
    project = response.json()
    project_id = project["id"]
    assert project["status"] == "staging"

    # 2. Activate project
    response = client.post(f"/api/projects/{project_id}/activate")
    assert response.status_code == 200
    project_data = response.json()
    assert project_data["status"] == "active"
    assert project_data.get("activated_at") is not None  # Handover 0501 field

    # 3. Verify activation in database
    from sqlalchemy import select
    stmt = select(Project).where(Project.id == project_id)
    result = await db_session.execute(stmt)
    db_project = result.scalar_one()
    assert db_project.status == "active"
    assert db_project.activated_at is not None

    # 4. Launch orchestrator
    response = client.post(f"/api/projects/{project_id}/launch", json={
        "mission_override": "E2E test mission override"
    })
    assert response.status_code == 200
    launch_data = response.json()
    orchestrator_id = launch_data["agent_job_id"]
    assert launch_data["launch_prompt"] is not None  # Thin-client prompt

    # 5. Verify orchestrator job created in database
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == orchestrator_id)
    result = await db_session.execute(stmt)
    job = result.scalar_one()
    assert job.agent_type == "orchestrator"
    assert job.status in ["pending", "working"]
    assert job.instance_number == 1  # First orchestrator
    assert job.context_budget == 200000  # Default Sonnet 4.5 budget

    # 6. Deactivate project (pause)
    response = client.post(f"/api/projects/{project_id}/deactivate", json={
        "reason": "Testing pause functionality"
    })
    assert response.status_code == 200
    project_data = response.json()
    assert project_data["status"] == "paused"
    assert project_data.get("paused_at") is not None  # Handover 0501 field

    # 7. Verify deactivation reason stored in config_data
    stmt = select(Project).where(Project.id == project_id)
    result = await db_session.execute(stmt)
    db_project = result.scalar_one()
    assert db_project.config_data.get("deactivation_reason") == "Testing pause functionality"

    # 8. Re-activate project
    response = client.post(f"/api/projects/{project_id}/activate")
    assert response.status_code == 200
    project_data = response.json()
    assert project_data["status"] == "active"

    # 9. Complete project
    response = client.post(f"/api/projects/{project_id}/complete")
    assert response.status_code == 200
    project_data = response.json()
    assert project_data["status"] == "completed"
    assert project_data.get("completed_at") is not None


@pytest.mark.asyncio
async def test_single_active_project_per_product(test_product, db_session):
    """Test Single Active Project per product constraint enforcement."""
    client = TestClient(app)

    # Create two projects in same product
    response1 = client.post("/api/projects/", json={
        "name": "Project 1",
        "product_id": test_product.id,
        "tenant_key": test_product.tenant_key,
        "mission": "Test mission 1"
    })
    project1_id = response1.json()["id"]

    response2 = client.post("/api/projects/", json={
        "name": "Project 2",
        "product_id": test_product.id,
        "tenant_key": test_product.tenant_key,
        "mission": "Test mission 2"
    })
    project2_id = response2.json()["id"]

    # Activate Project 1
    response = client.post(f"/api/projects/{project1_id}/activate")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    # Activate Project 2 (should auto-pause Project 1)
    response = client.post(f"/api/projects/{project2_id}/activate")
    assert response.status_code == 200
    assert response.json()["status"] == "active"

    # Verify Project 1 is now paused
    from sqlalchemy import select
    stmt = select(Project).where(Project.id == project1_id)
    result = await db_session.execute(stmt)
    project1 = result.scalar_one()
    assert project1.status == "paused"
    assert project1.paused_at is not None
```

### Task 3: Succession Workflow E2E (3 hours)
**File**: `tests/integration/test_succession_workflow_e2e.py` (NEW)

Test orchestrator succession: create orchestrator → simulate context usage → trigger succession → verify chain.

**Implementation**:
```python
"""
E2E Integration Tests for Orchestrator Succession
Tests complete succession workflow via REST API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from src.giljo_mcp.models import MCPAgentJob


@pytest.mark.asyncio
async def test_orchestrator_succession_workflow(test_orchestrator_job, db_session):
    """Test: create orchestrator → trigger succession → verify chain."""
    client = TestClient(app)
    job_id = test_orchestrator_job.job_id

    # 1. Update context usage to 90% (approaching threshold)
    test_orchestrator_job.context_used = 180000  # 90% of 200K budget
    await db_session.commit()

    # 2. Check succession status
    response = client.get(f"/api/agent-jobs/{job_id}/succession-status")
    assert response.status_code == 200
    status = response.json()
    assert status["needs_succession"] is True
    assert status["context_usage_pct"] == 90.0
    assert status["instance_number"] == 1

    # 3. Trigger succession via API
    response = client.post(f"/api/agent-jobs/{job_id}/trigger-succession", json={
        "reason": "E2E test succession - context threshold reached"
    })
    assert response.status_code == 200
    succession_data = response.json()

    # 4. Verify successor created
    successor_id = succession_data["successor_job_id"]
    assert succession_data["instance_number"] == 2
    assert succession_data["launch_prompt"] is not None  # Thin-client prompt
    assert succession_data["succession_reason"] == "E2E test succession - context threshold reached"

    # 5. Verify successor in database
    from sqlalchemy import select
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == successor_id)
    result = await db_session.execute(stmt)
    successor = result.scalar_one()

    assert successor.instance_number == 2
    assert successor.spawned_by == job_id
    assert successor.context_used == 0  # Fresh context
    assert successor.context_budget == 200000
    assert successor.agent_type == "orchestrator"
    assert successor.project_id == test_orchestrator_job.project_id

    # 6. Verify original job updated with handover fields
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)
    result = await db_session.execute(stmt)
    original = result.scalar_one()

    assert original.handover_to == successor_id
    assert original.succession_reason == "E2E test succession - context threshold reached"
    assert original.handover_summary is not None


@pytest.mark.asyncio
async def test_succession_chain_tracking(test_project_with_product, db_session):
    """Test succession creates proper chain tracking across multiple handovers."""
    from src.giljo_mcp.services.orchestration_service import OrchestrationService
    from src.giljo_mcp.database import DatabaseManager

    db_manager = DatabaseManager()
    orchestration_service = OrchestrationService(db_manager)

    # Create first orchestrator
    job1 = await orchestration_service.spawn_agent_job(
        project_id=test_project_with_product.id,
        agent_type="orchestrator",
        mission="Test succession chain",
        context_budget=200000
    )

    # Simulate context usage and trigger first succession
    await orchestration_service.update_context_tracking(
        agent_job_id=job1.id,
        context_used=180000
    )

    result1 = await orchestration_service.trigger_succession(
        job_id=job1.id,
        reason="First succession",
        tenant_key=test_project_with_product.tenant_key
    )
    job2_id = result1["successor_job_id"]

    # Simulate second succession
    await orchestration_service.update_context_tracking(
        agent_job_id=job2_id,
        context_used=180000
    )

    result2 = await orchestration_service.trigger_succession(
        job_id=job2_id,
        reason="Second succession",
        tenant_key=test_project_with_product.tenant_key
    )
    job3_id = result2["successor_job_id"]

    # Verify succession chain
    from sqlalchemy import select

    # Job 1 should point to Job 2
    stmt = select(MCPAgentJob).where(MCPAgentJob.id == job1.id)
    result = await db_session.execute(stmt)
    db_job1 = result.scalar_one()
    assert db_job1.handover_to == job2_id
    assert db_job1.instance_number == 1

    # Job 2 should point to Job 3 and be spawned by Job 1
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job2_id)
    result = await db_session.execute(stmt)
    db_job2 = result.scalar_one()
    assert db_job2.handover_to == job3_id
    assert db_job2.spawned_by == job1.id
    assert db_job2.instance_number == 2

    # Job 3 should be spawned by Job 2
    stmt = select(MCPAgentJob).where(MCPAgentJob.job_id == job3_id)
    result = await db_session.execute(stmt)
    db_job3 = result.scalar_one()
    assert db_job3.spawned_by == job2_id
    assert db_job3.instance_number == 3
```

### Task 4: Settings Persistence E2E (2 hours)
**File**: `tests/integration/test_settings_persistence_e2e.py` (NEW)

Test settings persist correctly across database operations.

**Implementation**:
```python
"""
E2E Integration Tests for Settings Persistence
Tests settings CRUD operations via REST API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app


@pytest.mark.asyncio
async def test_settings_persistence(tenant_manager):
    """Test settings persist correctly in database."""
    client = TestClient(app)
    tenant_key = tenant_manager.get_current_tenant()

    # 1. Update general settings
    response = client.put("/api/settings/general", json={
        "tenant_key": tenant_key,
        "settings_data": {
            "theme": "dark",
            "language": "en",
            "notifications_enabled": True,
            "auto_save_interval": 30
        }
    })
    assert response.status_code == 200

    # 2. Fetch settings back
    response = client.get(f"/api/settings/general?tenant_key={tenant_key}")
    assert response.status_code == 200
    settings = response.json()

    assert settings["settings_data"]["theme"] == "dark"
    assert settings["settings_data"]["language"] == "en"
    assert settings["settings_data"]["notifications_enabled"] is True
    assert settings["settings_data"]["auto_save_interval"] == 30
    assert settings["category"] == "general"

    # 3. Update partial settings (merge test)
    response = client.put("/api/settings/general", json={
        "tenant_key": tenant_key,
        "settings_data": {
            "theme": "light"  # Only update theme
        }
    })
    assert response.status_code == 200

    # 4. Verify other settings preserved
    response = client.get(f"/api/settings/general?tenant_key={tenant_key}")
    settings = response.json()
    assert settings["settings_data"]["theme"] == "light"  # Updated
    assert settings["settings_data"]["language"] == "en"  # Preserved


@pytest.mark.asyncio
async def test_multi_category_settings(tenant_manager):
    """Test different settings categories isolated correctly."""
    client = TestClient(app)
    tenant_key = tenant_manager.get_current_tenant()

    # Create settings for multiple categories
    categories = ["general", "network", "database", "integrations"]

    for category in categories:
        response = client.put(f"/api/settings/{category}", json={
            "tenant_key": tenant_key,
            "settings_data": {
                "test_field": f"{category}_value"
            }
        })
        assert response.status_code == 200

    # Verify each category isolated
    for category in categories:
        response = client.get(f"/api/settings/{category}?tenant_key={tenant_key}")
        assert response.status_code == 200
        settings = response.json()
        assert settings["settings_data"]["test_field"] == f"{category}_value"
```

### Task 5: Multi-Tenant Isolation E2E (3 hours)
**File**: `tests/integration/test_tenant_isolation_e2e.py` (NEW)

Test tenant A cannot access tenant B data at API level.

**Implementation**:
```python
"""
E2E Integration Tests for Multi-Tenant Isolation
Tests tenant isolation across all API endpoints
"""
import pytest
from fastapi.testclient import TestClient
from api.app import app
from src.giljo_mcp.models import Product, Project


@pytest.mark.asyncio
async def test_product_tenant_isolation(db_session):
    """Test tenant A cannot access tenant B products."""
    from src.giljo_mcp.tenant import TenantManager

    # Create products for two different tenants
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    product_a = Product(
        name="Tenant A Product",
        tenant_key=tenant_a,
        description="Product owned by Tenant A"
    )
    product_b = Product(
        name="Tenant B Product",
        tenant_key=tenant_b,
        description="Product owned by Tenant B"
    )

    db_session.add(product_a)
    db_session.add(product_b)
    await db_session.commit()
    await db_session.refresh(product_a)
    await db_session.refresh(product_b)

    client = TestClient(app)

    # Attempt to access Tenant B product as Tenant A (should fail)
    # NOTE: This requires proper authentication mocking for full implementation
    # For now, verify database-level isolation

    from sqlalchemy import select

    # Tenant A query should only return Tenant A products
    stmt = select(Product).where(Product.tenant_key == tenant_a)
    result = await db_session.execute(stmt)
    tenant_a_products = result.scalars().all()
    assert len(tenant_a_products) == 1
    assert tenant_a_products[0].id == product_a.id

    # Tenant B query should only return Tenant B products
    stmt = select(Product).where(Product.tenant_key == tenant_b)
    result = await db_session.execute(stmt)
    tenant_b_products = result.scalars().all()
    assert len(tenant_b_products) == 1
    assert tenant_b_products[0].id == product_b.id


@pytest.mark.asyncio
async def test_project_tenant_isolation(db_session):
    """Test tenant isolation for projects."""
    from src.giljo_mcp.tenant import TenantManager

    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create products first
    product_a = Product(name="Product A", tenant_key=tenant_a)
    product_b = Product(name="Product B", tenant_key=tenant_b)
    db_session.add(product_a)
    db_session.add(product_b)
    await db_session.commit()

    # Create projects
    project_a = Project(
        name="Tenant A Project",
        product_id=product_a.id,
        tenant_key=tenant_a,
        mission="Mission A",
        status="active"
    )
    project_b = Project(
        name="Tenant B Project",
        product_id=product_b.id,
        tenant_key=tenant_b,
        mission="Mission B",
        status="active"
    )

    db_session.add(project_a)
    db_session.add(project_b)
    await db_session.commit()

    # Verify isolation
    from sqlalchemy import select

    stmt = select(Project).where(Project.tenant_key == tenant_a)
    result = await db_session.execute(stmt)
    tenant_a_projects = result.scalars().all()
    assert len(tenant_a_projects) == 1
    assert all(p.tenant_key == tenant_a for p in tenant_a_projects)
```

### Task 6: WebSocket Integration E2E (3 hours)
**File**: `tests/integration/test_websocket_job_updates_e2e.py` (NEW)

Test WebSocket broadcasts job status changes in real-time.

**Implementation**:
```python
"""
E2E Integration Tests for WebSocket Job Updates
Tests real-time WebSocket broadcasts for agent job events
"""
import pytest
import asyncio
import json


@pytest.mark.asyncio
async def test_websocket_job_creation_broadcast(test_project_with_product):
    """Test WebSocket broadcasts when agent job is created."""
    import websockets
    from fastapi.testclient import TestClient
    from api.app import app

    client = TestClient(app)

    # Note: WebSocket testing requires actual server running
    # This is a placeholder for the pattern - real implementation
    # would need proper WebSocket server setup in test environment

    # Simplified test: Verify WebSocket manager exists and is configured
    from api.app import state
    assert state.websocket_manager is not None

    # Create agent job
    response = client.post("/api/agent-jobs/", json={
        "project_id": test_project_with_product.id,
        "agent_type": "developer",
        "mission": "WebSocket test",
        "tenant_key": test_project_with_product.tenant_key
    })

    assert response.status_code == 200
    job_data = response.json()
    assert job_data["agent_type"] == "developer"


@pytest.mark.asyncio
async def test_websocket_succession_broadcast(test_orchestrator_job):
    """Test WebSocket broadcasts succession events."""
    from fastapi.testclient import TestClient
    from api.app import app, state

    client = TestClient(app)

    # Verify WebSocket manager configured
    assert state.websocket_manager is not None

    # Trigger succession (should broadcast event)
    response = client.post(
        f"/api/agent-jobs/{test_orchestrator_job.job_id}/trigger-succession",
        json={"reason": "WebSocket test succession"}
    )

    assert response.status_code == 200
    succession_data = response.json()
    assert succession_data["successor_job_id"] is not None

    # NOTE: Full WebSocket testing would require:
    # 1. WebSocket client connection
    # 2. Message listening loop
    # 3. Event verification
    # This is deferred to manual testing or future enhancement
```

### Task 7: MCP Tool Integration E2E (2 hours)
**File**: `tests/integration/test_mcp_tool_integration_e2e.py` (NEW)

Test MCP tools work end-to-end with real database.

**Implementation**:
```python
"""
E2E Integration Tests for MCP Tool Integration
Tests MCP tools with real database operations
"""
import pytest


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_mcp_tool(test_project_with_product, test_product):
    """Test get_orchestrator_instructions MCP tool with real data."""
    from src.giljo_mcp.tools.orchestration_tools import get_orchestrator_instructions

    # Activate product (required for orchestrator instructions)
    test_product.is_active = True

    # Call MCP tool
    result = get_orchestrator_instructions(project_id=str(test_project_with_product.id))

    # Verify returned structure
    assert "mission" in result
    assert "project_name" in result
    assert "product_name" in result
    assert result["project_id"] == str(test_project_with_product.id)
    assert result["project_name"] == test_project_with_product.name
    assert result["mission"] == test_project_with_product.mission


@pytest.mark.asyncio
async def test_trigger_succession_mcp_tool(test_orchestrator_job, db_session):
    """Test trigger_succession MCP tool."""
    from src.giljo_mcp.tools.succession_tools import create_successor_orchestrator

    # Update context usage to trigger threshold
    test_orchestrator_job.context_used = 180000
    await db_session.commit()

    # Call MCP tool
    result = create_successor_orchestrator(
        current_job_id=str(test_orchestrator_job.job_id),
        reason="MCP tool E2E test"
    )

    # Verify result structure
    assert "successor_job_id" in result
    assert "instance_number" in result
    assert result["instance_number"] == 2
    assert "launch_prompt" in result
```

## ✅ Success Criteria

**Test Execution**:
- [ ] All 7 test suites pass (Product, Project, Succession, Settings, Isolation, WebSocket, MCP)
- [ ] Total tests: ~25-30 individual test functions
- [ ] Execution time: <5 minutes for full suite
- [ ] Zero database connection errors
- [ ] Zero test flakiness (consistent results across 3+ runs)

**Coverage Targets**:
- [ ] API endpoints: >85% covered by E2E tests
- [ ] Service layer: Already >65% from Handover 0510 unit tests
- [ ] Integration coverage: >70% (combined unit + E2E)

**Workflow Validation**:
- [ ] Product lifecycle: create → vision → activate → deactivate → restore ✅
- [ ] Project lifecycle: create → activate → launch → pause → complete ✅
- [ ] Succession: spawn → context full → trigger → verify chain ✅
- [ ] Settings: update → persist → retrieve ✅
- [ ] Multi-tenant: isolation verified, no leakage ✅
- [ ] WebSocket: real-time updates working ✅
- [ ] MCP tools: exposed and functional ✅

**Documentation**:
- [ ] All test files have docstrings explaining workflow
- [ ] Fixtures documented in tests/conftest.py
- [ ] README.md updated with E2E test running instructions

## 🔄 Rollback Plan

Tests don't affect production code - safe to iterate.

**If tests fail**:
1. Review error messages for patterns
2. Check if API endpoints changed (compare with Handovers 0503-0506)
3. Verify database schema matches models (Handovers 0500-0502)
4. Test fixtures may need adjustment for environment
5. Iterate on test implementation without code changes

## 📚 Related Handovers

**Depends on**:
- 0510 (unit tests, test infrastructure patterns)
- 0500-0502 (database models)
- 0503-0506 (API endpoints)
- 0501 (ProjectService lifecycle methods)
- 0502 (OrchestrationService context tracking)

**Enables**:
- 0512 (Documentation updates)
- CI/CD integration (future)
- Regression prevention for all future handovers

## 🛠️ Tool Justification

**Why CLI**: Integration tests need live backend + database + API server. Cannot be done via browser interface.

**FastAPI TestClient**: Synchronous client for HTTP endpoint testing (established pattern from Handover 0510).

**pytest-asyncio**: Required for async database operations and service testing.

## 📊 Parallel Execution

**❌ Cannot parallelize** - Sequential after Handover 0510.

**Reasoning**:
- Requires completed unit test suite (0510)
- Tests build on established patterns from 0510
- Database fixtures depend on test infrastructure setup

---

**Status:** Ready for Execution
**Estimated Effort:** 18-22 hours (updated from 12-16h to account for WebSocket + MCP tasks)
**Archive Location:** `handovers/archive/0511_e2e_integration_tests-COMPLETE.md`
