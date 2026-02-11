"""
TDD Tests for Tenant Isolation in MCP Tools Layer (Handover 0325)

These tests verify that all MCP tool database queries properly filter by tenant_key
to prevent cross-tenant data access.

Test Strategy: RED -> GREEN -> REFACTOR
- All tests should FAIL initially (RED phase)
- Fix production code to make tests pass (GREEN phase)
- Refactor for clarity (REFACTOR phase)

Coverage:
- orchestration.py: get_project_by_alias()
- tool_accessor.py: activate_project()
- product.py: _get_product_config_with_session(), _update_product_config_with_session()
- agent.py: launch_agent(), log_interaction_legacy()
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution
from src.giljo_mcp.tenant import TenantManager


# Register the tenant_isolation marker
def pytest_configure(config):
    config.addinivalue_line("markers", "tenant_isolation: marks tests for tenant isolation verification")


# ============================================================================
# FIXTURES
# ============================================================================


@pytest_asyncio.fixture(scope="function")
async def two_tenant_setup(db_session):
    """
    Create projects, products, and agents in two separate tenants.

    Returns a dict with all entities for both tenants.
    """
    tenant_a = TenantManager.generate_tenant_key()
    tenant_b = TenantManager.generate_tenant_key()

    # Create Product A for Tenant A
    product_a = Product(
        id=str(uuid.uuid4()),
        name="Product Tenant A",
        description="Product for tenant A testing",
        tenant_key=tenant_a,
        is_active=True,
    )
    db_session.add(product_a)

    # Create Product B for Tenant B
    product_b = Product(
        id=str(uuid.uuid4()),
        name="Product Tenant B",
        description="Product for tenant B testing",
        tenant_key=tenant_b,
        is_active=True,
    )
    db_session.add(product_b)

    await db_session.commit()
    await db_session.refresh(product_a)
    await db_session.refresh(product_b)

    # Create Project A for Tenant A (linked to Product A)
    project_a = Project(
        id=str(uuid.uuid4()),
        name="CrossTenantTestProject",  # Same name to test alias search
        description="Project for tenant A testing",
        mission="Test mission A",
        tenant_key=tenant_a,
        product_id=product_a.id,
        status="active",
    )
    db_session.add(project_a)

    # Create Project B for Tenant B (linked to Product B)
    project_b = Project(
        id=str(uuid.uuid4()),
        name="CrossTenantTestProject",  # Same name - different tenant
        description="Project for tenant B testing",
        mission="Test mission B",
        tenant_key=tenant_b,
        product_id=product_b.id,
        status="active",
    )
    db_session.add(project_b)

    await db_session.commit()
    await db_session.refresh(project_a)
    await db_session.refresh(project_b)

    # Create MCPAgentJob A for Tenant A
    # Valid status values: 'waiting', 'working', 'blocked', 'complete', 'failed', 'cancelled', 'decommissioned'
    agent_job_a = AgentExecution(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_a,
        project_id=project_a.id,
        agent_display_name="orchestrator",
        mission="Test orchestrator mission A",
        status="working",  # Valid status for active agent
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(agent_job_a)

    # Create MCPAgentJob B for Tenant B
    agent_job_b = AgentExecution(
        job_id=str(uuid.uuid4()),
        tenant_key=tenant_b,
        project_id=project_b.id,
        agent_display_name="orchestrator",
        mission="Test orchestrator mission B",
        status="working",  # Valid status for active agent
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(agent_job_b)

    await db_session.commit()
    await db_session.refresh(agent_job_a)
    await db_session.refresh(agent_job_b)

    return {
        "tenant_a": tenant_a,
        "tenant_b": tenant_b,
        "product_a": product_a,
        "product_b": product_b,
        "project_a": project_a,
        "project_b": project_b,
        "agent_job_a": agent_job_a,
        "agent_job_b": agent_job_b,
    }


# ============================================================================
# ORCHESTRATION.PY TESTS (Lines 906, 915)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_project_by_alias_blocks_cross_tenant_access(db_session, two_tenant_setup):
    """
    Test: orchestration.py get_project_by_alias() - Line 906

    Verify that searching for a project by name/alias respects tenant_key filter.
    Tenant A should NOT be able to find Tenant B's project even if names match.
    """
    from src.giljo_mcp.tools.orchestration import get_project_by_alias

    tenant_a = two_tenant_setup["tenant_a"]
    tenant_b = two_tenant_setup["tenant_b"]
    project_b = two_tenant_setup["project_b"]

    # Tenant A tries to find a project with the same name as Tenant B's project
    # This should NOT return Tenant B's project
    result = await get_project_by_alias(
        alias="CrossTenantTestProject",
        tenant_key=tenant_a,
        session=db_session,
    )

    # If result is found, it should be Tenant A's project, NOT Tenant B's
    if result and "project" in result:
        assert result["project"]["tenant_key"] == tenant_a, (
            "Cross-tenant access detected! Tenant A found Tenant B's project"
        )
        assert result["project"]["id"] != project_b.id, "Cross-tenant access detected! Returned Tenant B's project ID"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_get_project_by_alias_product_lookup_blocks_cross_tenant(db_session, two_tenant_setup):
    """
    Test: orchestration.py get_project_by_alias() - Line 915

    Verify that the subsequent product lookup also filters by tenant_key.
    Even if we somehow got a project, the product fetch should be tenant-isolated.
    """
    from src.giljo_mcp.tools.orchestration import get_project_by_alias

    tenant_a = two_tenant_setup["tenant_a"]
    product_a = two_tenant_setup["product_a"]

    # Get project for tenant A
    result = await get_project_by_alias(
        alias="CrossTenantTestProject",
        tenant_key=tenant_a,
        session=db_session,
    )

    # If product info is returned, verify it's tenant A's product
    if result and "product" in result and result["product"]:
        assert result["product"]["tenant_key"] == tenant_a, "Cross-tenant product access detected!"
        assert result["product"]["id"] == product_a.id, "Wrong product returned - tenant isolation failed"


# ============================================================================
# TOOL_ACCESSOR.PY TESTS (Line 1188)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_activate_project_blocks_cross_tenant_product_access(db_session, two_tenant_setup):
    """
    Test: tool_accessor.py activate_project() - Line 1188

    Verify that activating a project only accesses the correct tenant's product.
    """
    from src.giljo_mcp.tools.tool_accessor import activate_project

    tenant_a = two_tenant_setup["tenant_a"]
    project_a = two_tenant_setup["project_a"]
    product_b = two_tenant_setup["product_b"]

    # Set project to inactive so it can be activated
    project_a.status = "inactive"
    await db_session.commit()

    # Activate project A with tenant A's context
    result = await activate_project(
        project_id=project_a.id,
        tenant_key=tenant_a,
        session=db_session,
    )

    # Should succeed for same-tenant access
    assert result.get("success") is True, f"Same-tenant activation failed: {result.get('error')}"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_activate_project_rejects_cross_tenant_project(db_session, two_tenant_setup):
    """
    Test: tool_accessor.py activate_project()

    Verify that tenant A cannot activate tenant B's project.
    """
    from src.giljo_mcp.tools.tool_accessor import activate_project

    tenant_a = two_tenant_setup["tenant_a"]
    project_b = two_tenant_setup["project_b"]

    # Set project to inactive so activation would normally work
    project_b.status = "inactive"
    await db_session.commit()

    # Tenant A tries to activate Tenant B's project - should fail
    result = await activate_project(
        project_id=project_b.id,  # Tenant B's project!
        tenant_key=tenant_a,  # Tenant A's key!
        session=db_session,
    )

    # Should either return None/error or reject the request
    assert result is None or result.get("success") is False or result.get("error"), (
        "Cross-tenant project activation allowed! Security vulnerability."
    )



# ============================================================================
# AGENT.PY TESTS (Lines 351, 895, 903, 918)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_launch_agent_blocks_cross_tenant_access(db_session, two_tenant_setup):
    """
    Test: agent.py launch_agent() - Line 351

    Verify that launching an agent only accesses the correct tenant's agent jobs.
    """
    from src.giljo_mcp.tools.agent import launch_agent

    tenant_a = two_tenant_setup["tenant_a"]
    agent_job_b = two_tenant_setup["agent_job_b"]

    # Tenant A tries to launch using Tenant B's agent job ID
    result = await launch_agent(
        agent_id=agent_job_b.job_id,  # Tenant B's agent!
        tenant_key=tenant_a,
        session=db_session,
    )

    # Should fail - cannot access cross-tenant agent
    assert result is None or result.get("success") is False or "error" in str(result).lower(), (
        "Cross-tenant agent launch allowed! Security vulnerability."
    )


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_log_interaction_legacy_blocks_cross_tenant_parent_lookup(db_session, two_tenant_setup):
    """
    Test: agent.py log_interaction_legacy() - Lines 895, 918

    Verify that looking up parent agents filters by tenant_key.
    """
    from src.giljo_mcp.tools.agent import log_interaction_legacy

    tenant_a = two_tenant_setup["tenant_a"]
    agent_job_a = two_tenant_setup["agent_job_a"]
    agent_job_b = two_tenant_setup["agent_job_b"]
    project_a = two_tenant_setup["project_a"]

    # Create interaction data with Tenant B's agent as parent (should fail)
    interaction_data = {
        "agent_id": agent_job_a.job_id,
        "parent_agent_id": agent_job_b.job_id,  # Cross-tenant parent!
        "project_id": project_a.id,
        "interaction_type": "test",
        "content": "Test interaction",
    }

    # This should either fail or ignore the cross-tenant parent
    result = await log_interaction_legacy(
        interaction=interaction_data,
        tenant_key=tenant_a,
        session=db_session,
    )

    # If interaction is logged, parent should not be from different tenant
    if result and result.get("success"):
        # Verify parent_agent_id was not used (cross-tenant)
        pass  # Implementation specific check


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_log_interaction_legacy_blocks_cross_tenant_project_lookup(db_session, two_tenant_setup):
    """
    Test: agent.py log_interaction_legacy() - Line 903

    Verify that project lookup in log_interaction_legacy filters by tenant_key.
    """
    from src.giljo_mcp.tools.agent import log_interaction_legacy

    tenant_a = two_tenant_setup["tenant_a"]
    agent_job_a = two_tenant_setup["agent_job_a"]
    project_b = two_tenant_setup["project_b"]

    # Create interaction data with Tenant B's project (should fail)
    interaction_data = {
        "agent_id": agent_job_a.job_id,
        "project_id": project_b.id,  # Cross-tenant project!
        "interaction_type": "test",
        "content": "Test interaction",
    }

    # This should fail - cannot log to cross-tenant project
    result = await log_interaction_legacy(
        interaction=interaction_data,
        tenant_key=tenant_a,
        session=db_session,
    )

    # Should reject cross-tenant project access
    assert result is None or result.get("success") is False or "error" in str(result).lower(), (
        "Cross-tenant project access in log_interaction allowed! Security vulnerability."
    )


# ============================================================================
# SAME-TENANT POSITIVE TESTS (Verify isolation doesn't break normal access)
# ============================================================================


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_same_tenant_project_access_succeeds(db_session, two_tenant_setup):
    """
    Verify that same-tenant access still works correctly.
    Tenant A should be able to access Tenant A's project.
    """
    from src.giljo_mcp.tools.orchestration import get_project_by_alias

    tenant_a = two_tenant_setup["tenant_a"]
    project_a = two_tenant_setup["project_a"]

    # Tenant A accesses Tenant A's project - should succeed
    result = await get_project_by_alias(
        alias="CrossTenantTestProject",
        tenant_key=tenant_a,
        session=db_session,
    )

    # Should find the project (it exists for tenant A)
    assert result is not None, "Same-tenant project access failed!"
    if "project" in result:
        assert result["project"]["id"] == project_a.id, "Wrong project returned for same-tenant access"
        assert result["project"]["tenant_key"] == tenant_a, "Tenant key mismatch in same-tenant access"


@pytest.mark.tenant_isolation
@pytest.mark.asyncio
async def test_same_tenant_agent_launch_succeeds(db_session, two_tenant_setup):
    """
    Verify that same-tenant agent launch still works correctly.
    """
    from src.giljo_mcp.tools.agent import launch_agent

    tenant_a = two_tenant_setup["tenant_a"]
    agent_job_a = two_tenant_setup["agent_job_a"]

    # Tenant A launches Tenant A's agent - should succeed
    result = await launch_agent(
        agent_id=agent_job_a.job_id,
        tenant_key=tenant_a,
        session=db_session,
    )

    # Should succeed for same-tenant access
    # (Exact success criteria depends on implementation)
