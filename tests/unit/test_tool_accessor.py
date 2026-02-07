"""
Tests for ToolAccessor.get_available_agents() method (Handover 0422 Task 1).

Test Coverage:
- get_available_agents() method exists and is callable
- Returns agents list with staleness info
- Multi-tenant isolation
- Depth parameter passed through
- Handles database errors gracefully
- Integration with agent_discovery.get_available_agents()

TDD Approach:
1. RED: Write failing tests first ✅
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Improve code while keeping tests green
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate


class TestToolAccessorGetAvailableAgents:
    """Test suite for ToolAccessor.get_available_agents() method."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, db_manager, db_session):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        self.db_session = db_session
        # Generate valid tenant key
        self.tenant_key = TenantManager.generate_tenant_key()

        # Use provided db_manager fixture
        self.db_manager = db_manager

        # Create tenant manager
        self.tenant_manager = Mock()
        self.tenant_manager.get_current_tenant = Mock(return_value=self.tenant_key)

        # Create ToolAccessor with test session for transaction sharing
        self.tool_accessor = ToolAccessor(
            db_manager=self.db_manager,
            tenant_manager=self.tenant_manager,
            websocket_manager=None,
            test_session=db_session,  # Share transaction for testing
        )

    @pytest.mark.asyncio
    async def test_method_exists(self):
        """Verify get_available_agents method exists and is callable"""
        # Will FAIL initially - method doesn't exist yet
        assert hasattr(self.tool_accessor, "get_available_agents")
        assert callable(self.tool_accessor.get_available_agents)

    @pytest.mark.asyncio
    async def test_returns_agents_with_staleness_info(self, db_session):
        """Test returns agents list with staleness detection fields"""
        # Create test template with staleness
        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            name="implementer",
            role="Code Implementation Specialist",
            description="Implements features using TDD",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.1.0",
            system_instructions="Test mission content",
            updated_at=now,
            last_exported_at=now - timedelta(days=1),  # Stale
        )
        db_session.add(template)
        await db_session.commit()

        # Call method
        result = await self.tool_accessor.get_available_agents(
            tenant_key=self.tenant_key, active_only=True, depth="full"
        )

        # Verify response structure
        assert result["success"] is True
        assert "data" in result
        assert "agents" in result["data"]
        assert result["data"]["count"] == 1

        # Verify staleness fields present
        agent = result["data"]["agents"][0]
        assert "may_be_stale" in agent
        assert agent["may_be_stale"] is True
        assert "last_exported_at" in agent
        assert "updated_at" in agent

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, db_session):
        """Test tenant isolation in get_available_agents"""
        from src.giljo_mcp.tenant import TenantManager

        # Create templates for different tenants
        other_tenant = TenantManager.generate_tenant_key()

        template_a = AgentTemplate(
            name="implementer",
            role="Code Implementation",
            description="Tenant A agent",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Test mission content",
        )
        template_b = AgentTemplate(
            name="implementer",
            role="Code Implementation",
            description="Tenant B agent",
            tenant_key=other_tenant,
            is_active=True,
            version="1.0.0",
            system_instructions="Test mission content",
        )

        db_session.add(template_a)
        db_session.add(template_b)
        await db_session.commit()

        # Fetch agents for test_tenant
        result = await self.tool_accessor.get_available_agents(
            tenant_key=self.tenant_key, active_only=True, depth="full"
        )

        # Only test_tenant agent returned
        assert result["data"]["count"] == 1
        assert result["data"]["agents"][0]["description"] == "Tenant A agent"

    @pytest.mark.asyncio
    async def test_depth_parameter_passed_through(self, db_session):
        """Test depth parameter is passed to underlying function"""
        template = AgentTemplate(
            name="implementer",
            role="Code Implementation",
            description="Test agent",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Test mission content",
        )
        db_session.add(template)
        await db_session.commit()

        # Test with type_only depth
        result = await self.tool_accessor.get_available_agents(
            tenant_key=self.tenant_key, active_only=True, depth="type_only"
        )

        # Verify depth is reflected in response note
        assert "type_only" in result["data"]["note"]

        # Verify type_only excludes description field
        agent = result["data"]["agents"][0]
        assert "description" not in agent
        assert "name" in agent
        assert "role" in agent
        assert "version_tag" in agent

    @pytest.mark.asyncio
    async def test_staleness_warning_included_when_stale_agents(self, db_session):
        """Test staleness_warning is included when stale agents detected"""
        now = datetime.now(timezone.utc)

        # Create stale template
        stale_template = AgentTemplate(
            name="stale-agent",
            role="Stale Role",
            version="1.0.0",
            system_instructions="Stale template",
            tenant_key=self.tenant_key,
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )
        db_session.add(stale_template)
        await db_session.commit()

        result = await self.tool_accessor.get_available_agents(
            tenant_key=self.tenant_key, active_only=True, depth="full"
        )

        # Verify staleness warning present
        assert "staleness_warning" in result["data"]
        warning = result["data"]["staleness_warning"]
        assert warning["has_stale_agents"] is True
        assert warning["stale_count"] == 1
        assert "stale-agent" in warning["stale_agents"]

    @pytest.mark.asyncio
    async def test_no_staleness_warning_when_all_fresh(self, db_session):
        """Test staleness_warning omitted when all agents fresh"""
        now = datetime.now(timezone.utc)

        # Create fresh template
        fresh_template = AgentTemplate(
            name="fresh-agent",
            role="Fresh Role",
            version="1.0.0",
            system_instructions="Fresh template",
            tenant_key=self.tenant_key,
            is_active=True,
            updated_at=now - timedelta(days=1),
            last_exported_at=now,  # Exported AFTER last update
        )
        db_session.add(fresh_template)
        await db_session.commit()

        result = await self.tool_accessor.get_available_agents(
            tenant_key=self.tenant_key, active_only=True, depth="full"
        )

        # Verify staleness_warning NOT present
        assert "staleness_warning" not in result["data"]

    @pytest.mark.asyncio
    async def test_handles_empty_results(self, db_session):
        """Test handles no templates gracefully"""
        result = await self.tool_accessor.get_available_agents(
            tenant_key=self.tenant_key, active_only=True, depth="full"
        )

        assert result["success"] is True
        assert result["data"]["count"] == 0
        assert result["data"]["agents"] == []

    @pytest.mark.asyncio
    async def test_default_depth_is_full(self, db_session):
        """Test default depth parameter is 'full'"""
        template = AgentTemplate(
            name="implementer",
            role="Code Implementation",
            description="Test agent description",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Test mission content",
        )
        db_session.add(template)
        await db_session.commit()

        # Call without depth parameter
        result = await self.tool_accessor.get_available_agents(tenant_key=self.tenant_key, active_only=True)

        # Verify full depth fields are present
        agent = result["data"]["agents"][0]
        assert "description" in agent
        assert "expected_filename" in agent
        assert "created_at" in agent
