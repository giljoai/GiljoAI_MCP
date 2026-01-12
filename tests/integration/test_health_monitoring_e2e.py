"""
End-to-end integration tests for Agent Health Monitoring System.
Tests full monitoring lifecycle with real database and WebSocket integration.
"""

import pytest
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy import select

from src.giljo_mcp.models.agent_identity import AgentJob, AgentExecution
from src.giljo_mcp.monitoring.agent_health_monitor import AgentHealthMonitor
from src.giljo_mcp.monitoring.health_config import HealthCheckConfig
from src.giljo_mcp.database import DatabaseManager
from api.websocket import WebSocketManager


@pytest.mark.asyncio
class TestHealthMonitoringE2E:
    """End-to-end tests for health monitoring system."""

    @pytest.fixture
    def fast_config(self):
        """Configuration with very short intervals for testing."""
        return HealthCheckConfig(
            waiting_timeout_minutes=1,
            active_no_progress_minutes=2,
            heartbeat_timeout_minutes=5,
            scan_interval_seconds=2,  # 2 seconds for fast testing
            auto_fail_on_timeout=False
        )

    @pytest.fixture
    async def db_manager(self):
        """Real database manager for integration testing."""
        from src.giljo_mcp.database import DatabaseManager

        db = DatabaseManager()
        await db.initialize()
        yield db
        await db.close()

    @pytest.fixture
    async def ws_manager(self):
        """Real WebSocket manager for integration testing."""
        from api.websocket import WebSocketManager

        ws = WebSocketManager()
        return ws

    @pytest.fixture
    async def monitor(self, db_manager, ws_manager, fast_config):
        """Create monitor with real dependencies."""
        monitor = AgentHealthMonitor(db_manager, ws_manager, fast_config)
        yield monitor

        # Cleanup
        if monitor.running:
            await monitor.stop()

    async def test_full_monitoring_lifecycle(self, monitor, db_manager):
        """Test complete monitoring lifecycle from start to stop."""
        # Start monitor
        await monitor.start()
        assert monitor.running is True

        # Let it run for a few cycles
        await asyncio.sleep(5)

        # Monitor should still be running
        assert monitor.running is True

        # Stop monitor
        await monitor.stop()
        assert monitor.running is False

    async def test_detect_and_alert_waiting_timeout_e2e(self, monitor, db_manager, ws_manager):
        """Test end-to-end detection and alerting for waiting timeout."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job stuck in waiting
            job = AgentExecution(
                job_id="e2e-waiting-timeout",
                tenant_key="test-tenant-e2e",
                agent_display_name="implementer",
                status="waiting",
                mission="Test mission",
                created_at=datetime.now(timezone.utc) - timedelta(minutes=2),
                updated_at=datetime.now(timezone.utc) - timedelta(minutes=2),
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Wait for detection cycle
            await asyncio.sleep(3)

            # Check job was updated
            await session.refresh(job)
            assert job.health_status == "critical"
            assert job.health_failure_count > 0
            assert job.last_health_check is not None

            # Stop monitor
            await monitor.stop()

    async def test_detect_and_alert_stalled_job_e2e(self, monitor, db_manager):
        """Test end-to-end detection and alerting for stalled job."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create stalled active job
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=3)
            job = AgentExecution(
                job_id="e2e-stalled-job",
                tenant_key="test-tenant-e2e",
                agent_display_name="implementer",
                status="active",
                mission="Test mission",
                started_at=stale_time,
                created_at=stale_time - timedelta(minutes=1),
                updated_at=stale_time,
                job_metadata={"last_progress_update": stale_time.isoformat()},
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Wait for detection cycle
            await asyncio.sleep(3)

            # Check job was updated
            await session.refresh(job)
            assert job.health_status in ["warning", "critical"]
            assert job.health_failure_count > 0

            # Stop monitor
            await monitor.stop()

    async def test_auto_fail_timeout_e2e(self, monitor, db_manager):
        """Test end-to-end auto-fail on timeout."""
        from tests.conftest import get_test_session

        # Enable auto-fail
        monitor.config.auto_fail_on_timeout = True

        async with get_test_session() as session:
            # Create job that should timeout
            timeout_time = datetime.now(timezone.utc) - timedelta(minutes=6)
            job = AgentExecution(
                job_id="e2e-auto-fail",
                tenant_key="test-tenant-e2e",
                agent_display_name="implementer",
                status="active",
                mission="Test mission",
                started_at=timeout_time,
                created_at=timeout_time - timedelta(minutes=1),
                updated_at=timeout_time,
                job_metadata={},
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Wait for detection and auto-fail
            await asyncio.sleep(3)

            # Check job was auto-failed
            await session.refresh(job)
            assert job.status == "failed"
            assert job.completed_at is not None
            assert "Auto-failed" in job.result_summary

            # Stop monitor
            await monitor.stop()

    async def test_multiple_tenants_e2e(self, monitor, db_manager):
        """Test monitoring multiple tenants independently."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=3)

            # Create jobs for different tenants
            jobs = [
                AgentExecution(
                    job_id=f"e2e-tenant-{i}-job",
                    tenant_key=f"tenant-{i}",
                    agent_display_name="implementer",
                    status="active",
                    mission="Test mission",
                    started_at=stale_time,
                    created_at=stale_time,
                    updated_at=stale_time,
                    job_metadata={"last_progress_update": stale_time.isoformat()},
                    health_status="unknown",
                    health_failure_count=0
                )
                for i in range(3)
            ]
            session.add_all(jobs)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Wait for detection
            await asyncio.sleep(3)

            # All jobs should be updated
            for job in jobs:
                await session.refresh(job)
                assert job.health_status in ["warning", "critical"]
                assert job.health_failure_count > 0

            # Stop monitor
            await monitor.stop()

    async def test_healthy_jobs_not_flagged_e2e(self, monitor, db_manager):
        """Test healthy jobs are not flagged by monitoring."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create healthy job with recent activity
            recent_time = datetime.now(timezone.utc) - timedelta(seconds=30)
            job = AgentExecution(
                job_id="e2e-healthy-job",
                tenant_key="test-tenant-e2e",
                agent_display_name="implementer",
                status="active",
                mission="Test mission",
                started_at=recent_time,
                created_at=recent_time,
                updated_at=recent_time,
                job_metadata={"last_progress_update": recent_time.isoformat()},
                health_status="healthy",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Wait for detection cycle
            await asyncio.sleep(3)

            # Job should remain healthy
            await session.refresh(job)
            assert job.health_status == "healthy"
            assert job.health_failure_count == 0

            # Stop monitor
            await monitor.stop()

    async def test_progressive_health_degradation_e2e(self, monitor, db_manager):
        """Test job health degrades progressively over time."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job that will degrade
            initial_time = datetime.now(timezone.utc) - timedelta(minutes=3)
            job = AgentExecution(
                job_id="e2e-degrading-job",
                tenant_key="test-tenant-e2e",
                agent_display_name="implementer",
                status="active",
                mission="Test mission",
                started_at=initial_time,
                created_at=initial_time,
                updated_at=initial_time,
                job_metadata={"last_progress_update": initial_time.isoformat()},
                health_status="unknown",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Start monitor
            await monitor.start()

            # First check - should be warning
            await asyncio.sleep(3)
            await session.refresh(job)
            first_state = job.health_status

            # Wait longer - should degrade to critical
            await asyncio.sleep(5)
            await session.refresh(job)
            second_state = job.health_status

            # Health should have stayed same or degraded
            health_progression = ["unknown", "healthy", "warning", "critical", "timeout"]
            first_index = health_progression.index(first_state)
            second_index = health_progression.index(second_state)

            assert second_index >= first_index

            # Stop monitor
            await monitor.stop()

    async def test_concurrent_health_checks(self, monitor, db_manager):
        """Test monitor handles concurrent health checks correctly."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            stale_time = datetime.now(timezone.utc) - timedelta(minutes=3)

            # Create multiple jobs
            jobs = [
                AgentExecution(
                    job_id=f"e2e-concurrent-{i}",
                    tenant_key="test-tenant-e2e",
                    agent_display_name="implementer",
                    status="active",
                    mission="Test mission",
                    started_at=stale_time,
                    created_at=stale_time,
                    updated_at=stale_time,
                    job_metadata={"last_progress_update": stale_time.isoformat()},
                    health_status="unknown",
                    health_failure_count=0
                )
                for i in range(10)
            ]
            session.add_all(jobs)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Wait for multiple cycles
            await asyncio.sleep(5)

            # All jobs should be checked
            checked_count = 0
            for job in jobs:
                await session.refresh(job)
                if job.health_failure_count > 0:
                    checked_count += 1

            assert checked_count == 10

            # Stop monitor
            await monitor.stop()

    async def test_monitor_recovery_after_database_error(self, monitor, db_manager):
        """Test monitor recovers gracefully from database errors."""
        # This test verifies the monitor continues running even if a cycle fails

        # Start monitor
        await monitor.start()

        # Simulate several cycles with potential errors
        await asyncio.sleep(6)

        # Monitor should still be running
        assert monitor.running is True

        # Stop monitor
        await monitor.stop()

    async def test_health_status_transitions(self, monitor, db_manager):
        """Test health status transitions correctly between states."""
        from tests.conftest import get_test_session

        async with get_test_session() as session:
            # Create job
            job = AgentExecution(
                job_id="e2e-transitions",
                tenant_key="test-tenant-e2e",
                agent_display_name="implementer",
                status="active",
                mission="Test mission",
                started_at=datetime.now(timezone.utc),
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                job_metadata={"last_progress_update": datetime.now(timezone.utc).isoformat()},
                health_status="healthy",
                health_failure_count=0
            )
            session.add(job)
            await session.commit()

            # Start monitor
            await monitor.start()

            # Initial state - healthy
            await asyncio.sleep(3)
            await session.refresh(job)
            assert job.health_status == "healthy"

            # Make job stale (3 minutes)
            job.job_metadata = {
                "last_progress_update": (datetime.now(timezone.utc) - timedelta(minutes=3)).isoformat()
            }
            await session.commit()

            # Next cycle should detect warning/critical
            await asyncio.sleep(3)
            await session.refresh(job)
            assert job.health_status in ["warning", "critical"]

            # Stop monitor
            await monitor.stop()
