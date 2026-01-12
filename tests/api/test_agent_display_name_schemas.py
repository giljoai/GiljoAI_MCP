"""
Tests for agent_display_name → agent_display_name in API schemas (Handover 0414b).

RED Phase (TDD): These tests define expected behavior AFTER migration.
Tests will FAIL because API schemas still use agent_display_name field.

Semantic Meaning:
- agent_name = NORTH STAR (template lookup key) - KEEP
- agent_display_name = UI LABEL (what humans see) - NEW NAME
- agent_display_name = OLD ambiguous name - WILL BE RENAMED

Migration Target:
- Request schemas: agent_display_name → agent_display_name
- Response schemas: agent_display_name → agent_display_name
- WebSocket events: agent_display_name → agent_display_name
- Keep: agent_name unchanged (template lookup key)

Affected Schemas:
- api/schemas/agent_job.py: JobCreateRequest, JobResponse, ChildJobSpec
- api/events/schemas.py: AgentStatusChangedData, AgentCreatedData
- api/endpoints/agent_jobs/models.py: SpawnAgentRequest, JobResponse

Expected Failures:
- ValidationError: Field 'agent_display_name' not found in schema
- KeyError: 'agent_display_name' not in response JSON
- AssertionError: 'agent_display_name' should not be present after migration
"""

import pytest
from httpx import AsyncClient
from uuid import uuid4
from pydantic import ValidationError

from api.schemas.agent_job import JobCreateRequest, JobResponse, ChildJobSpec
from api.events.schemas import AgentStatusChangedData, AgentCreatedData, EventFactory
from api.endpoints.agent_jobs.models import SpawnAgentRequest, JobResponse as EndpointJobResponse


class TestSpawnAgentRequestSchema:
    """Test that SpawnAgentRequest uses agent_display_name."""

    def test_spawn_agent_request_has_agent_display_name_field(self):
        """
        Test that SpawnAgentRequest schema has agent_display_name field.

        EXPECTED FAILURE: ValidationError - 'agent_display_name' is not a valid field
        Reason: Schema currently uses 'agent_display_name' field.
        """
        # Create request with NEW field name (will fail)
        request = SpawnAgentRequest(
            agent_display_name="System Architect",  # NEW FIELD NAME (will fail)
            agent_name="system-architect",  # Template key (KEEP)
            mission="Design the system architecture",
            project_id=str(uuid4()),
            context_chunks=[]
        )

        assert request.agent_display_name == "System Architect"
        assert request.agent_name == "system-architect"

    def test_spawn_agent_request_does_not_have_agent_display_name_field(self):
        """
        Test that SpawnAgentRequest does NOT have agent_display_name field after migration.

        EXPECTED FAILURE: Test will pass NOW but should FAIL after migration
        Reason: agent_display_name currently exists but should be removed.
        """
        request_dict = {
            "agent_display_name": "TDD Implementor",
            "agent_name": "tdd-implementor",
            "mission": "Implement features using TDD",
            "project_id": str(uuid4()),
            "context_chunks": []
        }

        # Should succeed with agent_display_name
        request = SpawnAgentRequest(**request_dict)
        assert hasattr(request, "agent_display_name")

        # Should NOT have agent_display_name attribute
        assert not hasattr(request, "agent_display_name"), "agent_display_name should not exist after migration"

    def test_spawn_agent_request_validation(self):
        """
        Test that SpawnAgentRequest validates agent_display_name field.

        EXPECTED FAILURE: ValidationError on missing agent_display_name
        Reason: Schema currently requires agent_display_name, not agent_display_name.
        """
        # Missing agent_display_name should fail
        with pytest.raises(ValidationError) as exc_info:
            SpawnAgentRequest(
                agent_name="database-expert",
                mission="Optimize database queries",
                project_id=str(uuid4()),
                context_chunks=[]
                # agent_display_name missing - should FAIL
            )

        assert "agent_display_name" in str(exc_info.value)


