"""
Comprehensive Tests for Handover 0088 Amendments A & B

Amendment A: WebSocket Integration for Real-Time Updates
Amendment B: Agent Thin Client Implementation

These tests validate:
1. WebSocket broadcasting in get_orchestrator_instructions()
2. Frontend WebSocket listener registration
3. get_agent_mission() thin client enhancement
4. spawn_agent_job() thin client implementation
5. Agent prompts are thin (~10 lines)
6. Mission stored in database, NOT in prompt
"""

from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest

from src.giljo_mcp.models import AgentExecution, Project
from src.giljo_mcp.tools.orchestration import register_orchestration_tools


@pytest.fixture
async def test_project(db_session, test_tenant):
    """Create test project"""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        description="Test project for amendments",
        tenant_key=test_tenant.tenant_key,
        status="active",
        context_budget=150000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_orchestrator_job(db_session, test_project, test_tenant):
    """Create test orchestrator job"""
    orchestrator = AgentExecution(
        job_id=str(uuid4()),
        project_id=test_project.id,
        tenant_key=test_tenant.tenant_key,
        agent_display_name="orchestrator",
        mission="Test condensed mission with field priorities applied",
        status="waiting",
        context_budget=150000,
        context_used=0,
        instance_number=1,
        metadata={
            "field_priorities": {"product_vision": 10, "architecture": 7},
            "user_id": str(uuid4()),
            "tool": "claude-code",
            "created_via": "thin_client_generator",
        },
    )
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)
    return orchestrator


@pytest.fixture
async def test_agent_job(db_session, test_project, test_tenant, test_orchestrator_job):
    """Create test agent job"""
    agent = AgentExecution(
        job_id=str(uuid4()),
        project_id=test_project.id,
        tenant_key=test_tenant.tenant_key,
        agent_display_name="backend",
        mission="Implement authentication system with JWT tokens",
        status="waiting",
        spawned_by=test_orchestrator_job.job_id,
        metadata={
            "created_via": "thin_client_spawn",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "thin_client": True,
        },
    )
    db_session.add(agent)
    await db_session.commit()
    await db_session.refresh(agent)
    return agent


# =============================================================================
# AMENDMENT A: WebSocket Integration Tests
# =============================================================================


@pytest.mark.asyncio
async def test_websocket_broadcast_orchestrator_instructions(
    db_session, test_orchestrator_job, test_project, test_tenant
):
    """
    Test Amendment A: WebSocket broadcasting in get_orchestrator_instructions()

    Validates:
    - WebSocket manager is accessed correctly
    - Event type is "orchestrator:instructions_fetched"
    - Data includes orchestrator_id, project_id, estimated_tokens
    - Broadcast is to correct tenant
    - Non-blocking error handling
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    # Setup
    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")

    # Mock WebSocket manager
    mock_ws_manager = AsyncMock()
    mock_ws_manager.broadcast_to_tenant = AsyncMock()

    # Register tools
    register_orchestration_tools(mcp, db_manager)

    # Patch app state to return mock WebSocket manager
    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_ws_manager

        # Call get_orchestrator_instructions
        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        result = await get_orchestrator_instructions(
            orchestrator_id=test_orchestrator_job.job_id, tenant_key=test_tenant.tenant_key
        )

        # Verify result
        assert "error" not in result
        assert result["orchestrator_id"] == test_orchestrator_job.job_id
        assert result["thin_client"] is True

        # Verify WebSocket broadcast was called
        mock_ws_manager.broadcast_to_tenant.assert_called_once()

        # Verify broadcast parameters
        call_args = mock_ws_manager.broadcast_to_tenant.call_args
        assert call_args.kwargs["tenant_key"] == test_tenant.tenant_key
        assert call_args.kwargs["event_type"] == "orchestrator:instructions_fetched"

        data = call_args.kwargs["data"]
        assert data["orchestrator_id"] == test_orchestrator_job.job_id
        assert data["project_id"] == str(test_project.id)
        assert "estimated_tokens" in data
        assert data["status"] == "active"
        assert data["thin_client"] is True


@pytest.mark.asyncio
async def test_websocket_broadcast_graceful_failure(db_session, test_orchestrator_job, test_tenant):
    """
    Test Amendment A: Non-blocking WebSocket error handling

    Validates:
    - WebSocket failures don't break MCP tool
    - Error is logged but not propagated
    - Tool still returns success
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    # Setup
    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")

    # Mock WebSocket manager that raises error
    mock_ws_manager = AsyncMock()
    mock_ws_manager.broadcast_to_tenant.side_effect = Exception("WebSocket error")

    register_orchestration_tools(mcp, db_manager)

    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_ws_manager

        from giljo_mcp.tools.orchestration import get_orchestrator_instructions

        # Should NOT raise exception despite WebSocket error
        result = await get_orchestrator_instructions(
            orchestrator_id=test_orchestrator_job.job_id, tenant_key=test_tenant.tenant_key
        )

        # Verify tool still succeeds
        assert "error" not in result
        assert result["orchestrator_id"] == test_orchestrator_job.job_id


