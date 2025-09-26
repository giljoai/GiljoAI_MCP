"""
Unit tests for Health Check system
"""

# Import the health check system
import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.core.health import ComponentHealth, HealthChecker, HealthReport, HealthStatus
    from installer.core.health_integration import HealthCheckOrchestrator, InstallationHealthCheck

    HAS_HEALTH = True
except ImportError:
    HAS_HEALTH = False
    pytest.skip("Health check system not available", allow_module_level=True)

from tests.installer.fixtures.mock_utils import (
    MockDatabaseConnection,
    MockDockerClient,
    MockRedisConnection,
    MockSocket,
)


class TestHealthStatus:
    """Test HealthStatus enum"""

    def test_health_status_values(self):
        """Test all health status values"""
        assert HealthStatus.HEALTHY.value == "healthy"
        assert HealthStatus.WARNING.value == "warning"
        assert HealthStatus.ERROR.value == "error"
        assert HealthStatus.UNKNOWN.value == "unknown"
        assert HealthStatus.NOT_INSTALLED.value == "not_installed"


class TestComponentHealth:
    """Test ComponentHealth dataclass"""

    def test_component_health_creation(self):
        """Test creating component health"""
        health = ComponentHealth(
            name="PostgreSQL",
            status=HealthStatus.HEALTHY,
            message="Database is running",
            details={"version": "15.4", "port": 5432},
            check_time=0.1,
        )

        assert health.name == "PostgreSQL"
        assert health.status == HealthStatus.HEALTHY
        assert health.message == "Database is running"
        assert health.details["version"] == "15.4"
        assert health.check_time == 0.1

    def test_component_health_to_dict(self):
        """Test converting component health to dict"""
        health = ComponentHealth(name="Redis", status=HealthStatus.WARNING, message="Memory usage high")

        health_dict = health.to_dict()
        assert health_dict["name"] == "Redis"
        assert health_dict["status"] == "warning"
        assert health_dict["message"] == "Memory usage high"
        assert "timestamp" in health_dict


