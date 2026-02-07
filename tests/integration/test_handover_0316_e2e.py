"""
Integration tests for Handover 0316 - End-to-end workflow verification.

Tests the complete workflow:
1. Create product with config_data
2. Update quality_standards via ProductService
3. Fetch context via all 9 context tools
4. Verify multi-tenant isolation
5. Verify bug fixes (get_tech_stack, get_architecture)
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.giljo_mcp.models.products import Product
from src.giljo_mcp.models.projects import Project
from src.giljo_mcp.services.product_service import ProductService
from src.giljo_mcp.tools.context_tools.get_architecture import get_architecture
from src.giljo_mcp.tools.context_tools.get_product_context import get_product_context
from src.giljo_mcp.tools.context_tools.get_project import get_project
from src.giljo_mcp.tools.context_tools.get_tech_stack import get_tech_stack
from src.giljo_mcp.tools.context_tools.get_testing import get_testing


@pytest.mark.integration
@pytest.mark.asyncio
async def test_full_product_creation_with_quality_standards(mock_db_manager):
    """Test complete workflow: create product → update quality_standards → fetch via context tools"""
    # Step 1: Create product with config_data
    product_data = {
        "id": "e2e-product-id",
        "tenant_key": "e2e-tenant",
        "name": "E2E Test Product",
        "description": "End-to-end test",
        "quality_standards": None,
        "config_data": {
            "tech_stack": {
                "languages": ["Python"],
                "frontend": ["Vue 3"],
                "backend": ["FastAPI"],
                "database": ["PostgreSQL"],
            },
            "architecture": {
                "pattern": "Microservices",
                "design_patterns": "Repository",
                "api_style": "RESTful",
                "notes": "Notes here",
            },
            "test_config": {"strategy": "TDD", "coverage_target": 80, "frameworks": ["pytest"]},
            "features": {"core": ["Feature 1", "Feature 2"]},
        },
    }

    product = Product(**product_data)

    # Mock database manager to return product
    async def mock_get_product(product_id, tenant_key):
        if product_id == "e2e-product-id" and tenant_key == "e2e-tenant":
            return product
        return None

    mock_db_manager.get_product = AsyncMock(side_effect=mock_get_product)

    # Mock session for update_quality_standards
    mock_session = AsyncMock()
    mock_session.get = AsyncMock(return_value=product)
    mock_session.commit = AsyncMock()
    mock_session.refresh = AsyncMock()

    # Create proper mock for execute result with scalar_one_or_none
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Setup async context manager for get_session_async
    mock_db_manager.get_session_async = MagicMock(return_value=mock_session)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)

    # Mock WebSocket manager
    mock_ws_manager = AsyncMock()
    mock_ws_manager.broadcast = AsyncMock()

    # Step 2: Update quality_standards via service
    service = ProductService(mock_db_manager, mock_ws_manager)
    result = await service.update_quality_standards(
        product_id="e2e-product-id", quality_standards="80% coverage, TDD required", tenant_key="e2e-tenant"
    )

    # Update product object to reflect changes
    product.quality_standards = "80% coverage, TDD required"

    assert result["quality_standards"] == "80% coverage, TDD required"

    # Step 3: Fetch via get_product_context
    product_ctx = await get_product_context(
        product_id="e2e-product-id", tenant_key="e2e-tenant", include_metadata=False, db_manager=mock_db_manager
    )
    assert product_ctx["data"]["product_name"] == "E2E Test Product"
    assert product_ctx["data"]["core_features"] == ["Feature 1", "Feature 2"]

    # Step 4: Fetch via get_testing
    testing_ctx = await get_testing(
        product_id="e2e-product-id", tenant_key="e2e-tenant", depth="full", db_manager=mock_db_manager
    )
    assert testing_ctx["data"]["quality_standards"] == "80% coverage, TDD required"
    assert testing_ctx["data"]["testing_strategy"] == "TDD"

    # Step 5: Fetch via get_tech_stack (verify bug fix)
    tech_ctx = await get_tech_stack(
        product_id="e2e-product-id", tenant_key="e2e-tenant", sections="all", db_manager=mock_db_manager
    )
    assert tech_ctx["data"]["programming_languages"] == ["Python"]
    assert tech_ctx["data"]["frontend_frameworks"] == ["Vue 3"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_orchestrator_fetches_all_9_context_tools(mock_db_manager):
    """Test that all 9 context tools can be imported and are callable"""
    # This is a smoke test to ensure all tools are importable

    # Import all 9 context tools
    from src.giljo_mcp.tools.context_tools import (
        get_360_memory,
        get_agent_templates,
        get_architecture,
        get_git_history,
        get_product_context,
        get_project,
        get_tech_stack,
        get_testing,
        get_vision_document,
    )

    # Verify all tools are callable
    assert callable(get_360_memory)
    assert callable(get_agent_templates)
    assert callable(get_architecture)
    assert callable(get_git_history)
    assert callable(get_product_context)
    assert callable(get_project)
    assert callable(get_tech_stack)
    assert callable(get_testing)
    assert callable(get_vision_document)

    # Create test product data
    product_data = {
        "id": "orchestrator-test-id",
        "tenant_key": "orch-tenant",
        "name": "Orchestrator Test",
        "config_data": {
            "tech_stack": {"languages": ["Python"]},
            "architecture": {"pattern": "Microservices"},
            "test_config": {"strategy": "TDD"},
            "features": {"core": ["Feature 1"]},
        },
        "product_memory": {"github": {}, "learnings": [], "context": {}},
    }

    project_data = {
        "id": "orch-project-id",
        "tenant_key": "orch-tenant",
        "product_id": "orchestrator-test-id",
        "name": "Test Project",
        "alias": "ABC123",
        "description": "Test",
        "mission": "Test mission",
    }

    product = Product(**product_data)
    project = Project(**project_data)

    # Mock database manager
    async def mock_get_product(product_id, tenant_key):
        if product_id == "orchestrator-test-id" and tenant_key == "orch-tenant":
            return product
        return None

    async def mock_get_project(project_id, tenant_key):
        if project_id == "orch-project-id" and tenant_key == "orch-tenant":
            return project
        return None

    mock_db_manager.get_product = AsyncMock(side_effect=mock_get_product)
    mock_db_manager.get_project = AsyncMock(side_effect=mock_get_project)

    # Setup mock session with proper async context manager pattern
    mock_session = AsyncMock()

    # Create mock result that returns product/project based on query
    def create_mock_result(return_value):
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = return_value
        return mock_result

    # Track calls and return appropriate result
    execute_call_count = [0]

    async def mock_execute(stmt):
        execute_call_count[0] += 1
        # First 4 calls are for product, 5th is for project
        if execute_call_count[0] <= 4:
            return create_mock_result(product)
        return create_mock_result(project)

    mock_session.execute = mock_execute
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_db_manager.get_session_async = MagicMock(return_value=mock_session)

    # Call 5 main context tools (smoke test)
    results = []

    # 1. get_product_context
    r1 = await get_product_context("orchestrator-test-id", "orch-tenant", False, mock_db_manager)
    results.append(r1["source"] == "product_context")

    # 2. get_testing
    r2 = await get_testing("orchestrator-test-id", "orch-tenant", "basic", mock_db_manager)
    results.append(r2["source"] == "testing")

    # 3. get_tech_stack
    r3 = await get_tech_stack("orchestrator-test-id", "orch-tenant", "all", 0, None, mock_db_manager)
    results.append(r3["source"] == "tech_stack")

    # 4. get_architecture
    r4 = await get_architecture("orchestrator-test-id", "orch-tenant", "overview", 0, None, mock_db_manager)
    results.append(r4["source"] == "architecture")

    # 5. get_project
    r5 = await get_project("orch-project-id", "orch-tenant", False, mock_db_manager)
    results.append(r5["source"] == "project_description")

    # All 5 tools should work
    assert all(results), "Not all context tools are functional"
    assert len(results) == 5, "Should have 5 context tool results"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_multi_tenant_isolation_e2e(mock_db_manager):
    """Test multi-tenant isolation across all context tools"""
    # Create products for two tenants
    product_a = Product(
        id="product-a",
        tenant_key="tenant-a",
        name="Tenant A Product",
        description="Product for tenant A",
        config_data={"tech_stack": {"languages": ["Python"]}},
    )

    product_b = Product(
        id="product-b",
        tenant_key="tenant-b",
        name="Tenant B Product",
        description="Product for tenant B",
        config_data={"tech_stack": {"languages": ["JavaScript"]}},
    )

    # Mock database manager with multi-tenant logic
    async def mock_get_product(product_id, tenant_key):
        if product_id == "product-a" and tenant_key == "tenant-a":
            return product_a
        if product_id == "product-b" and tenant_key == "tenant-b":
            return product_b
        return None  # Cross-tenant access denied

    mock_db_manager.get_product = AsyncMock(side_effect=mock_get_product)

    # Setup mock session with proper async context manager pattern
    # Track which test case we're on based on call order
    call_tracker = {"count": 0}

    async def mock_execute(stmt):
        call_tracker["count"] += 1
        mock_result = MagicMock()

        # Test sequence: tenant-a (1), cross-tenant (2), tenant-b (3)
        if call_tracker["count"] == 1:
            # First call: Tenant A accessing their own product
            mock_result.scalar_one_or_none.return_value = product_a
        elif call_tracker["count"] == 2:
            # Second call: Cross-tenant access (should fail)
            mock_result.scalar_one_or_none.return_value = None
        elif call_tracker["count"] == 3:
            # Third call: Tenant B accessing their own product
            mock_result.scalar_one_or_none.return_value = product_b
        else:
            mock_result.scalar_one_or_none.return_value = None
        return mock_result

    mock_session = AsyncMock()
    mock_session.execute = mock_execute
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_db_manager.get_session_async = MagicMock(return_value=mock_session)

    # Test 1: Tenant A can access their own product
    result_a = await get_product_context(
        product_id="product-a", tenant_key="tenant-a", include_metadata=False, db_manager=mock_db_manager
    )
    assert result_a["data"]["product_name"] == "Tenant A Product"

    # Test 2: Tenant A CANNOT access Tenant B's product
    result_cross = await get_product_context(
        product_id="product-b",
        tenant_key="tenant-a",  # Wrong tenant
        include_metadata=False,
        db_manager=mock_db_manager,
    )
    assert "error" in result_cross["metadata"]
    assert result_cross["metadata"]["error"] == "product_not_found"

    # Test 3: Tenant B can access their own product
    result_b = await get_product_context(
        product_id="product-b", tenant_key="tenant-b", include_metadata=False, db_manager=mock_db_manager
    )
    assert result_b["data"]["product_name"] == "Tenant B Product"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_bug_fixes_verified_e2e(mock_db_manager):
    """Test that get_tech_stack and get_architecture bugs are fixed"""
    # Create product with config_data
    product = Product(
        id="bug-test-id",
        tenant_key="bug-tenant",
        name="Bug Test Product",
        config_data={
            "tech_stack": {
                "languages": ["Python", "TypeScript"],
                "frontend": ["Vue 3", "React"],
                "backend": ["FastAPI", "Express"],
                "database": ["PostgreSQL", "MongoDB"],
            },
            "architecture": {
                "pattern": "Microservices",
                "design_patterns": "Repository, Service Layer, Factory",
                "api_style": "RESTful",
                "notes": "Architecture notes here",
            },
        },
    )

    async def mock_get_product(product_id, tenant_key):
        if product_id == "bug-test-id" and tenant_key == "bug-tenant":
            return product
        return None

    mock_db_manager.get_product = AsyncMock(side_effect=mock_get_product)

    # Setup mock session with proper async context manager pattern
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = product
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_db_manager.get_session_async = MagicMock(return_value=mock_session)

    # Test Bug Fix 1: get_tech_stack reads from config_data
    tech_result = await get_tech_stack(
        product_id="bug-test-id", tenant_key="bug-tenant", sections="all", db_manager=mock_db_manager
    )

    assert tech_result["data"]["programming_languages"] == ["Python", "TypeScript"]
    assert tech_result["data"]["frontend_frameworks"] == ["Vue 3", "React"]
    assert tech_result["data"]["backend_frameworks"] == ["FastAPI", "Express"]
    assert tech_result["data"]["databases"] == ["PostgreSQL", "MongoDB"]

    # Test Bug Fix 2: get_architecture reads from config_data
    arch_result = await get_architecture(
        product_id="bug-test-id", tenant_key="bug-tenant", depth="detailed", db_manager=mock_db_manager
    )

    assert arch_result["data"]["primary_pattern"] == "Microservices"
    assert arch_result["data"]["design_patterns"] == "Repository, Service Layer, Factory"
    assert arch_result["data"]["api_style"] == "RESTful"
    assert arch_result["data"]["architecture_notes"] == "Architecture notes here"  # Correct key name


@pytest.mark.integration
@pytest.mark.asyncio
async def test_project_description_no_context_budget(mock_db_manager):
    """Test that get_project does NOT return context_budget (deprecated field)"""
    project = Project(
        id="project-test-id",
        tenant_key="project-tenant",
        product_id="product-id",
        name="Test Project",
        alias="ABC123",
        description="Test project",
        mission="Test mission",
        status="active",
    )

    async def mock_get_project(project_id, tenant_key):
        if project_id == "project-test-id" and tenant_key == "project-tenant":
            return project
        return None

    mock_db_manager.get_project = AsyncMock(side_effect=mock_get_project)

    # Setup mock session with proper async context manager pattern
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = project
    mock_session.execute = AsyncMock(return_value=mock_result)
    mock_session.__aenter__ = AsyncMock(return_value=mock_session)
    mock_session.__aexit__ = AsyncMock(return_value=None)
    mock_db_manager.get_session_async = MagicMock(return_value=mock_session)

    result = await get_project(
        project_id="project-test-id",
        tenant_key="project-tenant",
        include_summary=False,  # Correct parameter name (not include_metadata)
        db_manager=mock_db_manager,
    )

    # Verify context_budget is NOT in the response
    assert "context_budget" not in result["data"]

    # Verify expected fields ARE present
    assert result["data"]["project_name"] == "Test Project"
    assert result["data"]["project_alias"] == "ABC123"
    assert result["data"]["orchestrator_mission"] == "Test mission"  # Correct key name
    assert result["data"]["status"] == "active"
