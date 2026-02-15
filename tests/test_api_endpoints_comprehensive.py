"""
Comprehensive test suite for GiljoAI MCP REST API endpoints
"""

# Import the FastAPI app
import sys
import uuid
from pathlib import Path

import pytest
from fastapi.testclient import TestClient


sys.path.insert(0, str(Path(__file__).parent.parent))

from api.app import create_app


class TestAPIEndpoints:
    """Comprehensive test suite for all API endpoints"""

    @pytest.fixture(autouse=True)
    async def setup(self):
        """Setup test environment"""
        self.app = create_app()
        self.client = TestClient(self.app)

        # Create test data
        self.test_project_id = str(uuid.uuid4())
        self.test_agent_name = "test_agent"
        self.test_message_id = str(uuid.uuid4())

        yield

        # Cleanup
        await self.cleanup()

    async def cleanup(self):
        """Clean up test data"""
        # Clean up would happen here in production

    # ==================== PROJECT ENDPOINTS ====================

    def test_create_project(self):
        """Test creating a new project"""
        response = self.client.post(
            "/api/v1/projects/",
            json={
                "name": "Test Project",
                "mission": "Test mission for comprehensive API testing",
                "agents": ["analyzer", "implementer"],
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Project"
        assert data["mission"] == "Test mission for comprehensive API testing"
        assert data["status"] == "active"
        assert "id" in data
        assert "created_at" in data

        self.test_project_id = data["id"]

    def test_list_projects(self):
        """Test listing all projects"""
        # First create a project
        self.test_create_project()

        # List projects
        response = self.client.get("/api/v1/projects/")
        assert response.status_code == 200

        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

        # Test with filters
        response = self.client.get("/api/v1/projects/?status=active")
        assert response.status_code == 200

        response = self.client.get("/api/v1/projects/?limit=5&offset=0")
        assert response.status_code == 200

    def test_get_project(self):
        """Test getting a specific project"""
        # First create a project
        self.test_create_project()

        response = self.client.get(f"/api/v1/projects/{self.test_project_id}")
        assert response.status_code == 200

        data = response.json()
        assert data["id"] == self.test_project_id
        assert "agent_count" in data
        assert "message_count" in data

    def test_update_project(self):
        """Test updating project details"""
        # First create a project
        self.test_create_project()

        response = self.client.patch(
            f"/api/v1/projects/{self.test_project_id}",
            json={"mission": "Updated mission for testing", "status": "active"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["mission"] == "Updated mission for testing"

    def test_close_project(self):
        """Test closing a project"""
        # First create a project
        self.test_create_project()

        response = self.client.delete(
            f"/api/v1/projects/{self.test_project_id}", params={"summary": "Project completed successfully"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]

    # ==================== AGENT ENDPOINTS ====================

    def test_create_agent(self):
        """Test creating a new agent"""
        # First create a project
        self.test_create_project()

        response = self.client.post(
            "/api/v1/agents/",
            json={
                "project_id": self.test_project_id,
                "name": "test_agent",
                "role": "analyzer",
                "mission": "Analyze code and provide insights",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "test_agent"
        assert data["role"] == "analyzer"
        assert data["status"] == "active"

    def test_get_agent_health(self):
        """Test getting agent health status"""
        # First create an agent
        self.test_create_agent()

        response = self.client.get(f"/api/v1/agents/{self.test_agent_name}/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "context_usage" in data
        assert "message_queue_size" in data

    def test_decommission_agent(self):
        """Test decommissioning an agent"""
        # First create an agent
        self.test_create_agent()

        response = self.client.delete(f"/api/v1/agents/{self.test_agent_name}", params={"reason": "Task completed"})

        assert response.status_code == 200
        data = response.json()
        assert data["success"]

    # ==================== MESSAGE ENDPOINTS ====================

    def test_send_message(self):
        """Test sending a message"""
        # First create project and agent
        self.test_create_project()
        self.test_create_agent()

        response = self.client.post(
            "/api/v1/messages/",
            json={
                "to_agents": ["test_agent"],
                "content": "Test message content",
                "project_id": self.test_project_id,
                "message_type": "direct",
                "priority": "normal",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "message_id" in data
        assert data["status"] == "sent"

        self.test_message_id = data["message_id"]

    def test_get_messages(self):
        """Test retrieving messages for an agent"""
        # First send a message
        self.test_send_message()

        response = self.client.get(
            f"/api/v1/messages/agent/{self.test_agent_name}", params={"project_id": self.test_project_id}
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) > 0

    def test_acknowledge_message(self):
        """Test acknowledging a message"""
        # First send a message
        self.test_send_message()

        response = self.client.post(
            f"/api/v1/messages/{self.test_message_id}/acknowledge", params={"agent_name": self.test_agent_name}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["status"] == "acknowledged"

    def test_complete_message(self):
        """Test completing a message"""
        # First acknowledge a message
        self.test_acknowledge_message()

        response = self.client.post(
            f"/api/v1/messages/{self.test_message_id}/complete",
            json={"agent_name": self.test_agent_name, "result": "Message processed successfully"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["status"] == "database_initialized"

    # ==================== CONFIGURATION ENDPOINTS ====================

    def test_get_system_configuration(self):
        """Test getting system configuration"""
        response = self.client.get("/api/v1/config/")

        assert response.status_code == 200
        data = response.json()
        assert "database" in data
        assert "api" in data
        assert "orchestration" in data
        assert "security" in data
        assert "features" in data

    def test_get_configuration_key(self):
        """Test getting specific configuration value"""
        response = self.client.get("/api/v1/config/key/database.pool_size")

        assert response.status_code == 200
        data = response.json()
        assert "key" in data
        assert "value" in data
        assert "source" in data
        assert data["key"] == "database.pool_size"

    def test_set_configuration(self):
        """Test setting configuration value"""
        response = self.client.put("/api/v1/config/key/test.value", json={"key": "test.value", "value": 123})

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert data["value"] == 123

    def test_update_multiple_configurations(self):
        """Test updating multiple configurations"""
        response = self.client.patch(
            "/api/v1/config/",
            json={"configurations": {"test.value1": 100, "test.value2": "test_string", "test.value3": True}},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]
        assert len(data["updated"]) == 3

    def test_reload_configuration(self):
        """Test reloading configuration"""
        response = self.client.post("/api/v1/config/reload")

        assert response.status_code == 200
        data = response.json()
        assert data["success"]

    def test_tenant_configuration(self):
        """Test tenant-specific configuration"""
        tenant_key = "test_tenant_123"

        # Set tenant config
        response = self.client.put(
            f"/api/v1/config/tenant/{tenant_key}",
            json={"max_agents": 20, "features.custom": True},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"]

        # Get tenant config
        response = self.client.get(f"/api/v1/config/tenant/{tenant_key}")
        assert response.status_code == 200
        data = response.json()
        assert "max_agents" in data

        # List tenants
        response = self.client.get("/api/v1/config/tenants")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Delete tenant config
        response = self.client.delete(f"/api/v1/config/tenant/{tenant_key}")
        assert response.status_code == 200

    # ==================== STATISTICS ENDPOINTS ====================

    def test_get_system_statistics(self):
        """Test getting system statistics"""
        response = self.client.get("/api/v1/stats/system")

        assert response.status_code == 200
        data = response.json()
        assert "total_projects" in data
        assert "active_projects" in data
        assert "total_agents" in data
        assert "total_messages" in data
        assert "average_context_usage" in data
        assert "database_size_mb" in data
        assert "uptime_seconds" in data

    def test_get_project_statistics(self):
        """Test getting project statistics"""
        response = self.client.get("/api/v1/stats/projects")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        # Test with filters
        response = self.client.get("/api/v1/stats/projects?status=active&limit=10")
        assert response.status_code == 200

    def test_get_agent_statistics(self):
        """Test getting agent statistics"""
        response = self.client.get("/api/v1/stats/agents")

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

        if len(data) > 0:
            agent_stat = data[0]
            assert "agent_id" in agent_stat
            assert "messages_sent" in agent_stat
            assert "messages_received" in agent_stat
            assert "tasks_completed" in agent_stat

    def test_get_message_statistics(self):
        """Test getting message statistics"""
        response = self.client.get("/api/v1/stats/messages")

        assert response.status_code == 200
        data = response.json()
        assert "total_messages" in data
        assert "pending_messages" in data
        assert "average_processing_time_seconds" in data
        assert "messages_per_hour" in data

        # Test with time range
        response = self.client.get("/api/v1/stats/messages?time_range=24h")
        assert response.status_code == 200

    def test_get_performance_metrics(self):
        """Test getting performance metrics"""
        response = self.client.get("/api/v1/stats/performance")

        assert response.status_code == 200
        data = response.json()
        assert "api_response_time_ms" in data
        assert "database_query_time_ms" in data
        assert "memory_usage_mb" in data
        assert "cpu_usage_percent" in data
        assert "websocket_connections" in data

    def test_get_timeseries_data(self):
        """Test getting time series data"""
        metrics = ["messages", "agents", "tasks", "context_usage", "errors"]

        for metric in metrics:
            response = self.client.get(f"/api/v1/stats/timeseries/{metric}?period=1h")

            assert response.status_code == 200
            data = response.json()
            assert data["metric"] == metric
            assert "data_points" in data
            assert isinstance(data["data_points"], list)

    def test_get_detailed_health(self):
        """Test getting detailed health status"""
        response = self.client.get("/api/v1/stats/health/detailed")

        assert response.status_code == 200
        data = response.json()
        assert "overall" in data
        assert "components" in data
        assert "checks_passed" in data
        assert "checks_failed" in data

        # Check component health
        assert "api" in data["components"]
        assert "database" in data["components"]
        assert "configuration" in data["components"]

    # ==================== TASK ENDPOINTS ====================

    def test_task_endpoints(self):
        """Test task management endpoints"""
        # Create a task
        response = self.client.post(
            "/api/v1/tasks/",
            json={
                "project_id": self.test_project_id,
                "content": "Test task content",
                "priority": "high",
                "category": "bug_fix",
            },
        )

        if response.status_code == 200:
            data = response.json()
            task_id = data["task_id"]

            # Get tasks
            response = self.client.get(f"/api/v1/tasks/?project_id={self.test_project_id}")
            assert response.status_code == 200

            # Update task
            response = self.client.patch(
                f"/api/v1/tasks/{task_id}", json={"status": "in_progress", "assigned_to": "test_agent"}
            )
            assert response.status_code == 200

            # Complete task
            response = self.client.post(
                f"/api/v1/tasks/{task_id}/complete", json={"result": "Task completed successfully"}
            )
            assert response.status_code == 200

    # ==================== CONTEXT ENDPOINTS ====================

    def test_context_endpoints(self):
        """Test context management endpoints"""
        # Get vision document
        response = self.client.get("/api/v1/context/vision")

        if response.status_code == 200:
            data = response.json()
            assert "content" in data or "vision" in data
            assert "total_parts" in data

            # Get vision part if chunked
            if data.get("total_parts", 1) > 1:
                response = self.client.get("/api/v1/context/vision?part=1")
                assert response.status_code == 200

        # Get context index
        response = self.client.get("/api/v1/context/index")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))

    # ==================== ERROR HANDLING TESTS ====================

    def test_404_not_found(self):
        """Test 404 error handling"""
        response = self.client.get("/api/v1/projects/nonexistent-id")
        assert response.status_code == 404

        data = response.json()
        assert "error" in data or "detail" in data

    def test_400_bad_request(self):
        """Test 400 error handling"""
        response = self.client.post(
            "/api/v1/projects/",
            json={
                # Missing required field "name"
                "mission": "Test mission"
            },
        )

        # Could be 400 or 422 depending on validation
        assert response.status_code in [400, 422]

    def test_method_not_allowed(self):
        """Test 405 method not allowed"""
        response = self.client.put("/api/v1/projects/")  # PUT not allowed on this endpoint
        assert response.status_code == 405

    # ==================== WEBSOCKET TESTS ====================

    def test_websocket_connection(self):
        """Test WebSocket connection"""

        with self.client.websocket_connect("/ws/test_client") as websocket:
            # Send ping
            websocket.send_json({"type": "ping"})
            data = websocket.receive_json()
            assert data["type"] == "pong"

            # Subscribe to updates
            websocket.send_json({"type": "subscribe", "entity_type": "project", "entity_id": self.test_project_id})
            data = websocket.receive_json()
            assert data["type"] == "subscribed"

            # Unsubscribe
            websocket.send_json({"type": "unsubscribe", "entity_type": "project", "entity_id": self.test_project_id})
            data = websocket.receive_json()
            assert data["type"] == "unsubscribed"

    # ==================== INTEGRATION TESTS ====================

    def test_full_workflow(self):
        """Test complete workflow from project creation to completion"""
        # 1. Create project
        project_response = self.client.post(
            "/api/v1/projects/", json={"name": "Integration Test Project", "mission": "Complete workflow test"}
        )
        assert project_response.status_code == 200
        project_id = project_response.json()["id"]

        # 2. Create agents
        agents = ["analyzer", "implementer", "tester"]
        for agent_name in agents:
            response = self.client.post(
                "/api/v1/agents/",
                json={
                    "project_id": project_id,
                    "name": agent_name,
                    "role": agent_name,
                    "mission": f"Act as {agent_name}",
                },
            )
            assert response.status_code == 200

        # 3. Send messages between agents
        response = self.client.post(
            "/api/v1/messages/",
            json={
                "to_agents": ["implementer"],
                "from_agent": "analyzer",
                "content": "Analysis complete, ready for implementation",
                "project_id": project_id,
            },
        )
        assert response.status_code == 200

        # 4. Get project statistics
        response = self.client.get(f"/api/v1/stats/project/{project_id}")
        if response.status_code == 200:
            stats = response.json()
            assert stats["agent_count"] == 3
            assert stats["message_count"] > 0

        # 5. Close project
        response = self.client.delete(
            f"/api/v1/projects/{project_id}", params={"summary": "Integration test completed"}
        )
        assert response.status_code == 200


# Run tests
if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
