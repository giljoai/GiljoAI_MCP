"""
Integration tests for thin client prompt endpoints (Handover 0088).

Tests the complete thin prompt generation workflow.
Coverage targets: 90%+ endpoint coverage
"""

from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import MCPAgentJob, Project, User


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create test user."""
    user = User(
        id=str(uuid4()),
        username="testuser",
        email="test@example.com",
        tenant_key="test_tenant",
        is_active=True,
        password_hash="$2b$12$test_hash",
        field_priority_config={"product_vision": 10, "architecture": 7},
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def test_project_thin(db_session: AsyncSession, test_user: User) -> Project:
    """Create test project."""
    project = Project(
        id=str(uuid4()),
        name="Test Project",
        description="Test project",
        tenant_key=test_user.tenant_key,
        status="active",
        context_budget=150000,
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest_asyncio.fixture
async def authenticated_client(api_client, test_user):
    """Client with mocked authentication."""
    from api.app import app
    from src.giljo_mcp.auth.dependencies import get_current_active_user

    async def mock_get_current_user():
        return test_user

    app.dependency_overrides[get_current_active_user] = mock_get_current_user
    yield api_client

    if get_current_active_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_active_user]


@pytest.mark.asyncio
class TestThinPromptEndpoint:
    """Integration tests for POST /api/prompts/orchestrator."""

    async def test_generate_thin_prompt_success(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, test_user: User, test_project_thin: Project
    ):
        """Test successful thin prompt generation."""
        # Make request
        response = await authenticated_client.post(
            "/api/prompts/orchestrator",
            json={"project_id": str(test_project_thin.id), "tool": "claude-code", "instance_number": 1},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert "prompt" in data
        assert "orchestrator_id" in data
        assert data["thin_client"] is True
        assert data["estimated_prompt_tokens"] < 100

        # Verify orchestrator job created
        result = await db_session.get(MCPAgentJob, data["orchestrator_id"])
        assert result is not None
        assert result.agent_type == "orchestrator"
        assert result.status == "pending"
        assert result.mission is not None

    async def test_endpoint_requires_authentication(self, api_client: AsyncClient, test_project_thin: Project):
        """Test authentication required."""
        response = await api_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(test_project_thin.id), "tool": "claude-code"}
        )
        assert response.status_code == 401

    async def test_multi_tenant_isolation(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test multi-tenant isolation."""
        # Create project for different tenant
        other_project = Project(id=str(uuid4()), name="Other Project", tenant_key="other_tenant", status="active")
        db_session.add(other_project)
        await db_session.commit()

        # Try to access it
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(other_project.id), "tool": "claude-code"}
        )
        assert response.status_code == 404

    async def test_user_field_priorities_applied(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, test_user: User, test_project_thin: Project
    ):
        """Test user field priorities applied."""
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(test_project_thin.id), "tool": "codex"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify orchestrator has field priorities
        orchestrator = await db_session.get(MCPAgentJob, data["orchestrator_id"])
        assert orchestrator.metadata["user_id"] == str(test_user.id)
        assert "field_priorities" in orchestrator.metadata

    @patch("api.endpoints.prompts.get_websocket_dependency")
    async def test_websocket_broadcast(
        self, mock_ws_dep, authenticated_client: AsyncClient, test_project_thin: Project
    ):
        """Test WebSocket event broadcast."""
        # Mock WebSocket
        mock_ws = AsyncMock()
        mock_ws.is_available.return_value = True
        mock_ws.broadcast_to_tenant = AsyncMock()
        mock_ws_dep.return_value = mock_ws

        # Generate prompt
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(test_project_thin.id), "tool": "gemini"}
        )

        assert response.status_code == 200
        mock_ws.broadcast_to_tenant.assert_called_once()

    async def test_invalid_project_error(self, authenticated_client: AsyncClient):
        """Test invalid project ID error."""
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(uuid4()), "tool": "claude-code"}
        )
        assert response.status_code == 404

    async def test_invalid_tool_validation(self, authenticated_client: AsyncClient, test_project_thin: Project):
        """Test invalid tool validation."""
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(test_project_thin.id), "tool": "invalid-tool"}
        )
        assert response.status_code == 422

    async def test_prompt_structure(self, authenticated_client: AsyncClient, test_project_thin: Project):
        """Test thin prompt structure."""
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(test_project_thin.id), "tool": "claude-code"}
        )

        assert response.status_code == 200
        data = response.json()

        prompt = data["prompt"]
        assert "Orchestrator" in prompt
        assert data["orchestrator_id"] in prompt
        assert "get_orchestrator_instructions" in prompt
        assert len(prompt) < 2000  # Thin, not fat

    async def test_backward_compatible_response(self, authenticated_client: AsyncClient, test_project_thin: Project):
        """Test response structure backward compatibility."""
        response = await authenticated_client.post(
            "/api/prompts/orchestrator", json={"project_id": str(test_project_thin.id), "tool": "claude-code"}
        )

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        required = [
            "prompt",
            "orchestrator_id",
            "project_id",
            "project_name",
            "estimated_prompt_tokens",
            "mcp_tool_name",
            "instructions_stored",
            "thin_client",
        ]
        for field in required:
            assert field in data

    async def test_orchestrator_job_metadata(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, test_user: User, test_project_thin: Project
    ):
        """Test orchestrator job metadata stored correctly."""
        response = await authenticated_client.post(
            "/api/prompts/orchestrator",
            json={"project_id": str(test_project_thin.id), "tool": "claude-code", "instance_number": 3},
        )

        assert response.status_code == 200
        data = response.json()

        # Verify metadata
        orchestrator = await db_session.get(MCPAgentJob, data["orchestrator_id"])
        assert orchestrator.metadata["tool"] == "claude-code"
        assert orchestrator.metadata["created_via"] == "thin_client_generator"
        assert orchestrator.instance_number == 3


@pytest.mark.asyncio
class TestStagingEndpointThinClient:
    """Tests for GET /api/prompts/staging/{project_id}."""

    async def test_staging_returns_thin_prompt(self, authenticated_client: AsyncClient, test_project_thin: Project):
        """Test staging endpoint returns thin prompt."""
        response = await authenticated_client.get(
            f"/api/prompts/staging/{test_project_thin.id}?tool=claude-code&instance_number=1"
        )

        assert response.status_code == 200
        data = response.json()

        assert data["thin_client"] is True
        assert data["estimated_prompt_tokens"] < 100
        assert len(data["prompt"]) < 2000

    async def test_staging_creates_orchestrator(
        self, authenticated_client: AsyncClient, db_session: AsyncSession, test_project_thin: Project
    ):
        """Test staging creates orchestrator job."""
        response = await authenticated_client.get(f"/api/prompts/staging/{test_project_thin.id}?tool=codex")

        assert response.status_code == 200
        data = response.json()

        # Verify job exists
        orchestrator = await db_session.get(MCPAgentJob, data["orchestrator_id"])
        assert orchestrator is not None
        assert orchestrator.mission is not None

    async def test_staging_multi_tenant_isolation(self, authenticated_client: AsyncClient, db_session: AsyncSession):
        """Test staging enforces multi-tenant isolation."""
        # Create other tenant project
        other_project = Project(id=str(uuid4()), name="Other Project", tenant_key="other_tenant", status="active")
        db_session.add(other_project)
        await db_session.commit()

        response = await authenticated_client.get(f"/api/prompts/staging/{other_project.id}")
        assert response.status_code == 404
