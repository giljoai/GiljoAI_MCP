"""
TDD tests for get_self_identity context tool.

Handover 0430: Add self_identity category to fetch_context()

RED Phase: Write failing tests first
GREEN Phase: Implement minimal code to pass
REFACTOR Phase: Clean up and optimize
"""

import uuid

import pytest

from src.giljo_mcp.models import AgentTemplate


class TestGetSelfIdentityBasic:
    """Basic functionality tests for get_self_identity internal tool."""

    @pytest.mark.asyncio
    async def test_returns_template_by_name(self, db_manager, db_session):
        """
        GIVEN an existing agent template with behavioral rules and success criteria
        WHEN get_self_identity is called with matching agent_name
        THEN it returns the template's identity information
        """
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"

        # Create test template with all self_identity fields
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="orchestrator-coordinator",
            role="Orchestrator",
            description="Orchestrates multi-agent workflows",
            system_instructions="Use MCP tools natively. Call fetch_context for context.",
            user_instructions="Follow 7-task staging workflow.",
            behavioral_rules=["Check-in after completing tasks", "Use thin-client prompts"],
            success_criteria=["All agents complete", "Project closed out"],
            is_active=True,
            meta_data={"capabilities": ["orchestration", "coordination"]},
        )
        db_session.add(template)
        await db_session.flush()

        # Import and call the function under test
        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        result = await get_self_identity(
            agent_name="orchestrator-coordinator",
            tenant_key=tenant_key,
            db_manager=db_manager,
            session=db_session,  # Pass session for test isolation
        )

        # Verify response structure
        assert result["source"] == "self_identity"
        assert "data" in result
        assert "metadata" in result

        # Verify data content
        data = result["data"]
        assert data["name"] == "orchestrator-coordinator"
        assert data["role"] == "Orchestrator"
        assert "Use MCP tools natively" in data["system_instructions"]
        assert "7-task staging workflow" in data["user_instructions"]
        assert "Check-in after completing tasks" in data["behavioral_rules"]
        assert "All agents complete" in data["success_criteria"]

        # Verify metadata
        assert result["metadata"]["agent_name"] == "orchestrator-coordinator"
        assert result["metadata"]["tenant_key"] == tenant_key

    @pytest.mark.asyncio
    async def test_template_not_found_returns_error(self, db_manager, db_session):
        """
        GIVEN no template exists with the given name
        WHEN get_self_identity is called
        THEN it returns empty data with error in metadata
        """
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"

        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        result = await get_self_identity(
            agent_name="nonexistent-agent", tenant_key=tenant_key, db_manager=db_manager, session=db_session
        )

        assert result["source"] == "self_identity"
        assert result["data"] == {}
        assert "error" in result["metadata"]
        assert "not_found" in result["metadata"]["error"]

    @pytest.mark.asyncio
    async def test_inactive_template_not_returned(self, db_manager, db_session):
        """
        GIVEN a template exists but is inactive
        WHEN get_self_identity is called
        THEN it returns not found error
        """
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"

        # Create inactive template
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="inactive-agent",
            role="Inactive Agent",
            description="This agent is inactive",
            system_instructions="Inactive template",
            is_active=False,  # INACTIVE
        )
        db_session.add(template)
        await db_session.flush()

        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        result = await get_self_identity(
            agent_name="inactive-agent", tenant_key=tenant_key, db_manager=db_manager, session=db_session
        )

        assert result["source"] == "self_identity"
        assert result["data"] == {}
        assert "not_found" in result["metadata"]["error"]