class TestHealthReport:
    """Test HealthReport dataclass"""

    def test_health_report_creation(self):
        """Test creating health report"""
        components = [
            ComponentHealth("System", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("Database", HealthStatus.WARNING, "High load"),
        ]

        report = HealthReport(overall_status=HealthStatus.WARNING, components=components, total_check_time=1.5)

        assert report.overall_status == HealthStatus.WARNING
        assert len(report.components) == 2
        assert report.total_check_time == 1.5

    def test_health_report_to_dict(self):
        """Test converting report to dict"""
        components = [ComponentHealth("Test", HealthStatus.HEALTHY, "OK")]

        report = HealthReport(overall_status=HealthStatus.HEALTHY, components=components, total_check_time=0.5)

        report_dict = report.to_dict()
        assert report_dict["overall_status"] == "healthy"
        assert len(report_dict["components"]) == 1
        assert report_dict["total_check_time"] == 0.5

    def test_health_report_summary(self):
        """Test getting report summary"""
        components = [
            ComponentHealth("System", HealthStatus.HEALTHY, "System OK"),
            ComponentHealth("Database", HealthStatus.ERROR, "Connection failed"),
        ]

        report = HealthReport(overall_status=HealthStatus.ERROR, components=components, total_check_time=2.1)

        summary = report.get_summary()
        assert "Health Check Report" in summary
        assert "Overall Status: ERROR" in summary
        assert "Total Check Time: 2.10s" in summary
        assert "[OK] System" in summary
        assert "[ERR] Database" in summary


class TestHealthChecker:
    """Test HealthChecker class"""

    def test_health_checker_initialization(self):
        """Test HealthChecker initialization"""
        checker = HealthChecker()
        assert checker is not None
        assert len(checker.components) == 0

        # Test with config
        config = {"postgresql": {"host": "localhost", "port": 5432}}
        checker = HealthChecker(config)
        assert checker.config == config

    @pytest.mark.asyncio
    @patch("installer.core.health.shutil.disk_usage")
    async def test_system_check(self, mock_disk_usage):
        """Test system health check"""
        # Mock disk usage
        mock_disk_usage.return_value = type(
            "DiskUsage",
            (),
            {
                "free": 5 * 1024**3,  # 5GB free
                "total": 100 * 1024**3,  # 100GB total
                "used": 95 * 1024**3,  # 95GB used
            },
        )()

        checker = HealthChecker()
        await checker._check_system()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "System"
        assert component.status == HealthStatus.HEALTHY
        assert "Windows is operational" in component.message
        assert "disk_free_gb" in component.details

    @pytest.mark.asyncio
    @patch("installer.core.health.HAS_PSYCOPG2", True)
    @patch("psycopg2.connect")
    async def test_postgresql_check_success(self, mock_connect):
        """Test successful PostgreSQL check"""
        # Mock successful connection
        mock_conn = MockDatabaseConnection(should_fail=False, version="15.4")
        mock_connect.return_value = mock_conn

        checker = HealthChecker(
            {
                "postgresql": {
                    "host": "localhost",
                    "port": 5432,
                    "database": "test_db",
                    "user": "test_user",
                    "password": "test_pass",
                }
            }
        )

        await checker._check_postgresql()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "PostgreSQL"
        assert component.status == HealthStatus.HEALTHY
        assert "Connected to PostgreSQL" in component.message
        assert component.details["version"] == "15.4"

    @pytest.mark.asyncio
    @patch("installer.core.health.HAS_PSYCOPG2", False)
    async def test_postgresql_check_not_installed(self):
        """Test PostgreSQL check when psycopg2 not installed"""
        checker = HealthChecker()
        await checker._check_postgresql()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "PostgreSQL"
        assert component.status == HealthStatus.NOT_INSTALLED
        assert "psycopg2 module not installed" in component.message

    @pytest.mark.asyncio
    @patch("installer.core.health.HAS_REDIS", True)
    @patch("redis.Redis")
    async def test_redis_check_success(self, mock_redis_class):
        """Test successful Redis check"""
        # Mock Redis connection
        mock_redis = MockRedisConnection(should_fail=False)
        mock_redis_class.return_value = mock_redis

        checker = HealthChecker({"redis": {"host": "localhost", "port": 6379, "db": 0}})

        await checker._check_redis()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "Redis"
        assert component.status == HealthStatus.HEALTHY
        assert "Connected to Redis" in component.message

    @pytest.mark.asyncio
    @patch("installer.core.health.HAS_DOCKER", True)
    @patch("docker.from_env")
    async def test_docker_check_success(self, mock_docker_from_env):
        """Test successful Docker check"""
        # Mock Docker client
        mock_client = MockDockerClient(should_fail=False)
        mock_docker_from_env.return_value = mock_client

        checker = HealthChecker()
        await checker._check_docker()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "Docker"
        assert component.status == HealthStatus.HEALTHY
        assert "Docker daemon is running" in component.message

    @pytest.mark.asyncio
    @patch("socket.socket")
    async def test_port_availability_check(self, mock_socket_class):
        """Test port availability check"""

        def mock_socket_factory(*args, **kwargs):
            mock_sock = MockSocket(should_fail=True)  # Port available
            return mock_sock

        mock_socket_class.side_effect = mock_socket_factory

        checker = HealthChecker({"ports": {"api": 8000, "frontend": 3000, "postgresql": 5432}})

        await checker._check_ports()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "Ports"
        assert component.status == HealthStatus.HEALTHY
        assert "All required ports are available" in component.message

    @pytest.mark.asyncio
    @patch("platform.system", return_value="Linux")
    @patch("shutil.which", return_value="/usr/bin/systemctl")
    @patch("subprocess.run")
    async def test_services_check_linux(self, mock_run, mock_which, mock_platform):
        """Test services check on Linux"""
        # Mock systemctl responses
        mock_run.return_value = type("Result", (), {"returncode": 0, "stdout": "active"})()

        checker = HealthChecker({"services": ["postgresql", "redis"]})

        await checker._check_services()

        assert len(checker.components) == 1
        component = checker.components[0]
        assert component.name == "Services"

    @pytest.mark.asyncio
    async def test_network_connectivity(self):
        """Test network connectivity check"""
        with patch("installer.core.health.HealthChecker._can_connect") as mock_connect:
            mock_connect.side_effect = [True, True]  # localhost and external OK

            checker = HealthChecker()
            await checker._check_network()

            assert len(checker.components) == 1
            component = checker.components[0]
            assert component.name == "Network"
            assert component.status == HealthStatus.HEALTHY
            assert "Network connectivity is good" in component.message

    @pytest.mark.asyncio
    async def test_check_all_components(self):
        """Test checking all components"""
        with patch.multiple(
            "installer.core.health.HealthChecker",
            _check_system=AsyncMock(),
            _check_postgresql=AsyncMock(),
            _check_redis=AsyncMock(),
            _check_docker=AsyncMock(),
            _check_ports=AsyncMock(),
            _check_services=AsyncMock(),
            _check_python=AsyncMock(),
            _check_network=AsyncMock(),
        ):
            checker = HealthChecker()

            # Mock some components
            checker.components = [
                ComponentHealth("System", HealthStatus.HEALTHY, "OK"),
                ComponentHealth("Database", HealthStatus.WARNING, "High load"),
                ComponentHealth("Cache", HealthStatus.HEALTHY, "OK"),
            ]

            report = await checker.check_all()

            assert isinstance(report, HealthReport)
            assert report.overall_status == HealthStatus.WARNING
            assert len(report.components) == 3

    @pytest.mark.asyncio
    async def test_database_services_check(self):
        """Test specific database services check"""
        with patch.multiple(
            "installer.core.health.HealthChecker",
            _check_postgresql=AsyncMock(),
            _check_redis=AsyncMock(),
            _check_ports=AsyncMock(),
        ):
            checker = HealthChecker()
            report = await checker.check_database_services()

            assert isinstance(report, HealthReport)

    @pytest.mark.asyncio
    async def test_installation_readiness_check(self):
        """Test installation readiness check"""
        with patch.multiple(
            "installer.core.health.HealthChecker",
            _check_system=AsyncMock(),
            _check_python=AsyncMock(),
            _check_network=AsyncMock(),
            _check_ports=AsyncMock(),
        ):
            checker = HealthChecker()
            report = await checker.check_installation_readiness()

            assert isinstance(report, HealthReport)

    def test_calculate_overall_status(self):
        """Test overall status calculation"""
        checker = HealthChecker()

        # All healthy
        checker.components = [
            ComponentHealth("A", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("B", HealthStatus.HEALTHY, "OK"),
        ]
        assert checker._calculate_overall_status() == HealthStatus.HEALTHY

        # Mixed with warning
        checker.components = [
            ComponentHealth("A", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("B", HealthStatus.WARNING, "Issue"),
        ]
        assert checker._calculate_overall_status() == HealthStatus.WARNING

        # Has error
        checker.components = [
            ComponentHealth("A", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("B", HealthStatus.ERROR, "Failed"),
        ]
        assert checker._calculate_overall_status() == HealthStatus.ERROR


class TestInstallationHealthCheck:
    """Test InstallationHealthCheck class"""

    @pytest.mark.asyncio
    async def test_pre_installation_check(self):
        """Test pre-installation health check"""
        health_checker = HealthChecker()
        installation_check = InstallationHealthCheck(health_checker)

        with patch.object(health_checker, "check_installation_readiness") as mock_check:
            # Mock healthy report
            mock_report = HealthReport(
                overall_status=HealthStatus.HEALTHY,
                components=[
                    ComponentHealth("System", HealthStatus.HEALTHY, "OK"),
                    ComponentHealth("Python", HealthStatus.HEALTHY, "OK"),
                ],
                total_check_time=1.0,
            )
            mock_check.return_value = mock_report

            result = await installation_check.pre_installation_check()

            assert result["ready"] == True
            assert len(result["errors"]) == 0
            assert "System" in result["details"]

    @pytest.mark.asyncio
    async def test_database_health_check(self):
        """Test database health check"""
        health_checker = HealthChecker()
        installation_check = InstallationHealthCheck(health_checker)

        with patch.object(health_checker, "check_database_services") as mock_check:
            # Mock database report
            mock_report = HealthReport(
                overall_status=HealthStatus.WARNING,
                components=[
                    ComponentHealth("PostgreSQL", HealthStatus.HEALTHY, "Connected"),
                    ComponentHealth("Redis", HealthStatus.ERROR, "Connection failed"),
                ],
                total_check_time=2.0,
            )
            mock_check.return_value = mock_report

            result = await installation_check.check_database_health()

            assert result["postgresql"]["healthy"] == True
            assert result["redis"]["healthy"] == False
            assert result["both_healthy"] == False

    @pytest.mark.asyncio
    async def test_gui_callback_integration(self):
        """Test GUI callback integration"""
        health_checker = HealthChecker()
        callback_calls = []

        def mock_callback(data):
            callback_calls.append(data)

        installation_check = InstallationHealthCheck(health_checker, mock_callback)

        with patch.object(health_checker, "check_installation_readiness") as mock_check:
            mock_report = HealthReport(overall_status=HealthStatus.HEALTHY, components=[], total_check_time=0.5)
            mock_check.return_value = mock_report

            await installation_check.pre_installation_check()

            assert len(callback_calls) == 1
            assert callback_calls[0]["phase"] == "pre_installation"
            assert callback_calls[0]["status"] == "ready"


class TestHealthCheckOrchestrator:
    """Test HealthCheckOrchestrator class"""

    def test_orchestrator_initialization(self):
        """Test orchestrator initialization"""
        orchestrator = HealthCheckOrchestrator()
        assert orchestrator is not None
        assert orchestrator.health_checker is not None

        # Test with config
        config = {"test": "value"}
        orchestrator = HealthCheckOrchestrator(config)
        assert orchestrator.health_checker.config == config

    @pytest.mark.asyncio
    async def test_full_installation_workflow(self):
        """Test full installation workflow"""
        orchestrator = HealthCheckOrchestrator()

        with (
            patch.object(orchestrator.installation_checker, "pre_installation_check") as mock_pre,
            patch.object(orchestrator.installation_checker, "check_database_health") as mock_db,
        ):
            # Mock pre-installation check - ready
            mock_pre.return_value = {"ready": True, "warnings": [], "errors": []}

            # Mock database check - nothing installed
            mock_db.return_value = {"postgresql": {"healthy": False}, "redis": {"healthy": False}}

            result = await orchestrator.full_installation_workflow()

            assert result["status"] == "ready"
            assert result["needs_postgresql"] == True
            assert result["needs_redis"] == True

    @pytest.mark.asyncio
    async def test_parallel_service_check(self):
        """Test parallel service checking"""
        orchestrator = HealthCheckOrchestrator()

        with patch.multiple(
            orchestrator.health_checker,
            _check_postgresql=AsyncMock(),
            _check_redis=AsyncMock(),
            _check_ports=AsyncMock(),
        ):
            # Mock components
            orchestrator.health_checker.components = [
                ComponentHealth("PostgreSQL", HealthStatus.HEALTHY, "Connected"),
                ComponentHealth("Redis", HealthStatus.ERROR, "Failed"),
                ComponentHealth("Ports", HealthStatus.HEALTHY, "Available"),
            ]

            result = await orchestrator.parallel_service_check()

            assert "report" in result
            assert result["postgresql_ready"] == True
            assert result["redis_ready"] == False
            assert result["ports_available"] == True


# Pytest fixtures
@pytest.fixture
def health_checker():
    """Create HealthChecker for testing"""
    return HealthChecker()


@pytest.fixture
def sample_components():
    """Create sample component health objects"""
    return [
        ComponentHealth("System", HealthStatus.HEALTHY, "System OK"),
        ComponentHealth("Database", HealthStatus.WARNING, "High load"),
        ComponentHealth("Cache", HealthStatus.HEALTHY, "Cache OK"),
    ]


@pytest.fixture
def health_report(sample_components):
    """Create sample health report"""
    return HealthReport(overall_status=HealthStatus.WARNING, components=sample_components, total_check_time=1.5)


# Integration test
@pytest.mark.asyncio
async def test_end_to_end_health_check():
    """Test complete health check workflow"""
    config = {"postgresql": {"host": "localhost", "port": 5432}, "redis": {"host": "localhost", "port": 6379}}

    checker = HealthChecker(config)

    # This would normally make real network calls
    # In a real test environment, you'd have services running
    # For unit tests, we mock the calls above

    with patch.multiple(checker, _check_system=AsyncMock(), _check_postgresql=AsyncMock(), _check_redis=AsyncMock()):
        # Mock healthy components
        checker.components = [
            ComponentHealth("System", HealthStatus.HEALTHY, "OK"),
            ComponentHealth("PostgreSQL", HealthStatus.HEALTHY, "Connected"),
            ComponentHealth("Redis", HealthStatus.HEALTHY, "Connected"),
        ]

        report = await checker.check_all(["system", "postgresql", "redis"])

        assert isinstance(report, HealthReport)
        assert len(report.components) == 3
        assert report.overall_status == HealthStatus.HEALTHY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
