"""
Integration tests for messages API endpoints.
Tests routing, endpoint implementation, and ToolAccessor integration.

Handover 0130: Inter-agent messaging system validation
"""

from datetime import datetime, timezone

import pytest
from httpx import AsyncClient

from api.app import create_app
from src.giljo_mcp.models import AgentExecution, Project
from src.giljo_mcp.tenant import TenantManager


@pytest.fixture
async def client():
    """Create test client with FastAPI app"""
    app = create_app()
    async with AsyncClient(app=app, base_url="http://test") as c:
        yield c


@pytest.fixture
async def db_session(db_manager):
    """Create database session"""
    async with db_manager.get_session_async() as session:
        yield session


@pytest.fixture
async def test_tenant(db_session):
    """Create test tenant"""
    tenant = TenantManager(db_session)
    return await tenant.create_tenant("test_tenant")


@pytest.fixture
async def test_project(db_session, test_tenant):
    """Create test project"""
    project = Project(
        name="Test Project",
        description="Test project for messaging",
        tenant_key=test_tenant["tenant_key"],
        mission="Test mission",
    )
    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)
    return project


@pytest.fixture
async def test_agent_job(db_session, test_project):
    """Create test agent job"""
    job = AgentExecution(
        project_id=test_project.id,
        agent_display_name="test-agent",
        agent_name="Test Agent",
        status="running",
        tenant_key=test_project.tenant_key,
        messages_sent_count=0,
        messages_waiting_count=0,
        messages_read_count=0,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)
    return job


class TestMessagesRouterRegistration:
    """Test 1: Verify messages router is registered in app.py"""

    @pytest.mark.asyncio
    async def test_messages_router_registered(self, client):
        """Verify /api/v1/messages endpoint exists"""
        # This will return 401 without auth, but proves the route is registered
        response = await client.get("/api/v1/messages/", headers={"Authorization": "Bearer invalid"})
        # 401 means route exists but auth failed
        # 404 would mean route doesn't exist
        assert response.status_code in [401, 403, 400], (
            f"Expected auth error, got {response.status_code}: {response.text}"
        )

    @pytest.mark.asyncio
    async def test_openapi_includes_messages_routes(self, client):
        """Verify messages routes are in OpenAPI spec"""
        response = await client.get("/openapi.json")
        assert response.status_code == 200

        openapi = response.json()
        paths = openapi.get("paths", {})

        # Check for messages routes
        expected_paths = [
            "/api/v1/messages/",
            "/api/v1/messages/agent/{agent_name}",
            "/api/v1/messages/{message_id}/acknowledge",
            "/api/v1/messages/{message_id}/complete",
        ]

        for path in expected_paths:
            assert path in paths, f"Missing route: {path}"


class TestMessagesEndpoints:
    """Test 2: Test messages endpoint implementation"""

    @pytest.mark.asyncio
    async def test_send_message_endpoint_exists(self, client):
        """Test POST /api/v1/messages/ endpoint"""
        # Test without auth - should fail with 401, not 404
        response = await client.post(
            "/api/v1/messages/",
            json={
                "to_agents": ["agent1"],
                "content": "Test message",
                "project_id": "test-proj",
            },
        )
        # Not 404 = endpoint exists
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_list_messages_endpoint_exists(self, client):
        """Test GET /api/v1/messages/ endpoint"""
        response = await client.get("/api/v1/messages/")
        # Not 404 = endpoint exists
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_get_agent_messages_endpoint_exists(self, client):
        """Test GET /api/v1/messages/agent/{agent_name} endpoint"""
        response = await client.get("/api/v1/messages/agent/test-agent")
        # Not 404 = endpoint exists
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_acknowledge_endpoint_exists(self, client):
        """Test POST /api/v1/messages/{message_id}/acknowledge endpoint"""
        response = await client.post("/api/v1/messages/test-msg-id/acknowledge", params={"agent_name": "test-agent"})
        # Not 404 = endpoint exists
        assert response.status_code != 404

    @pytest.mark.asyncio
    async def test_complete_endpoint_exists(self, client):
        """Test POST /api/v1/messages/{message_id}/complete endpoint"""
        response = await client.post(
            "/api/v1/messages/test-msg-id/complete", params={"agent_name": "test-agent", "result": "completed"}
        )
        # Not 404 = endpoint exists
        assert response.status_code != 404