class TestGetSelfIdentityTenantIsolation:
    """Multi-tenant isolation tests for get_self_identity."""

    @pytest.mark.asyncio
    async def test_wrong_tenant_returns_empty(self, db_manager, db_session):
        """
        GIVEN a template exists in tenant_a
        WHEN get_self_identity is called with tenant_b
        THEN it returns empty data (not found)
        """
        tenant_a = f"tenant_a_{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid.uuid4().hex[:8]}"

        # Create template in tenant_a
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_a,  # Belongs to tenant_a
            name="shared-agent-name",
            role="Agent Role",
            description="Template in tenant_a",
            system_instructions="Tenant A content",
            is_active=True,
        )
        db_session.add(template)
        await db_session.flush()

        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        # Try to fetch from tenant_b
        result = await get_self_identity(
            agent_name="shared-agent-name",
            tenant_key=tenant_b,  # Different tenant!
            db_manager=db_manager,
            session=db_session,
        )

        # Should not find the template (tenant isolation)
        assert result["data"] == {}
        assert "not_found" in result["metadata"]["error"]

    @pytest.mark.asyncio
    async def test_same_name_different_tenants_isolated(self, db_manager, db_session):
        """
        GIVEN templates with same name exist in different tenants
        WHEN get_self_identity is called for each tenant
        THEN each tenant gets their own template
        """
        tenant_a = f"tenant_a_{uuid.uuid4().hex[:8]}"
        tenant_b = f"tenant_b_{uuid.uuid4().hex[:8]}"

        # Create template in tenant_a
        template_a = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_a,
            name="orchestrator",
            role="Orchestrator A",
            description="Tenant A orchestrator",
            system_instructions="Tenant A content",
            is_active=True,
        )

        # Create template in tenant_b with same name
        template_b = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_b,
            name="orchestrator",
            role="Orchestrator B",
            description="Tenant B orchestrator",
            system_instructions="Tenant B content",
            is_active=True,
        )

        db_session.add_all([template_a, template_b])
        await db_session.flush()

        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        # Fetch from tenant_a
        result_a = await get_self_identity(
            agent_name="orchestrator", tenant_key=tenant_a, db_manager=db_manager, session=db_session
        )

        # Fetch from tenant_b
        result_b = await get_self_identity(
            agent_name="orchestrator", tenant_key=tenant_b, db_manager=db_manager, session=db_session
        )

        # Each should get their own template
        assert result_a["data"]["role"] == "Orchestrator A"
        assert "Tenant A" in result_a["data"]["system_instructions"]

        assert result_b["data"]["role"] == "Orchestrator B"
        assert "Tenant B" in result_b["data"]["system_instructions"]


class TestGetSelfIdentityDBManager:
    """Test db_manager parameter validation."""

    @pytest.mark.asyncio
    async def test_raises_error_without_db_manager(self):
        """
        GIVEN db_manager is None
        WHEN get_self_identity is called
        THEN it raises ValueError
        """
        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        with pytest.raises(ValueError, match="db_manager.*session.*required"):
            await get_self_identity(agent_name="test-agent", tenant_key="test-tenant", db_manager=None, session=None)


class TestGetSelfIdentityTokenEstimate:
    """Test token estimation for self_identity responses."""

    @pytest.mark.asyncio
    async def test_includes_estimated_tokens(self, db_manager, db_session):
        """
        GIVEN a template with substantial content
        WHEN get_self_identity is called
        THEN response includes estimated_tokens in metadata
        """
        tenant_key = f"tenant_{uuid.uuid4().hex[:8]}"

        # Create template with substantial content
        template = AgentTemplate(
            id=str(uuid.uuid4()),
            tenant_key=tenant_key,
            name="full-agent",
            role="Full Agent",
            description="A fully featured agent template",
            system_instructions="Long system instructions " * 50,  # ~250 tokens
            user_instructions="User instructions " * 20,  # ~60 tokens
            behavioral_rules=["Rule " + str(i) for i in range(10)],  # Multiple rules
            success_criteria=["Criteria " + str(i) for i in range(5)],
            is_active=True,
            meta_data={"capabilities": ["cap" + str(i) for i in range(20)]},
        )
        db_session.add(template)
        await db_session.flush()

        from src.giljo_mcp.tools.context_tools.get_self_identity import get_self_identity

        result = await get_self_identity(
            agent_name="full-agent", tenant_key=tenant_key, db_manager=db_manager, session=db_session
        )

        # Should have token estimate
        assert "estimated_tokens" in result["metadata"]
        assert result["metadata"]["estimated_tokens"] > 0