class TestJobResponseSchema:
    """Test that JobResponse uses agent_display_name."""

    def test_job_response_has_agent_display_name_field(self):
        """
        Test that JobResponse schema has agent_display_name field.

        EXPECTED FAILURE: ValidationError - 'agent_display_name' is not a valid field
        Reason: Schema currently uses 'agent_display_name' field.
        """
        from datetime import datetime, timezone

        # Create response with NEW field name (will fail)
        response = JobResponse(
            id=1,
            job_id=str(uuid4()),
            tenant_key="tenant-abc",
            agent_display_name="Documentation Manager",  # NEW FIELD NAME (will fail)
            agent_name="documentation-manager",  # Template key (KEEP)
            mission="Maintain project documentation",
            status="pending",
            spawned_by=None,
            context_chunks=[],
            messages=[],
            created_at=datetime.now(timezone.utc)
        )

        assert response.agent_display_name == "Documentation Manager"
        assert response.agent_name == "documentation-manager"

    def test_job_response_does_not_have_agent_display_name_field(self):
        """
        Test that JobResponse does NOT have agent_display_name field after migration.

        EXPECTED FAILURE: Test will pass NOW but should FAIL after migration
        Reason: agent_display_name currently exists in schema.
        """
        from datetime import datetime, timezone

        response = JobResponse(
            id=1,
            job_id=str(uuid4()),
            tenant_key="tenant-abc",
            agent_display_name="Frontend Tester",
            agent_name="frontend-tester",
            mission="Test frontend components",
            status="active",
            spawned_by=None,
            context_chunks=[],
            messages=[],
            created_at=datetime.now(timezone.utc)
        )

        # Should NOT have agent_display_name attribute
        assert not hasattr(response, "agent_display_name"), "agent_display_name should not exist after migration"


class TestChildJobSpecSchema:
    """Test that ChildJobSpec uses agent_display_name."""

    def test_child_job_spec_has_agent_display_name_field(self):
        """
        Test that ChildJobSpec schema has agent_display_name field.

        EXPECTED FAILURE: ValidationError - 'agent_display_name' is not a valid field
        Reason: Schema currently uses 'agent_display_name' field.
        """
        # Create child job spec with NEW field name (will fail)
        spec = ChildJobSpec(
            agent_display_name="UX Designer",  # NEW FIELD NAME (will fail)
            agent_name="ux-designer",  # Template key (KEEP)
            mission="Design user experience flows",
            context_chunks=[]
        )

        assert spec.agent_display_name == "UX Designer"
        assert spec.agent_name == "ux-designer"

    def test_child_job_spec_does_not_have_agent_display_name_field(self):
        """
        Test that ChildJobSpec does NOT have agent_display_name field after migration.

        EXPECTED FAILURE: Test will pass NOW but should FAIL after migration
        Reason: agent_display_name currently exists in schema.
        """
        spec = ChildJobSpec(
            agent_display_name="Network Security Engineer",
            agent_name="network-security-engineer",
            mission="Secure network communications",
            context_chunks=[]
        )

        assert not hasattr(spec, "agent_display_name"), "agent_display_name should not exist after migration"


class TestAgentStatusChangedEventSchema:
    """Test that AgentStatusChangedData uses agent_display_name."""

    def test_agent_status_changed_has_agent_display_name_field(self):
        """
        Test that AgentStatusChangedData schema has agent_display_name field.

        EXPECTED FAILURE: ValidationError - 'agent_display_name' is not a valid field
        Reason: Schema currently uses 'agent_display_name' field.
        """
        # Create event data with NEW field name (will fail)
        data = AgentStatusChangedData(
            job_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key="tenant-abc",
            old_status="waiting",
            new_status="working",
            agent_display_name="Orchestrator Coordinator",  # NEW FIELD NAME (will fail)
            duration_seconds=None
        )

        assert data.agent_display_name == "Orchestrator Coordinator"

    def test_agent_status_changed_does_not_have_agent_display_name_field(self):
        """
        Test that AgentStatusChangedData does NOT have agent_display_name field.

        EXPECTED FAILURE: Test will pass NOW but should FAIL after migration
        Reason: agent_display_name currently exists in schema.
        """
        data = AgentStatusChangedData(
            job_id=str(uuid4()),
            project_id=str(uuid4()),
            tenant_key="tenant-abc",
            old_status="working",
            new_status="complete",
            agent_display_name="Deep Researcher",
            duration_seconds=120.5
        )

        assert not hasattr(data, "agent_display_name"), "agent_display_name should not exist after migration"

    def test_event_factory_agent_status_changed_uses_agent_display_name(self):
        """
        Test that EventFactory.agent_status_changed() uses agent_display_name parameter.

        EXPECTED FAILURE: TypeError - unexpected keyword argument 'agent_display_name'
        Reason: EventFactory currently expects 'agent_display_name' parameter.
        """
        job_id = str(uuid4())
        tenant_key = "tenant-abc"

        # Create event using NEW parameter name (will fail)
        event = EventFactory.agent_status_changed(
            job_id=job_id,
            tenant_key=tenant_key,
            old_status="pending",
            new_status="active",
            agent_display_name="Version Manager",  # NEW PARAMETER NAME (will fail)
            project_id=str(uuid4()),
            duration_seconds=None
        )

        assert event["data"]["agent_display_name"] == "Version Manager"
        assert "agent_display_name" not in event["data"], "agent_display_name should not exist in event data"


