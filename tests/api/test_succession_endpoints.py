"""
API Tests for Orchestrator Succession Endpoints.

Handover 0080: Tests for succession REST API endpoints.

Test Coverage:
- GET /agent_jobs/{job_id}/succession_chain
- POST /agent_jobs/{job_id}/trigger_succession
- Multi-tenant isolation in API layer
- Error handling and validation
"""

from datetime import datetime, timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from api.app import app
from src.giljo_mcp.database import DatabaseManager
from src.giljo_mcp.models import MCPAgentJob, User


# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def client():
    """Provide FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def db_manager():
    """Provide DatabaseManager instance."""
    return DatabaseManager()


@pytest.fixture
def tenant_key():
    """Provide consistent tenant key for testing."""
    return "test-tenant-" + str(uuid4())


@pytest.fixture
def auth_token(db_manager: DatabaseManager, tenant_key: str):
    """Create test user and return auth token."""
    with db_manager.get_session() as session:
        # Create test user
        user = User(
            id=str(uuid4()),
            tenant_key=tenant_key,
            username="test_user",
            email="test@example.com",
            is_active=True,
            is_superuser=False,
        )
        user.set_password("testpassword123")
        session.add(user)
        session.commit()

    # Login to get token
    client = TestClient(app)
    response = client.post(
        "/api/auth/login",
        data={"username": "test_user", "password": "testpassword123"},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def headers(auth_token: str):
    """Provide authorization headers."""
    return {"Authorization": f"Bearer {auth_token}"}


@pytest.fixture
def orchestrator_chain(db_manager: DatabaseManager, tenant_key: str):
    """Create a succession chain of orchestrators for testing."""
    with db_manager.get_session() as session:
        # Instance 1 (complete)
        orch1 = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Instance 1",
            status="complete",
            instance_number=1,
            context_used=145000,
            context_budget=150000,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(orch1)
        session.flush()

        # Instance 2 (complete)
        orch2 = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Instance 2",
            status="complete",
            instance_number=2,
            context_used=140000,
            context_budget=150000,
            spawned_by=orch1.job_id,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(orch2)
        session.flush()

        # Instance 3 (working)
        orch3 = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Instance 3",
            status="working",
            instance_number=3,
            context_used=50000,
            context_budget=150000,
            spawned_by=orch2.job_id,
        )
        session.add(orch3)

        # Set handover linkage
        orch1.handover_to = orch2.job_id
        orch2.handover_to = orch3.job_id

        session.commit()
        session.refresh(orch1)
        session.refresh(orch2)
        session.refresh(orch3)

        return [orch1, orch2, orch3]


# ============================================================================
# Tests: GET /agent_jobs/{job_id}/succession_chain
# ============================================================================


def test_get_succession_chain_success(
    client: TestClient,
    headers: dict,
    orchestrator_chain: list,
):
    """Test retrieving succession chain returns all instances."""
    orch1, orch2, orch3 = orchestrator_chain

    # Request succession chain for any instance (should return full chain)
    response = client.get(
        f"/api/agent_jobs/{orch2.job_id}/succession_chain",
        headers=headers,
    )

    assert response.status_code == 200
    chain = response.json()

    # Should return all 3 instances
    assert len(chain) == 3

    # Verify instance ordering (should be sorted by instance_number)
    assert chain[0]["instance_number"] == 1
    assert chain[1]["instance_number"] == 2
    assert chain[2]["instance_number"] == 3

    # Verify job IDs match
    assert chain[0]["job_id"] == orch1.job_id
    assert chain[1]["job_id"] == orch2.job_id
    assert chain[2]["job_id"] == orch3.job_id

    # Verify statuses
    assert chain[0]["status"] == "complete"
    assert chain[1]["status"] == "complete"
    assert chain[2]["status"] == "working"


def test_get_succession_chain_includes_metadata(
    client: TestClient,
    headers: dict,
    orchestrator_chain: list,
):
    """Test succession chain includes relevant metadata."""
    orch1, orch2, orch3 = orchestrator_chain

    response = client.get(
        f"/api/agent_jobs/{orch1.job_id}/succession_chain",
        headers=headers,
    )

    assert response.status_code == 200
    chain = response.json()

    # Verify each instance has required fields
    for instance in chain:
        assert "job_id" in instance
        assert "instance_number" in instance
        assert "status" in instance
        assert "context_used" in instance
        assert "context_budget" in instance
        assert "created_at" in instance

    # Verify handover linkage
    assert chain[0]["handover_to"] == orch2.job_id
    assert chain[1]["handover_to"] == orch3.job_id
    assert chain[1]["spawned_by"] == orch1.job_id
    assert chain[2]["spawned_by"] == orch2.job_id


def test_get_succession_chain_single_instance(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test succession chain with single orchestrator (no successors)."""
    with db_manager.get_session() as session:
        # Create single orchestrator
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Standalone orchestrator",
            status="working",
            instance_number=1,
            context_used=50000,
            context_budget=150000,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)

    response = client.get(
        f"/api/agent_jobs/{orch.job_id}/succession_chain",
        headers=headers,
    )

    assert response.status_code == 200
    chain = response.json()

    # Should return single instance
    assert len(chain) == 1
    assert chain[0]["job_id"] == orch.job_id
    assert chain[0]["instance_number"] == 1


