"""
Unit tests for Agent Health Monitoring System.
Following TDD: Tests written BEFORE implementation.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.giljo_mcp.models import Product, Project
from src.giljo_mcp.models.agent_identity import AgentExecution, AgentJob
from src.giljo_mcp.monitoring.agent_health_monitor import AgentHealthMonitor
from src.giljo_mcp.monitoring.health_config import AgentHealthStatus, HealthCheckConfig


class TestHealthCheckConfig:
    """Test health configuration dataclass."""

    def test_default_configuration(self):
        """Test default configuration values."""
        config = HealthCheckConfig()

        assert config.waiting_timeout_minutes == 2
        assert config.active_no_progress_minutes == 5
        assert config.heartbeat_timeout_minutes == 10
        assert config.scan_interval_seconds == 300
        assert config.auto_fail_on_timeout is False
        assert config.notify_orchestrator is True

    def test_agent_display_name_timeout_overrides(self):
        """Test agent-type-specific timeout overrides."""
        config = HealthCheckConfig()

        assert config.get_timeout_for_agent("orchestrator") == 15
        assert config.get_timeout_for_agent("implementer") == 10
        assert config.get_timeout_for_agent("tester") == 8
        assert config.get_timeout_for_agent("reviewer") == 6
        assert config.get_timeout_for_agent("documenter") == 5
        assert config.get_timeout_for_agent("analyzer") == 5

    def test_default_timeout_for_unknown_agent(self):
        """Test fallback to default timeout for unknown agent types."""
        config = HealthCheckConfig()

        # Unknown agent type should use heartbeat_timeout_minutes
        assert config.get_timeout_for_agent("unknown_agent") == 10

    def test_custom_configuration(self):
        """Test custom configuration values."""
        config = HealthCheckConfig(
            waiting_timeout_minutes=5,
            active_no_progress_minutes=10,
            heartbeat_timeout_minutes=20,
            scan_interval_seconds=600,
            auto_fail_on_timeout=True,
            notify_orchestrator=False,
            timeout_overrides={"custom_agent": 30},
        )

        assert config.waiting_timeout_minutes == 5
        assert config.scan_interval_seconds == 600
        assert config.auto_fail_on_timeout is True
        assert config.notify_orchestrator is False
        assert config.get_timeout_for_agent("custom_agent") == 30


class TestAgentHealthStatus:
    """Test health status dataclass."""

    def test_health_status_creation(self):
        """Test creating health status object."""
        now = datetime.now(timezone.utc)

        status = AgentHealthStatus(
            job_id="test-job-1",
            agent_id="agent-uuid-1",
            agent_display_name="implementer",
            current_status="working",
            health_state="warning",
            last_update=now,
            minutes_since_update=6.5,
            issue_description="No progress for 6.5 minutes",
            recommended_action="Check agent logs",
        )

        assert status.job_id == "test-job-1"
        assert status.agent_display_name == "implementer"
        assert status.current_status == "working"
        assert status.health_state == "warning"
        assert status.last_update == now
        assert status.minutes_since_update == 6.5
        assert "6.5 minutes" in status.issue_description
        assert "Check agent logs" in status.recommended_action


@pytest.mark.asyncio
class TestAgentHealthMonitor:
    """Test agent health monitoring system."""

    @pytest.fixture
    def mock_db_manager(self):
        """Mock database manager."""
        db_manager = MagicMock()
        db_manager.get_session = AsyncMock()
        return db_manager

    @pytest.fixture
    def mock_ws_manager(self):
        """Mock WebSocket manager."""
        ws_manager = MagicMock()
        ws_manager.broadcast_health_alert = AsyncMock()
        ws_manager.broadcast_agent_auto_failed = AsyncMock()
        return ws_manager

    @pytest.fixture
    def test_config(self):
        """Test configuration with short intervals."""
        return HealthCheckConfig(
            waiting_timeout_minutes=2,
            active_no_progress_minutes=5,
            heartbeat_timeout_minutes=10,
            scan_interval_seconds=1,  # Fast for testing
            auto_fail_on_timeout=False,
        )

    @pytest.fixture
    async def monitor(self, mock_db_manager, mock_ws_manager, test_config):
        """Create health monitor instance."""
        return AgentHealthMonitor(mock_db_manager, mock_ws_manager, test_config)

    async def create_test_data(
        self,
        session,
        job_id: str,
        tenant_key: str,
        status: str,
        agent_display_name: str = "implementer",
        created_at=None,
        started_at=None,
        updated_at=None,
        last_progress_at=None,
        last_message_check_at=None,
        job_metadata=None,
        project_status: str = "active",
    ):
        """Create test data with proper hierarchy. Handover 0424."""
        # Create Product (use job_id to ensure uniqueness across multiple calls)
        product = Product(id=f"prod-{job_id}", tenant_key=tenant_key, name="Test Product", description="Test")
        session.add(product)
        await session.flush()

        # Create Project
        project = Project(
            id=f"proj-{job_id}",
            tenant_key=tenant_key,
            product_id=product.id,
            name="Test Project",
            description="Test",
            mission="Test mission",
            status=project_status,
            deleted_at=None,
        )
        session.add(project)
        await session.flush()

        # Create AgentJob
        job = AgentJob(
            job_id=job_id,
            tenant_key=tenant_key,
            project_id=project.id,
            mission="Test mission",
            job_type=agent_display_name,
            created_at=created_at or datetime.now(timezone.utc),
        )
        session.add(job)
        await session.flush()

        # Create AgentExecution
        execution = AgentExecution(
            job_id=job_id,
            tenant_key=tenant_key,
            agent_display_name=agent_display_name,
            status=status,
            started_at=started_at,
            last_progress_at=last_progress_at,
            last_message_check_at=last_message_check_at,
        )
        execution.job = job  # Set relationship
        session.add(execution)
        await session.commit()

        return execution

    async def test_monitor_initialization(self, monitor, test_config):
        """Test monitor initializes correctly."""
        assert monitor.running is False
        assert monitor._task is None
        assert monitor.config == test_config

    async def test_start_monitoring(self, monitor):
        """Test starting background monitoring loop."""
        await monitor.start()

        assert monitor.running is True
        assert monitor._task is not None
        assert not monitor._task.done()

        # Clean up
        await monitor.stop()

    async def test_start_monitoring_already_running(self, monitor):
        """Test starting monitor when already running logs warning."""
        await monitor.start()

        # Try to start again
        with patch("src.giljo_mcp.monitoring.agent_health_monitor.logger") as mock_logger:
            await monitor.start()
            mock_logger.warning.assert_called_once()

        await monitor.stop()

    async def test_stop_monitoring(self, monitor):
        """Test stopping monitoring gracefully."""
        await monitor.start()
        await asyncio.sleep(0.1)

        await monitor.stop()

        assert monitor.running is False
        assert monitor._task.cancelled() or monitor._task.done()

    async def test_stop_monitoring_not_running(self, monitor):
        """Test stopping monitor when not running."""
        # Should not raise error
        await monitor.stop()
        assert monitor.running is False

    async def test_detect_waiting_timeout(self, monitor, db_session):
        """Test detection of jobs stuck in waiting state."""
        session = db_session
        await self.create_test_data(
            session,
            job_id="test-job-waiting-1",
            tenant_key="test-tenant",
            status="waiting",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=3),
        )

        unhealthy = await monitor._detect_waiting_timeouts(session, "test-tenant")

        assert len(unhealthy) == 1
        assert unhealthy[0].job_id == "test-job-waiting-1"
        assert unhealthy[0].health_state == "critical"
        assert "never acknowledged" in unhealthy[0].issue_description.lower()
        assert unhealthy[0].minutes_since_update >= 2

    async def test_no_waiting_timeout_for_recent_jobs(self, monitor, db_session):
        """Test recent waiting jobs are not flagged."""
        session = db_session
        await self.create_test_data(
            session,
            job_id="test-job-waiting-2",
            tenant_key="test-tenant",
            status="waiting",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
        )

        unhealthy = await monitor._detect_waiting_timeouts(session, "test-tenant")

        assert len(unhealthy) == 0

    async def test_detect_stalled_job_warning(self, monitor, db_session):
        """Test detection of active jobs without progress (warning state)."""
        session = db_session
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=6)
        await self.create_test_data(
            session,
            job_id="test-job-stalled-1",
            tenant_key="test-tenant",
            status="working",
            created_at=stale_time - timedelta(minutes=1),
            started_at=stale_time,
            updated_at=stale_time,
            last_progress_at=stale_time,
        )

        unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

        assert len(unhealthy) == 1
        assert unhealthy[0].job_id == "test-job-stalled-1"
        assert unhealthy[0].health_state in ["warning", "critical"]
        assert unhealthy[0].minutes_since_update >= 5
        assert "no progress" in unhealthy[0].issue_description.lower()

    async def test_detect_stalled_job_critical(self, monitor, db_session):
        """Test detection of active jobs without progress (critical state)."""
        session = db_session
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=8)
        await self.create_test_data(
            session,
            job_id="test-job-stalled-2",
            tenant_key="test-tenant",
            status="working",
            created_at=stale_time - timedelta(minutes=1),
            started_at=stale_time,
            updated_at=stale_time,
            last_progress_at=stale_time,
        )

        unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

        assert len(unhealthy) == 1
        assert unhealthy[0].health_state == "critical"

    async def test_detect_stalled_job_timeout(self, monitor, db_session):
        """Test detection of active jobs without progress (timeout state)."""
        session = db_session
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=12)
        await self.create_test_data(
            session,
            job_id="test-job-stalled-3",
            tenant_key="test-tenant",
            status="working",
            created_at=stale_time - timedelta(minutes=1),
            started_at=stale_time,
            updated_at=stale_time,
            last_progress_at=stale_time,
        )

        unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

        assert len(unhealthy) == 1
        assert unhealthy[0].health_state == "timeout"

    async def test_no_stalled_detection_for_active_jobs(self, monitor, db_session):
        """Test active jobs with recent progress are not flagged."""
        session = db_session
        recent_time = datetime.now(timezone.utc) - timedelta(minutes=2)
        await self.create_test_data(
            session,
            job_id="test-job-active-healthy",
            tenant_key="test-tenant",
            status="working",
            created_at=recent_time - timedelta(minutes=1),
            started_at=recent_time,
            updated_at=recent_time,
            last_progress_at=recent_time,
        )

        unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

        assert len(unhealthy) == 0

    async def test_agent_display_name_specific_timeouts(self, monitor, db_session):
        """Test orchestrators get longer timeout than other agents."""
        session = db_session
        silent_time = datetime.now(timezone.utc) - timedelta(minutes=12)

        await self.create_test_data(
            session,
            job_id="orch-1",
            tenant_key="test-tenant",
            status="working",
            agent_display_name="orchestrator",
            created_at=silent_time - timedelta(minutes=1),
            started_at=silent_time,
            updated_at=silent_time,
            last_progress_at=silent_time,
        )

        await self.create_test_data(
            session,
            job_id="impl-1",
            tenant_key="test-tenant",
            status="working",
            agent_display_name="implementer",
            created_at=silent_time - timedelta(minutes=1),
            started_at=silent_time,
            updated_at=silent_time,
            last_progress_at=silent_time,
        )

        unhealthy = await monitor._detect_heartbeat_failures(session, "test-tenant")

        unhealthy_ids = [h.job_id for h in unhealthy]
        assert "impl-1" in unhealthy_ids
        assert "orch-1" not in unhealthy_ids

    async def test_detect_heartbeat_failure(self, monitor, db_session):
        """Test detection of jobs with extended silence."""
        session = db_session
        silent_time = datetime.now(timezone.utc) - timedelta(minutes=15)
        await self.create_test_data(
            session,
            job_id="test-job-silent-1",
            tenant_key="test-tenant",
            status="working",
            created_at=silent_time - timedelta(minutes=1),
            started_at=silent_time,
            updated_at=silent_time,
        )

        unhealthy = await monitor._detect_heartbeat_failures(session, "test-tenant")

        assert len(unhealthy) == 1
        assert unhealthy[0].job_id == "test-job-silent-1"
        assert unhealthy[0].health_state == "timeout"
        assert "silence" in unhealthy[0].issue_description.lower()
        assert unhealthy[0].minutes_since_update >= 10

    async def test_get_last_progress_time_from_metadata(self, monitor):
        """Test extracting last progress time from job metadata."""
        progress_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        mock_job = AgentJob(
            job_id="test-job-1",
            tenant_key="test-tenant",
            mission="Test mission",
            job_type="implementer",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )

        execution = AgentExecution(
            job_id="test-job-1",
            tenant_key="test-tenant",
            agent_display_name="implementer",
            status="working",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            last_progress_at=progress_time,
        )
        execution.job = mock_job

        result = monitor._get_last_progress_time(execution)

        assert result == progress_time

    async def test_get_last_progress_time_fallback(self, monitor):
        """Test fallback to started_at when no progress metadata."""
        started_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        mock_job = AgentJob(
            job_id="test-job-2",
            tenant_key="test-tenant",
            mission="Test mission",
            job_type="implementer",
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
        )

        execution = AgentExecution(
            job_id="test-job-2",
            tenant_key="test-tenant",
            agent_display_name="implementer",
            status="working",
            started_at=started_time,
            last_progress_at=None,
        )
        execution.job = mock_job

        result = monitor._get_last_progress_time(execution)

        assert result == started_time

    async def test_get_last_activity_time(self, monitor):
        """Test getting most recent activity timestamp."""
        now = datetime.now(timezone.utc)

        mock_job = AgentJob(
            job_id="test-job-3",
            tenant_key="test-tenant",
            mission="Test mission",
            job_type="implementer",
            created_at=now - timedelta(minutes=10),
        )

        execution = AgentExecution(
            job_id="test-job-3",
            tenant_key="test-tenant",
            agent_display_name="implementer",
            status="working",
            started_at=now - timedelta(minutes=8),
            last_progress_at=now - timedelta(minutes=5),
            last_message_check_at=now - timedelta(minutes=6),
        )
        execution.job = mock_job

        result = monitor._get_last_activity_time(execution)

        # Should return the most recent timestamp (last_progress_at is 5 minutes ago, most recent)
        assert result == execution.last_progress_at

    async def test_handle_unhealthy_job_warning(self, monitor, mock_ws_manager, db_session):
        """Test handling unhealthy job in warning state."""
        session = db_session
        execution = await self.create_test_data(
            session, job_id="test-job-warning", tenant_key="test-tenant", status="working"
        )

        health_status = AgentHealthStatus(
            job_id="test-job-warning",
            agent_id=execution.agent_id,
            agent_display_name="implementer",
            current_status="working",
            health_state="warning",
            last_update=datetime.now(timezone.utc) - timedelta(minutes=6),
            minutes_since_update=6.0,
            issue_description="No progress for 6 minutes",
            recommended_action="Check agent logs",
        )

        monitor.ws = mock_ws_manager

        await monitor._handle_unhealthy_job(session, health_status, "test-tenant")

        await session.refresh(execution)
        assert execution.health_status == "warning"
        assert execution.health_failure_count == 1
        assert execution.last_health_check is not None
        assert execution.status == "working"

        mock_ws_manager.broadcast_health_alert.assert_called_once()

    async def test_handle_unhealthy_job_timeout_no_auto_fail(self, monitor, mock_ws_manager, db_session):
        """Test handling timeout without auto-fail enabled."""
        session = db_session
        monitor.config.auto_fail_on_timeout = False

        execution = await self.create_test_data(
            session, job_id="test-job-timeout-1", tenant_key="test-tenant", status="working"
        )

        health_status = AgentHealthStatus(
            job_id="test-job-timeout-1",
            agent_id=execution.agent_id,
            agent_display_name="implementer",
            current_status="working",
            health_state="timeout",
            last_update=datetime.now(timezone.utc) - timedelta(minutes=15),
            minutes_since_update=15.0,
            issue_description="Timeout",
            recommended_action="Manual intervention",
        )

        monitor.ws = mock_ws_manager

        await monitor._handle_unhealthy_job(session, health_status, "test-tenant")

        await session.refresh(execution)
        assert execution.health_status == "timeout"
        assert execution.status == "working"
        assert execution.completed_at is None

        mock_ws_manager.broadcast_health_alert.assert_called_once()
        mock_ws_manager.broadcast_agent_auto_failed.assert_not_called()

    async def test_auto_fail_on_timeout(self, monitor, mock_ws_manager, db_session):
        """Test auto-fail when configured."""
        session = db_session
        monitor.config.auto_fail_on_timeout = True

        execution = await self.create_test_data(
            session,
            job_id="timeout-job",
            tenant_key="test-tenant",
            status="working",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=15),
        )

        health_status = AgentHealthStatus(
            job_id="timeout-job",
            agent_id=execution.agent_id,
            agent_display_name="implementer",
            current_status="working",
            health_state="timeout",
            last_update=execution.started_at,
            minutes_since_update=15.0,
            issue_description="Complete silence for 15 minutes",
            recommended_action="Auto-fail",
        )

        monitor.ws = mock_ws_manager

        await monitor._handle_unhealthy_job(session, health_status, "test-tenant")

        await session.refresh(execution)
        assert execution.status == "failed"
        assert execution.completed_at is not None
        assert "Auto-failed" in execution.result_summary
        assert "Complete silence" in execution.result_summary

        mock_ws_manager.broadcast_agent_auto_failed.assert_called_once()
        call_args = mock_ws_manager.broadcast_agent_auto_failed.call_args
        assert call_args[1]["tenant_key"] == "test-tenant"
        assert call_args[1]["job_id"] == "timeout-job"

    async def test_multi_tenant_isolation(self, monitor, db_session):
        """Test health checks respect tenant boundaries."""
        session = db_session
        stale_time = datetime.now(timezone.utc) - timedelta(minutes=6)

        await self.create_test_data(
            session,
            job_id="job-tenant-a",
            tenant_key="tenant-a",
            status="working",
            created_at=stale_time,
            started_at=stale_time,
            updated_at=stale_time,
            last_progress_at=stale_time,
        )

        await self.create_test_data(
            session,
            job_id="job-tenant-b",
            tenant_key="tenant-b",
            status="working",
            created_at=stale_time,
            started_at=stale_time,
            updated_at=stale_time,
            last_progress_at=stale_time,
        )

        unhealthy_a = await monitor._detect_stalled_jobs(session, "tenant-a")

        assert len(unhealthy_a) == 1
        assert unhealthy_a[0].job_id == "job-tenant-a"

        unhealthy_b = await monitor._detect_stalled_jobs(session, "tenant-b")

        assert len(unhealthy_b) == 1
        assert unhealthy_b[0].job_id == "job-tenant-b"

    async def test_monitoring_loop_error_recovery(self, monitor):
        """Test monitoring loop continues after errors."""
        # Mock run_health_check_cycle to fail once, then succeed
        call_count = 0

        async def mock_check_cycle():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Simulated error")
            # Second call succeeds silently

        monitor._run_health_check_cycle = mock_check_cycle

        # Start monitor
        await monitor.start()

        # Wait for at least 2 cycles
        await asyncio.sleep(2.5)

        # Monitor should still be running
        assert monitor.running is True
        assert call_count >= 2  # Should have recovered and continued

        await monitor.stop()

    async def test_get_all_tenants(self, monitor, db_session):
        """Test retrieving all unique tenant keys."""
        session = db_session

        for i in range(6):
            await self.create_test_data(session, job_id=f"job-{i}", tenant_key=f"tenant-{i % 3}", status="working")

        tenants = await monitor._get_all_tenants(session)

        # Check that our test tenants are included (may have others from previous tests)
        tenant_set = set(tenants)
        assert "tenant-0" in tenant_set
        assert "tenant-1" in tenant_set
        assert "tenant-2" in tenant_set

    async def test_scan_tenant_jobs_combines_all_detections(self, monitor, db_session):
        """Test scan combines waiting, stalled, and heartbeat detections."""
        session = db_session
        now = datetime.now(timezone.utc)

        await self.create_test_data(
            session,
            job_id="waiting-timeout",
            tenant_key="test-tenant",
            status="waiting",
            created_at=now - timedelta(minutes=3),
            updated_at=now - timedelta(minutes=3),
        )

        await self.create_test_data(
            session,
            job_id="stalled-job",
            tenant_key="test-tenant",
            status="working",
            created_at=now - timedelta(minutes=7),
            started_at=now - timedelta(minutes=6),
            updated_at=now - timedelta(minutes=6),
            last_progress_at=now - timedelta(minutes=6),
        )

        await self.create_test_data(
            session,
            job_id="heartbeat-fail",
            tenant_key="test-tenant",
            status="working",
            agent_display_name="tester",
            created_at=now - timedelta(minutes=13),
            started_at=now - timedelta(minutes=12),
            updated_at=now - timedelta(minutes=12),
            last_progress_at=now - timedelta(minutes=12),
        )

        unhealthy = await monitor._scan_tenant_jobs(session, "test-tenant")

        assert len(unhealthy) >= 3
        job_ids = {h.job_id for h in unhealthy}
        assert "waiting-timeout" in job_ids
        assert "stalled-job" in job_ids
        assert "heartbeat-fail" in job_ids