# =============================================================================
# AMENDMENT B: Agent Thin Client Tests
# =============================================================================


@pytest.mark.asyncio
async def test_get_agent_mission_thin_client(db_session, test_agent_job, test_tenant):
    """
    Test Amendment B: get_agent_mission() enhanced for thin client

    Validates:
    - Fetches from MCPAgentJob (not Agent model)
    - Returns mission stored in database
    - Includes thin_client flag
    - Token estimate calculated
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    from giljo_mcp.tools.orchestration import get_agent_mission

    result = await get_agent_mission(job_id=test_agent_job.job_id, tenant_key=test_tenant.tenant_key)

    # Verify result structure
    assert result["success"] is True
    assert result["job_id"] == test_agent_job.job_id
    assert result["agent_display_name"] == "backend"
    assert result["mission"] == test_agent_job.mission
    assert result["project_id"] == str(test_agent_job.project_id)
    assert result["thin_client"] is True
    assert "estimated_tokens" in result
    assert result["estimated_tokens"] > 0


@pytest.mark.asyncio
async def test_get_agent_mission_not_found(db_session, test_tenant):
    """
    Test Amendment B: Error handling for missing agent

    Validates:
    - Returns structured error response
    - Includes troubleshooting steps
    - Multi-tenant isolation enforced
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    from giljo_mcp.tools.orchestration import get_agent_mission

    result = await get_agent_mission(job_id="nonexistent-id", tenant_key=test_tenant.tenant_key)

    # Verify error response
    assert result["error"] == "NOT_FOUND"
    assert "message" in result
    assert "troubleshooting" in result
    assert len(result["troubleshooting"]) > 0
    assert result["severity"] == "ERROR"


@pytest.mark.asyncio
async def test_spawn_agent_job_thin_prompt(db_session, test_project, test_tenant, test_orchestrator_job):
    """
    Test Amendment B: spawn_agent_job() generates thin prompts

    Validates:
    - Agent job created in database with mission
    - Returned prompt is ~10 lines (not 1000+)
    - Prompt contains identity only
    - Mission NOT embedded in prompt
    - Token estimates calculated
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    # Mock WebSocket manager
    mock_ws_manager = AsyncMock()
    mock_ws_manager.broadcast_to_tenant = AsyncMock()

    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_ws_manager

        from giljo_mcp.tools.orchestration import spawn_agent_job

        mission_text = "Implement user authentication with JWT tokens, password hashing, and session management"

        result = await spawn_agent_job(
            agent_display_name="backend",
            agent_name="Backend Implementer",
            mission=mission_text,
            project_id=str(test_project.id),
            tenant_key=test_tenant.tenant_key,
            parent_job_id=test_orchestrator_job.job_id,
        )

        # Verify success
        assert result["success"] is True
        assert "job_id" in result
        assert result["thin_client"] is True
        assert result["mission_stored"] is True

        # Verify prompt is thin
        prompt = result["agent_prompt"]
        prompt_lines = prompt.split("\n")
        assert len(prompt_lines) <= 20, f"Prompt should be ~10-15 lines, got {len(prompt_lines)}"

        # Verify mission NOT in prompt
        assert mission_text not in prompt, "Mission should NOT be embedded in prompt"

        # Verify prompt contains get_agent_mission instruction
        assert "get_agent_mission" in prompt
        assert result["job_id"] in prompt

        # Verify token estimates
        assert result["prompt_tokens"] < 100, "Prompt should be <100 tokens"
        assert result["mission_tokens"] > 0

        # Verify agent job created in database
        agent_job = await db_session.get(AgentExecution, result["job_id"])
        assert agent_job is not None
        assert agent_job.mission == mission_text
        assert agent_job.spawned_by == test_orchestrator_job.job_id


@pytest.mark.asyncio
async def test_agent_prompt_is_thin(db_session, test_project, test_tenant):
    """
    Test Amendment B: Validate agent prompts are thin (~10 lines)

    Critical validation that prompts are NOT fat (1000+ lines)
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    mock_ws_manager = AsyncMock()

    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_ws_manager

        from giljo_mcp.tools.orchestration import spawn_agent_job

        # Create agent with large mission (500 lines)
        large_mission = "\n".join([f"Task {i}: Do something complex" for i in range(500)])

        result = await spawn_agent_job(
            agent_display_name="frontend",
            agent_name="Frontend Builder",
            mission=large_mission,
            project_id=str(test_project.id),
            tenant_key=test_tenant.tenant_key,
        )

        # Prompt should STILL be thin even with large mission
        prompt = result["agent_prompt"]
        prompt_lines = len(prompt.split("\n"))

        assert prompt_lines <= 20, f"Prompt MUST be thin (~10-15 lines), got {prompt_lines}"
        assert large_mission not in prompt, "Large mission MUST NOT be in prompt"