def test_get_succession_chain_not_found(
    client: TestClient,
    headers: dict,
):
    """Test succession chain with non-existent job ID."""
    fake_job_id = str(uuid4())

    response = client.get(
        f"/api/agent_jobs/{fake_job_id}/succession_chain",
        headers=headers,
    )

    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()


def test_get_succession_chain_non_orchestrator(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test succession chain for non-orchestrator agent type."""
    with db_manager.get_session() as session:
        # Create non-orchestrator agent job
        job = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="implementer",
            mission="Implement feature X",
            status="working",
            instance_number=1,
        )
        session.add(job)
        session.commit()
        session.refresh(job)

    response = client.get(
        f"/api/agent_jobs/{job.job_id}/succession_chain",
        headers=headers,
    )

    # Should return error or empty chain (implementation choice)
    # Assuming 400 for non-orchestrator types
    assert response.status_code in [400, 200]
    if response.status_code == 400:
        assert "orchestrator" in response.json()["detail"].lower()


def test_get_succession_chain_multi_tenant_isolation(
    client: TestClient,
    db_manager: DatabaseManager,
):
    """Test succession chain respects tenant boundaries."""
    tenant_a = "tenant-a-" + str(uuid4())
    tenant_b = "tenant-b-" + str(uuid4())

    with db_manager.get_session() as session:
        # Create orchestrator for tenant A
        orch_a = MCPAgentJob(
            tenant_key=tenant_a,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Tenant A",
            status="working",
            instance_number=1,
        )
        # Create orchestrator for tenant B
        orch_b = MCPAgentJob(
            tenant_key=tenant_b,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Tenant B",
            status="working",
            instance_number=1,
        )
        session.add(orch_a)
        session.add(orch_b)
        session.commit()
        session.refresh(orch_a)
        session.refresh(orch_b)

    # Create auth token for tenant A
    with db_manager.get_session() as session:
        user_a = User(
            id=str(uuid4()),
            tenant_key=tenant_a,
            username="tenant_a_user",
            email="tenant_a@example.com",
            is_active=True,
        )
        user_a.set_password("password123")
        session.add(user_a)
        session.commit()

    client_instance = TestClient(app)
    login_response = client_instance.post(
        "/api/auth/login",
        data={"username": "tenant_a_user", "password": "password123"},
    )
    token_a = login_response.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Tenant A can access their orchestrator
    response_a = client_instance.get(
        f"/api/agent_jobs/{orch_a.job_id}/succession_chain",
        headers=headers_a,
    )
    assert response_a.status_code == 200

    # Tenant A CANNOT access tenant B's orchestrator
    response_b = client_instance.get(
        f"/api/agent_jobs/{orch_b.job_id}/succession_chain",
        headers=headers_a,
    )
    assert response_b.status_code in [403, 404]


# ============================================================================
# Tests: POST /agent_jobs/{job_id}/trigger_succession
# ============================================================================


def test_trigger_manual_succession_success(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test manually triggering succession creates successor."""
    with db_manager.get_session() as session:
        # Create orchestrator at 50% context (below auto threshold)
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test orchestrator",
            status="working",
            instance_number=1,
            context_used=75000,  # 50% of 150K
            context_budget=150000,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Trigger manual succession
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "manual"},
    )

    assert response.status_code == 200
    result = response.json()

    # Verify response structure
    assert "successor_id" in result
    assert "instance_number" in result
    assert "handover_summary" in result

    # Verify successor created
    assert result["instance_number"] == 2
    successor_id = result["successor_id"]

    # Verify database state
    with db_manager.get_session() as session:
        # Original orchestrator should be complete
        orch_query = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)
        orch = session.execute(orch_query).scalar_one()
        assert orch.status == "complete"
        assert orch.handover_to == successor_id

        # Successor should exist and be waiting
        successor_query = select(MCPAgentJob).where(MCPAgentJob.job_id == successor_id)
        successor = session.execute(successor_query).scalar_one()
        assert successor.status == "waiting"
        assert successor.instance_number == 2
        assert successor.spawned_by == job_id


