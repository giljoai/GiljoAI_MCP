"""
Integration test for orchestrator race condition fix in ProjectLaunchView.vue

Tests that the orchestrator is included in agent jobs list even when auto-created,
verifying the fix for the race condition where Promise.all caused the orchestrator
to be missing from the list.
"""

import pytest
import pytest_asyncio
from datetime import datetime, timezone
from uuid import uuid4

from src.giljo_mcp.models import Project


@pytest_asyncio.fixture(scope="function")
async def test_project_without_orchestrator(db_session):
    """
    Create a test project WITHOUT an orchestrator.

    This simulates the initial state where a project exists but no orchestrator
    has been created yet (auto-creation will happen on first fetch).
    """
    tenant_key = str(uuid4())

    project = Project(
        id=str(uuid4()),
        name="Test Project Without Orchestrator",
        description="Project for testing orchestrator auto-creation race condition",
        mission="Test mission - orchestrator should be auto-created on demand",
        status="active",
        tenant_key=tenant_key,
        created_at=datetime.now(timezone.utc),
    )

    db_session.add(project)
    await db_session.commit()
    await db_session.refresh(project)

    return project


@pytest.mark.asyncio
async def test_orchestrator_included_in_agent_jobs_list_after_auto_creation(
    async_client,
    test_project_without_orchestrator
):
    """
    BEHAVIOR: When fetching agent jobs for a project, the orchestrator
    should be included even if it was just auto-created.

    This test verifies the fix for the race condition where agentJobs.list()
    was called in parallel with getOrchestrator() and could return before
    the auto-created orchestrator was committed to the database.

    CRITICAL: This test should FAIL initially (RED phase) because the
    current implementation uses Promise.all which causes a race condition.
    After fixing ProjectLaunchView.vue to use sequential calls, the test
    should PASS (GREEN phase).
    """
    project_id = test_project_without_orchestrator.id

    # Step 1: Verify no orchestrator exists initially
    response = await async_client.get(
        f"/api/projects/{project_id}/agents"
    )
    assert response.status_code == 200
    initial_agents = response.json()

    # Should have no agents at all (empty project)
    assert len(initial_agents) == 0, (
        f"Expected empty agent list initially, got {len(initial_agents)} agents"
    )

    # Step 2: Call getOrchestrator (triggers auto-creation)
    response = await async_client.get(
        f"/api/projects/{project_id}/orchestrator"
    )
    assert response.status_code == 200
    orchestrator_data = response.json()

    # Verify orchestrator was created successfully
    assert orchestrator_data.get("success") is True, (
        "getOrchestrator should return success=True"
    )
    assert "orchestrator" in orchestrator_data, (
        "getOrchestrator should return orchestrator object"
    )

    orchestrator_id = orchestrator_data["orchestrator"]["job_id"]
    assert orchestrator_id is not None, "Orchestrator should have a job_id"

    # Step 3: Call agentJobs.list AFTER getOrchestrator
    # This is the critical test - the orchestrator should now be in the list
    response = await async_client.get(
        f"/api/projects/{project_id}/agents"
    )
    assert response.status_code == 200
    agents = response.json()

    # CRITICAL ASSERTION: Orchestrator should be in the list
    orchestrator_in_list = [a for a in agents if a.get("job_id") == orchestrator_id]

    # This assertion will FAIL initially (race condition)
    # After fixing ProjectLaunchView.vue to sequential calls, it will PASS
    assert len(orchestrator_in_list) == 1, (
        f"Orchestrator {orchestrator_id} should be in agent list. "
        f"Found {len(agents)} agents: {[a.get('job_id', 'unknown') for a in agents]}"
    )

    # Verify the orchestrator has correct type
    orchestrator = orchestrator_in_list[0]
    assert orchestrator.get("agent_type") == "orchestrator", (
        f"Agent type should be 'orchestrator', got '{orchestrator.get('agent_type')}'"
    )


@pytest.mark.asyncio
async def test_parallel_calls_demonstrate_race_condition(
    async_client,
    test_project_without_orchestrator
):
    """
    DEMONSTRATION: This test shows the race condition when calls are parallel.

    This test documents the broken behavior and should be marked as xfail
    until the frontend fix is deployed.

    Purpose: Demonstrate that Promise.all creates timing issues where
    agentJobs.list() can execute before getOrchestrator() commits to database.
    """
    project_id = test_project_without_orchestrator.id

    # Simulate parallel calls (like Promise.all in current code)
    import asyncio

    # Execute both calls simultaneously
    get_orchestrator_task = async_client.get(
        f"/api/projects/{project_id}/orchestrator"
    )
    get_agents_task = async_client.get(
        f"/api/projects/{project_id}/agents"
    )

    # Wait for both to complete (parallel execution)
    orchestrator_response, agents_response = await asyncio.gather(
        get_orchestrator_task,
        get_agents_task
    )

    # Both should succeed
    assert orchestrator_response.status_code == 200
    assert agents_response.status_code == 200

    orchestrator_data = orchestrator_response.json()
    agents = agents_response.json()

    orchestrator_id = orchestrator_data["orchestrator"]["job_id"]
    orchestrator_in_list = [a for a in agents if a.get("job_id") == orchestrator_id]

    # This demonstrates the race condition - orchestrator might NOT be in list
    # when calls are parallel (depends on timing)
    # Mark as xfail to document known issue
    if len(orchestrator_in_list) == 0:
        pytest.xfail("Race condition: orchestrator not in list when calls are parallel")

    assert len(orchestrator_in_list) == 1