@pytest.mark.asyncio
async def test_agent_mission_stored_not_embedded(db_session, test_project, test_tenant):
    """
    Test Amendment B: Critical validation that mission is stored, not embedded

    This is THE defining characteristic of thin client architecture.
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    mock_ws_manager = AsyncMock()

    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_ws_manager

        from giljo_mcp.tools.orchestration import spawn_agent_job

        mission = "SECRET_MISSION_TEXT_12345"  # Unique identifier

        result = await spawn_agent_job(
            agent_display_name="tester",
            agent_name="QA Tester",
            mission=mission,
            project_id=str(test_project.id),
            tenant_key=test_tenant.tenant_key,
        )

        # Verify mission is NOT in prompt
        assert mission not in result["agent_prompt"], "CRITICAL: Mission must NOT be embedded in prompt"

        # Verify mission IS in database
        agent_job = await db_session.get(AgentExecution, result["job_id"])
        assert agent_job.mission == mission, "CRITICAL: Mission must be stored in database"


@pytest.mark.asyncio
async def test_websocket_broadcast_agent_created(db_session, test_project, test_tenant):
    """
    Test Amendment B: WebSocket broadcast when agent spawned

    Validates:
    - agent:created event broadcast
    - Contains agent details
    - Includes thin_client flag
    - Token estimates included
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    mock_ws_manager = AsyncMock()
    mock_ws_manager.broadcast_to_tenant = AsyncMock()

    with patch("api.app.state") as mock_state:
        mock_state.websocket_manager = mock_ws_manager

        from giljo_mcp.tools.orchestration import spawn_agent_job

        result = await spawn_agent_job(
            agent_display_name="orchestrator",
            agent_name="Sub-Orchestrator",
            mission="Coordinate sub-agents",
            project_id=str(test_project.id),
            tenant_key=test_tenant.tenant_key,
        )

        # Verify WebSocket broadcast
        mock_ws_manager.broadcast_to_tenant.assert_called_once()

        call_args = mock_ws_manager.broadcast_to_tenant.call_args
        assert call_args.kwargs["event_type"] == "agent:created"

        data = call_args.kwargs["data"]
        assert data["job_id"] == result["job_id"]
        assert data["agent_display_name"] == "orchestrator"
        assert data["agent_name"] == "Sub-Orchestrator"
        assert data["thin_client"] is True
        assert "prompt_tokens" in data
        assert "mission_tokens" in data


# =============================================================================
# MULTI-TENANT ISOLATION TESTS
# =============================================================================


@pytest.mark.asyncio
async def test_multi_tenant_isolation_get_agent_mission(db_session, test_agent_job):
    """
    Test Amendment B: Multi-tenant isolation in get_agent_mission()

    Validates:
    - Cannot access agent from different tenant
    - Returns NOT_FOUND error
    - No data leakage
    """
    from fastmcp import FastMCP

    from giljo_mcp.database import DatabaseManager

    mcp = FastMCP("test-mcp")
    db_manager = DatabaseManager(":memory:")
    register_orchestration_tools(mcp, db_manager)

    from giljo_mcp.tools.orchestration import get_agent_mission

    # Try to access with wrong tenant
    result = await get_agent_mission(job_id=test_agent_job.job_id, tenant_key="wrong_tenant_key")

    # Verify access denied
    assert result["error"] == "NOT_FOUND"
    assert "mission" not in result
    assert "agent_name" not in result


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
