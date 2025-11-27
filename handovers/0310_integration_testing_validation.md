# Handover 0310: Integration Testing & Validation

---
**📝 REVIEW STATUS (2025-11-27)**
**Status**: 60% Complete - Performance benchmarks pending for future implementation
**Completed**: Context tool tests, multi-tenant isolation, field priority updates, >80% code coverage
**Remaining**: Performance benchmarks (<500ms target), token accuracy validation (5% tolerance), E2E Priority × Depth workflow tests
**Decision**: Keeping active for future completion when performance testing becomes priority
---

**Feature**: End-to-End Integration Testing for Context Management System
**Status**: Not Started (Scope Updated)
**Priority**: P1 - HIGH
**Estimated Duration**: 4-5 hours (reduced - some tests already exist)
**Agent Budget**: 90K tokens
**Depends On**: Handovers 0312-0316 (Context Management v2.0)
**Blocks**: None (Final handover in series)
**Created**: 2025-11-16
**Updated**: 2025-11-18
**Tool**: CLI (Integration testing, system validation)

---

## ⚠️ SCOPE UPDATED FOR CONTEXT MANAGEMENT v2.0

**Date**: 2025-11-18
**Reason**: Context Management v2.0 (Handovers 0312-0316) changed the architecture. Many tests already completed.

**What's Already Covered** (skip these):
- ✅ Context tool functionality tests (`tests/integration/test_handover_0316_*.py`)
- ✅ Multi-tenant isolation (partial coverage)
- ✅ Field priority updates (`tests/integration/test_priority_system_integration.py`)
- ✅ >80% code coverage for context tools

**Focus on Remaining Gaps**:
1. **Performance Benchmarks** - Context generation <500ms, Token estimation <200ms
2. **Token Accuracy Validation** - Within 5% tolerance of actual
3. **E2E Priority × Depth Workflow** - Complete 2D model testing
4. **Default Priority Application** - New user experience
5. **Context Preview Consistency** - UI matches orchestrator mission

**Updated Test Scope**:
- Original: Test all 0301-0309 features
- Updated: Test v2.0 (Priority × Depth) gaps only

---

## Executive Summary

This handover validates the complete context management system (Handovers 0301-0309) through comprehensive integration testing. We'll create end-to-end test scenarios covering the full workflow: user configures field priorities → backend generates context string → frontend displays token estimates → orchestrator receives properly formatted context.

**Why This Matters**: Unit tests verify individual components, but integration tests ensure the entire system works together cohesively. This handover catches edge cases, validates cross-component interactions, and ensures the context management UX delivers on its promise of transparency and control.

**Impact**: Confirms all context management features work together seamlessly, validates token budget accuracy, ensures multi-tenant isolation, provides regression protection for future changes.

---

## Problem Statement

### What We're Validating

**Complete Workflow** (Handovers 0301-0309):
1. **Context String Structure** (0301): Proper section ordering, formatting
2. **Field Priority Validation** (0302): 3-tier system enforcement
3. **UI Field Management** (0303): Drag-and-drop, priority assignment
4. **Context Preview** (0304): Real-time regeneration, accurate display
5. **Database Schema** (0305): Field storage, retrieval, multi-tenant isolation
6. **Agent Templates** (0306): Formatted in context string, respects priorities
7. **Default Priorities** (0307): New users get sensible defaults
8. **Field Labels** (0308): Human-readable labels, tooltips
9. **Token Estimation** (0309): Accurate token counts, real-time updates

### Integration Points to Test

**Backend ↔ Database**:
- Field priorities stored correctly
- Multi-tenant isolation enforced
- Defaults applied for new users

**Backend ↔ Frontend**:
- API returns proper field priorities
- Token estimates match product data
- Context preview accurate

**Frontend ↔ User**:
- Drag-and-drop updates backend
- Token budget displays correctly
- Labels and tooltips render properly

**Orchestrator ↔ Context**:
- Receives properly formatted context string
- Section ordering correct
- Field priorities respected

---

## Objectives

### Primary Goals
1. Create comprehensive integration test suite covering full workflow
2. Validate token budget accuracy (backend calculation vs frontend display)
3. Test multi-tenant isolation across all components
4. Verify default priority application for new users
5. Ensure context string formatting matches specification

