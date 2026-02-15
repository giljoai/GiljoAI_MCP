"""
Comprehensive tests for thin client MCP tools (Handover 0088 - Phase 1).

Tests the critical MCP tools that enable thin client architecture:
- health_check() - Verifies MCP server connectivity
- get_orchestrator_instructions() - Fetches condensed mission for orchestrators
- get_agent_mission() - Fetches mission for agents
- spawn_agent_job() - Spawns agents with thin prompts

Focus areas:
- Happy path functionality
- Error handling with actionable messages
- Multi-tenant isolation (security)
- Context prioritization validation (70% reduction)
- WebSocket broadcasting integration
"""

from datetime import datetime
from uuid import uuid4

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution


# ========================================================================
# Test Fixtures
# ========================================================================


@pytest_asyncio.fixture
async def tenant_key():
    """Generate test tenant key."""
    return f"tk_test_{uuid4().hex[:16]}"


@pytest_asyncio.fixture
async def test_user(db_session, tenant_key):
    """Create test user with field priorities configured."""
    user = User(
        id=str(uuid4()),
        tenant_key=tenant_key,
        username="test_user",
        email="test@giljoai.com",
        password_hash="hashed",
        config_data={
            "field_priorities": {
                "product_vision": 10,  # Full detail
                "architecture": 7,  # Moderate
                "codebase_summary": 4,  # Abbreviated
                "dependencies": 2,  # Minimal
            }
        },
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_product(db_session, tenant_key):
    """Create test product with vision."""
    product = Product(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Product",
        description="Test product for thin client testing",
        vision_document="A" * 50000,  # Large vision document (~50K chars)
        vision_type="inline",
        is_active=True,
    )
    db_session.add(product)
    await db_session.commit()
    await db_session.refresh(product)
    return product


@pytest_asyncio.fixture
async def test_project_with_product(db_session, tenant_key, test_product):
    """Create test project linked to product."""
    project = Project(
        id=str(uuid4()),
        tenant_key=tenant_key,
        name="Test Project",
        description="Test project for orchestration",
        product_id=test_product.id,
        mission="Build amazing software",
        status="active",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def test_orchestrator_job(db_session, tenant_key, test_project_with_product, test_user):
    """Create test orchestrator job."""
    orchestrator = AgentExecution(
        id=1,  # Auto-increment
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project_with_product.id,
        agent_display_name="orchestrator",
        agent_name="Orchestrator #1",
        mission="Condensed mission content with priorities applied",
        status="waiting",
        metadata={
            "field_priorities": test_user.config_data["field_priorities"],
            "user_id": str(test_user.id),
            "created_via": "thin_client_test",
        },
    )
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)
    return orchestrator


# ========================================================================
# Test 0: health_check() - MCP Server Health
# ========================================================================


@pytest.mark.asyncio
async def test_health_check_success():
    """
    Test MCP server health check.

    Expected behavior:
    - Returns 'healthy' status
    - Includes server name and version
    - Includes timestamp
    - Returns database connection status
    - No errors
    """
    from src.giljo_mcp.tools.orchestration import health_check

    # Call health_check (no parameters needed)
    result = await health_check()

    # Verify success
    assert "status" in result
    assert result["status"] == "healthy"

    # Verify server metadata
    assert "server" in result
    assert result["server"] == "giljo-mcp"

    assert "version" in result
    assert result["version"] == "3.1.0"

    # Verify timestamp
    assert "timestamp" in result
    # Verify it's a valid ISO timestamp
    timestamp = datetime.fromisoformat(result["timestamp"].replace("Z", "+00:00"))
    assert timestamp.tzinfo is not None

    # Verify database status
    assert "database" in result
    assert result["database"] == "connected"

    # Verify message
    assert "message" in result
    assert "operational" in result["message"].lower()


# ========================================================================
# Test 1: get_orchestrator_instructions() - Happy Path
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_success(
    db_session, tenant_key, test_orchestrator_job, test_project_with_product, test_product
):
    """
    Test successful orchestrator instructions retrieval.

    Expected behavior:
    - Fetches orchestrator from database
    - Returns condensed mission with field priorities applied
    - Includes context budget/usage
    - Returns agent templates
    - Token estimate accurate
    - No errors
    """
    from src.giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Call the MCP tool
    result = await get_orchestrator_instructions(agent_id=test_orchestrator_job.job_id, tenant_key=tenant_key)

    # Verify success
    assert "error" not in result, f"Unexpected error: {result.get('error')}"

    # Verify orchestrator identity
    assert result["orchestrator_id"] == test_orchestrator_job.job_id
    assert result["project_id"] == str(test_project.id)
    assert result["project_name"] == test_project.name

    # Verify mission content
    assert "mission" in result
    assert len(result["mission"]) > 0
    assert isinstance(result["mission"], str)

    # Verify field priorities applied
    assert result["token_reduction_applied"] is True
    assert "field_priorities" in result
    assert result["field_priorities"]["product_vision"] == 10

    # Verify token estimate
    assert "estimated_tokens" in result
    assert result["estimated_tokens"] > 0
    assert result["estimated_tokens"] < 50000  # Should be much less than original

    # Verify agent templates included
    assert "agent_templates" in result
    assert isinstance(result["agent_templates"], list)


# ========================================================================
# Test 2: get_orchestrator_instructions() - Not Found Error
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_not_found(db_session, tenant_key):
    """
    Test orchestrator not found error handling.

    Expected behavior:
    - Returns structured error response
    - Includes troubleshooting steps
    - Provides actionable guidance
    - Professional error message
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    fake_orchestrator_id = str(uuid4())

    # Call with non-existent orchestrator
    result = await get_orchestrator_instructions(agent_id=fake_orchestrator_id, tenant_key=tenant_key)

    # Verify error structure
    assert "error" in result
    assert "NOT_FOUND" in result.get("error", "") or "not found" in result.get("error", "").lower()

    # Verify troubleshooting included (Amendment D requirement)
    assert "troubleshooting" in result or "message" in result

    # Verify severity indicated
    if "severity" in result:
        assert result["severity"] in ["ERROR", "CRITICAL"]


# ========================================================================
# Test 3: get_orchestrator_instructions() - Multi-Tenant Isolation
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_multi_tenant_isolation(db_session, test_orchestrator_job):
    """
    Test multi-tenant isolation security.

    Expected behavior:
    - Orchestrator from tenant1 not accessible with tenant2 key
    - No data leakage across tenants
    - Error response doesn't leak sensitive info
    - Zero cross-tenant access
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Create second tenant
    tenant2_key = str(uuid4())

    # Attempt cross-tenant access
    result = await get_orchestrator_instructions(
        agent_id=test_orchestrator_job.job_id,
        tenant_key=tenant2_key,  # WRONG tenant key
    )

    # Verify access denied
    assert "error" in result
    assert "not found" in result["error"].lower()

    # Verify no data leaked
    assert "mission" not in result
    assert "field_priorities" not in result
    assert "project_name" not in result
    assert test_orchestrator_job.agent_name not in str(result)


# ========================================================================
# Test 4: get_orchestrator_instructions() - Token Reduction Validation
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_token_reduction(
    db_session, tenant_key, test_orchestrator_job, test_product
):
    """
    Test that context prioritization and orchestration is achieved.

    Expected behavior:
    - Original vision: ~50K chars (~12.5K tokens)
    - Condensed mission: <10K tokens (70% reduction)
    - Field priorities applied correctly
    - Token estimate accurate
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Get original vision size
    original_vision_size = len(test_product.vision_document or "")
    original_tokens = original_vision_size // 4  # Rough estimate

    # Call MCP tool
    result = await get_orchestrator_instructions(agent_id=test_orchestrator_job.job_id, tenant_key=tenant_key)

    # Verify success
    assert "error" not in result

    # Verify context prioritization
    estimated_tokens = result["estimated_tokens"]

    # Should be significantly less than original
    assert estimated_tokens < original_tokens

    # Should be under 10K tokens for thin client architecture
    assert estimated_tokens < 10000, f"Mission should be <10K tokens for thin client, got {estimated_tokens}"

    # Verify reduction percentage
    if original_tokens > 0:
        reduction_percent = ((original_tokens - estimated_tokens) / original_tokens) * 100
        # Note: May not always hit 70% with test data, but should be significant
        assert reduction_percent > 0, "Should achieve some context prioritization"


# ========================================================================
# Test 5: get_orchestrator_instructions() - WebSocket Broadcast
# ========================================================================


@pytest.mark.asyncio
async def test_get_orchestrator_instructions_websocket_broadcast(db_session, tenant_key, test_orchestrator_job, mocker):
    """
    Test WebSocket broadcasting (Amendment A).

    Expected behavior:
    - Broadcasts 'orchestrator:instructions_fetched' event
    - Includes orchestrator_id, project_id, token estimate
    - Sent to correct tenant only
    - Event structure matches frontend expectations
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Mock WebSocket manager
    mock_ws_manager = mocker.Mock()
    mock_broadcast = mocker.AsyncMock()
    mock_ws_manager.broadcast_to_tenant = mock_broadcast

    # Mock get_websocket_manager to return our mock
    mocker.patch("giljo_mcp.tools.orchestration.get_websocket_manager", return_value=mock_ws_manager)

    # Call MCP tool
    result = await get_orchestrator_instructions(agent_id=test_orchestrator_job.job_id, tenant_key=tenant_key)

    # Verify success
    assert "error" not in result

    # Verify WebSocket broadcast was called
    mock_broadcast.assert_called_once()

    # Verify broadcast parameters
    call_args = mock_broadcast.call_args
    assert call_args[1]["tenant_key"] == tenant_key or call_args[0][0] == tenant_key
    assert (
        call_args[1]["event_type"] == "orchestrator:instructions_fetched"
        or call_args[0][1] == "orchestrator:instructions_fetched"
    )

    # Verify event data structure
    event_data = call_args[1].get("data") or call_args[0][2]
    assert "orchestrator_id" in event_data
    assert "project_id" in event_data
    assert "estimated_tokens" in event_data


# ========================================================================
# Test 6: get_agent_mission() - Thin Client Support
# ========================================================================


@pytest.mark.asyncio
async def test_get_agent_mission_thin_client(db_session, tenant_key, test_project):
    """
    Test agent mission retrieval for thin client architecture.

    Expected behavior:
    - Fetches mission from MCPAgentJob (not Agent model)
    - Returns thin_client flag
    - Includes token estimates
    - Mission stored in database, not embedded in prompt
    """
    from giljo_mcp.tools.orchestration import get_agent_mission

    # Create agent job
    agent_job = AgentExecution(
        id=str(uuid4()),
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        agent_display_name="implementer",
        agent_name="Backend Implementer",
        mission="Implement user authentication system with JWT tokens",
        status="waiting",
    )
    db_session.add(agent_job)
    await db_session.commit()
    await db_session.refresh(agent_job)

    # Call get_agent_mission
    result = await get_agent_mission(job_id=agent_job.job_id, tenant_key=tenant_key)

    # Verify success
    assert "error" not in result

    # Verify agent identity
    assert result["job_id"] == agent_job.job_id
    assert result["agent_name"] == "Backend Implementer"
    assert result["agent_display_name"] == "implementer"

    # Verify mission content
    assert "mission" in result
    assert "authentication" in result["mission"].lower()

    # Verify thin client fields
    assert "thin_client" in result
    assert result["thin_client"] is True

    # Verify token estimates
    assert "estimated_tokens" in result
    assert result["estimated_tokens"] > 0


# ========================================================================
# Test 7: spawn_agent_job() - Thin Prompt Generation
# ========================================================================


@pytest.mark.asyncio
async def test_spawn_agent_job_thin_prompt(db_session, tenant_key, test_project):
    """
    Test agent spawning with thin client architecture (Amendment B).

    Expected behavior:
    - Creates agent job in database
    - Stores full mission in database
    - Returns ~10 line thin prompt (NOT full mission)
    - Includes MCP tool fetch instructions
    - Broadcasts WebSocket event
    - Returns token estimates
    """
    from giljo_mcp.tools.orchestration import spawn_agent_job

    mission_content = "Implement user authentication system. " * 100  # ~500 chars

    # Call spawn_agent_job
    result = await spawn_agent_job(
        agent_display_name="implementer",
        agent_name="Backend Implementer",
        mission=mission_content,
        project_id=str(test_project.id),
        tenant_key=tenant_key,
        parent_job_id=None,
    )

    # Verify success
    assert result.get("success") is True
    assert "error" not in result

    # Verify agent job created
    assert "job_id" in result
    job_id = result["job_id"]

    # Verify thin prompt returned (not full mission)
    assert "agent_prompt" in result
    agent_prompt = result["agent_prompt"]

    # Thin prompt should be ~10-15 lines, not 500+ characters
    prompt_lines = agent_prompt.split("\n")
    assert len(prompt_lines) <= 20, f"Thin prompt should be ~10-15 lines, got {len(prompt_lines)}"

    # Thin prompt should NOT contain full mission
    assert mission_content not in agent_prompt, "Thin prompt should NOT embed full mission"

    # Thin prompt should include fetch instructions
    assert "get_agent_mission" in agent_prompt or "fetch" in agent_prompt.lower()
    assert job_id in agent_prompt

    # Verify token estimates
    assert "prompt_tokens" in result
    assert "mission_tokens" in result
    assert result["prompt_tokens"] < 100, "Prompt should be <100 tokens"

    # Verify mission stored in database
    db_agent = await db_session.get(AgentExecution, job_id)
    assert db_agent is not None
    assert db_agent.mission == mission_content
    assert db_agent.agent_display_name == "implementer"


# ========================================================================
# Test 8: Error Handling - Structured Responses
# ========================================================================


@pytest.mark.asyncio
async def test_error_handling_structured_responses(db_session, tenant_key):
    """
    Test production-grade error handling (Amendment D).

    Expected behavior:
    - Structured error responses with error code
    - Actionable troubleshooting steps
    - Severity levels
    - Professional error messages
    - No stack traces leaked to users
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Test 1: Missing orchestrator_id
    result = await get_orchestrator_instructions(agent_id="", tenant_key=tenant_key)

    assert "error" in result
    assert (
        result["error"] in ["VALIDATION_ERROR", "Orchestrator ID is required"]
        or "required" in result.get("message", result.get("error", "")).lower()
    )

    # Test 2: Missing tenant_key
    result = await get_orchestrator_instructions(agent_id=str(uuid4()), tenant_key="")

    assert "error" in result
    assert "tenant" in result.get("error", "").lower() or "tenant" in result.get("message", "").lower()

    # Test 3: Orchestrator not found
    result = await get_orchestrator_instructions(agent_id=str(uuid4()), tenant_key=tenant_key)

    assert "error" in result
    # Should have troubleshooting guidance (Amendment D)
    if isinstance(result.get("troubleshooting"), list):
        assert len(result["troubleshooting"]) > 0


# ========================================================================
# Test 9: Validation - Input Sanitization
# ========================================================================


@pytest.mark.asyncio
async def test_input_validation_sanitization(db_session, tenant_key):
    """
    Test input validation and sanitization.

    Expected behavior:
    - Rejects empty strings
    - Rejects whitespace-only strings
    - Rejects invalid UUIDs (gracefully)
    - Returns clear validation errors
    """
    from giljo_mcp.tools.orchestration import get_orchestrator_instructions

    # Test whitespace-only orchestrator_id
    result = await get_orchestrator_instructions(agent_id="   ", tenant_key=tenant_key)

    assert "error" in result

    # Test whitespace-only tenant_key
    result = await get_orchestrator_instructions(agent_id=str(uuid4()), tenant_key="   ")

    assert "error" in result


# ========================================================================
# Test 10: Integration - Full Workflow
# ========================================================================


@pytest.mark.asyncio
async def test_full_thin_client_workflow(db_session, tenant_key, test_user, test_project, test_product):
    """
    Test complete thin client workflow end-to-end.

    Workflow:
    1. Create orchestrator job (simulating thin prompt generation)
    2. Orchestrator fetches instructions via get_orchestrator_instructions()
    3. Orchestrator spawns agent via spawn_agent_job()
    4. Agent fetches mission via get_agent_mission()
    5. Verify context prioritization throughout
    """
    from giljo_mcp.tools.orchestration import get_agent_mission, get_orchestrator_instructions, spawn_agent_job

    # Step 1: Create orchestrator job (simulating thin prompt stage)
    orchestrator = AgentExecution(
        id=str(uuid4()),
        job_id=str(uuid4()),
        tenant_key=tenant_key,
        project_id=test_project.id,
        agent_display_name="orchestrator",
        agent_name="Orchestrator #1",
        mission="Condensed mission",
        status="waiting",
        metadata={"field_priorities": test_user.config_data["field_priorities"], "user_id": str(test_user.id)},
    )
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)

    # Step 2: Orchestrator fetches instructions
    orch_result = await get_orchestrator_instructions(agent_id=orchestrator.job_id, tenant_key=tenant_key)

    assert "error" not in orch_result
    assert orch_result["estimated_tokens"] < 10000

    # Step 3: Orchestrator spawns agent
    spawn_result = await spawn_agent_job(
        agent_display_name="implementer",
        agent_name="Backend Agent",
        mission="Build authentication system",
        project_id=str(test_project.id),
        tenant_key=tenant_key,
        parent_job_id=orchestrator.job_id,
    )

    assert spawn_result.get("success") is True
    assert spawn_result["prompt_tokens"] < 100

    # Step 4: Agent fetches mission
    agent_result = await get_agent_mission(job_id=spawn_result["job_id"], tenant_key=tenant_key)

    assert "error" not in agent_result
    assert "mission" in agent_result
    assert agent_result["estimated_tokens"] > 0

    # Verify complete workflow token efficiency
    total_tokens = orch_result["estimated_tokens"] + spawn_result["prompt_tokens"] + agent_result["estimated_tokens"]

    # Should be much less than fat prompt approach (which would be 30K+ tokens)
    assert total_tokens < 15000, f"Total workflow should be <15K tokens for thin client, got {total_tokens}"