class TestAgentCreatedEventSchema:
    """Test that AgentCreatedData uses agent_display_name in nested agent data."""

    def test_agent_created_event_agent_data_has_agent_display_name(self):
        """
        Test that agent data in AgentCreatedData contains agent_display_name.

        EXPECTED FAILURE: KeyError - 'agent_display_name' not found in agent dict
        Reason: Agent data currently uses 'agent_display_name' key.
        """
        agent_data = {
            "id": str(uuid4()),
            "agent_display_name": "Backend Integration Tester",  # NEW KEY (will fail)
            "agent_name": "backend-integration-tester",  # Template key (KEEP)
            "status": "pending",
            "mission": "Test backend integrations",
            "mode": "claude"
        }

        data = AgentCreatedData(
            project_id=str(uuid4()),
            tenant_key="tenant-abc",
            agent=agent_data
        )

        assert data.agent["agent_display_name"] == "Backend Integration Tester"
        assert data.agent["agent_name"] == "backend-integration-tester"

    def test_agent_created_event_agent_data_does_not_have_agent_display_name(self):
        """
        Test that agent data does NOT contain agent_display_name key after migration.

        EXPECTED FAILURE: ValidationError - missing required field 'agent_display_name'
        Reason: Current validation requires agent_display_name in agent data.
        """
        agent_data = {
            "id": str(uuid4()),
            "agent_display_name": "Installation Flow Agent",
            "agent_name": "installation-flow-agent",
            "status": "pending"
        }

        data = AgentCreatedData(
            project_id=str(uuid4()),
            tenant_key="tenant-abc",
            agent=agent_data
        )

        assert "agent_display_name" not in data.agent, "agent_display_name should not exist in agent data"


class TestAPIEndpointResponseSchemas:
    """Test that API endpoint response models use agent_display_name."""

    def test_endpoint_job_response_has_agent_display_name(self):
        """
        Test that api/endpoints/agent_jobs/models.py JobResponse has agent_display_name.

        EXPECTED FAILURE: ValidationError - 'agent_display_name' is not a valid field
        Reason: Endpoint model currently uses 'agent_display_name' field.
        """
        from datetime import datetime, timezone

        response = EndpointJobResponse(
            id=str(uuid4()),
            job_id=str(uuid4()),
            agent_id=str(uuid4()),
            tenant_key="tenant-abc",
            project_id=str(uuid4()),
            agent_display_name="Database Expert",  # NEW FIELD NAME (will fail)
            agent_name="database-expert",  # Template key (KEEP)
            mission="Optimize database schema",
            status="working",
            progress=50,
            spawned_by=None,
            tool_type="universal",
            context_chunks=[],
            messages=[],
            started_at=datetime.now(timezone.utc),
            completed_at=None,
            created_at=datetime.now(timezone.utc),
            updated_at=None,
            mission_acknowledged_at=datetime.now(timezone.utc),
            steps={"total": 5, "completed": 2}
        )

        assert response.agent_display_name == "Database Expert"
        assert not hasattr(response, "agent_display_name"), "agent_display_name should not exist"


