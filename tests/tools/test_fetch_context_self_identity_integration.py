"""
Integration tests for fetch_context() with self_identity category.

Handover 0430: Verifies self_identity integration into unified fetch_context() API.
"""

import pytest

from src.giljo_mcp.models import AgentTemplate
from src.giljo_mcp.tools.context_tools.fetch_context import fetch_context


@pytest.mark.asyncio
async def test_fetch_context_self_identity_success(db_manager, test_tenant_key):
    """Test fetch_context() returns agent template via self_identity category."""
    # Create test template
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            name="orchestrator-coordinator",
            role="Orchestrator",
            description="Coordinates all agents",
            system_instructions="You are the orchestrator coordinator",
            user_instructions="Follow the staging workflow",
            behavioral_rules=["Always verify identity", "Report progress"],
            success_criteria=["All agents completed", "No errors"],
            tenant_key=test_tenant_key,
            is_active=True,
        )
        session.add(template)
        await session.commit()

    # Fetch via fetch_context
    result = await fetch_context(
        product_id="dummy-uuid",  # Not used for self_identity
        tenant_key=test_tenant_key,
        categories=["self_identity"],
        agent_name="orchestrator-coordinator",
        db_manager=db_manager,
    )

    # Verify structure
    assert result["source"] == "fetch_context"
    assert result["categories_requested"] == ["self_identity"]
    assert result["categories_returned"] == ["self_identity"]

    # Verify data
    data = result["data"]["self_identity"]
    assert data["name"] == "orchestrator-coordinator"
    assert data["role"] == "Orchestrator"
    assert data["description"] == "Coordinates all agents"
    assert data["system_instructions"] == "Use MCP tools for coordination"
    assert data["user_instructions"] == "Follow the staging workflow"
    assert data["behavioral_rules"] == ["Always verify identity", "Report progress"]
    assert data["success_criteria"] == ["All agents completed", "No errors"]

    # Verify metadata (estimated_tokens is tracked at fetch_context level via logging,
    # but the actual token data comes from get_self_identity's metadata)
    assert result["metadata"]["format"] == "structured"


@pytest.mark.asyncio
async def test_fetch_context_self_identity_missing_agent_name(db_manager, test_tenant_key):
    """Test fetch_context() returns error when agent_name missing for self_identity."""
    result = await fetch_context(
        product_id="dummy-uuid",
        tenant_key=test_tenant_key,
        categories=["self_identity"],
        agent_name=None,  # Missing required parameter
        db_manager=db_manager,
    )

    # Should return error in metadata
    assert result["source"] == "fetch_context"
    assert result["categories_requested"] == ["self_identity"]
    assert result["categories_returned"] == []  # No data returned

    # Check data is empty dict or has error metadata
    data = result["data"]["self_identity"]
    assert data == {} or "error" in data


@pytest.mark.asyncio
async def test_fetch_context_self_identity_template_not_found(db_manager, test_tenant_key):
    """Test fetch_context() returns empty when template not found."""
    result = await fetch_context(
        product_id="dummy-uuid",
        tenant_key=test_tenant_key,
        categories=["self_identity"],
        agent_name="nonexistent-agent",
        db_manager=db_manager,
    )

    assert result["source"] == "fetch_context"
    assert result["categories_requested"] == ["self_identity"]

    # Data should be empty or contain error
    data = result["data"]["self_identity"]
    assert data == {} or "error" in data.get("metadata", {})


@pytest.mark.asyncio
async def test_fetch_context_self_identity_tenant_isolation(db_manager, test_tenant_key):
    """Test fetch_context() enforces tenant isolation for self_identity."""
    # Create template in tenant A
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            name="test-agent",
            role="Tester",
            description="Test role",
            system_instructions="You are a test agent",
            tenant_key=test_tenant_key,
            is_active=True,
        )
        session.add(template)
        await session.commit()

    # Try to fetch from tenant B
    result = await fetch_context(
        product_id="dummy-uuid",
        tenant_key="different_tenant_key",
        categories=["self_identity"],
        agent_name="test-agent",
        db_manager=db_manager,
    )

    # Should return empty - template belongs to different tenant
    data = result["data"]["self_identity"]
    assert data == {} or "error" in data.get("metadata", {})


@pytest.mark.asyncio
async def test_fetch_context_self_identity_flat_format(db_manager, test_tenant_key):
    """Test fetch_context() with self_identity returns correct format in flat mode."""
    # Create test template
    async with db_manager.get_session_async() as session:
        template = AgentTemplate(
            name="implementor-agent",
            role="Implementer",
            description="Implements features",
            system_instructions="You are an implementer agent",
            tenant_key=test_tenant_key,
            is_active=True,
        )
        session.add(template)
        await session.commit()

    # Fetch with flat format
    result = await fetch_context(
        product_id="dummy-uuid",
        tenant_key=test_tenant_key,
        categories=["self_identity"],
        agent_name="implementor-agent",
        format="flat",
        db_manager=db_manager,
    )

    # In flat mode, data should be at top level (not nested in "self_identity")
    assert result["source"] == "fetch_context"
    assert result["metadata"]["format"] == "flat"

    # Data should be directly accessible (not nested by category)
    data = result["data"]
    assert data["name"] == "implementor-agent"
    assert data["role"] == "Implementer"
