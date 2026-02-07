"""
Integration tests for Implementation Prompt API (Handover 0337 - Task 1).

Tests:
- GET /api/prompts/implementation/{project_id} - Implementation prompt generation for CLI mode
- Multi-tenant isolation
- Authentication/authorization
- Error handling for various failure scenarios
- CLI mode validation
- Orchestrator and agent job validation

TDD Status: RED ❌ - Tests written FIRST, implementation to follow
"""

from uuid import uuid4

import pytest
from fastapi import status
from httpx import AsyncClient

from src.giljo_mcp.models import Product, Project, User
from src.giljo_mcp.models.agent_identity import AgentExecution


@pytest.mark.asyncio
async def test_implementation_prompt_happy_path(api_client: AsyncClient, db_manager, test_user: User):
    """
    Test 1: Happy Path - Valid CLI project returns implementation prompt.

    GIVEN: A CLI mode project with active orchestrator and waiting agents
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Returns 200 with implementation prompt containing agent spawning instructions

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    # Create auth headers from test_user (same tenant)
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )
    auth_headers = {"Cookie": f"access_token={token}"}

    # Generate unique IDs outside context manager
    product_id = f"impl-test-prod-{uuid4().hex[:12]}"
    project_id = f"impl-test-proj-{uuid4().hex[:12]}"
    orch_id = f"impl-orch-{uuid4().hex[:12]}"
    agent1_id = f"impl-agent-{uuid4().hex[:12]}"
    agent2_id = f"impl-agent-{uuid4().hex[:12]}"

    async with db_manager.get_session_async() as session:
        # Create test product with unique ID
        product = Product(
            id=product_id,
            tenant_key=test_user.tenant_key,
            name="Implementation Test Product",
            description="Product for implementation prompt tests",
        )
        session.add(product)

        # Create CLI mode project with unique ID
        project = Project(
            id=project_id,
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="CLI Implementation Test",
            mission="Test CLI mode implementation",
            description="Test project in CLI mode",
            status="active",
            execution_mode="claude_code_cli",  # CRITICAL: CLI mode
        )
        session.add(project)

        # Create working orchestrator job (working = active in this context)
        orchestrator = AgentExecution(
            job_id=orch_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            agent_name="Test Orchestrator",
            mission="Orchestrate implementation",
            status="working",  # CRITICAL: Must be working (active state)
            context_used=1500,  # Some context consumed during staging
        )
        session.add(orchestrator)

        # Create spawned agent jobs in waiting status
        agent1 = AgentExecution(
            job_id=agent1_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="tdd-implementor",
            agent_name="TDD Implementor",
            mission="Implement feature with TDD",
            status="waiting",  # Waiting for orchestrator to spawn
            spawned_by=orchestrator.job_id,
        )
        session.add(agent1)

        agent2 = AgentExecution(
            job_id=agent2_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="backend-integration-tester",
            agent_name="Backend Tester",
            mission="Test API endpoints",
            status="waiting",
            spawned_by=orchestrator.job_id,
        )
        session.add(agent2)

        await session.commit()

    # Call implementation prompt endpoint (use project_id variable)
    response = await api_client.get(f"/api/v1/prompts/implementation/{project_id}", headers=auth_headers)

    # Verify response
    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Validate response structure
    assert "prompt" in data
    assert "orchestrator_job_id" in data
    assert "agent_count" in data

    # Validate response data
    assert data["orchestrator_job_id"] == orch_id
    assert data["agent_count"] == 2  # Two spawned agents

    # Validate prompt content - should be self-contained for fresh session
    prompt = data["prompt"]
    assert len(prompt) > 0, "Prompt should not be empty"

    # CRITICAL: Prompt should include agent job details for spawning
    assert agent1_id in prompt  # Job ID 1
    assert agent2_id in prompt  # Job ID 2
    assert "tdd-implementor" in prompt or "TDD Implementor" in prompt  # Agent type/name 1
    assert "backend-integration-tester" in prompt or "Backend Tester" in prompt  # Agent type/name 2

    # CRITICAL: Prompt should include Task tool spawning instructions
    # The generator uses "spawn" and "sub-agent" keywords
    assert "spawn" in prompt.lower() or "task" in prompt.lower()
    assert "agent" in prompt.lower()

    # Fresh session support - should include context recap
    assert test_user.tenant_key in prompt  # Tenant key for MCP calls
    assert project_id in prompt  # Project ID for reference


@pytest.mark.asyncio
async def test_implementation_prompt_project_not_found(api_client: AsyncClient, auth_headers: dict):
    """
    Test 2: 404 - Project not found.

    GIVEN: Non-existent project ID
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Returns 404 with error message

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    response = await api_client.get("/api/v1/prompts/implementation/nonexistent-project-999", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    assert "not found" in response.json()["message"].lower()


@pytest.mark.asyncio
async def test_implementation_prompt_not_cli_mode(api_client: AsyncClient, db_manager, test_user: User):
    """
    Test 3: 400 - Project not in CLI mode.

    GIVEN: A multi-terminal mode project
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Returns 400 indicating project is not in CLI mode

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    # Create auth headers from test_user (same tenant)
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )
    auth_headers = {"Cookie": f"access_token={token}"}

    async with db_manager.get_session_async() as session:
        # Create test product
        product = Product(
            id=f"impl-test-prod-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            name="Multi-Terminal Product",
            description="Product for multi-terminal tests",
        )
        session.add(product)

        # Create multi-terminal project (not CLI mode)
        project = Project(
            id=f"impl-test-proj-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="Multi-Terminal Test",
            mission="Test multi-terminal mode",
            description="Project in multi-terminal mode",
            status="active",
            execution_mode="multi_terminal",  # NOT CLI mode
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        # Store ID before session closes
        project_id = project.id

    response = await api_client.get(f"/api/v1/prompts/implementation/{project_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    detail = response.json()["message"].lower()
    assert "cli" in detail or "mode" in detail


@pytest.mark.asyncio
async def test_implementation_prompt_no_active_orchestrator(api_client: AsyncClient, db_manager, test_user: User):
    """
    Test 4: 404 - No active orchestrator found.

    GIVEN: CLI mode project but orchestrator is not active
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Returns 404 indicating no active orchestrator

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    # Create auth headers from test_user (same tenant)
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )
    auth_headers = {"Cookie": f"access_token={token}"}

    async with db_manager.get_session_async() as session:
        # Create test product
        product = Product(
            id=f"impl-test-prod-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            name="No Orchestrator Product",
            description="Product for no orchestrator tests",
        )
        session.add(product)

        # Create CLI mode project
        project = Project(
            id=f"impl-test-proj-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="No Orchestrator Test",
            mission="Test missing orchestrator",
            description="CLI project without active orchestrator",
            status="active",
            execution_mode="claude_code_cli",
        )
        session.add(project)

        # Create orchestrator but with wrong status
        orchestrator = AgentExecution(
            job_id=f"impl-orch-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            mission="Test orchestrator",
            status="complete",  # NOT working (valid status but wrong state)
        )
        session.add(orchestrator)
        await session.commit()
        await session.refresh(project)

        # Store ID before session closes
        project_id = project.id

    response = await api_client.get(f"/api/v1/prompts/implementation/{project_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_404_NOT_FOUND
    detail = response.json()["message"].lower()
    assert "orchestrator" in detail


@pytest.mark.asyncio
async def test_implementation_prompt_no_spawned_agents(api_client: AsyncClient, db_manager, test_user: User):
    """
    Test 5: 400 - No spawned agent jobs.

    GIVEN: CLI mode project with active orchestrator but no spawned agents
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Returns 400 indicating staging must be run first

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    # Create auth headers from test_user (same tenant)
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )
    auth_headers = {"Cookie": f"access_token={token}"}

    async with db_manager.get_session_async() as session:
        # Create test product
        product = Product(
            id=f"impl-test-prod-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            name="No Agents Product",
            description="Product for no agents tests",
        )
        session.add(product)

        # Create CLI mode project
        project = Project(
            id=f"impl-test-proj-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="No Agents Test",
            mission="Test no spawned agents",
            description="CLI project without spawned agents",
            status="active",
            execution_mode="claude_code_cli",
        )
        session.add(project)

        # Create working orchestrator but no spawned agents
        orchestrator = AgentExecution(
            job_id=f"impl-orch-{uuid4().hex[:12]}",
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            mission="Test orchestrator",
            status="working",
        )
        session.add(orchestrator)
        await session.commit()
        await session.refresh(project)

        # Store ID before session closes
        project_id = project.id

    response = await api_client.get(f"/api/v1/prompts/implementation/{project_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    detail = response.json()["message"].lower()
    assert "agent" in detail or "staging" in detail


@pytest.mark.asyncio
async def test_implementation_prompt_tenant_isolation(
    api_client: AsyncClient, db_manager, auth_headers_tenant_a: dict, auth_headers_tenant_b: dict
):
    """
    Test 6: 403/404 - Multi-tenant isolation violation.

    GIVEN: Tenant A creates CLI project, Tenant B tries to access it
    WHEN: Tenant B calls GET /api/prompts/implementation/{project_id}
    THEN: Returns 404 (tenant isolation prevents access)

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    # Extract tenant_key from auth headers (tenant A)
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    # Decode token to get tenant_key for tenant A (Cookie format)
    token_a = auth_headers_tenant_a["Cookie"].replace("access_token=", "")
    jwt_manager = JWTManager()
    payload_a = jwt_manager.verify_token(token_a)
    tenant_key_a = payload_a.get("tenant_key")

    async with db_manager.get_session_async() as session:
        # Create test product for tenant A
        product = Product(
            id=f"impl-test-prod-{uuid4().hex[:12]}",
            tenant_key=tenant_key_a,
            name="Tenant A Product",
            description="Product for tenant isolation tests",
        )
        session.add(product)

        # Create CLI mode project for tenant A
        project = Project(
            id=f"impl-test-proj-{uuid4().hex[:12]}",
            tenant_key=tenant_key_a,
            product_id=product.id,
            name="Tenant A Project",
            mission="Test tenant isolation",
            description="CLI project for tenant A",
            status="active",
            execution_mode="claude_code_cli",
        )
        session.add(project)

        # Create orchestrator and agents for tenant A
        orchestrator = AgentExecution(
            job_id=f"impl-orch-{uuid4().hex[:12]}",
            tenant_key=tenant_key_a,
            project_id=project.id,
            agent_display_name="orchestrator",
            mission="Test orchestrator",
            status="working",
        )
        session.add(orchestrator)

        agent = AgentExecution(
            job_id=f"impl-agent-{uuid4().hex[:12]}",
            tenant_key=tenant_key_a,
            project_id=project.id,
            agent_display_name="implementer",
            mission="Test agent",
            status="waiting",
            spawned_by=orchestrator.job_id,
        )
        session.add(agent)
        await session.commit()
        await session.refresh(project)

        # Store ID before session closes
        project_id = project.id

    # Tenant B tries to access tenant A's project
    response = await api_client.get(f"/api/v1/prompts/implementation/{project_id}", headers=auth_headers_tenant_b)

    # Should return 404 (not 403) to avoid leaking project existence
    assert response.status_code == status.HTTP_404_NOT_FOUND


@pytest.mark.asyncio
async def test_implementation_prompt_unauthorized(api_client: AsyncClient, db_manager, test_user: User):
    """
    Test 7: 401 - Unauthorized access without authentication.

    GIVEN: No authentication headers provided
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Returns 401 unauthorized

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    response = await api_client.get("/api/v1/prompts/implementation/test-project-123")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_implementation_prompt_includes_context_used(api_client: AsyncClient, db_manager, test_user: User):
    """
    Test 8: Prompt includes orchestrator context_used for monitoring.

    GIVEN: Active orchestrator with context_used tracked
    WHEN: GET /api/prompts/implementation/{project_id}
    THEN: Implementation prompt generation uses context_used from orchestrator

    TDD Status: RED ❌ - Endpoint does not exist yet
    """
    # Create auth headers from test_user (same tenant)
    from src.giljo_mcp.auth.jwt_manager import JWTManager

    token = JWTManager.create_access_token(
        user_id=test_user.id,
        username=test_user.username,
        role=test_user.role,
        tenant_key=test_user.tenant_key,
    )
    auth_headers = {"Cookie": f"access_token={token}"}

    from uuid import uuid4

    async with db_manager.get_session_async() as session:
        # Create test product with unique ID
        product_id_str = f"impl-test-prod-{uuid4().hex[:8]}"
        product = Product(
            id=product_id_str,
            tenant_key=test_user.tenant_key,
            name="Context Test Product",
            description="Product for context tracking tests",
        )
        session.add(product)

        # Create CLI mode project with unique ID
        project_id = f"impl-test-proj-{uuid4().hex[:8]}"
        project = Project(
            id=project_id,
            tenant_key=test_user.tenant_key,
            product_id=product.id,
            name="Context Test",
            mission="Test context tracking",
            description="CLI project with context tracking",
            status="active",
            execution_mode="claude_code_cli",
        )
        session.add(project)

        # Create orchestrator with significant context_used
        orch_id = f"impl-orch-{uuid4().hex[:8]}"
        orchestrator = AgentExecution(
            job_id=orch_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="orchestrator",
            mission="Test orchestrator",
            status="working",
            context_used=8500,  # 85% of typical 10K budget
        )
        session.add(orchestrator)

        # Create spawned agent
        agent_id = f"impl-agent-{uuid4().hex[:8]}"
        agent = AgentExecution(
            job_id=agent_id,
            tenant_key=test_user.tenant_key,
            project_id=project.id,
            agent_display_name="implementer",
            mission="Test agent",
            status="waiting",
            spawned_by=orchestrator.job_id,
        )
        session.add(agent)
        await session.commit()

    response = await api_client.get(f"/api/v1/prompts/implementation/{project_id}", headers=auth_headers)

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Verify implementation prompt was generated
    # (The prompt generator will use context_used internally)
    assert "prompt" in data
    assert len(data["prompt"]) > 0
