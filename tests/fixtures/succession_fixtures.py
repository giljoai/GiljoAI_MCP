"""
Test fixtures for Orchestrator Succession Architecture (Handover 0080)

Provides reusable fixtures for testing orchestrator succession, handover workflows,
and multi-instance orchestrator management.
"""

import uuid
from datetime import datetime, timezone
from typing import Any

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from src.giljo_mcp.models import Project
from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution


class SuccessionTestData:
    """Test data generators for succession testing"""

    @staticmethod
    def generate_orchestrator_job_data(
        project_id: str,
        tenant_key: str,
        instance_number: int = 1,
        context_used: int = 0,
        context_budget: int = 150000,
        spawned_by: str | None = None,
        status: str = "waiting",
    ) -> dict[str, Any]:
        """Generate orchestrator job data for testing"""
        return {
            "job_id": str(uuid.uuid4()),  # UUID is exactly 36 chars, no prefix
            "tenant_key": tenant_key,
            "project_id": project_id,
            "agent_display_name": "orchestrator",
            "mission": f"Orchestrate project development - Instance {instance_number}",
            "status": status,
            "instance_number": instance_number,
            "context_used": context_used,
            "context_budget": context_budget,
            "spawned_by": spawned_by,
            "progress": 0,
            "tool_type": "universal",
            "agent_name": f"Orchestrator Instance {instance_number}",
            "messages": [],
            "context_chunks": [],
            "handover_context_refs": [],
        }

    @staticmethod
    def generate_handover_summary() -> dict[str, Any]:
        """Generate realistic handover summary for testing"""
        return {
            "project_status": "60% complete",
            "active_agents": [
                {"job_id": str(uuid.uuid4()), "type": "frontend-dev", "status": "working"},
                {"job_id": str(uuid.uuid4()), "type": "backend-api", "status": "waiting"},
            ],
            "completed_phases": ["requirements", "architecture", "database-schema"],
            "pending_decisions": [
                "API endpoint naming convention",
                "Authentication method selection",
            ],
            "critical_context_refs": [f"chunk-{i}" for i in range(1, 6)],
            "message_count": 42,
            "unresolved_blockers": [],
            "next_steps": "Implement API endpoints, then frontend integration",
            "token_estimate": 9500,  # Under 10K target
        }

    @staticmethod
    def generate_handover_message(from_job_id: str, to_job_id: str) -> dict[str, Any]:
        """Generate handover message for agent communication"""
        return {
            "type": "handover",
            "from": from_job_id,
            "to": to_job_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": SuccessionTestData.generate_handover_summary(),
        }


@pytest_asyncio.fixture(scope="function")
async def test_tenant_key() -> str:
    """Generate a unique tenant key for test isolation"""
    return f"tk_test_{uuid.uuid4().hex[:16]}"


@pytest_asyncio.fixture(scope="function")
async def orchestrator_at_90_percent(db_session: AsyncSession, test_project: Project, test_tenant_key: str):
    """
    Create an orchestrator job at 90% context usage.

    This simulates an orchestrator approaching context limits (manual succession scenario).
    Context: 135K/150K = 90%
    Note: Auto-succession removed in Handover 0461a - succession is now manual-only.
    """
    context_budget = 150000
    context_used = int(context_budget * 0.90)  # 135000 tokens

    job_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=1,
        context_used=context_used,
        context_budget=context_budget,
        status="working",
    )

    orchestrator = AgentExecution(**job_data)
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)

    return orchestrator


@pytest_asyncio.fixture(scope="function")
async def orchestrator_below_threshold(db_session: AsyncSession, test_project: Project, test_tenant_key: str):
    """
    Create an orchestrator job with moderate context usage.

    Context: 60K/150K = 40% - well within budget
    """
    context_budget = 150000
    context_used = int(context_budget * 0.40)  # 60000 tokens

    job_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=1,
        context_used=context_used,
        context_budget=context_budget,
        status="working",
    )

    orchestrator = AgentExecution(**job_data)
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)

    return orchestrator


@pytest_asyncio.fixture(scope="function")
async def orchestrator_over_100_percent(db_session: AsyncSession, test_project: Project, test_tenant_key: str):
    """
    Create an orchestrator job that exceeded 100% context budget.

    This simulates an edge case where context usage exceeded the budget.
    Context: 155K/150K = 103% - manual succession recommended
    """
    context_budget = 150000
    context_used = int(context_budget * 1.03)  # 154500 tokens

    job_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=1,
        context_used=context_used,
        context_budget=context_budget,
        status="working",
    )

    orchestrator = AgentExecution(**job_data)
    db_session.add(orchestrator)
    await db_session.commit()
    await db_session.refresh(orchestrator)

    return orchestrator


