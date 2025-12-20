"""
Test suite for agent_discovery.py - Phase C TDD (RED Phase).

Tests enforce new semantic parameter naming from Handover 0366c:
- job_id = work order UUID (the WHAT - persistent)
- agent_id = executor UUID (the WHO - specific instance)

These tests should FAIL initially until implementation is updated.

Handover 0366c: Agent Identity Refactor - Phase C (TDD Implementation)
"""

import pytest
import pytest_asyncio
from uuid import uuid4

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.models.templates import AgentTemplate
from src.giljo_mcp.tools.agent_discovery import get_available_agents, _format_agent_info


@pytest.mark.asyncio
class TestAgentDiscoverySemantics:
    """Test agent discovery tool uses correct semantic naming."""

    async def test_get_available_agents_returns_agent_metadata(self, db_manager, db_session):
        """
        Test get_available_agents returns agent template metadata correctly.

        SEMANTIC CHECK: This tool returns agent TEMPLATES (the WHAT - job types),
        not specific executions (the WHO - agent instances).
        """
        tenant_key = str(uuid4())

        # Create test agent templates
        template1 = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="implementer",
            role="Code Implementation Specialist",
            description="Implements features following TDD principles",
            version="1.0.0",
            is_active=True,
            template_content="You are a code implementer.",  # Required field (deprecated)
            system_instructions="Coordinate with MCP server for mission details.",
        )
        template2 = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="tester",
            role="Test Automation Engineer",
            description="Writes comprehensive test suites",
            version="2.1.3",
            is_active=True,
            template_content="You are a test automation engineer.",  # Required field (deprecated)
            system_instructions="Coordinate with MCP server for mission details.",
        )

        db_session.add_all([template1, template2])
        await db_session.commit()

        # Call discovery tool
        result = await get_available_agents(db_session, tenant_key, depth="full")

        # Assert correct structure
        assert result["success"] is True
        assert result["data"]["count"] == 2
        assert len(result["data"]["agents"]) == 2

        # Assert templates returned (not executions)
        agent_names = [agent["name"] for agent in result["data"]["agents"]]
        assert "implementer" in agent_names
        assert "tester" in agent_names

        # Assert metadata includes version info
        for agent in result["data"]["agents"]:
            assert "version_tag" in agent
            assert "role" in agent
            assert agent["version_tag"] in ["1.0.0", "2.1.3"]


    async def test_get_available_agents_multi_tenant_isolation(self, db_manager, db_session):
        """
        Test multi-tenant isolation in agent discovery.

        CRITICAL: Must enforce tenant_key filtering to prevent cross-tenant leakage.
        """
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        # Create templates for tenant A
        template_a1 = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_a,
            name="implementer",
            role="Code Implementation Specialist",
            description="Tenant A implementer",
            version="1.0.0",
            is_active=True,
            template_content="You are a code implementer for tenant A.",
            system_instructions="Coordinate with MCP server.",
        )

        # Create templates for tenant B
        template_b1 = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_b,
            name="implementer",
            role="Code Implementation Specialist",
            description="Tenant B implementer",
            version="1.0.0",
            is_active=True,
            template_content="You are a code implementer for tenant B.",
            system_instructions="Coordinate with MCP server.",
        )

        db_session.add_all([template_a1, template_b1])
        await db_session.commit()

        # Query for tenant A
        result_a = await get_available_agents(db_session, tenant_a, depth="full")

        # Query for tenant B
        result_b = await get_available_agents(db_session, tenant_b, depth="full")

        # Assert isolation - each tenant sees only their own templates
        assert result_a["success"] is True
        assert result_a["data"]["count"] == 1
        assert result_a["data"]["agents"][0]["description"] == "Tenant A implementer"

        assert result_b["success"] is True
        assert result_b["data"]["count"] == 1
        assert result_b["data"]["agents"][0]["description"] == "Tenant B implementer"


    async def test_get_available_agents_depth_type_only(self, db_manager, db_session):
        """
        Test depth="type_only" returns minimal agent metadata.

        Should return name, role, version_tag ONLY (no description, ~50 tokens).
        """
        tenant_key = str(uuid4())

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="analyzer",
            role="System Analyzer",
            description="This is a long description that should NOT be included in type_only mode.",
            version="3.2.1",
            is_active=True,
            template_content="You are a system analyzer.",
            system_instructions="Coordinate with MCP server.",
        )

        db_session.add(template)
        await db_session.commit()

        # Call with depth="type_only"
        result = await get_available_agents(db_session, tenant_key, depth="type_only")

        assert result["success"] is True
        assert result["data"]["count"] == 1

        agent = result["data"]["agents"][0]

        # Assert minimal fields only
        assert "name" in agent
        assert "role" in agent
        assert "version_tag" in agent

        # Assert rich fields excluded
        assert "description" not in agent
        assert "expected_filename" not in agent
        assert "created_at" not in agent


    async def test_get_available_agents_depth_full(self, db_manager, db_session):
        """
        Test depth="full" returns complete agent metadata.

        Should return all fields including description (~1.2k tokens).
        """
        tenant_key = str(uuid4())

        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="orchestrator",
            role="Project Orchestrator",
            description="Coordinates agent workflows and manages project lifecycle.",
            version="2.0.0",
            is_active=True,
            template_content="You are a project orchestrator.",
            system_instructions="Coordinate with MCP server.",
        )

        db_session.add(template)
        await db_session.commit()

        # Call with depth="full"
        result = await get_available_agents(db_session, tenant_key, depth="full")

        assert result["success"] is True
        assert result["data"]["count"] == 1

        agent = result["data"]["agents"][0]

        # Assert all fields present
        assert agent["name"] == "orchestrator"
        assert agent["role"] == "Project Orchestrator"
        assert agent["version_tag"] == "2.0.0"
        assert agent["description"] == "Coordinates agent workflows and manages project lifecycle."
        assert agent["expected_filename"] == "orchestrator_2.0.0.md"
        assert "created_at" in agent


    async def test_format_agent_info_handles_missing_fields(self, db_manager, db_session):
        """
        Test _format_agent_info gracefully handles missing fields.

        Should use sensible defaults for missing version/role/description.

        NOTE: AgentTemplate has database defaults (version="1.0.0"), so we need to
        explicitly set version=None to test the fallback behavior.
        """
        tenant_key = str(uuid4())

        # Create template with minimal fields
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="minimal_agent",
            is_active=True,
            template_content="Minimal template.",  # Required field
            system_instructions="",  # Has default, but be explicit
            version=None,  # Explicitly set to None to test fallback
            # No role or description
        )

        db_session.add(template)
        await db_session.commit()
        await db_session.refresh(template)  # Refresh to see actual DB state

        # Format with full depth
        result = _format_agent_info(template, depth="full")

        # Assert defaults used
        assert result["name"] == "minimal_agent"
        assert result["role"] == "Specialized Agent"  # DEFAULT_ROLE
        # version=None in code, but DB may have default "1.0.0" or None
        # _format_agent_info should handle both cases
        assert result["version_tag"] in ["unknown", "1.0.0"]  # Accept either
        assert result["description"] == ""  # Empty string for missing description


    async def test_get_available_agents_filters_inactive_templates(self, db_manager, db_session):
        """
        Test get_available_agents only returns active templates.

        Inactive templates should be excluded from discovery.
        """
        tenant_key = str(uuid4())

        # Create active template
        active_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="active_agent",
            role="Active Agent",
            version="1.0.0",
            is_active=True,
            template_content="Active agent template.",
            system_instructions="Coordinate with MCP server.",
        )

        # Create inactive template
        inactive_template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="inactive_agent",
            role="Inactive Agent",
            version="1.0.0",
            is_active=False,
            template_content="Inactive agent template.",
            system_instructions="Coordinate with MCP server.",
        )

        db_session.add_all([active_template, inactive_template])
        await db_session.commit()

        # Call discovery
        result = await get_available_agents(db_session, tenant_key, depth="full")

        # Assert only active template returned
        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["agents"][0]["name"] == "active_agent"


    async def test_get_available_agents_invalid_tenant_key(self, db_manager, db_session):
        """
        Test get_available_agents handles invalid tenant_key gracefully.

        Should return empty list with success=True (not crash).
        """
        # Call with invalid tenant_key
        result = await get_available_agents(db_session, "", depth="full")

        assert result["success"] is True
        assert result["data"]["count"] == 0
        assert result["data"]["agents"] == []
        assert "Invalid tenant key" in result["data"]["note"]


