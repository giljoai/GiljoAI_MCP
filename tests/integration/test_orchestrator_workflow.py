"""
Integration tests for orchestrator workflow and API schema validation.

Tests the complete orchestrator workflow including:
- Project creation with product_id
- Product_id persistence and API responses
- Agent spawning with correct schema
- Task creation with correct schema
- Team planning capabilities
"""

from uuid import uuid4

import pytest


class TestProjectProductAssociation:
    """Test product-project association and product_id persistence."""

    @pytest.mark.asyncio
    async def test_create_project_with_product_id(self, db_manager, tenant_manager):
        """Test that product_id is correctly saved and returned."""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tool_accessor = ToolAccessor(db_manager, tenant_manager)
        product_id = str(uuid4())

        # Create project with product_id
        result = await tool_accessor.create_project(name="Test Project", mission="Test mission", product_id=product_id)

        assert result["success"] is True
        assert result["product_id"] == product_id

        # Verify in database via get_project
        project_result = await tool_accessor.get_project(result["project_id"])
        assert project_result["success"] is True
        assert project_result["project"]["product_id"] == product_id

    @pytest.mark.asyncio
    async def test_list_projects_includes_product_id(self, db_manager, tenant_manager):
        """Test that list_projects returns product_id."""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tool_accessor = ToolAccessor(db_manager, tenant_manager)
        product_id = str(uuid4())

        # Create project
        create_result = await tool_accessor.create_project(
            name="List Test Project", mission="Test mission", product_id=product_id
        )
        assert create_result["success"] is True

        # List projects
        list_result = await tool_accessor.list_projects()
        assert list_result["success"] is True

        # Find our project
        project = next((p for p in list_result["projects"] if p["id"] == create_result["project_id"]), None)
        assert project is not None
        assert project["product_id"] == product_id

    @pytest.mark.asyncio
    async def test_project_status_includes_product_id(self, db_manager, tenant_manager):
        """Test that project_status returns product_id."""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tool_accessor = ToolAccessor(db_manager, tenant_manager)
        product_id = str(uuid4())

        # Create project
        create_result = await tool_accessor.create_project(
            name="Status Test Project", mission="Test mission", product_id=product_id
        )
        assert create_result["success"] is True

        # Get project status
        status_result = await tool_accessor.project_status(create_result["project_id"])
        assert status_result["success"] is True
        assert status_result["project"]["product_id"] == product_id


class TestAPISchemaValidation:
    """Test API endpoint schema validation for agents and tasks."""

    @pytest.mark.asyncio
    async def test_agent_create_schema(self, test_client, db_manager):
        """Test agent creation with correct schema (agent_name field)."""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Create test project first
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        project_result = await tool_accessor.create_project(name="Agent Test Project", mission="Test mission")
        assert project_result["success"] is True

        # Test agent creation with correct schema
        agent_data = {
            "agent_name": "Test Agent",
            "project_id": project_result["project_id"],
            "mission": "Test agent mission",
        }

        response = test_client.post("/api/v1/agents", json=agent_data)
        assert response.status_code == 200

        agent = response.json()
        assert agent["name"] == "Test Agent"
        assert agent["project_id"] == project_result["project_id"]

    @pytest.mark.asyncio
    async def test_agent_create_rejects_wrong_field(self, test_client, db_manager):
        """Test that agent creation rejects 'name' field (should be 'agent_name')."""
        from src.giljo_mcp.tenant import TenantManager
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        # Create test project first
        tenant_manager = TenantManager()
        tool_accessor = ToolAccessor(db_manager, tenant_manager)

        project_result = await tool_accessor.create_project(name="Agent Schema Test", mission="Test mission")
        assert project_result["success"] is True

        # Test with wrong field name
        agent_data = {
            "name": "Wrong Field",  # Should be agent_name
            "project_id": project_result["project_id"],
        }

        response = test_client.post("/api/v1/agents", json=agent_data)
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio
    async def test_task_create_schema(self, test_client):
        """Test task creation with correct schema (title field, string priority)."""
        task_data = {
            "title": "Test Task",
            "description": "Test description",
            "priority": "high",  # String, not integer
            "category": "test",
        }

        response = test_client.post("/api/v1/tasks", json=task_data)
        assert response.status_code == 200

        task = response.json()
        assert task["title"] == "Test Task"
        assert task["priority"] == "high"

    @pytest.mark.asyncio
    async def test_task_create_rejects_wrong_fields(self, test_client):
        """Test that task creation rejects wrong field names/types."""
        # Test wrong field name
        task_data = {
            "name": "Wrong Field",  # Should be title
            "priority": "high",
        }

        response = test_client.post("/api/v1/tasks", json=task_data)
        assert response.status_code == 422  # Validation error

        # Test wrong priority type
        task_data = {
            "title": "Test Task",
            "priority": 1,  # Should be string
        }

        response = test_client.post("/api/v1/tasks", json=task_data)
        assert response.status_code == 422  # Validation error


class TestOrchestratorWorkflow:
    """Test complete orchestrator workflow."""

    @pytest.mark.asyncio
    async def test_complete_workflow(self, db_manager, tenant_manager):
        """Test the complete orchestrator workflow from project creation to team planning."""
        from src.giljo_mcp.tools.tool_accessor import ToolAccessor

        tool_accessor = ToolAccessor(db_manager, tenant_manager)
        product_id = str(uuid4())

        # Step 1: Create project with product
        project_result = await tool_accessor.create_project(
            name="Workflow Test Project", mission="Build a REST API", product_id=product_id
        )
        assert project_result["success"] is True
        assert project_result["product_id"] == product_id

        # Step 2: Switch to project
        switch_result = await tool_accessor.switch_project(project_result["project_id"])
        assert switch_result["success"] is True

        # Step 3: Spawn orchestrator agent
        agent_result = await tool_accessor.spawn_agent(
            project_id=project_result["project_id"],
            name="Orchestrator",
            role="orchestrator",
            mission="Coordinate project execution",
        )
        assert agent_result["success"] is True

        # Step 4: Create task/mission
        task_result = await tool_accessor.create_task(
            name="Build API", description="Create REST API with authentication", priority="high"
        )
        assert task_result["success"] is True

        # Step 5: Verify team can be planned (conceptual test)
        # In reality, the orchestrator would analyze and plan the team
        # Here we verify the infrastructure supports it
        project_status = await tool_accessor.project_status(project_result["project_id"])
        assert project_status["success"] is True
        assert len(project_status["agents"]) >= 1  # At least orchestrator



@pytest.fixture
async def db_manager():
    """Database manager fixture."""
    from src.giljo_mcp.config_manager import get_config
    from src.giljo_mcp.database import DatabaseManager

    config = get_config()
    manager = DatabaseManager(database_url=config.database.url)
    yield manager
    await manager.close()


@pytest.fixture
def tenant_manager():
    """Tenant manager fixture."""
    from src.giljo_mcp.tenant import TenantManager

    return TenantManager()


@pytest.fixture
def test_client():
    """FastAPI test client fixture."""
    from fastapi.testclient import TestClient

    from api.app import app

    return TestClient(app)