@pytest_asyncio.fixture(scope="function")
async def succession_chain_3_instances(db_session: AsyncSession, test_project: Project, test_tenant_key: str):
    """
    Create a pre-existing succession chain of 3 orchestrator instances.

    Instance 1: Complete (handed over to Instance 2)
    Instance 2: Complete (handed over to Instance 3)
    Instance 3: Working (current active)

    This tests multi-generational succession tracking.
    """
    # Instance 1 - Complete
    instance1_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=1,
        context_used=145000,
        context_budget=150000,
        status="complete",
    )
    instance1 = AgentExecution(**instance1_data)
    instance1.completed_at = datetime.now(timezone.utc)
    instance1.succession_reason = "context_limit"
    db_session.add(instance1)
    await db_session.flush()

    # Instance 2 - Complete (spawned by Instance 1)
    instance2_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=2,
        context_used=140000,
        context_budget=150000,
        spawned_by=instance1.job_id,
        status="complete",
    )
    instance2 = AgentExecution(**instance2_data)
    instance2.completed_at = datetime.now(timezone.utc)
    instance2.succession_reason = "context_limit"
    db_session.add(instance2)
    await db_session.flush()

    # Update Instance 1 with handover_to
    instance1.handover_to = instance2.job_id
    instance1.handover_summary = SuccessionTestData.generate_handover_summary()

    # Instance 3 - Working (spawned by Instance 2)
    instance3_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=test_tenant_key,
        instance_number=3,
        context_used=80000,
        context_budget=150000,
        spawned_by=instance2.job_id,
        status="working",
    )
    instance3 = AgentExecution(**instance3_data)
    db_session.add(instance3)
    await db_session.flush()

    # Update Instance 2 with handover_to
    instance2.handover_to = instance3.job_id
    instance2.handover_summary = SuccessionTestData.generate_handover_summary()

    await db_session.commit()
    await db_session.refresh(instance1)
    await db_session.refresh(instance2)
    await db_session.refresh(instance3)

    return {
        "instance1": instance1,
        "instance2": instance2,
        "instance3": instance3,
        "chain": [instance1, instance2, instance3],
    }


@pytest_asyncio.fixture(scope="function")
async def handover_summary_sample() -> dict[str, Any]:
    """Sample handover summary for testing validation and serialization"""
    return SuccessionTestData.generate_handover_summary()


@pytest_asyncio.fixture(scope="function")
async def multi_tenant_orchestrators(db_session: AsyncSession, test_project: Project):
    """
    Create orchestrators for two different tenants to test isolation.

    Returns:
        dict with tenant_a and tenant_b orchestrators
    """
    tenant_a_key = f"tk_tenant_a_{uuid.uuid4().hex[:8]}"
    tenant_b_key = f"tk_tenant_b_{uuid.uuid4().hex[:8]}"

    # Tenant A - Orchestrator at 90%
    orch_a_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=tenant_a_key,
        instance_number=1,
        context_used=135000,
        context_budget=150000,
        status="working",
    )
    orchestrator_a = AgentExecution(**orch_a_data)
    db_session.add(orchestrator_a)

    # Tenant B - Orchestrator at 50%
    orch_b_data = SuccessionTestData.generate_orchestrator_job_data(
        project_id=test_project.id,
        tenant_key=tenant_b_key,
        instance_number=1,
        context_used=75000,
        context_budget=150000,
        status="working",
    )
    orchestrator_b = AgentExecution(**orch_b_data)
    db_session.add(orchestrator_b)

    await db_session.commit()
    await db_session.refresh(orchestrator_a)
    await db_session.refresh(orchestrator_b)

    return {
        "tenant_a": {"tenant_key": tenant_a_key, "orchestrator": orchestrator_a},
        "tenant_b": {"tenant_key": tenant_b_key, "orchestrator": orchestrator_b},
    }


@pytest.fixture
def succession_reason_values() -> list[str]:
    """Valid succession reason enum values"""
    return ["context_limit", "manual", "phase_transition"]


@pytest.fixture
def orchestrator_status_values() -> list[str]:
    """Valid orchestrator status values"""
    return ["waiting", "preparing", "working", "review", "complete", "failed", "blocked"]
