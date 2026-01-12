"""
Integration tests for MCP orchestration tools HTTP exposure (Simplified).

Tests basic functionality of orchestration tools accessible via HTTP API.
These tests verify the tool accessor methods are properly wired into the HTTP endpoint.

Key tests:
- health_check
- get_pending_jobs
- acknowledge_job
- complete_job
"""

from uuid import uuid4

import pytest


class TestOrchestrationToolsHTTPExposure:
    """Test orchestration tools are exposed via ToolAccessor"""

    @pytest.mark.asyncio
    async def test_health_check_accessible(self, db_manager):
        """Test health_check method exists on ToolAccessor"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call health_check
        result = await tool_accessor.health_check()

        assert result["status"] == "healthy"
        assert result["server"] == "giljo-mcp"
        assert "timestamp" in result

    @pytest.mark.asyncio
    async def test_get_pending_jobs_accessible(self, db_manager):
        """Test get_pending_jobs method exists and has basic validation"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with valid params (should return empty list if no jobs)
        tenant_key = f"tk_{uuid4().hex}"
        result = await tool_accessor.get_pending_jobs("implementer", tenant_key)

        assert result["status"] == "success"
        assert isinstance(result["jobs"], list)
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_get_pending_jobs_validation(self, db_manager):
        """Test get_pending_jobs validates inputs"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with empty agent_display_name
        result = await tool_accessor.get_pending_jobs("", "tenant_key")

        assert result["status"] == "error"
        assert "agent_display_name" in result["error"]

    @pytest.mark.asyncio
    async def test_acknowledge_job_validation(self, db_manager):
        """Test acknowledge_job validates inputs"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(f"tk_{uuid4().hex}")
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with empty job_id
        result = await tool_accessor.acknowledge_job("", "agent_id")

        assert result["status"] == "error"
        assert "job_id" in result["error"]

    @pytest.mark.asyncio
    async def test_complete_job_validation(self, db_manager):
        """Test complete_job validates inputs"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(f"tk_{uuid4().hex}")
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with empty job_id
        result = await tool_accessor.complete_job("", {"summary": "Test"})

        assert result["status"] == "error"
        assert "job_id" in result["error"]

    @pytest.mark.asyncio
    async def test_report_error_validation(self, db_manager):
        """Test report_error validates inputs"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(f"tk_{uuid4().hex}")
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with empty error message
        result = await tool_accessor.report_error("job_id", "")

        assert result["status"] == "error"
        assert "error message" in result["error"]

    @pytest.mark.asyncio
    async def test_report_progress_validation(self, db_manager):
        """Test report_progress validates inputs"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tenant_manager.set_current_tenant(f"tk_{uuid4().hex}")
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with empty job_id
        result = await tool_accessor.report_progress("", {"percent": 50})

        assert result["status"] == "error"
        assert "job_id" in result["error"]

    @pytest.mark.asyncio
    async def test_get_orchestrator_instructions_accessible(self, db_manager):
        """Test get_orchestrator_instructions method exists"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with fake ID (should return error but not crash)
        fake_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex}"
        result = await tool_accessor.get_orchestrator_instructions(fake_id, tenant_key)

        # Should return structured error, not crash
        assert "error" in result or "orchestrator_id" in result

    @pytest.mark.asyncio
    async def test_spawn_agent_job_accessible(self, db_manager):
        """Test spawn_agent_job method exists"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with fake project (should return error but not crash)
        fake_project_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex}"
        result = await tool_accessor.spawn_agent_job(
            agent_display_name="implementer",
            agent_name="Test Agent",
            mission="Test mission",
            project_id=fake_project_id,
            tenant_key=tenant_key,
        )

        # Should return structured response, not crash
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_get_agent_mission_accessible(self, db_manager):
        """Test get_agent_mission method exists"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with fake ID (should return error but not crash)
        fake_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex}"
        result = await tool_accessor.get_agent_mission(fake_id, tenant_key)

        # Should return structured error, not crash
        assert "error" in result or "job_id" in result

    @pytest.mark.asyncio
    async def test_orchestrate_project_accessible(self, db_manager):
        """Test orchestrate_project method exists"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with fake ID (should return error but not crash)
        fake_project_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex}"
        result = await tool_accessor.orchestrate_project(fake_project_id, tenant_key)

        # Should return structured error, not crash
        assert "error" in result or "project_id" in result

    @pytest.mark.asyncio
    async def test_get_workflow_status_accessible(self, db_manager):
        """Test get_workflow_status method exists"""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        # Call with fake ID (should return error but not crash)
        fake_project_id = str(uuid4())
        tenant_key = f"tk_{uuid4().hex}"
        result = await tool_accessor.get_workflow_status(fake_project_id, tenant_key)

        # Should return structured error, not crash
        assert "error" in result or "total_agents" in result


class TestToolMapExposure:
    """Test tools are registered in HTTP tool map"""

    def test_orchestration_tools_in_map(self):
        """Test orchestration tools are registered in mcp_tools.py"""
        from pathlib import Path

        # Read mcp_tools.py
        mcp_tools_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_tools.py")
        content = mcp_tools_path.read_text()

        # Verify tools are in the file
        orchestration_tools = [
            "health_check",
            "get_orchestrator_instructions",
            "spawn_agent_job",
            "get_agent_mission",
            "orchestrate_project",
            "get_workflow_status",
        ]

        for tool in orchestration_tools:
            assert f'"{tool}":' in content, f"Tool {tool} not found in tool_map"

    def test_agent_coordination_tools_in_map(self):
        """Test agent coordination tools are registered in mcp_tools.py"""
        from pathlib import Path

        # Read mcp_tools.py
        mcp_tools_path = Path("F:/GiljoAI_MCP/api/endpoints/mcp_tools.py")
        content = mcp_tools_path.read_text()

        # Verify tools are in the file
        coordination_tools = ["get_pending_jobs", "acknowledge_job", "report_progress", "complete_job", "report_error"]

        for tool in coordination_tools:
            assert f'"{tool}":' in content, f"Tool {tool} not found in tool_map"