@pytest.mark.asyncio
class TestAgentDiscoveryDocumentation:
    """Test tool signature and documentation clarity."""

    def test_get_available_agents_signature_clarity(self):
        """
        Test get_available_agents has clear parameter names.

        SEMANTIC CHECK: Parameters should clearly indicate their purpose.
        - tenant_key: Multi-tenant isolation
        - depth: Detail level (type_only vs full)

        No job_id or agent_id parameters (this tool discovers templates, not executions).
        """
        import inspect
        from src.giljo_mcp.tools.agent_discovery import get_available_agents

        sig = inspect.signature(get_available_agents)
        params = list(sig.parameters.keys())

        # Assert expected parameters
        assert "session" in params
        assert "tenant_key" in params
        assert "depth" in params

        # Assert NO job_id or agent_id (this discovers templates, not executions)
        assert "job_id" not in params
        assert "agent_id" not in params


    def test_format_agent_info_signature_clarity(self):
        """
        Test _format_agent_info has clear parameter names.

        SEMANTIC CHECK: Should accept AgentTemplate (not AgentJob or AgentExecution).
        """
        import inspect
        from src.giljo_mcp.tools.agent_discovery import _format_agent_info

        sig = inspect.signature(_format_agent_info)
        params = list(sig.parameters.keys())

        # Assert expected parameters
        assert "template" in params  # Clear: receives AgentTemplate
        assert "depth" in params

        # Parameter annotation should indicate AgentTemplate
        template_param = sig.parameters["template"]
        assert template_param.annotation.__name__ == "AgentTemplate"


