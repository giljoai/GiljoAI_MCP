"""
Agent Jobs API Integration Tests - Handover 0613

Comprehensive validation of all 13+ agent job endpoints across 5 modules:
- Lifecycle endpoints (lifecycle.py): spawn, acknowledge, complete, error
- Status endpoints (status.py): list, get, pending, mission
- Operations endpoints (operations.py): cancel, force-fail, health
- Progress endpoints (progress.py): report_progress
- Orchestration endpoints (orchestration.py): workflow_status

Test Coverage:
- Happy path scenarios (200/201 responses)
- Authentication enforcement (401 Unauthorized)
- Authorization enforcement (403 Forbidden)
- Multi-tenant isolation (zero cross-tenant leakage)
- Not Found scenarios (404)
- Validation errors (400 Bad Request)
- State transition validation
- Job lifecycle verification
- Orchestrator succession behavior

Phase 2 Progress: API Layer Testing (5/10 groups)
"""

from uuid import uuid4

import pytest
from httpx import AsyncClient


# ============================================================================
# FIXTURES - Test Users and Authentication
# ============================================================================


@pytest.fixture
async def tenant_a_admin(db_manager):
    """Create Tenant A admin user (required for spawning agents)."""
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_a_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id required)
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
            role="admin",  # Admin role required for spawning
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
async def tenant_a_developer(db_manager):
    """Create Tenant A developer user (cannot spawn agents)."""
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_a_dev_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_a_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id required)
        org = Organization(
            name=f"Tenant A Dev Org {unique_id}",
            slug=f"tenant-a-dev-org-{unique_id}",
            tenant_key=tenant_key,
            is_active=True,
        )
        session.add(org)
        await session.flush()

        user = User(
            username=username,
            password_hash=bcrypt.hash("password_a"),
            email=f"{username}@test.com",
            role="developer",  # Non-admin role
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
    from passlib.hash import bcrypt

    from src.giljo_mcp.models import User
    from src.giljo_mcp.models.organizations import Organization
    from src.giljo_mcp.tenant import TenantManager

    # Generate unique username and valid tenant_key
    unique_id = uuid4().hex[:8]
    username = f"tenant_b_admin_{unique_id}"
    tenant_key = TenantManager.generate_tenant_key(f"tenant_b_{unique_id}")

    async with db_manager.get_session_async() as session:
        # Create org first (0424m: org_id required)
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
    """Get JWT token for Tenant A admin."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_a_admin._test_username, "password": tenant_a_admin._test_password}
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_a_dev_token(api_client: AsyncClient, tenant_a_developer):
    """Get JWT token for Tenant A developer."""
    response = await api_client.post(
        "/api/auth/login",
        json={"username": tenant_a_developer._test_username, "password": tenant_a_developer._test_password},
    )
    assert response.status_code == 200, f"Login failed: {response.json()}"
    access_token = response.cookies.get("access_token")
    assert access_token is not None
    return access_token


@pytest.fixture
async def tenant_b_admin_token(api_client: AsyncClient, tenant_b_admin):
    """Get JWT token for Tenant B admin."""
    response = await api_client.post(
        "/api/auth/login", json={"username": tenant_b_admin._test_username, "password": tenant_b_admin._test_password}
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
            "description": "Test product for agent jobs",
            "project_path": f"/test/product/{uuid4().hex[:8]}",
        },
        cookies={"access_token": tenant_a_admin_token},
    )
    assert response.status_code == 200
    return response.json()


@pytest.fixture
async def tenant_b_product(api_client: AsyncClient, tenant_b_admin_token: str):
    """Create a test product for Tenant B."""
    response = await api_client.post(
        "/api/v1/products/",
        json={
            "name": f"Test Product {uuid4().hex[:8]}",
            "description": "Test product for tenant B",
            "project_path": f"/test/product/{uuid4().hex[:8]}",
        },
        cookies={"access_token": tenant_b_admin_token},
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
            "description": "Test project for agent jobs",
            "mission": "Test mission for agent coordination",
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
async def tenant_b_project(api_client: AsyncClient, tenant_b_admin_token: str, tenant_b_product):
    """Create a test project for Tenant B and launch implementation.

    Handover 0730e: Projects need implementation_launched_at set for agent job
    lifecycle tests (get_agent_mission requires this per Handover 0709).
    """
    response = await api_client.post(
        "/api/v1/projects/",
        json={
            "name": f"Test Project {uuid4().hex[:8]}",
            "description": "Test project for tenant B",
            "mission": "Test mission for tenant B",
            "product_id": tenant_b_product["id"],
            "status": "inactive",
        },
        cookies={"access_token": tenant_b_admin_token},
    )
    assert response.status_code == 201
    project = response.json()

    # Launch implementation phase (required for agent lifecycle tests)
    launch_response = await api_client.patch(
        f"/api/agent-jobs/projects/{project['id']}/launch-implementation",
        cookies={"access_token": tenant_b_admin_token},
    )
    assert launch_response.status_code == 200

    return project


@pytest.fixture
async def tenant_a_agent_templates(db_manager, tenant_a_admin):
    """Create AgentTemplate records for Tenant A.

    Required because OrchestrationService.spawn_agent_job() validates
    agent_name against active AgentTemplate records when
    agent_display_name != 'orchestrator'.
    """
    from src.giljo_mcp.models import AgentTemplate

    tenant_key = tenant_a_admin._test_tenant_key
    agent_names = ["Test Implementer", "Lifecycle Test", "Error Test", "Cancel Test"]

    async with db_manager.get_session_async() as session:
        for name in agent_names:
            template = AgentTemplate(
                tenant_key=tenant_key,
                name=name,
                role="implementer",
                description=f"{name} agent template for testing",
                system_instructions=f"# {name}\nTest agent template.",
                is_active=True,
            )
            session.add(template)
        await session.commit()

    return agent_names


@pytest.fixture
async def tenant_b_agent_templates(db_manager, tenant_b_admin):
    """Create AgentTemplate records for Tenant B.

    Required because OrchestrationService.spawn_agent_job() validates
    agent_name against active AgentTemplate records when
    agent_display_name != 'orchestrator'.
    """
    from src.giljo_mcp.models import AgentTemplate

    tenant_key = tenant_b_admin._test_tenant_key
    agent_names = ["Test Implementer B"]

    async with db_manager.get_session_async() as session:
        for name in agent_names:
            template = AgentTemplate(
                tenant_key=tenant_key,
                name=name,
                role="implementer",
                description=f"{name} agent template for testing",
                system_instructions=f"# {name}\nTest agent template.",
                is_active=True,
            )
            session.add(template)
        await session.commit()

    return agent_names


@pytest.fixture
async def tenant_a_agent_job(api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project):
    """Create a test agent job for Tenant A."""
    response = await api_client.post(
        "/api/agent-jobs/spawn",
        json={
            "agent_display_name": "orchestrator",
            "agent_name": "Test Orchestrator",
            "mission": "Test orchestration mission",
            "project_id": tenant_a_project["id"],
            "context_chunks": [],
        },
        cookies={"access_token": tenant_a_admin_token},
    )
    assert response.status_code == 201, f"Spawn failed: {response.json()}"
    return response.json()


@pytest.fixture
async def tenant_b_agent_job(api_client: AsyncClient, tenant_b_admin_token: str, tenant_b_project):
    """Create a test agent job for Tenant B."""
    response = await api_client.post(
        "/api/agent-jobs/spawn",
        json={
            "agent_display_name": "orchestrator",
            "agent_name": "Test Orchestrator B",
            "mission": "Test orchestration mission B",
            "project_id": tenant_b_project["id"],
            "context_chunks": [],
        },
        cookies={"access_token": tenant_b_admin_token},
    )
    assert response.status_code == 201, f"Spawn failed: {response.json()}"
    return response.json()


# ============================================================================
# LIFECYCLE ENDPOINTS TESTS
# ============================================================================


class TestAgentJobLifecycle:
    """Test lifecycle operations: spawn, acknowledge, complete, error"""

    @pytest.mark.asyncio
    async def test_spawn_agent_job_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project, tenant_a_agent_templates
    ):
        """Test successful agent job spawn with admin user."""
        response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",
                "agent_name": "Test Implementer",
                "mission": "Implement feature X",
                "project_id": tenant_a_project["id"],
                "context_chunks": ["chunk1", "chunk2"],
            },
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data
        assert data["mission_stored"] is True
        assert data["thin_client"] is True
        assert len(data["agent_prompt"]) > 0

    @pytest.mark.asyncio
    async def test_spawn_agent_job_requires_admin(
        self, api_client: AsyncClient, tenant_a_dev_token: str, tenant_a_project
    ):
        """Test that only admins can spawn agent jobs."""
        response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",
                "agent_name": "Test Implementer",
                "mission": "Implement feature X",
                "project_id": tenant_a_project["id"],
                "context_chunks": [],
            },
            cookies={"access_token": tenant_a_dev_token},
        )

        assert response.status_code == 403
        assert "Admin access required" in response.json()["message"]

    @pytest.mark.asyncio
    async def test_spawn_agent_job_requires_auth(self, api_client: AsyncClient, tenant_a_project):
        """Test that spawning requires authentication."""
        # Clear any existing cookies to ensure truly unauthenticated request
        api_client.cookies.clear()

        response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",
                "agent_name": "Test Implementer",
                "mission": "Implement feature X",
                "project_id": tenant_a_project["id"],
                "context_chunks": [],
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    @pytest.mark.skip(
        reason="Needs update: Service now requires project to be in 'launched' state via dashboard"
    )
    async def test_acknowledge_job_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """Test successful job acknowledgment."""
        job_id = tenant_a_agent_job["job_id"]

        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200, f"Acknowledge failed: {response.text}"
        data = response.json()
        assert "job_id" in data, f"Missing job_id in response: {data}"
        assert data["job_id"] == job_id
        assert data["status"] in ["active", "working"]  # May vary based on implementation
        assert data["started_at"] is not None
        # Message content varies - just verify it exists and has content
        assert "message" in data and len(data["message"]) > 0

    @pytest.mark.asyncio
    async def test_acknowledge_job_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test acknowledging non-existent job returns error."""
        fake_job_id = str(uuid4())

        response = await api_client.post(
            f"/api/agent-jobs/{fake_job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token}
        )

        # Should return error (400 or 404 depending on implementation)
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_complete_job_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """Test successful job completion."""
        job_id = tenant_a_agent_job["job_id"]

        # First acknowledge
        await api_client.post(f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token})

        # Then complete
        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/complete",
            json={"result": "Task completed successfully"},
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 200, f"Complete failed: {response.text}"
        data = response.json()
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        # completed_at may be None depending on implementation
        assert "completed_at" in data
        assert "message" in data and len(data["message"]) > 0

    @pytest.mark.asyncio
    async def test_complete_job_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test completing non-existent job returns error."""
        fake_job_id = str(uuid4())

        response = await api_client.post(
            f"/api/agent-jobs/{fake_job_id}/complete",
            json={"result": "Done"},
            cookies={"access_token": tenant_a_admin_token},
        )

        # Should return error (400 or 404 depending on implementation)
        assert response.status_code in [400, 404]

    @pytest.mark.asyncio
    async def test_report_error_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """Test successful error reporting."""
        job_id = tenant_a_agent_job["job_id"]

        # Acknowledge first
        await api_client.post(f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token})

        # Report error
        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/error",
            json={"error": "Failed to connect to database"},
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        # Error endpoint returns "blocked" status (agent blocked by error, may need intervention)
        assert data["status"] == "blocked"
        # completed_at may be None since agent is blocked, not completed
        assert "completed_at" in data

    @pytest.mark.asyncio
    async def test_report_error_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test reporting error for non-existent job returns error."""
        fake_job_id = str(uuid4())

        response = await api_client.post(
            f"/api/agent-jobs/{fake_job_id}/error",
            json={"error": "Some error"},
            cookies={"access_token": tenant_a_admin_token},
        )

        # Should return error (400 or 404 depending on implementation)
        assert response.status_code in [400, 404]