def test_trigger_succession_at_threshold(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggering succession at 90% threshold."""
    with db_manager.get_session() as session:
        # Create orchestrator at 90% context
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test orchestrator",
            status="working",
            instance_number=1,
            context_used=135000,  # 90% of 150K
            context_budget=150000,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Trigger succession
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "context_limit"},
    )

    assert response.status_code == 200
    result = response.json()

    assert result["instance_number"] == 2
    assert "successor_id" in result


def test_trigger_succession_phase_transition(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggering succession for phase transition."""
    with db_manager.get_session() as session:
        # Create orchestrator at moderate context usage
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test orchestrator",
            status="working",
            instance_number=1,
            context_used=80000,  # ~53% of 150K
            context_budget=150000,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Trigger succession for phase transition
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "phase_transition"},
    )

    assert response.status_code == 200
    result = response.json()

    # Verify succession completed
    with db_manager.get_session() as session:
        orch_query = select(MCPAgentJob).where(MCPAgentJob.job_id == job_id)
        orch = session.execute(orch_query).scalar_one()
        assert orch.succession_reason == "phase_transition"


def test_trigger_succession_not_found(
    client: TestClient,
    headers: dict,
):
    """Test triggering succession for non-existent job."""
    fake_job_id = str(uuid4())

    response = client.post(
        f"/api/agent_jobs/{fake_job_id}/trigger_succession",
        headers=headers,
        json={"reason": "manual"},
    )

    assert response.status_code == 404


def test_trigger_succession_already_complete(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggering succession on already completed orchestrator."""
    with db_manager.get_session() as session:
        # Create completed orchestrator
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test orchestrator",
            status="complete",
            instance_number=1,
            context_used=145000,
            context_budget=150000,
            completed_at=datetime.now(timezone.utc),
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Attempt to trigger succession on completed job
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "manual"},
    )

    # Should return error (cannot trigger on completed job)
    assert response.status_code == 400
    assert "complete" in response.json()["detail"].lower()


def test_trigger_succession_non_orchestrator(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggering succession on non-orchestrator agent."""
    with db_manager.get_session() as session:
        # Create non-orchestrator job
        job = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="implementer",
            mission="Implement feature",
            status="working",
            instance_number=1,
        )
        session.add(job)
        session.commit()
        session.refresh(job)
        job_id = job.job_id

    # Attempt to trigger succession on non-orchestrator
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "manual"},
    )

    # Should return error
    assert response.status_code == 400
    assert "orchestrator" in response.json()["detail"].lower()