class TestToolAccessorIntegration:
    """Test 3: Verify ToolAccessor has message methods"""

    def test_tool_accessor_has_send_message(self):
        """Test ToolAccessor.send_message() exists"""
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        assert hasattr(ToolAccessor, "send_message")
        assert callable(ToolAccessor.send_message)

    def test_tool_accessor_has_get_messages(self):
        """Test ToolAccessor.get_messages() exists"""
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        assert hasattr(ToolAccessor, "get_messages")
        assert callable(ToolAccessor.get_messages)

    def test_tool_accessor_has_acknowledge_message(self):
        """Test ToolAccessor.acknowledge_message() exists"""
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        assert hasattr(ToolAccessor, "acknowledge_message")
        assert callable(ToolAccessor.acknowledge_message)

    def test_tool_accessor_has_complete_message(self):
        """Test ToolAccessor.complete_message() exists"""
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        assert hasattr(ToolAccessor, "complete_message")
        assert callable(ToolAccessor.complete_message)

    def test_tool_accessor_has_list_messages(self):
        """Test ToolAccessor.list_messages() exists"""
        from giljo_mcp.tools.tool_accessor import ToolAccessor

        assert hasattr(ToolAccessor, "list_messages")
        assert callable(ToolAccessor.list_messages)

    def test_tool_accessor_has_message_service(self):
        """Test ToolAccessor initializes MessageService"""
        # Check __init__ creates _message_service
        import inspect

        from giljo_mcp.tools.tool_accessor import ToolAccessor

        init_source = inspect.getsource(ToolAccessor.__init__)
        assert "_message_service = MessageService" in init_source


class TestMessageServiceIntegration:
    """Test 4: Verify MessageService is available"""

    def test_message_service_exists(self):
        """Test MessageService can be imported"""
        from giljo_mcp.message_service import MessageService

        assert MessageService is not None

    def test_message_service_has_send_method(self):
        """Test MessageService has send method"""
        from giljo_mcp.message_service import MessageService

        assert hasattr(MessageService, "send_message")


class TestEndpointModels:
    """Test 5: Verify endpoint models are properly defined"""

    def test_message_send_model(self):
        """Test MessageSend model is defined"""
        from api.endpoints.messages import MessageSend

        # Create valid model
        msg = MessageSend(to_agents=["agent1"], content="Test", project_id="proj-123")
        assert msg.to_agents == ["agent1"]
        assert msg.content == "Test"
        assert msg.project_id == "proj-123"
        assert msg.message_type == "direct"
        assert msg.priority == "normal"

    def test_message_response_model(self):
        """Test MessageResponse model is defined"""
        from api.endpoints.messages import MessageResponse

        msg = MessageResponse(
            id="msg-123",
            from_agent="test-agent",
            to_agents=["recipient"],
            content="Test response",
            message_type="direct",
            priority="normal",
            status="waiting",
            created_at=datetime.now(timezone.utc),
        )
        assert msg.id == "msg-123"
        assert msg.status == "pending"


class TestDatabaseIntegration:
    """Test 6: Verify message storage in database"""

    @pytest.mark.asyncio
    async def test_messages_stored_in_agent_job(self, db_session, test_agent_job):
        """Test messages stored in AgentExecution.messages JSONB"""
        # Add message to job
        message = {
            "id": "msg-1",
            "from": "test-agent",
            "to_agent": "recipient",
            "content": "Test message",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "pending",
            "type": "direct",
            "priority": "normal",
        }

        test_agent_job.messages.append(message)
        db_session.add(test_agent_job)
        await db_session.commit()

        # Verify stored
        await db_session.refresh(test_agent_job)
        assert len(test_agent_job.messages) > 0
        assert test_agent_job.messages[0]["id"] == "msg-1"
