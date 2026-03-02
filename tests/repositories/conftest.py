"""
Shared fixtures for tests/repositories/ test modules.
"""

import random
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from src.giljo_mcp.models import Message, Project, Task
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.models.config import ApiMetrics
from src.giljo_mcp.repositories.statistics_repository import StatisticsRepository


@pytest.fixture
def stats_repo(db_manager):
    """Create StatisticsRepository instance"""
    return StatisticsRepository(db_manager)


@pytest_asyncio.fixture
async def test_project_with_data(db_session, test_tenant_key):
    """Create a test project with associated data"""
    project = Project(
        id="proj_001",
        tenant_key=test_tenant_key,
        name="Test Project",
        description="Project for statistics testing",
        mission="Test mission",
        status="active",
        series_number=random.randint(1, 999999),
        created_at=datetime.now(timezone.utc),
    )
    db_session.add(project)
    await db_session.commit()
    return project


@pytest_asyncio.fixture
async def test_api_metrics(db_session, test_tenant_key):
    """Create test API metrics"""
    metrics = ApiMetrics(
        tenant_key=test_tenant_key,
        total_api_calls=100,
        total_mcp_calls=50,
    )
    db_session.add(metrics)
    await db_session.commit()
    return metrics


@pytest_asyncio.fixture
async def test_messages(db_session, test_tenant_key, test_project_with_data):
    """Create test messages"""
    messages = []
    statuses = ["pending", "acknowledged", "completed", "failed"]
    for i, status in enumerate(statuses):
        msg = Message(
            id=f"msg_{i:03d}",
            tenant_key=test_tenant_key,
            project_id=test_project_with_data.id,
            # NOTE: from_agent removed in Handover 0116 - Agent model eliminated
            # Original statistics.py code references from_agent but model doesn't have it (BUG!)
            to_agents=["test_agent_2"],
            content=f"Test message {i}",
            message_type="direct",
            status=status,
            created_at=datetime.now(timezone.utc) - timedelta(hours=i),
        )
        db_session.add(msg)
        messages.append(msg)
    await db_session.commit()
    return messages


@pytest_asyncio.fixture
async def test_tasks(db_session, test_tenant_key, test_project_with_data):
    """Create test tasks"""
    tasks = []
    for i in range(5):
        task = Task(
            id=f"task_{i:03d}",
            tenant_key=test_tenant_key,
            project_id=test_project_with_data.id,
            title=f"Task {i}",
            description=f"Test task {i}",
            status="completed" if i < 3 else "pending",
            created_at=datetime.now(timezone.utc),
        )
        db_session.add(task)
        tasks.append(task)
    await db_session.commit()
    return tasks


@pytest_asyncio.fixture
async def test_agent_executions(db_session, test_tenant_key, test_project_with_data):
    """Create test agent executions"""
    # Create AgentJob first
    job = AgentJob(
        job_id="job_001",
        tenant_key=test_tenant_key,
        project_id=test_project_with_data.id,
        job_type="worker",
        mission="Test mission",
        status="active",
        created_at=datetime.now(timezone.utc),
        job_metadata={},
    )
    db_session.add(job)

    # Create AgentExecutions
    executions = []
    statuses = ["waiting", "working", "complete"]
    for i, status in enumerate(statuses):
        execution = AgentExecution(
            agent_id=f"agent_{i:03d}",
            job_id=job.job_id,
            tenant_key=test_tenant_key,
            agent_display_name="worker",
            agent_name=f"Test Agent {i}",
            status=status,
            progress=0,
            messages_sent_count=0,
            messages_waiting_count=0,
            messages_read_count=0,
            health_status="healthy",
            tool_type="universal",
        )
        db_session.add(execution)
        executions.append(execution)

    await db_session.commit()
    return job, executions