@pytest.mark.asyncio
class TestAgentDiscoveryIntegrationWithNewModel:
    """Test agent discovery integrates correctly with AgentJob/AgentExecution model."""

    async def test_discovery_independent_of_job_execution_state(self, db_manager, db_session):
        """
        Test get_available_agents returns templates regardless of job/execution state.

        CRITICAL: Template discovery should NOT be affected by running jobs or executions.
        Templates are the WHAT (available job types).
        Jobs/Executions are instances of those templates (running work).
        """
        tenant_key = str(uuid4())

        # Create agent template
        template = AgentTemplate(
            id=str(uuid4()),
            tenant_key=tenant_key,
            name="implementer",
            role="Code Implementation Specialist",
            version="1.0.0",
            is_active=True,
            template_content="Implementer template.",
            system_instructions="Coordinate with MCP server.",
        )

        db_session.add(template)
        await db_session.commit()

        # Create job using this template
        job = AgentJob(
            job_id=str(uuid4()),
            tenant_key=tenant_key,
            mission="Build authentication system",
            job_type="implementer",
            status="active",
            template_id=template.id,
        )

        db_session.add(job)
        await db_session.commit()

        # Create execution for this job
        execution = AgentExecution(
            agent_id=str(uuid4()),
            job_id=job.job_id,
            tenant_key=tenant_key,
            agent_type="implementer",
            instance_number=1,
            status="working",
        )

        db_session.add(execution)
        await db_session.commit()

        # Call discovery - should return template regardless of job/execution state
        result = await get_available_agents(db_session, tenant_key, depth="full")

        assert result["success"] is True
        assert result["data"]["count"] == 1
        assert result["data"]["agents"][0]["name"] == "implementer"

        # Discovery returns TEMPLATES, not jobs or executions
        # No job_id or agent_id in response
        agent_data = result["data"]["agents"][0]
        assert "job_id" not in agent_data
        assert "agent_id" not in agent_data
