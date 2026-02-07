"""
Tests for get_available_agents() MCP tool (Handover 0246c).

Test Coverage:
- get_available_agents() function existence and signature
- Returns active templates with version metadata
- Multi-tenant isolation
- Handles inactive templates (exclusion)
- Handles empty results (no templates)
- Response includes timestamp and metadata
- Expected filename format
- MCP tool integration with OrchestrationTools
- active_only parameter handling
- Staleness detection (Handover 0421)

TDD Approach:
1. RED: Write failing tests first
2. GREEN: Implement minimal code to pass tests
3. REFACTOR: Improve code while keeping tests green
"""

from datetime import datetime, timedelta, timezone

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


class TestAgentStalenessDetection:
    """Test suite for agent staleness detection (Handover 0421)."""

    @pytest_asyncio.fixture(autouse=True)
    async def setup_method(self, db_session):
        """Setup for each test method"""
        from src.giljo_mcp.tenant import TenantManager

        self.db_session = db_session
        self.tenant_key = TenantManager.generate_tenant_key()

    @pytest.mark.asyncio
    async def test_format_agent_info_includes_staleness_fields(self, db_session):
        """Test that _format_agent_info() includes staleness detection fields."""
        from src.giljo_mcp.tools.agent_discovery import _format_agent_info

        # Create template with staleness
        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            id="test-template-1",
            tenant_key=self.tenant_key,
            name="test-agent",
            role="Tester",
            version="1.0.0",
            system_instructions="Test template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),  # Exported 1 day ago
        )

        # Format with full depth
        result = _format_agent_info(template, depth="full")

        # Verify staleness fields present
        assert "may_be_stale" in result
        assert result["may_be_stale"] is True  # updated_at > last_exported_at
        assert "last_exported_at" in result
        assert "updated_at" in result
        assert result["last_exported_at"] == (now - timedelta(days=1)).isoformat()
        assert result["updated_at"] == now.isoformat()

    @pytest.mark.asyncio
    async def test_format_agent_info_staleness_fields_with_type_only_depth(self, db_session):
        """Test that staleness fields are included even with type_only depth."""
        from src.giljo_mcp.tools.agent_discovery import _format_agent_info

        now = datetime.now(timezone.utc)
        template = AgentTemplate(
            id="test-template-2",
            tenant_key=self.tenant_key,
            name="test-agent",
            role="Tester",
            version="1.0.0",
            system_instructions="Test template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )

        # Format with type_only depth
        result = _format_agent_info(template, depth="type_only")

        # Staleness fields should still be present (always included)
        assert "may_be_stale" in result
        assert "last_exported_at" in result
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_get_available_agents_includes_staleness_warning(self, db_session):
        """Test that get_available_agents() includes staleness warning when stale agents detected."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create stale template
        now = datetime.now(timezone.utc)
        stale_template = AgentTemplate(
            id="stale-template",
            tenant_key=self.tenant_key,
            name="stale-agent",
            role="Stale Role",
            version="1.0.0",
            system_instructions="Stale template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )

        # Create fresh template
        fresh_template = AgentTemplate(
            id="fresh-template",
            tenant_key=self.tenant_key,
            name="fresh-agent",
            role="Fresh Role",
            version="1.0.0",
            system_instructions="Fresh template",
            is_active=True,
            updated_at=now - timedelta(days=2),
            last_exported_at=now,
        )

        db_session.add_all([stale_template, fresh_template])
        await db_session.commit()

        # Call get_available_agents
        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        # Verify response structure
        assert result["success"] is True
        assert "data" in result
        assert "agents" in result["data"]
        assert "staleness_warning" in result["data"]

        # Verify staleness warning
        warning = result["data"]["staleness_warning"]
        assert warning["has_stale_agents"] is True
        assert warning["stale_count"] == 1
        assert "stale-agent" in warning["stale_agents"]
        assert "fresh-agent" not in warning["stale_agents"]
        assert "action_required" in warning
        assert "options" in warning
        assert len(warning["options"]) == 3

    @pytest.mark.asyncio
    async def test_get_available_agents_no_staleness_warning_when_all_fresh(self, db_session):
        """Test that staleness_warning is omitted when all agents are fresh."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create fresh template
        now = datetime.now(timezone.utc)
        fresh_template = AgentTemplate(
            id="fresh-template",
            tenant_key=self.tenant_key,
            name="fresh-agent",
            role="Fresh Role",
            version="1.0.0",
            system_instructions="Fresh template",
            is_active=True,
            updated_at=now - timedelta(days=1),
            last_exported_at=now,
        )

        db_session.add(fresh_template)
        await db_session.commit()

        # Call get_available_agents
        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        # Verify staleness_warning is NOT present
        assert result["success"] is True
        assert "staleness_warning" not in result["data"]

    @pytest.mark.asyncio
    async def test_staleness_warning_includes_actionable_guidance(self, db_session):
        """Test that staleness warning provides actionable guidance."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        now = datetime.now(timezone.utc)
        stale_template = AgentTemplate(
            id="stale-template",
            tenant_key=self.tenant_key,
            name="stale-agent",
            role="Stale Role",
            version="1.0.0",
            system_instructions="Stale template",
            is_active=True,
            updated_at=now,
            last_exported_at=now - timedelta(days=1),
        )

        db_session.add(stale_template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        warning = result["data"]["staleness_warning"]

        # Verify action_required mentions key concepts
        assert "gil_get_claude_agents" in warning["action_required"]
        assert "sync" in warning["action_required"].lower() or "export" in warning["action_required"].lower()

        # Verify options provide clear choices
        assert any("gil_get_claude_agents" in option for option in warning["options"])
        assert any("continue" in option.lower() for option in warning["options"])
        assert any("abort" in option.lower() for option in warning["options"])

    @pytest.mark.asyncio
    async def test_staleness_detection_handles_null_timestamps(self, db_session):
        """Test staleness detection handles null last_exported_at gracefully."""
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        # Create template that was never exported
        template = AgentTemplate(
            id="never-exported",
            tenant_key=self.tenant_key,
            name="new-agent",
            role="New Role",
            version="1.0.0",
            system_instructions="New template",
            is_active=True,
            updated_at=datetime.now(timezone.utc),
            last_exported_at=None,  # Never exported
        )

        db_session.add(template)
        await db_session.commit()

        result = await get_available_agents(db_session, self.tenant_key, depth="full")

        # Should not crash, template should NOT be marked as stale
        assert result["success"] is True
        agents = result["data"]["agents"]
        assert len(agents) == 1
        assert agents[0]["may_be_stale"] is False  # Not stale if never exported
        assert agents[0]["last_exported_at"] is None