def test_trigger_succession_invalid_reason(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggering succession with invalid reason."""
    with db_manager.get_session() as session:
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test orchestrator",
            status="working",
            instance_number=1,
            context_used=100000,
            context_budget=150000,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Use invalid reason
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "invalid_reason"},
    )

    # Should return validation error
    assert response.status_code == 422  # Validation error


def test_trigger_succession_includes_handover_summary(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggered succession includes handover summary in response."""
    with db_manager.get_session() as session:
        # Create orchestrator with messages and context
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test orchestrator",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
            messages=[
                {"type": "mission", "content": "Start project"},
                {"type": "status", "content": "Phase 1 complete"},
            ],
            context_chunks=["chunk-1", "chunk-2"],
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Trigger succession
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={"reason": "context_limit"},
    )

    assert response.status_code == 200
    result = response.json()

    # Verify handover summary present
    assert "handover_summary" in result
    summary = result["handover_summary"]

    # Verify summary structure
    assert "project_status" in summary
    assert "active_agents" in summary
    assert "message_count" in summary
    assert summary["message_count"] == 2


def test_trigger_succession_multi_tenant_isolation(
    client: TestClient,
    db_manager: DatabaseManager,
):
    """Test succession trigger respects tenant isolation."""
    tenant_a = "tenant-a-" + str(uuid4())
    tenant_b = "tenant-b-" + str(uuid4())

    with db_manager.get_session() as session:
        # Create orchestrator for tenant B
        orch_b = MCPAgentJob(
            tenant_key=tenant_b,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Tenant B orchestrator",
            status="working",
            instance_number=1,
            context_used=135000,
            context_budget=150000,
        )
        session.add(orch_b)
        session.commit()
        session.refresh(orch_b)
        job_id_b = orch_b.job_id

    # Create tenant A user and token
    with db_manager.get_session() as session:
        user_a = User(
            id=str(uuid4()),
            tenant_key=tenant_a,
            username="tenant_a_user_succession",
            email="tenant_a_succession@example.com",
            is_active=True,
        )
        user_a.set_password("password123")
        session.add(user_a)
        session.commit()

    client_instance = TestClient(app)
    login_response = client_instance.post(
        "/api/auth/login",
        data={"username": "tenant_a_user_succession", "password": "password123"},
    )
    token_a = login_response.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Tenant A tries to trigger succession on tenant B's orchestrator
    response = client_instance.post(
        f"/api/agent_jobs/{job_id_b}/trigger_succession",
        headers=headers_a,
        json={"reason": "manual"},
    )

    # Should be forbidden or not found
    assert response.status_code in [403, 404]


# ============================================================================
# Tests: Error Handling
# ============================================================================


def test_succession_endpoints_require_authentication(client: TestClient):
    """Test succession endpoints require authentication."""
    fake_job_id = str(uuid4())

    # GET succession chain without auth
    response = client.get(f"/api/agent_jobs/{fake_job_id}/succession_chain")
    assert response.status_code == 401

    # POST trigger succession without auth
    response = client.post(
        f"/api/agent_jobs/{fake_job_id}/trigger_succession",
        json={"reason": "manual"},
    )
    assert response.status_code == 401


def test_succession_chain_invalid_uuid(
    client: TestClient,
    headers: dict,
):
    """Test succession chain with invalid UUID format."""
    response = client.get(
        "/api/agent_jobs/not-a-valid-uuid/succession_chain",
        headers=headers,
    )

    # Should return validation error
    assert response.status_code == 422


def test_trigger_succession_missing_reason(
    client: TestClient,
    headers: dict,
    db_manager: DatabaseManager,
    tenant_key: str,
):
    """Test triggering succession without reason parameter."""
    with db_manager.get_session() as session:
        orch = MCPAgentJob(
            tenant_key=tenant_key,
            job_id=str(uuid4()),
            agent_type="orchestrator",
            mission="Test",
            status="working",
            instance_number=1,
        )
        session.add(orch)
        session.commit()
        session.refresh(orch)
        job_id = orch.job_id

    # Trigger without reason
    response = client.post(
        f"/api/agent_jobs/{job_id}/trigger_succession",
        headers=headers,
        json={},  # Missing reason
    )

    # Should return validation error
    assert response.status_code == 422