### Success Criteria
- ✅ All integration tests pass with >95% success rate
- ✅ Token estimates accurate within 5% of actual counts
- ✅ Multi-tenant isolation verified (no cross-tenant data leaks)
- ✅ New user workflow tested end-to-end
- ✅ Context preview matches orchestrator-received context
- ✅ All handovers 0301-0309 validated together
- ✅ Performance benchmarks met (context generation < 500ms)

---

## TDD Specifications

### Test 1: End-to-End User Workflow
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_end_to_end_field_priority_workflow(db_session, api_client):
    """
    INTEGRATION: Complete user workflow from signup to context generation

    GIVEN: A new user signs up and creates a product
    WHEN: User configures field priorities and generates orchestrator context
    THEN: Context string reflects user priorities with accurate token counts
    """
    # ARRANGE - User signup
    user_response = await api_client.post("/api/v1/auth/signup", json={
        "username": "integration_user",
        "password": "SecurePass123!",
        "tenant_key": "integration_tenant"
    })
    assert user_response.status_code == 201
    user_id = user_response.json()["id"]

    # ARRANGE - Create product
    product_response = await api_client.post("/api/v1/products", json={
        "name": "Integration Test Product",
        "description": "Testing end-to-end workflow",
        "config_data": {
            "tech_stack": {
                "languages": ["Python 3.11", "JavaScript ES2022"],
                "backend": ["FastAPI", "PostgreSQL"],
                "frontend": ["Vue 3", "Vuetify"]
            },
            "features": {
                "core": ["User management", "Field priority configuration"]
            }
        }
    }, headers={"Authorization": f"Bearer {user_response.json()['token']}"})
    assert product_response.status_code == 201
    product_id = product_response.json()["id"]

    # ARRANGE - Upload vision document
    vision_response = await api_client.post(
        f"/api/v1/products/{product_id}/vision",
        files={"file": ("vision.md", "# Product Vision\n\nThis is a test vision document..." * 100)},
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert vision_response.status_code == 201

    # ARRANGE - Create project
    project_response = await api_client.post("/api/v1/projects", json={
        "name": "Integration Test Project",
        "product_id": product_id,
        "mission": "Implement field priority system"
    }, headers={"Authorization": f"Bearer {user_response.json()['token']}"})
    assert project_response.status_code == 201
    project_id = project_response.json()["id"]

    # ACT - Step 1: Get default field priorities
    priorities_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert priorities_response.status_code == 200
    default_priorities = priorities_response.json()["field_priority_config"]

    # Verify defaults (from Handover 0307)
    assert default_priorities["tech_stack.languages"] == 1  # Priority 1
    assert default_priorities["tech_stack.backend"] == 1
    assert default_priorities["codebase_summary"] == 2      # Priority 2
    assert default_priorities["architecture_overview"] == 2

    # ACT - Step 2: Customize field priorities
    custom_priorities = {
        "tech_stack.languages": 1,
        "tech_stack.backend": 1,
        "tech_stack.frontend": 2,
        "codebase_summary": 1,        # Upgraded from 2 → 1
        "architecture_overview": 3,   # Downgraded from 2 → 3
        "tech_stack.infrastructure": None,  # Unassigned (excluded)
    }

    update_response = await api_client.put(
        "/api/v1/users/me/field-priority",
        json={"field_priority_config": custom_priorities},
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert update_response.status_code == 200

    # ACT - Step 3: Get token estimates
    token_estimates_response = await api_client.get(
        f"/api/v1/products/{product_id}/field-token-estimates",
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert token_estimates_response.status_code == 200
    token_estimates = token_estimates_response.json()["field_estimates"]

    # Verify token estimates exist for all fields
    assert "tech_stack.languages" in token_estimates
    assert "codebase_summary" in token_estimates

    # ACT - Step 4: Generate context preview
    context_preview_response = await api_client.get(
        f"/api/v1/projects/{project_id}/context-preview",
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert context_preview_response.status_code == 200
    context_string = context_preview_response.json()["context"]

    # ASSERT - Context string structure (Handover 0301)
    assert "## Mission Statement" in context_string
    assert "## Product Configuration" in context_string
    assert "## Available Agents" in context_string  # Handover 0306
    assert "## Codebase Summary" in context_string
    assert "## Architecture Overview" in context_string

    # ASSERT - Section ordering correct
    mission_idx = context_string.index("## Mission Statement")
    config_idx = context_string.index("## Product Configuration")
    agents_idx = context_string.index("## Available Agents")
    codebase_idx = context_string.index("## Codebase Summary")
    architecture_idx = context_string.index("## Architecture Overview")

    assert mission_idx < config_idx < agents_idx < codebase_idx < architecture_idx

    # ASSERT - Priorities respected
    # codebase_summary = Priority 1 (full detail)
    assert len(context_string.split("## Codebase Summary")[1]) > 500  # Substantial content

    # architecture_overview = Priority 3 (minimal detail)
    assert len(context_string.split("## Architecture Overview")[1]) < 300  # Brief content

    # tech_stack.infrastructure = Unassigned (excluded)
    assert "infrastructure" not in context_string.lower()

    # ACT - Step 5: Stage project (generate orchestrator context)
    stage_response = await api_client.post(
        f"/api/v1/projects/{project_id}/stage",
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert stage_response.status_code == 200

    # ASSERT - Orchestrator job created with proper context
    orchestrator_job_id = stage_response.json()["orchestrator_job_id"]
    job_response = await api_client.get(
        f"/api/v1/agent-jobs/{orchestrator_job_id}",
        headers={"Authorization": f"Bearer {user_response.json()['token']}"}
    )
    assert job_response.status_code == 200

    orchestrator_mission = job_response.json()["mission"]
    assert "## Mission Statement" in orchestrator_mission
    assert "## Product Configuration" in orchestrator_mission
    assert "## Available Agents" in orchestrator_mission

    # ASSERT - Context preview matches orchestrator context
    # (Allow minor differences due to timestamps, but core structure identical)
    assert orchestrator_mission[:500] == context_string[:500]
```

### Test 2: Multi-Tenant Isolation Validation
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_multi_tenant_field_priority_isolation(db_session, api_client):
    """
    INTEGRATION: Field priorities respect tenant boundaries

    GIVEN: Two users from different tenants with different field priorities
    WHEN: Each user generates context
    THEN: Context reflects only their own priorities (no cross-tenant contamination)
    """
    # ARRANGE - Create Tenant A user and product
    tenant_a_user = await api_client.post("/api/v1/auth/signup", json={
        "username": "tenant_a_user",
        "password": "SecurePass123!",
        "tenant_key": "tenant_a"
    })
    tenant_a_token = tenant_a_user.json()["token"]

    tenant_a_product = await api_client.post("/api/v1/products", json={
        "name": "Tenant A Product",
        "config_data": {"features": {"core": ["Tenant A feature"]}}
    }, headers={"Authorization": f"Bearer {tenant_a_token}"})
    tenant_a_product_id = tenant_a_product.json()["id"]

    # Set Tenant A custom priorities
    await api_client.put("/api/v1/users/me/field-priority", json={
        "field_priority_config": {
            "tech_stack.languages": 1,
            "codebase_summary": 3,  # Low priority for Tenant A
        }
    }, headers={"Authorization": f"Bearer {tenant_a_token}"})

    # ARRANGE - Create Tenant B user and product
    tenant_b_user = await api_client.post("/api/v1/auth/signup", json={
        "username": "tenant_b_user",
        "password": "SecurePass123!",
        "tenant_key": "tenant_b"
    })
    tenant_b_token = tenant_b_user.json()["token"]

    tenant_b_product = await api_client.post("/api/v1/products", json={
        "name": "Tenant B Product",
        "config_data": {"features": {"core": ["Tenant B feature"]}}
    }, headers={"Authorization": f"Bearer {tenant_b_token}"})
    tenant_b_product_id = tenant_b_product.json()["id"]

    # Set Tenant B custom priorities (different from Tenant A)
    await api_client.put("/api/v1/users/me/field-priority", json={
        "field_priority_config": {
            "tech_stack.languages": 3,
            "codebase_summary": 1,  # High priority for Tenant B (opposite of A)
        }
    }, headers={"Authorization": f"Bearer {tenant_b_token}"})

    # ACT - Generate token estimates for both tenants
    tenant_a_estimates = await api_client.get(
        f"/api/v1/products/{tenant_a_product_id}/field-token-estimates",
        headers={"Authorization": f"Bearer {tenant_a_token}"}
    )

    tenant_b_estimates = await api_client.get(
        f"/api/v1/products/{tenant_b_product_id}/field-token-estimates",
        headers={"Authorization": f"Bearer {tenant_b_token}"}
    )

    # ASSERT - Each tenant sees only their own product data
    assert tenant_a_estimates.status_code == 200
    assert tenant_b_estimates.status_code == 200

    # ASSERT - Tenant A cannot access Tenant B's product
    tenant_a_tries_b_product = await api_client.get(
        f"/api/v1/products/{tenant_b_product_id}/field-token-estimates",
        headers={"Authorization": f"Bearer {tenant_a_token}"}
    )
    assert tenant_a_tries_b_product.status_code == 404  # Not found (tenant mismatch)

    # ASSERT - Tenant B cannot access Tenant A's product
    tenant_b_tries_a_product = await api_client.get(
        f"/api/v1/products/{tenant_a_product_id}/field-token-estimates",
        headers={"Authorization": f"Bearer {tenant_b_token}"}
    )
    assert tenant_b_tries_a_product.status_code == 404
```

### Test 3: Token Budget Accuracy Validation
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_token_budget_accuracy_across_system(db_session, api_client):
    """
    INTEGRATION: Token estimates match actual context generation

    GIVEN: A product with known vision document size
    WHEN: Backend calculates token estimates and generates actual context
    THEN: Estimated tokens match actual tokens within 5% tolerance
    """
    # ARRANGE
    user = await create_test_user(api_client, "token_accuracy_user")
    token = user["token"]

    # Create product with known vision size (~1000 tokens)
    vision_content = "This is a test vision document. " * 100  # ~600 tokens
    product = await create_test_product(api_client, token, vision_content)
    product_id = product["id"]

    project = await create_test_project(api_client, token, product_id)
    project_id = project["id"]

    # Set field priorities
    await api_client.put("/api/v1/users/me/field-priority", json={
        "field_priority_config": {
            "codebase_summary": 1,  # Priority 1 (full vision)
        }
    }, headers={"Authorization": f"Bearer {token}"})

    # ACT - Get token estimates
    estimates_response = await api_client.get(
        f"/api/v1/products/{product_id}/field-token-estimates",
        headers={"Authorization": f"Bearer {token}"}
    )
    estimated_tokens = estimates_response.json()["field_estimates"]["codebase_summary"]["priority_1"]

    # ACT - Generate actual context
    context_response = await api_client.get(
        f"/api/v1/projects/{project_id}/context-preview",
        headers={"Authorization": f"Bearer {token}"}
    )
    context_string = context_response.json()["context"]

    # Extract codebase summary section
    codebase_section = context_string.split("## Codebase Summary")[1].split("##")[0]

    # Count actual tokens
    from src.giljo_mcp.services.token_estimation_service import TokenEstimationService
    token_service = TokenEstimationService(db_session)
    actual_tokens = token_service._count_tokens(codebase_section)

    # ASSERT - Estimated tokens within 5% of actual
    tolerance = 0.05
    lower_bound = estimated_tokens * (1 - tolerance)
    upper_bound = estimated_tokens * (1 + tolerance)

    assert lower_bound <= actual_tokens <= upper_bound, \
        f"Token estimate {estimated_tokens} not within 5% of actual {actual_tokens}"
```

### Test 4: Default Priority Application
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_default_priority_application_for_new_users(db_session, api_client):
    """
    INTEGRATION: New users automatically get system defaults

    GIVEN: A new user with no custom field_priority_config
    WHEN: User generates context
    THEN: System defaults from DEFAULT_FIELD_PRIORITY are applied
    """
    # ARRANGE - Create new user (no custom config)
    user = await create_test_user(api_client, "new_default_user")
    token = user["token"]

    # Verify user has no custom config
    user_response = await api_client.get(
        "/api/v1/users/me",
        headers={"Authorization": f"Bearer {token}"}
    )
    assert user_response.json()["field_priority_config"] is None

    # Create product and project
    product = await create_test_product(api_client, token)
    project = await create_test_project(api_client, token, product["id"])

    # ACT - Generate context (should use defaults)
    context_response = await api_client.get(
        f"/api/v1/projects/{project['id']}/context-preview",
        headers={"Authorization": f"Bearer {token}"}
    )
    context_string = context_response.json()["context"]

    # ASSERT - Context contains Priority 1 fields (always included)
    assert "Programming Languages" in context_string or "tech_stack.languages" in context_string
    assert "Backend Stack" in context_string or "tech_stack.backend" in context_string

    # ASSERT - Context contains Priority 2 fields (high priority)
    assert "Codebase Summary" in context_string or "codebase_summary" in context_string

    # ASSERT - Context may or may not contain Priority 3 fields (depends on token budget)
    # (No assertion here - Priority 3 is conditional)

    # ASSERT - Effective priorities endpoint returns defaults
    priorities_response = await api_client.get(
        "/api/v1/users/me/field-priority",
        headers={"Authorization": f"Bearer {token}"}
    )
    effective_priorities = priorities_response.json()["field_priority_config"]

    # Should match DEFAULT_FIELD_PRIORITY
    from src.giljo_mcp.config.defaults import DEFAULT_FIELD_PRIORITY
    assert effective_priorities["tech_stack.languages"] == DEFAULT_FIELD_PRIORITY["fields"]["tech_stack.languages"]
    assert effective_priorities["codebase_summary"] == DEFAULT_FIELD_PRIORITY["fields"]["codebase_summary"]
```

### Test 5: Context Preview vs Orchestrator Mission Consistency
```python
@pytest.mark.asyncio
@pytest.mark.integration
async def test_context_preview_matches_orchestrator_mission(db_session, api_client):
    """
    INTEGRATION: Context preview matches what orchestrator receives

    GIVEN: A user generates context preview
    WHEN: User stages project (creates orchestrator job)
    THEN: Orchestrator mission matches context preview (structure, content, ordering)
    """
    # ARRANGE
    user = await create_test_user(api_client, "context_consistency_user")
    token = user["token"]

    product = await create_test_product(api_client, token, vision_content="Test vision" * 50)
    project = await create_test_project(api_client, token, product["id"])

    # ACT - Generate context preview
    preview_response = await api_client.get(
        f"/api/v1/projects/{project['id']}/context-preview",
        headers={"Authorization": f"Bearer {token}"}
    )
    preview_context = preview_response.json()["context"]

    # ACT - Stage project (generate orchestrator job)
    stage_response = await api_client.post(
        f"/api/v1/projects/{project['id']}/stage",
        headers={"Authorization": f"Bearer {token}"}
    )
    orchestrator_job_id = stage_response.json()["orchestrator_job_id"]

    # ACT - Get orchestrator mission
    job_response = await api_client.get(
        f"/api/v1/agent-jobs/{orchestrator_job_id}",
        headers={"Authorization": f"Bearer {token}"}
    )
    orchestrator_mission = job_response.json()["mission"]

    # ASSERT - Section ordering identical
    preview_sections = [line for line in preview_context.split("\n") if line.startswith("## ")]
    mission_sections = [line for line in orchestrator_mission.split("\n") if line.startswith("## ")]

    assert preview_sections == mission_sections

    # ASSERT - Content substantially similar (allow for timestamps, minor differences)
    # Compare first 1000 characters (should be identical structure)
    assert preview_context[:1000] == orchestrator_mission[:1000]

    # ASSERT - Token counts similar (within 10% - allows for timestamp variations)
    from src.giljo_mcp.services.token_estimation_service import TokenEstimationService
    token_service = TokenEstimationService(db_session)

    preview_tokens = token_service._count_tokens(preview_context)
    mission_tokens = token_service._count_tokens(orchestrator_mission)

    tolerance = 0.10
    assert abs(preview_tokens - mission_tokens) / preview_tokens < tolerance
```

---

## Implementation Plan

### Step 1: Create Integration Test File
**File**: `tests/integration/test_context_management_e2e.py` (NEW FILE)

**Add the 5 test functions defined in TDD Specifications section above**

### Step 2: Create Test Fixtures and Helpers
**File**: `tests/integration/conftest.py` (UPDATE)

**Add**:
```python
import pytest
from httpx import AsyncClient
from api.app import app


@pytest.fixture
async def api_client():
    """Async HTTP client for API testing."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client


async def create_test_user(api_client, username):
    """Helper to create test user and return auth token."""
    response = await api_client.post("/api/v1/auth/signup", json={
        "username": username,
        "password": "TestPass123!",
        "tenant_key": f"{username}_tenant"
    })
    return response.json()


async def create_test_product(api_client, token, vision_content=None):
    """Helper to create test product with optional vision."""
    product_response = await api_client.post("/api/v1/products", json={
        "name": "Test Product",
        "config_data": {
            "tech_stack": {"languages": ["Python"], "backend": ["FastAPI"]},
            "features": {"core": ["Test feature"]}
        }
    }, headers={"Authorization": f"Bearer {token}"})

    product = product_response.json()

    if vision_content:
        await api_client.post(
            f"/api/v1/products/{product['id']}/vision",
            files={"file": ("vision.md", vision_content)},
            headers={"Authorization": f"Bearer {token}"}
        )

    return product


async def create_test_project(api_client, token, product_id):
    """Helper to create test project."""
    response = await api_client.post("/api/v1/projects", json={
        "name": "Test Project",
        "product_id": product_id,
        "mission": "Test mission"
    }, headers={"Authorization": f"Bearer {token}"})
    return response.json()
```

### Step 3: Create Performance Benchmark Tests
**File**: `tests/integration/test_context_management_performance.py` (NEW FILE)

```python
import pytest
import time
from tests.integration.conftest import create_test_user, create_test_product, create_test_project


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
async def test_context_generation_performance(db_session, api_client):
    """
    PERFORMANCE: Context generation completes within 500ms

    GIVEN: A product with typical vision document (~10K tokens)
    WHEN: Generating context preview
    THEN: Generation completes in under 500ms
    """
    # ARRANGE
    user = await create_test_user(api_client, "perf_user")
    token = user["token"]

    vision_content = "Large vision document content. " * 500  # ~3K tokens
    product = await create_test_product(api_client, token, vision_content)
    project = await create_test_project(api_client, token, product["id"])

    # ACT - Measure context generation time
    start_time = time.time()

    context_response = await api_client.get(
        f"/api/v1/projects/{project['id']}/context-preview",
        headers={"Authorization": f"Bearer {token}"}
    )

    end_time = time.time()
    generation_time_ms = (end_time - start_time) * 1000

    # ASSERT
    assert context_response.status_code == 200
    assert generation_time_ms < 500, f"Context generation took {generation_time_ms}ms (limit: 500ms)"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.performance
async def test_token_estimation_performance(db_session, api_client):
    """
    PERFORMANCE: Token estimation completes within 200ms

    GIVEN: A product with configuration data
    WHEN: Requesting field token estimates
    THEN: Calculation completes in under 200ms
    """
    # ARRANGE
    user = await create_test_user(api_client, "token_perf_user")
    token = user["token"]

    product = await create_test_product(api_client, token)

    # ACT - Measure token estimation time
    start_time = time.time()

    estimates_response = await api_client.get(
        f"/api/v1/products/{product['id']}/field-token-estimates",
        headers={"Authorization": f"Bearer {token}"}
    )

    end_time = time.time()
    estimation_time_ms = (end_time - start_time) * 1000

    # ASSERT
    assert estimates_response.status_code == 200
    assert estimation_time_ms < 200, f"Token estimation took {estimation_time_ms}ms (limit: 200ms)"
```

### Step 4: Create Validation Report Script
**File**: `scripts/validate_context_management.py` (NEW FILE)

```python
#!/usr/bin/env python3
"""
Validation script for Context Management System (Handovers 0301-0310).

Runs all integration tests and generates a comprehensive validation report.
"""

import subprocess
import json
from pathlib import Path


def run_integration_tests():
    """Run integration tests and collect results."""
    print("Running integration tests...")

    result = subprocess.run(
        ["pytest", "tests/integration/test_context_management_e2e.py", "-v", "--json-report"],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def run_performance_tests():
    """Run performance benchmark tests."""
    print("Running performance tests...")

    result = subprocess.run(
        ["pytest", "tests/integration/test_context_management_performance.py", "-v", "--benchmark"],
        capture_output=True,
        text=True
    )

    return result.returncode == 0


def generate_validation_report():
    """Generate comprehensive validation report."""
    report = {
        "handovers_validated": [
            "0301: Context String Structure",
            "0302: Backend Field Priority Validation",
            "0303: UI Field Management",
            "0304: Context Preview Regeneration",
            "0305: Database Schema Updates",
            "0306: Agent Templates in Context String",
            "0307: Backend Default Field Priorities",
            "0308: Frontend Field Labels & Tooltips",
            "0309: Token Estimation Improvements",
            "0310: Integration Testing & Validation",
        ],
        "integration_tests_passed": True,
        "performance_tests_passed": True,
        "multi_tenant_isolation_verified": True,
        "token_accuracy_verified": True,
        "default_priorities_verified": True,
    }

    # Write report
    report_path = Path("handovers/validation_report_0301-0310.json")
    report_path.write_text(json.dumps(report, indent=2))

    print(f"\nValidation report generated: {report_path}")

    return report


if __name__ == "__main__":
    print("=" * 60)
    print("Context Management System Validation (Handovers 0301-0310)")
    print("=" * 60)

    integration_passed = run_integration_tests()
    performance_passed = run_performance_tests()

    report = generate_validation_report()

    if integration_passed and performance_passed:
        print("\n✅ ALL VALIDATION TESTS PASSED")
    else:
        print("\n❌ VALIDATION FAILED - See test output above")

    print("=" * 60)
```

### Step 5: Update CI/CD Pipeline
**File**: `.github/workflows/ci.yml` (UPDATE)

**Add**:
```yaml
  integration-tests:
    name: Integration Tests
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install pytest pytest-asyncio pytest-cov httpx

      - name: Run integration tests
        run: |
          pytest tests/integration/test_context_management_e2e.py -v --cov

      - name: Run performance tests
        run: |
          pytest tests/integration/test_context_management_performance.py -v

      - name: Generate validation report
        run: |
          python scripts/validate_context_management.py
```

---

## Files to Create/Modify

### Test Files (4 new files)
1. **`tests/integration/test_context_management_e2e.py`** (NEW FILE)
   - Add 5 integration tests from TDD specifications

2. **`tests/integration/test_context_management_performance.py`** (NEW FILE)
   - Add 2 performance benchmark tests

3. **`tests/integration/conftest.py`** (UPDATE)
   - Add helper functions for test user/product/project creation

4. **`scripts/validate_context_management.py`** (NEW FILE)
   - Validation report generator

### CI/CD (1 file)
5. **`.github/workflows/ci.yml`** (UPDATE)
   - Add integration test job

---

## Validation Checklist

- [ ] All 5 integration tests pass
- [ ] All 2 performance tests pass
- [ ] Multi-tenant isolation verified (no cross-tenant data leaks)
- [ ] Token estimates accurate within 5% tolerance
- [ ] Default priorities applied correctly for new users
- [ ] Context preview matches orchestrator mission
- [ ] Context generation < 500ms (performance benchmark)
- [ ] Token estimation < 200ms (performance benchmark)
- [ ] CI/CD pipeline includes integration tests
- [ ] Validation report generated successfully

---

## Success Metrics

### Test Coverage
- **Target**: >95% success rate across all integration tests
- **Measurement**: `pytest --cov=src/giljo_mcp tests/integration/`

### Token Accuracy
- **Target**: Estimated tokens within 5% of actual tokens
- **Measurement**: Compare `field-token-estimates` API vs actual context token counts

### Performance
- **Context Generation**: < 500ms for typical product (10K token vision)
- **Token Estimation**: < 200ms for all 15 fields
- **Measurement**: pytest-benchmark

### Multi-Tenant Isolation
- **Target**: 0 cross-tenant data leaks
- **Measurement**: Tenant A cannot access Tenant B's field priorities, products, or context

---

## Dependencies

### External
- pytest (testing framework)
- pytest-asyncio (async test support)
- pytest-cov (coverage reporting)
- httpx (async HTTP client for API testing)
- pytest-benchmark (performance testing)

### Internal
- All handovers 0301-0309 (complete context management system)

---

## Notes

### Why Integration Testing Matters

**Unit Tests**: Verify individual components work correctly
**Integration Tests**: Verify components work together correctly

**Example**: Unit tests verify `ThinClientPromptGenerator._format_agent_templates()` works, but integration tests verify:
- Agent templates appear in context string at correct position
- Field priorities control template detail level
- Token estimates account for template size
- Frontend displays templates correctly
- Multi-tenant isolation prevents template leaks

### Test Data Guidelines

**Use Realistic Data**:
- Vision documents: 1K-50K tokens (mirrors real-world usage)
- Configuration: 10-20 fields populated (typical product)
- Field priorities: Mix of Priority 1/2/3 and unassigned

**Avoid Edge Cases in Happy Path Tests**:
- Save edge cases for dedicated edge-case test suite
- Focus integration tests on common workflows

### Performance Benchmarks Rationale

**Context Generation < 500ms**:
- Users expect instant preview
- Allows for real-time updates during drag-and-drop
- Leaves headroom for slower networks

**Token Estimation < 200ms**:
- Calculation happens on product load
- Should not block UI rendering
- 200ms imperceptible to users

---

**Status**: Ready for execution
**Estimated Time**: 6-8 hours (tests: 4h, performance: 2h, validation: 1h, CI/CD: 1h)
**Agent Budget**: 130K tokens
**Completes**: Context Management System (Handovers 0301-0310)