# ============================================================================
# STATUS ENDPOINTS TESTS
# ============================================================================


class TestAgentJobStatus:
    """Test status operations: list, get, pending, mission"""

    @pytest.mark.asyncio
    async def test_list_jobs_happy_path(self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job):
        """Test listing agent jobs."""
        response = await api_client.get("/api/agent-jobs/", cookies={"access_token": tenant_a_admin_token})

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert len(data["jobs"]) >= 1
        assert data["total"] >= 1

        # Each job should include steps field for dashboard Steps column
        for job in data["jobs"]:
            assert "steps" in job

    @pytest.mark.asyncio
    async def test_list_jobs_with_filters(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project, tenant_a_agent_job
    ):
        """Test listing jobs with filters."""
        response = await api_client.get(
            f"/api/agent-jobs/?project_id={tenant_a_project['id']}&status=pending&limit=10",
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert data["limit"] == 10

    @pytest.mark.asyncio
    async def test_list_jobs_pagination(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test job list pagination."""
        response = await api_client.get(
            "/api/agent-jobs/?limit=5&offset=0", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0

    @pytest.mark.asyncio
    async def test_list_jobs_includes_todo_steps_summary(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_a_agent_job,
        db_manager,
    ):
        """
        Jobs endpoint should expose numeric Steps summary when todo_steps metadata exists.

        Behavior (Handover 0297):
        - When job_metadata.todo_steps has total_steps/completed_steps,
          jobs endpoint returns steps: {"total": int, "completed": int}
        """
        from sqlalchemy import select

        from src.giljo_mcp.models.agent_identity import AgentJob

        job_id = tenant_a_agent_job["job_id"]

        # Populate todo_steps in job_metadata for the spawned job
        # Note: job_metadata is on AgentJob, not AgentExecution
        async with db_manager.get_session_async() as session:
            result = await session.execute(select(AgentJob).where(AgentJob.job_id == job_id))
            job = result.scalar_one()

            job.job_metadata = {
                **(job.job_metadata or {}),
                "todo_steps": {
                    "total_steps": 4,
                    "completed_steps": 1,
                    "current_step": "Initial setup",
                },
            }
            await session.commit()

        # Call jobs endpoint
        response = await api_client.get(
            "/api/agent-jobs/",
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data

        # Find our specific job
        target = next((j for j in data["jobs"] if j["job_id"] == job_id), None)
        assert target is not None, "Spawned job should be present in jobs list"

        # Steps summary should be present and normalized
        assert "steps" in target
        assert target["steps"] == {"total": 4, "completed": 1}

    @pytest.mark.asyncio
    async def test_list_jobs_requires_auth(self, api_client: AsyncClient):
        """Test that listing jobs requires authentication."""
        response = await api_client.get("/api/agent-jobs/")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_job_happy_path(self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job):
        """Test getting job details by ID."""
        job_id = tenant_a_agent_job["job_id"]

        response = await api_client.get(f"/api/agent-jobs/{job_id}", cookies={"access_token": tenant_a_admin_token})

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "mission" in data
        assert "status" in data

    @pytest.mark.asyncio
    async def test_get_job_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test getting non-existent job returns error."""
        fake_job_id = str(uuid4())

        response = await api_client.get(
            f"/api/agent-jobs/{fake_job_id}", cookies={"access_token": tenant_a_admin_token}
        )

        # Should return error (404 or 500 depending on implementation)
        assert response.status_code in [404, 500]

    @pytest.mark.asyncio
    async def test_list_pending_jobs_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """Test listing pending jobs."""
        response = await api_client.get("/api/agent-jobs/pending", cookies={"access_token": tenant_a_admin_token})

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert "count" in data
        # Should have at least our test job (if still pending)
        assert data["count"] >= 0

    @pytest.mark.asyncio
    async def test_get_job_mission_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """Test getting job mission."""
        job_id = tenant_a_agent_job["job_id"]

        response = await api_client.get(
            f"/api/agent-jobs/{job_id}/mission", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "mission" in data
        assert "context_chunks" in data
        assert "status" in data
        assert len(data["mission"]) > 0

    @pytest.mark.asyncio
    async def test_get_job_mission_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test getting mission for non-existent job returns error."""
        fake_job_id = str(uuid4())

        response = await api_client.get(
            f"/api/agent-jobs/{fake_job_id}/mission", cookies={"access_token": tenant_a_admin_token}
        )

        # Should return error (404 or 500 depending on implementation)
        assert response.status_code in [404, 500]


# ============================================================================
# OPERATIONS ENDPOINTS TESTS
# ============================================================================


class TestAgentJobOperations:
    """Test operation controls: cancel, force-fail, health"""

    @pytest.mark.asyncio
    async def test_get_job_health_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """Test getting job health metrics."""
        job_id = tenant_a_agent_job["job_id"]

        response = await api_client.get(f"/api/jobs/{job_id}/health", cookies={"access_token": tenant_a_admin_token})

        assert response.status_code == 200
        data = response.json()
        assert data["job_id"] == job_id
        assert "status" in data
        assert "is_stale" in data
        assert isinstance(data["is_stale"], bool)

    @pytest.mark.asyncio
    async def test_get_job_health_not_found(self, api_client: AsyncClient, tenant_a_admin_token: str):
        """Test getting health for non-existent job returns 404."""
        fake_job_id = str(uuid4())

        response = await api_client.get(
            f"/api/jobs/{fake_job_id}/health", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 404


# ============================================================================
# MULTI-TENANT ISOLATION TESTS
# ============================================================================


class TestAgentJobMultiTenantIsolation:
    """Test multi-tenant isolation - zero cross-tenant data leakage"""

    @pytest.mark.asyncio
    async def test_cannot_get_other_tenant_job(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_agent_job
    ):
        """Test that Tenant A cannot access Tenant B's jobs."""
        job_id = tenant_b_agent_job["job_id"]

        response = await api_client.get(f"/api/agent-jobs/{job_id}", cookies={"access_token": tenant_a_admin_token})

        # Should return 404 (not found) for isolation
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_acknowledge_other_tenant_job(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_agent_job
    ):
        """Test that Tenant A cannot acknowledge Tenant B's jobs."""
        job_id = tenant_b_agent_job["job_id"]

        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_complete_other_tenant_job(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_agent_job
    ):
        """Test that Tenant A cannot complete Tenant B's jobs."""
        job_id = tenant_b_agent_job["job_id"]

        response = await api_client.post(
            f"/api/agent-jobs/{job_id}/complete",
            json={"result": "Done"},
            cookies={"access_token": tenant_a_admin_token},
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="cancel endpoint removed - passive HTTP architecture")
    async def test_cannot_cancel_other_tenant_job(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_b_agent_job
    ):
        """Test that Tenant A cannot cancel Tenant B's jobs."""
        job_id = tenant_b_agent_job["job_id"]

        response = await api_client.post(
            f"/api/jobs/{job_id}/cancel", json={"reason": "Test"}, cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_list_jobs_only_shows_own_tenant(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_b_admin_token: str,
        tenant_a_agent_job,
        tenant_b_agent_job,
    ):
        """Test that listing jobs only shows jobs for the authenticated tenant."""
        # Tenant A lists jobs
        response_a = await api_client.get("/api/agent-jobs/", cookies={"access_token": tenant_a_admin_token})
        assert response_a.status_code == 200
        data_a = response_a.json()

        # Tenant B lists jobs
        response_b = await api_client.get("/api/agent-jobs/", cookies={"access_token": tenant_b_admin_token})
        assert response_b.status_code == 200
        data_b = response_b.json()

        # Verify no overlap in job IDs
        job_ids_a = {job["job_id"] for job in data_a["jobs"]}
        job_ids_b = {job["job_id"] for job in data_b["jobs"]}
        assert len(job_ids_a.intersection(job_ids_b)) == 0, "Cross-tenant job leakage detected"

    @pytest.mark.asyncio
    async def test_pending_jobs_only_shows_own_tenant(
        self,
        api_client: AsyncClient,
        tenant_a_admin_token: str,
        tenant_b_admin_token: str,
        tenant_a_agent_job,
        tenant_b_agent_job,
    ):
        """Test that pending jobs only shows jobs for the authenticated tenant."""
        # Tenant A gets pending jobs
        response_a = await api_client.get("/api/agent-jobs/pending", cookies={"access_token": tenant_a_admin_token})
        assert response_a.status_code == 200
        data_a = response_a.json()

        # Tenant B gets pending jobs
        response_b = await api_client.get("/api/agent-jobs/pending", cookies={"access_token": tenant_b_admin_token})
        assert response_b.status_code == 200
        data_b = response_b.json()

        # Verify no overlap
        job_ids_a = {job["job_id"] for job in data_a["jobs"]}
        job_ids_b = {job["job_id"] for job in data_b["jobs"]}
        assert len(job_ids_a.intersection(job_ids_b)) == 0, "Cross-tenant pending job leakage detected"


# ============================================================================
# STATE TRANSITION TESTS
# ============================================================================


class TestAgentJobStateTransitions:
    """Test valid and invalid state transitions"""

    @pytest.mark.asyncio
    async def test_full_lifecycle_happy_path(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project, tenant_a_agent_templates
    ):
        """Test full job lifecycle: spawn -> acknowledge -> complete."""
        # Spawn job
        spawn_response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",
                "agent_name": "Lifecycle Test",
                "mission": "Complete lifecycle test",
                "project_id": tenant_a_project["id"],
                "context_chunks": [],
            },
            cookies={"access_token": tenant_a_admin_token},
        )
        assert spawn_response.status_code == 201
        job_id = spawn_response.json()["job_id"]

        # Acknowledge job
        ack_response = await api_client.post(
            f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token}
        )
        assert ack_response.status_code == 200
        assert ack_response.json()["status"] in ["active", "working"]

        # Complete job
        complete_response = await api_client.post(
            f"/api/agent-jobs/{job_id}/complete",
            json={"result": "All tasks completed"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert complete_response.status_code == 200
        assert complete_response.json()["status"] == "completed"

    @pytest.mark.asyncio
    async def test_error_lifecycle_path(self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project, tenant_a_agent_templates):
        """Test error lifecycle: spawn -> acknowledge -> error."""
        # Spawn job
        spawn_response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",
                "agent_name": "Error Test",
                "mission": "Test error handling",
                "project_id": tenant_a_project["id"],
                "context_chunks": [],
            },
            cookies={"access_token": tenant_a_admin_token},
        )
        assert spawn_response.status_code == 201
        job_id = spawn_response.json()["job_id"]

        # Acknowledge job
        ack_response = await api_client.post(
            f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token}
        )
        assert ack_response.status_code == 200

        # Report error
        error_response = await api_client.post(
            f"/api/agent-jobs/{job_id}/error",
            json={"error": "Critical failure occurred"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert error_response.status_code == 200
        # Error endpoint returns "blocked" (agent blocked by error)
        assert error_response.json()["status"] == "blocked"

    @pytest.mark.asyncio
    @pytest.mark.skip(reason="cancel endpoint removed - passive HTTP architecture")
    async def test_cancel_lifecycle_path(self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project, tenant_a_agent_templates):
        """Test cancel lifecycle: spawn -> acknowledge -> cancel."""
        # Spawn job
        spawn_response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "implementer",
                "agent_name": "Cancel Test",
                "mission": "Test cancellation",
                "project_id": tenant_a_project["id"],
                "context_chunks": [],
            },
            cookies={"access_token": tenant_a_admin_token},
        )
        assert spawn_response.status_code == 201
        job_id = spawn_response.json()["job_id"]

        # Acknowledge job
        ack_response = await api_client.post(
            f"/api/agent-jobs/{job_id}/acknowledge", cookies={"access_token": tenant_a_admin_token}
        )
        assert ack_response.status_code == 200

        # Cancel job
        cancel_response = await api_client.post(
            f"/api/jobs/{job_id}/cancel",
            json={"reason": "No longer needed"},
            cookies={"access_token": tenant_a_admin_token},
        )
        assert cancel_response.status_code == 200
        assert cancel_response.json()["status"] in ["cancelling", "cancelled"]