class TestAPIIntegrationEndToEnd:
    """Test full API request/response cycle uses agent_display_name."""

    @pytest.mark.asyncio
    async def test_spawn_agent_api_uses_agent_display_name(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_project
    ):
        """
        Test that spawning an agent via API uses agent_display_name field.

        EXPECTED FAILURE: 422 Unprocessable Entity - field 'agent_display_name' not recognized
        Reason: API endpoint currently expects 'agent_display_name' field in request.

        Note: This test requires api_client and tenant fixtures from conftest.py
        """
        response = await api_client.post(
            "/api/agent-jobs/spawn",
            json={
                "agent_display_name": "System Architect",  # NEW FIELD NAME (will fail)
                "agent_name": "system-architect",  # Template key (KEEP)
                "mission": "Design system architecture",
                "project_id": tenant_a_project["id"],
                "context_chunks": []
            },
            cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert "job_id" in data

    @pytest.mark.asyncio
    async def test_list_jobs_api_returns_agent_display_name(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """
        Test that listing jobs returns agent_display_name field, not agent_display_name.

        EXPECTED FAILURE: KeyError - 'agent_display_name' not in response
        Reason: API currently returns 'agent_display_name' field in job responses.

        Note: This test requires api_client and tenant fixtures from conftest.py
        """
        response = await api_client.get(
            "/api/agent-jobs/",
            cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "jobs" in data
        assert len(data["jobs"]) > 0

        # Check first job has agent_display_name
        job = data["jobs"][0]
        assert "agent_display_name" in job, "Response should include agent_display_name"
        assert "agent_display_name" not in job, "Response should NOT include agent_display_name after migration"
        assert "agent_name" in job, "Response should still include agent_name (template key)"

    @pytest.mark.asyncio
    async def test_get_job_api_returns_agent_display_name(
        self, api_client: AsyncClient, tenant_a_admin_token: str, tenant_a_agent_job
    ):
        """
        Test that getting a single job returns agent_display_name field.

        EXPECTED FAILURE: KeyError - 'agent_display_name' not in response
        Reason: API currently returns 'agent_display_name' field.

        Note: This test requires api_client and tenant fixtures from conftest.py
        """
        job_id = tenant_a_agent_job["job_id"]

        response = await api_client.get(
            f"/api/agent-jobs/{job_id}",
            cookies={"access_token": tenant_a_admin_token}
        )

        assert response.status_code == 200
        data = response.json()
        assert "agent_display_name" in data
        assert "agent_display_name" not in data, "agent_display_name should not exist after migration"
        assert "agent_name" in data, "agent_name should still exist"


class TestWebSocketEventSchemas:
    """Test that WebSocket events use agent_display_name."""

    def test_websocket_event_factory_creates_events_with_agent_display_name(self):
        """
        Test that WebSocket events contain agent_display_name field.

        EXPECTED FAILURE: TypeError or KeyError
        Reason: EventFactory methods currently use agent_display_name parameter.
        """
        job_id = str(uuid4())
        project_id = str(uuid4())
        tenant_key = "tenant-abc"

        # Create agent:status_changed event
        event = EventFactory.agent_status_changed(
            job_id=job_id,
            tenant_key=tenant_key,
            old_status="pending",
            new_status="working",
            agent_display_name="Orchestrator Coordinator",  # NEW PARAMETER
            project_id=project_id
        )

        assert event["data"]["agent_display_name"] == "Orchestrator Coordinator"
        assert "agent_display_name" not in event["data"]

    def test_websocket_event_agent_created_uses_agent_display_name(self):
        """
        Test that agent:created events use agent_display_name in agent data.

        EXPECTED FAILURE: KeyError - agent data should have 'agent_display_name' key
        Reason: Agent data currently uses 'agent_display_name' key.
        """
        agent_data = {
            "id": str(uuid4()),
            "agent_display_name": "TDD Implementor",
            "agent_name": "tdd-implementor",
            "status": "pending",
            "mission": "Implement using TDD"
        }

        event = EventFactory.agent_created(
            project_id=str(uuid4()),
            tenant_key="tenant-abc",
            agent=agent_data
        )

        assert event["data"]["agent"]["agent_display_name"] == "TDD Implementor"
        assert "agent_display_name" not in event["data"]["agent"]


class TestBackwardCompatibilityConsiderations:
    """
    Tests documenting backward compatibility considerations.

    These tests document BREAKING CHANGES and should guide migration planning.
    """

    def test_agent_display_name_field_removed_is_breaking_change(self):
        """
        Document that removing agent_display_name is a BREAKING CHANGE.

        Any external systems or frontend code accessing 'agent_display_name' will break.
        Migration requires:
        1. Update all API consumers to use agent_display_name
        2. Update WebSocket event handlers
        3. Update database queries

        This test documents the breaking change for future reference.
        """
        # This will FAIL after migration (intentionally)
        with pytest.raises((AttributeError, ValidationError, KeyError)):
            # Attempting to access agent_display_name should fail after migration
            request = SpawnAgentRequest(
                agent_display_name="orchestrator",  # OLD FIELD NAME (should fail after migration)
                mission="Test mission",
                project_id=str(uuid4()),
                context_chunks=[]
            )

    def test_agent_name_preserved_for_template_lookup(self):
        """
        Document that agent_name is PRESERVED and should not change.

        agent_name is the NORTH STAR template lookup key and must remain unchanged.
        This test should PASS both before and after migration.
        """
        request = SpawnAgentRequest(
            agent_display_name="System Architect",
            agent_name="system-architect",  # NORTH STAR - never changes
            mission="Design system",
            project_id=str(uuid4()),
            context_chunks=[]
        )

        # Both fields should coexist
        assert request.agent_display_name == "System Architect"
        assert request.agent_name == "system-architect"
