"""
Unit tests for Agent Health Monitoring System.
Following TDD: Tests written BEFORE implementation.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.monitoring.agent_health_monitor import AgentHealthMonitor
from src.giljo_mcp.monitoring.health_config import (
    HealthCheckConfig,
    AgentHealthStatus
)


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

    def test_agent_type_timeout_overrides(self):
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
            timeout_overrides={"custom_agent": 30}
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
            agent_type="implementer",
            current_status="active",
            health_state="warning",
            last_update=now,
            minutes_since_update=6.5,
            issue_description="No progress for 6.5 minutes",
            recommended_action="Check agent logs"
        )

        assert status.job_id == "test-job-1"
        assert status.agent_type == "implementer"
        assert status.current_status == "active"
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
            auto_fail_on_timeout=False
        )

    @pytest.fixture
    async def monitor(self, mock_db_manager, mock_ws_manager, test_config):
        """Create health monitor instance."""
        return AgentHealthMonitor(mock_db_manager, mock_ws_manager, test_config)

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

    async def test_detect_waiting_timeout(self, monitor):
        """Test detection of jobs stuck in waiting state."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job 3 minutes ago in 'waiting' state
            job = AgentExecution(
                job_id="test-job-waiting-1",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="waiting",
                mission="Test mission",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=3),
                updated_at=datetime.now(timezone.utc) - timedelta(minutes=3)
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_waiting_timeouts(session, "test-tenant")

            assert len(unhealthy) == 1
            assert unhealthy[0].job_id == "test-job-waiting-1"
            assert unhealthy[0].health_state == "critical"
            assert "never acknowledged" in unhealthy[0].issue_description.lower()
            assert unhealthy[0].minutes_since_update >= 2

    async def test_no_waiting_timeout_for_recent_jobs(self, monitor):
        """Test recent waiting jobs are not flagged."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job 1 minute ago (below threshold)
            job = AgentExecution(
                job_id="test-job-waiting-2",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="waiting",
                mission="Test mission",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                updated_at=datetime.now(timezone.utc) - timedelta(minutes=1)
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_waiting_timeouts(session, "test-tenant")

            assert len(unhealthy) == 0

    async def test_detect_stalled_job_warning(self, monitor):
        """Test detection of active jobs without progress (warning state)."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create active job with stale progress (6 minutes)
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=6)
            job = AgentExecution(
                job_id="test-job-stalled-1",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=stale_time,
                created_at=stale_time - timedelta(minutes=1),
                updated_at=stale_time,
                job_metadata={"last_progress_update": stale_time.isoformat()}
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

            assert len(unhealthy) == 1
            assert unhealthy[0].job_id == "test-job-stalled-1"
            assert unhealthy[0].health_state in ["warning", "critical"]
            assert unhealthy[0].minutes_since_update >= 5
            assert "no progress" in unhealthy[0].issue_description.lower()

    async def test_detect_stalled_job_critical(self, monitor):
        """Test detection of active jobs without progress (critical state)."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create active job with very stale progress (8 minutes)
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=8)
            job = AgentExecution(
                job_id="test-job-stalled-2",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=stale_time,
                created_at=stale_time - timedelta(minutes=1),
                updated_at=stale_time,
                job_metadata={"last_progress_update": stale_time.isoformat()}
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

            assert len(unhealthy) == 1
            assert unhealthy[0].health_state == "critical"

    async def test_detect_stalled_job_timeout(self, monitor):
        """Test detection of active jobs without progress (timeout state)."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create active job with extremely stale progress (12 minutes)
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=12)
            job = AgentExecution(
                job_id="test-job-stalled-3",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=stale_time,
                created_at=stale_time - timedelta(minutes=1),
                updated_at=stale_time,
                job_metadata={"last_progress_update": stale_time.isoformat()}
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

            assert len(unhealthy) == 1
            assert unhealthy[0].health_state == "timeout"

    async def test_no_stalled_detection_for_active_jobs(self, monitor):
        """Test active jobs with recent progress are not flagged."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create active job with recent progress
            recent_time = datetime.now(timezone.utc) - timedelta(minutes=2)
            job = AgentExecution(
                job_id="test-job-active-healthy",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=recent_time,
                created_at=recent_time - timedelta(minutes=1),
                updated_at=recent_time,
                job_metadata={"last_progress_update": recent_time.isoformat()}
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_stalled_jobs(session, "test-tenant")

            assert len(unhealthy) == 0

    async def test_agent_type_specific_timeouts(self, monitor):
        """Test orchestrators get longer timeout than other agents."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            silent_time = datetime.now(timezone.utc) - timedelta(minutes=12)

            # Create orchestrator job silent for 12 minutes
            orch_job = AgentExecution(
                job_id="orch-1",
                tenant_key="test-tenant",
                agent_type="orchestrator",
                status="active",
                mission="Test mission",
                started_at=silent_time,
                created_at=silent_time - timedelta(minutes=1),
                updated_at=silent_time,
                job_metadata={"last_progress_update": silent_time.isoformat()}
            )

            # Create implementer job silent for 12 minutes
            impl_job = AgentExecution(
                job_id="impl-1",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=silent_time,
                created_at=silent_time - timedelta(minutes=1),
                updated_at=silent_time,
                job_metadata={"last_progress_update": silent_time.isoformat()}
            )

            session.add_all([orch_job, impl_job])
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_heartbeat_failures(session, "test-tenant")

            # Orchestrator gets 15min timeout - should NOT be unhealthy
            # Implementer gets 10min timeout - SHOULD be unhealthy
            unhealthy_ids = [h.job_id for h in unhealthy]
            assert "impl-1" in unhealthy_ids
            assert "orch-1" not in unhealthy_ids  # Still within 15min timeout

    async def test_detect_heartbeat_failure(self, monitor):
        """Test detection of jobs with extended silence."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job silent for 15 minutes (exceeds 10min timeout)
            silent_time = datetime.now(timezone.utc) - timedelta(minutes=15)
            job = AgentExecution(
                job_id="test-job-silent-1",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=silent_time,
                created_at=silent_time - timedelta(minutes=1),
                updated_at=silent_time,
                job_metadata={}
            )
            session.add(job)
            await session.commit()

            # Run detection
            unhealthy = await monitor._detect_heartbeat_failures(session, "test-tenant")

            assert len(unhealthy) == 1
            assert unhealthy[0].job_id == "test-job-silent-1"
            assert unhealthy[0].health_state == "timeout"
            assert "silence" in unhealthy[0].issue_description.lower()
            assert unhealthy[0].minutes_since_update >= 10

    async def test_get_last_progress_time_from_metadata(self, monitor):
        """Test extracting last progress time from job metadata."""
        progress_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        job = AgentExecution(
            job_id="test-job-1",
            tenant_key="test-tenant",
            agent_type="implementer",
            status="active",
            mission="Test mission",
            started_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            job_metadata={"last_progress_update": progress_time.isoformat()}
        )

        result = monitor._get_last_progress_time(job)

        # Allow small difference due to ISO parsing
        assert abs((result - progress_time).total_seconds()) < 1

    async def test_get_last_progress_time_fallback(self, monitor):
        """Test fallback to started_at when no progress metadata."""
        started_time = datetime.now(timezone.utc) - timedelta(minutes=5)

        job = AgentExecution(
            job_id="test-job-2",
            tenant_key="test-tenant",
            agent_type="implementer",
            status="active",
            mission="Test mission",
            started_at=started_time,
            created_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            updated_at=datetime.now(timezone.utc) - timedelta(minutes=10),
            job_metadata={}
        )

        result = monitor._get_last_progress_time(job)

        assert result == started_time

    async def test_get_last_activity_time(self, monitor):
        """Test getting most recent activity timestamp."""
        now = datetime.now(timezone.utc)

        job = AgentExecution(
            job_id="test-job-3",
            tenant_key="test-tenant",
            agent_type="implementer",
            status="active",
            mission="Test mission",
            created_at=now - timedelta(minutes=10),
            started_at=now - timedelta(minutes=8),
            updated_at=now - timedelta(minutes=2),  # Most recent
            job_metadata={"last_progress_update": (now - timedelta(minutes=5)).isoformat()}
        )

        result = monitor._get_last_activity_time(job)

        # Should return updated_at as most recent
        assert result == job.updated_at

    async def test_handle_unhealthy_job_warning(self, monitor, mock_ws_manager):
        """Test handling unhealthy job in warning state."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job
            job = AgentExecution(
                job_id="test-job-warning",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Create health status
            health_status = AgentHealthStatus(
                job_id="test-job-warning",
                agent_type="implementer",
                current_status="active",
                health_state="warning",
                last_update=datetime.now(timezone.utc) - timedelta(minutes=6),
                minutes_since_update=6.0,
                issue_description="No progress for 6 minutes",
                recommended_action="Check agent logs"
            )

            # Override monitor's ws_manager with mock
            monitor.ws = mock_ws_manager

            # Handle unhealthy job
            await monitor._handle_unhealthy_job(session, health_status, "test-tenant")

            # Verify job updated
            await session.refresh(job)
            assert job.health_status == "warning"
            assert job.health_failure_count == 1
            assert job.last_health_check is not None
            assert job.status == "active"  # Not auto-failed

            # Verify WebSocket broadcast
            mock_ws_manager.broadcast_health_alert.assert_called_once()

    async def test_handle_unhealthy_job_timeout_no_auto_fail(self, monitor, mock_ws_manager):
        """Test handling timeout without auto-fail enabled."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Ensure auto-fail is disabled
            monitor.config.auto_fail_on_timeout = False

            # Create job
            job = AgentExecution(
                job_id="test-job-timeout-1",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Create health status
            health_status = AgentHealthStatus(
                job_id="test-job-timeout-1",
                agent_type="implementer",
                current_status="active",
                health_state="timeout",
                last_update=datetime.now(timezone.utc) - timedelta(minutes=15),
                minutes_since_update=15.0,
                issue_description="Timeout",
                recommended_action="Manual intervention"
            )

            # Override monitor's ws_manager with mock
            monitor.ws = mock_ws_manager

            # Handle unhealthy job
            await monitor._handle_unhealthy_job(session, health_status, "test-tenant")

            # Verify job NOT auto-failed
            await session.refresh(job)
            assert job.health_status == "timeout"
            assert job.status == "active"  # Still active
            assert job.completed_at is None

            # Verify health alert sent (not auto-fail)
            mock_ws_manager.broadcast_health_alert.assert_called_once()
            mock_ws_manager.broadcast_agent_auto_failed.assert_not_called()

    async def test_auto_fail_on_timeout(self, monitor, mock_ws_manager):
        """Test auto-fail when configured."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Enable auto-fail
            monitor.config.auto_fail_on_timeout = True

            # Create timed-out job
            job = AgentExecution(
                job_id="timeout-job",
                tenant_key="test-tenant",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=datetime.now(timezone.utc) - timedelta(minutes=15),
                created_at=datetime.now(timezone.utc) - timedelta(minutes=16),
                updated_at=datetime.now(timezone.utc) - timedelta(minutes=15),
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Create health status
            health_status = AgentHealthStatus(
                job_id="timeout-job",
                agent_type="implementer",
                current_status="active",
                health_state="timeout",
                last_update=job.started_at,
                minutes_since_update=15.0,
                issue_description="Complete silence for 15 minutes",
                recommended_action="Auto-fail"
            )

            # Override monitor's ws_manager with mock
            monitor.ws = mock_ws_manager

            # Handle unhealthy job
            await monitor._handle_unhealthy_job(session, health_status, "test-tenant")

            # Verify job failed
            await session.refresh(job)
            assert job.status == "failed"
            assert job.completed_at is not None
            assert "Auto-failed" in job.result_summary
            assert "Complete silence" in job.result_summary

            # Verify auto-fail broadcast
            mock_ws_manager.broadcast_agent_auto_failed.assert_called_once()
            call_args = mock_ws_manager.broadcast_agent_auto_failed.call_args
            assert call_args[1]["tenant_key"] == "test-tenant"
            assert call_args[1]["job_id"] == "timeout-job"

    async def test_multi_tenant_isolation(self, monitor):
        """Test health checks respect tenant boundaries."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=6)

            # Create jobs for different tenants
            job_tenant_a = AgentExecution(
                job_id="job-tenant-a",
                tenant_key="tenant-a",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=stale_time,
                created_at=stale_time,
                updated_at=stale_time,
                job_metadata={"last_progress_update": stale_time.isoformat()}
            )

            job_tenant_b = AgentExecution(
                job_id="job-tenant-b",
                tenant_key="tenant-b",
                agent_type="implementer",
                status="active",
                mission="Test mission",
                started_at=stale_time,
                created_at=stale_time,
                updated_at=stale_time,
                job_metadata={"last_progress_update": stale_time.isoformat()}
            )

            session.add_all([job_tenant_a, job_tenant_b])
            await session.commit()

            # Scan only tenant-a
            unhealthy_a = await monitor._detect_stalled_jobs(session, "tenant-a")

            # Should only find tenant-a job
            assert len(unhealthy_a) == 1
            assert unhealthy_a[0].job_id == "job-tenant-a"

            # Scan only tenant-b
            unhealthy_b = await monitor._detect_stalled_jobs(session, "tenant-b")

            # Should only find tenant-b job
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

    async def test_get_all_tenants(self, monitor):
        """Test retrieving all unique tenant keys."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create jobs for multiple tenants
            jobs = [
                AgentExecution(
                    job_id=f"job-{i}",
                    tenant_key=f"tenant-{i % 3}",  # 3 unique tenants
                    agent_type="implementer",
                    status="active",
                    mission="Test mission",
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                for i in range(6)
            ]
            session.add_all(jobs)
            await session.commit()

            # Get all tenants
            tenants = await monitor._get_all_tenants(session)

            # Should return 3 unique tenant keys
            assert len(tenants) == 3
            assert set(tenants) == {"tenant-0", "tenant-1", "tenant-2"}

    async def test_scan_tenant_jobs_combines_all_detections(self, monitor):
        """Test scan combines waiting, stalled, and heartbeat detections."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            now = datetime.now(timezone.utc)

            # Create jobs triggering different detections
            jobs = [
                # Waiting timeout
                AgentExecution(
                    job_id="waiting-timeout",
                    tenant_key="test-tenant",
                    agent_type="implementer",
                    status="waiting",
                    mission="Test mission",
                    created_at=now - timedelta(minutes=3),
                    updated_at=now - timedelta(minutes=3)
                ),
                # Stalled job
                AgentExecution(
                    job_id="stalled-job",
                    tenant_key="test-tenant",
                    agent_type="implementer",
                    status="active",
                    mission="Test mission",
                    started_at=now - timedelta(minutes=6),
                    created_at=now - timedelta(minutes=7),
                    updated_at=now - timedelta(minutes=6),
                    job_metadata={"last_progress_update": (now - timedelta(minutes=6)).isoformat()}
                ),
                # Heartbeat failure
                AgentExecution(
                    job_id="heartbeat-fail",
                    tenant_key="test-tenant",
                    agent_type="tester",  # 8min timeout
                    status="active",
                    mission="Test mission",
                    started_at=now - timedelta(minutes=12),
                    created_at=now - timedelta(minutes=13),
                    updated_at=now - timedelta(minutes=12),
                    job_metadata={}
                )
            ]
            session.add_all(jobs)
            await session.commit()

            # Scan tenant
            unhealthy = await monitor._scan_tenant_jobs(session, "test-tenant")

            # Should detect all 3 issues
            assert len(unhealthy) >= 3
            job_ids = {h.job_id for h in unhealthy}
            assert "waiting-timeout" in job_ids
            assert "stalled-job" in job_ids
            assert "heartbeat-fail" in job_ids
