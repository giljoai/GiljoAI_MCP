"""
Test mission_acknowledged_at tracking in AgentJobManager (Handover 0233)
"""
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import pytest

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.giljo_mcp.agent_job_manager import AgentJobManager
from src.giljo_mcp.database import DatabaseManager
from tests.helpers.test_db_helper import PostgreSQLTestHelper


@pytest.fixture
def db_manager():
    """Create a synchronous database manager for testing."""
    manager = DatabaseManager(PostgreSQLTestHelper.get_test_db_url(async_driver=False))
    manager.create_tables()
    yield manager
    manager.close()


@pytest.fixture
def db_session(db_manager):
    """Get a database session for testing."""
    with db_manager.get_session() as session:
        yield session


def test_status_transition_to_working_sets_mission_acknowledged_at(db_session, db_manager):
    """Test that transitioning to 'working' status sets mission_acknowledged_at"""
    tenant_key = str(uuid4())
    manager = AgentJobManager(db_manager)

    # Create job in 'waiting' status
    job = manager.create_job(
        tenant_key=tenant_key,
        agent_display_name="implementer",
        mission="Test mission",
    )

    assert job.mission_acknowledged_at is None
    assert job.status == "waiting"

    # Transition to 'working' status
    updated_job = manager.update_job_status(
        tenant_key=tenant_key,
        job_id=job.job_id,
        status="working"
    )

    # Verify mission_acknowledged_at is set
    assert updated_job.mission_acknowledged_at is not None
    assert isinstance(updated_job.mission_acknowledged_at, datetime)


def test_mission_acknowledged_at_only_set_once(db_session, db_manager):
    """Test that mission_acknowledged_at is only set on FIRST transition to working"""
    tenant_key = str(uuid4())
    manager = AgentJobManager(db_manager)

    # Create and transition to working
    job = manager.create_job(
        tenant_key=tenant_key,
        agent_display_name="implementer",
        mission="Test mission",
    )

    job = manager.update_job_status(
        tenant_key=tenant_key,
        job_id=job.job_id,
        status="working"
    )

    first_ack_time = job.mission_acknowledged_at
    assert first_ack_time is not None

    # Transition to 'blocked' then back to 'working'
    manager.update_job_status(
        tenant_key=tenant_key,
        job_id=job.job_id,
        status="blocked"
    )

    job = manager.update_job_status(
        tenant_key=tenant_key,
        job_id=job.job_id,
        status="working"
    )

    # Verify timestamp UNCHANGED (idempotent)
    assert job.mission_acknowledged_at == first_ack_time


def test_other_status_transitions_dont_set_mission_acknowledged_at(db_session, db_manager):
    """Test that non-'working' status transitions don't set mission_acknowledged_at"""
    tenant_key = str(uuid4())
    manager = AgentJobManager(db_manager)

    job = manager.create_job(
        tenant_key=tenant_key,
        agent_display_name="implementer",
        mission="Test mission",
    )

    assert job.mission_acknowledged_at is None

    # Transition to 'failed' (not 'working')
    updated_job = manager.update_job_status(
        tenant_key=tenant_key,
        job_id=job.job_id,
        status="failed"
    )

    # Verify mission_acknowledged_at is still None
    assert updated_job.mission_acknowledged_at is None
