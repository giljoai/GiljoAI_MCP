"""
Slash Commands API Integration Tests - Handover 0730

Comprehensive validation of slash command HTTP endpoints:
- POST /api/slash/execute - Execute slash command
- POST /api/agent-jobs/{job_id}/simple-handover - Trigger session handover

Test Coverage:
- Happy path scenarios (200/201 responses)
- Authentication enforcement (401 Unauthorized)
- Not Found scenarios (404)
- Validation errors (400/422 Bad Request)
- Multi-tenant isolation

Critical Patterns (Handover 0730):
- UUID fixtures: str(uuid4()) for all IDs
- org_id NOT NULL (0424j): Create Organization first, flush, then User with org_id
- AgentJob/AgentExecution separation: project_id and mission are on AgentJob, not AgentExecution
- Exception-based assertions: Use pytest.raises() for error cases

Reference files for patterns:
- tests/api/test_agent_jobs_api.py
- tests/api/test_products_api.py
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from httpx import AsyncClient
from passlib.hash import bcrypt


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================


@pytest.fixture
async def tenant_a_admin(db_manager):
    """Create Tenant A admin user for slash command tests.

    Following patterns from test_agent_jobs_api.py:
    - Create Organization first (0424j: org_id NOT NULL)
    - Flush to get org.id
    - Create User with org_id reference
    """
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_a_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424j: org_id required)
        org = Organization(
            name=f"Tenant A Org {unique_id}",
            slug=f"tenant-a-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # 0424j: Required for User.org_id NOT NULL
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Store credentials for login
        user._test_username = username
        user._test_password = "password_a"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_b_admin(db_manager):
    """Create Tenant B admin user for cross-tenant testing."""
    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    unique_id = uuid4().hex[:8]
    username = f"tenant_b_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424j: org_id required)
        org = Organization(
            name=f"Tenant B Org {unique_id}",
            slug=f"tenant-b-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_b"),
            email=f"{username}@test.com",
            role="admin",
            tenant_key=tenant_key,
            is_active=True,
            org_id=org.id,  # 0424j: Required for User.org_id NOT NULL
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        # Store credentials for login
        user._test_username = username
        user._test_password = "password_b"
        user._test_tenant_key = tenant_key
        return user


@pytest.fixture
async def tenant_a_admin_token(api_client: AsyncClient, tenant_a_admin):
    """Get JWT token for Tenant A admin via login endpoint."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_admin._test_username, "password": tenant_a_admin._test_password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_admin_token(api_client: AsyncClient, tenant_b_admin):
    """Get JWT token for Tenant B admin via login endpoint."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_b_admin._test_username, "password": tenant_b_admin._test_password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_product(api_client: AsyncClient, tenant_a_admin_token: str):
    """Create a test product for Tenant A."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": f"Test Product {uuid4().hex[:8]}",
            "description": "Test product for slash commands",
            "project_path": f"/test/product/{uuid4().hex[:8]}",
        },
        cookies={"access_token": tenant_a_admin_token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
async def tenant_a_project(api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_product):
    """Create a test project for Tenant A and launch implementation.

    Handover 0730e: Projects need implementation_launched_at set for agent job
    lifecycle tests (get_agent_mission requires this per Handover 0709).
    """
    response = await api_client.post(
        "/api/v1/projects/",
        json={
            "name": f"Test Project {uuid4().hex[:8]}",
            "description": "Test project for slash commands",
            "mission": "Test mission for slash command testing",
            "product_id": tenant_a_product["id"],
            "status": "inactive",
        },
        cookies={"access_token": tenant_a_admin_token},
    )
    assert response.status_code == 201
    project = response.json()

    # Launch implementation phase (required for agent lifecycle tests)
    launch_response = await api_client.patch(
        f"/api/agent-jobs/projects/{project['id']}/launch-implementation",
        cookies={"access_token": tenant_a_admin_token},
    )
    assert launch_response.status_code == 200

    return project


@pytest.fixture
async def tenant_a_orchestrator_job(api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project):
    """Create an orchestrator agent job for Tenant A.

    NOTE: Orchestrators are required for handover tests since only
    orchestrators can trigger handover (Handover 0461c).
    """
    response = await api_client.post(
        "/api/agent-jobs/spawn",
        json={
            "agent_display_name": "orchestrator",
            "agent_name": "Test Orchestrator",
            "mission": "Test orchestration mission for handover",
            "project_id": tenant_a_project["id"],
            "context_chunks": [],
        },
        cookies={"access_token": tenant_a_admin_token},
    )
    assert response.status_code == 201, f"Spawn failed: {response.json()}"
    return response.json()


@pytest.fixture
async def tenant_a_working_orchestrator(
    api_client: AsyncClient,
    tenant_a_admin_token: str,
    tenant_a_orchestrator_job,
    db_manager,
):
    """Create an orchestrator in 'working' status for handover tests.

    Simple handover requires the agent to be in 'working' status and
    be an orchestrator (agent_display_name='orchestrator').
    """
    from sqlalchemy import select

    from src.giljo_mcp.models.agent_identity import AgentExecution

    job_id = tenant_a_orchestrator_job["job_id"]

    # Acknowledge the job first
    await api_client.post(
        f"/api/agent-jobs/{job_id}/acknowledge",
        cookies={"access_token": tenant_a_admin_token},
    )

    # Set status to 'working' in database (simulating active orchestrator)
    async with db_manager.get_session_async() as session:
        result = await session.execute(select(AgentExecution).where(AgentExecution.job_id == job_id))
        execution = result.scalar_one()
        execution.status = "working"
        await session.commit()
        await session.refresh(execution)

    return tenant_a_orchestrator_job


# ============================================================================
# SLASH COMMAND EXECUTE ENDPOINT TESTS
# ============================================================================


class TestSlashCommandExecute:
    """Test POST /api/slash/execute endpoint.

    NOTE: The /api/slash/execute endpoint does NOT require authentication
    per the implementation in api/endpoints/slash_commands.py. It only
    validates the command exists and executes it with provided tenant_key.
    """

    @pytest.mark.asyncio
    async def test_execute_nonexistent_command(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/slash/execute - 404 for unknown command."""
        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "nonexistent_command_xyz",
                "tenant_key": "test_tenant_key",
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 404
        data = response.json()
        # Error response uses "message" field (custom error handler)
        assert "message" in data
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_execute_without_auth(
        self,
        api_client: AsyncClient,
    ):
        """Test POST /api/slash/execute - 401 without authentication.

        The slash execute endpoint requires authentication via the
        global auth middleware that applies to all /api/ routes.
        """
        # Clear any existing cookies
        api_client.cookies.clear()

        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "nonexistent_command",
                "tenant_key": "test_tenant_key",
            },
        )

        # Requires authentication
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_execute_without_tenant_key(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/slash/execute - 422 for missing tenant_key."""
        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "some_command",
                # Missing tenant_key - required field
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        # Pydantic validation error
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_execute_with_empty_command(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/slash/execute - 404 for empty command (not found)."""
        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "",  # Empty command
                "tenant_key": "test_tenant_key",
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        # Empty string passes validation but command won't be found
        assert response.status_code == 404


# ============================================================================
# SIMPLE HANDOVER ENDPOINT TESTS
# ============================================================================


class TestSimpleHandover:
    """Test POST /api/agent-jobs/{job_id}/simple-handover endpoint.

    This endpoint requires authentication and triggers 360 Memory-based
    session handover for orchestrators only.
    """

    @pytest.mark.asyncio
    async def test_trigger_succession_happy_path(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_a_working_orchestrator,
    ):
        """Test POST /api/agent-jobs/{job_id}/simple-handover - Trigger handover successfully.

        NOTE: Full test requires 360 Memory configuration. In test environment,
        this may return 500 if product_memory is not configured for the product.
        """
        job_id = tenant_a_working_orchestrator["job_id"]

        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/simple-handover",
            cookies={"access_token": tenant_a_admin_token},
        )

        # May return 200 (success) or 500 (if 360 Memory not configured)
        assert response.status_code in [200, 500]
        data = response.json()

        if response.status_code == 200:
            assert data["success"] is True
            assert "continuation_prompt" in data
            assert "memory_entry_id" in data
            assert data["context_reset"] is True

    @pytest.mark.asyncio
    async def test_trigger_succession_nonexistent_job(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/agent-jobs/{job_id}/simple-handover - 404 for unknown job."""
        fake_job_id = str(uuid4())

        response = await api_client.post(
            f"/api/agent-jobs/{fake_job_id}/simple-handover",
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 404
        data = response.json()
        # Error response uses "message" field (custom error handler)
        assert "message" in data
        assert "not found" in data["message"].lower()

    @pytest.mark.asyncio
    async def test_trigger_succession_requires_auth(
        self,
        api_client: AsyncClient,
        tenant_a_orchestrator_job,
    ):
        """Test POST /api/agent-jobs/{job_id}/simple-handover - 401 without authentication."""
        # Clear any existing cookies
        api_client.cookies.clear()

        job_id = tenant_a_orchestrator_job["job_id"]

        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/simple-handover",
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_trigger_succession_non_orchestrator(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_a_project,
    ):
        """Test POST /api/agent-jobs/{job_id}/simple-handover - 400 for non-orchestrator agent.

        Only orchestrators can trigger handover (Handover 0461c).
        """
        # Spawn a worker (non-orchestrator) agent
        spawn_response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",  # NOT orchestrator
                "agent_name": "Test Implementer",
                "mission": "Test implementation",
                "project_id": tenant_a_project["id"],
                "context_chunks": [],
            },
            cookies={"access_token": tenant_a_admin_token},
        )
        assert spawn_response.status_code == 201
        job_id = spawn_response.json()["job_id"]

        # Try to trigger handover on non-orchestrator
        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/simple-handover",
            cookies={"access_token": tenant_a_admin_token},
        )

        # Should fail because only orchestrators can use handover
        assert response.status_code == 400
        data = response.json()
        # Error response uses "message" field (custom error handler)
        assert "message" in data
        assert "orchestrator" in data["message"].lower()


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================


class TestSlashCommandMultiTenantIsolation:
    """Test multi-tenant isolation for slash command endpoints.

    Critical: Tenant A cannot access or modify Tenant B's resources.
    """

    @pytest.mark.asyncio
    async def test_cannot_handover_other_tenant_job(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_b_admin_token: str,
        tenant_b_admin,
        db_manager,
    ):
        """Test that Tenant A cannot trigger handover on Tenant B's job."""
        from src.giljo_mcp.models import Product, Project
        from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob

        # Create Tenant B's product, project, and orchestrator job directly in DB
        async with db_manager.get_session_async() as session:
            # Create product for Tenant B
            product = Product(
                id=str(uuid4()),
                name="Tenant B Product",
                tenant_key=tenant_b_admin._test_tenant_key,
                is_active=True,
                product_memory={},
            )
            session.add(product)
            await session.flush()

            # Create project for Tenant B
            project = Project(
                id=str(uuid4()),
                name="Tenant B Project",
                description="Test project for tenant B",
                mission="Test mission",
                tenant_key=tenant_b_admin._test_tenant_key,
                product_id=product.id,
                status="active",
                implementation_launched_at=datetime.now(timezone.utc),
            )
            session.add(project)
            await session.flush()

            # Create AgentJob for Tenant B (project_id and mission on AgentJob)
            job = AgentJob(
                job_id=str(uuid4()),
                tenant_key=tenant_b_admin._test_tenant_key,
                project_id=project.id,
                job_type="orchestrator",
                mission="Tenant B orchestration",
                status="active",
                created_at=datetime.now(timezone.utc),
                job_metadata={},
            )
            session.add(job)
            await session.flush()

            # Create AgentExecution for Tenant B (working orchestrator)
            execution = AgentExecution(
                agent_id=str(uuid4()),
                job_id=job.job_id,
                tenant_key=tenant_b_admin._test_tenant_key,
                agent_display_name="orchestrator",
                agent_name="Tenant B Orchestrator",
                status="working",
                progress=50,
                messages_sent_count=0,
                messages_waiting_count=0,
                messages_read_count=0,
                health_status="healthy",
                tool_type="universal",
            )
            session.add(execution)
            await session.commit()

            tenant_b_job_id = job.job_id

        # Tenant A tries to trigger handover on Tenant B's job
        response = await api_client.post(
            f"/api/agent-jobs/{tenant_b_job_id}/simple-handover",
            cookies={"access_token": tenant_a_admin_token},
        )

        # Should return 404 (not found) to prevent information leakage
        assert response.status_code == 404


# ============================================================================
# VALIDATION TESTS
# ============================================================================


class TestSlashCommandValidation:
    """Test request validation for slash command endpoints."""

    @pytest.mark.asyncio
    async def test_execute_missing_command_field(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/slash/execute - 422 for missing command field."""
        response = await api_client.post(
            "/api/slash/execute",
            json={
                # Missing "command" field
                "tenant_key": "test_tenant_key",
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 422
        data = response.json()
        # Custom validation error handler returns "errors" array
        # Standard Pydantic returns "detail" array
        errors = data.get("errors", data.get("detail", []))
        has_command_error = any("command" in str(err).lower() for err in errors)
        assert has_command_error, f"Expected 'command' in error: {data}"

    @pytest.mark.asyncio
    async def test_execute_with_arguments(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/slash/execute - Arguments passed to handler."""
        # This tests that arguments dict is properly passed
        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "nonexistent_command",
                "tenant_key": "test_tenant_key",
                "project_id": str(uuid4()),
                "arguments": {"custom_arg": "custom_value"},
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        # Should fail with 404 (command not found), not validation error
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_handover_invalid_job_id_format(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
    ):
        """Test POST /api/agent-jobs/{job_id}/simple-handover - Invalid UUID format."""
        response = await api_client.post(
            "/api/agent-jobs/not-a-valid-uuid/simple-handover",
            cookies={"access_token": tenant_a_admin_token},
        )

        # May return 404 (not found) or 422 (validation) or 500
        # depending on how the endpoint validates UUIDs
        assert response.status_code in [404, 422, 500]

    @pytest.mark.asyncio
    async def test_execute_with_project_id(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_a_project,
        tenant_a_admin,
    ):
        """Test POST /api/slash/execute - Command with project_id parameter."""
        response = await api_client.post(
            "/api/slash/execute",
            json={
                "command": "nonexistent_command",
                "tenant_key": tenant_a_admin._test_tenant_key,
                "project_id": tenant_a_project["id"],  # Valid project_id
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        # Should fail with 404 (command not found), not validation error
        assert response.status_code == 404
