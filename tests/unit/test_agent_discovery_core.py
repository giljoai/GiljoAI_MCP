"""
Tests for get_available_agents() MCP tool — core functionality (Handover 0246c).

Split from test_agent_discovery.py.

Test Coverage:
- get_available_agents() function existence and signature
- Returns active templates with version metadata
- Multi-tenant isolation
- Handles inactive templates (exclusion)
- Handles empty results (no templates)
- Response includes timestamp and metadata
- Expected filename format
- MCP tool integration with OrchestrationTools
"""

from datetime import datetime

import pytest
import pytest_asyncio

from src.giljo_mcp.models import AgentTemplate


class TestGetAvailableAgents:
    """Test suite for get_available_agents() function (Core Functionality)."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, db_session):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.db_session = db_session
        # Generate valid tenant key
        self.tenant_key = TenantManager.generate_tenant_key()

    @pytest.mark.asyncio
    async def test_function_exists(self):
        """Verify get_available_agents function exists and is callable"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Will FAIL initially - function doesn't exist yet
        assert callable(get_available_agents)

    @pytest.mark.asyncio
    async def test_returns_active_templates(self, db_session):
        """Test returns active templates with metadata"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create test templates
        template1 = AgentTemplate(
            name="implementer",
            role="Code Implementation Specialist",
            description="Implements features using TDD",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.1.0",
            system_instructions="Test mission content",
        )
        template2 = AgentTemplate(
            name="tester",
            role="Quality Assurance Specialist",
            description="Writes comprehensive tests",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Test mission content",
        )

        db_session.add(template1)
        db_session.add(template2)
        await db_session.commit()

        # Call discovery function
        result = await get_available_agents(db_session, self.tenant_key)

        # Verify response structure
        assert result["success"] is True
        assert "data" in result
        assert "agents" in result["data"]
        assert result["data"]["count"] == 2

    @pytest.mark.asyncio
    async def test_agent_metadata_includes_version(self, db_session):
        """Test agent metadata includes version information"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        template = AgentTemplate(
            name="implementer",
            role="Code Implementation",
            description="Implementation specialist",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.2.0",
            system_instructions="Test mission content",
        )
        db_session.add(template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key)

        agents = result["data"]["agents"]
        assert len(agents) == 1
        assert agents[0]["name"] == "implementer"
        assert agents[0]["version_tag"] == "1.2.0"
        assert "expected_filename" in agents[0]

    @pytest.mark.asyncio
    async def test_excludes_inactive_templates(self, db_session):
        """Test that inactive templates are excluded"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        active = AgentTemplate(
            name="implementer",
            role="Code Implementation",
            description="Active agent",
            tenant_key=self.tenant_key,
            is_active=True,
            version="1.0.0",
            system_instructions="Test mission content",
        )
        inactive = AgentTemplate(
            name="deprecated_agent",
            role="Old Agent",
            description="Deprecated agent",
            tenant_key=self.tenant_key,
            is_active=False,
            version="0.9.0",
            system_instructions="Test mission content",
        )

        db_session.add(active)
        db_session.add(inactive)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key)

        # Only active template returned
        assert result["data"]["count"] == 1
        assert result["data"]["agents"][0]["name"] == "implementer"

    @pytest.mark.asyncio
    async def test_tenant_isolation(self, db_session):
        """Test tenant isolation in agent discovery"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

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
        result = await get_available_agents(db_session, self.tenant_key)

        # Only test_tenant agent returned
        assert result["data"]["count"] == 1

    @pytest.mark.asyncio
    async def test_no_active_templates_returns_empty_list(self, db_session):
        """Test returns empty list when no active templates"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # No templates created
        result = await get_available_agents(db_session, self.tenant_key)

        assert result["success"] is True
        assert result["data"]["count"] == 0
        assert result["data"]["agents"] == []

    @pytest.mark.asyncio
    async def test_response_includes_timestamp(self, db_session):
        """Test response includes fetched_at timestamp"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        result = await get_available_agents(db_session, self.tenant_key)

        assert "fetched_at" in result["data"]
        # Verify it's a valid ISO timestamp
        datetime.fromisoformat(result["data"]["fetched_at"].replace("Z", "+00:00"))

    @pytest.mark.asyncio
    async def test_expected_filename_format(self, db_session):
        """Test expected_filename follows pattern name_version.md"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        template = AgentTemplate(
            name="reviewer",
            role="Code Reviewer",
            description="Reviews code",
            tenant_key=self.tenant_key,
            is_active=True,
            version="2.0.1",
            system_instructions="Test mission content",
        )
        db_session.add(template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key)

        agent = result["data"]["agents"][0]
        assert agent["expected_filename"] == "reviewer_2.0.1.md"

    @pytest.mark.asyncio
    async def test_response_includes_note(self, db_session):
        """Test response includes explanatory note about dynamic fetching"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        result = await get_available_agents(db_session, self.tenant_key)

        assert "note" in result["data"]
        assert "dynamic" in result["data"]["note"].lower()

    @pytest.mark.asyncio
    async def test_handles_missing_version_gracefully(self, db_session):
        """Test handles templates with missing version field"""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        template = AgentTemplate(
            name="legacy_agent",
            role="Legacy Agent",
            description="Old agent without version",
            tenant_key=self.tenant_key,
            is_active=True,
            version=None,  # Missing version
            system_instructions="Test mission content",
        )
        db_session.add(template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key)

        # Should handle gracefully (use "unknown" or similar)
        assert result["success"] is True
        agents = result["data"]["agents"]
        assert len(agents) == 1
        assert "version_tag" in agents[0]


class TestGetAvailableAgentsMCPTool:
    """Test MCP tool integration with OrchestrationTools."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, db_session):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.db_session = db_session
        # Generate valid tenant key
        self.tenant_key = TenantManager.generate_tenant_key()

    @pytest.mark.asyncio
    async def test_get_available_agents_mcp_tool_callable(self, db_session):
        """Test that get_available_agents is callable from orchestration module"""
        # This is a simplified test - we just verify the function can be called
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        result = await get_available_agents(db_session, self.tenant_key)

        # Should return a dict with success key
        assert isinstance(result, dict)
        assert "success" in result
