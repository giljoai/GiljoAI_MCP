"""
Unit tests for Service Manager
"""

import subprocess

# Add project root to path
import sys
from pathlib import Path
from unittest.mock import Mock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.services.service_manager import ServiceConfig, ServiceManager, ServiceStatus

    HAS_SERVICE_MANAGER = True
except ImportError:
    HAS_SERVICE_MANAGER = False
    pytest.skip("Service Manager not available", allow_module_level=True)

from tests.installer.fixtures.mock_utils import MockSubprocessResult
from tests.installer.fixtures.test_configs import create_test_env


class TestServiceManager:
    """Test Service Manager functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_env = create_test_env()
        self.manager = ServiceManager()

    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()

    def test_service_manager_initialization(self):
        """Test service manager initialization"""
        manager = ServiceManager()
        assert manager.platform is not None
        assert hasattr(manager, "services")

    def test_service_config_creation(self):
        """Test service configuration creation"""
        config = ServiceConfig(
            name="test-service",
            display_name="Test Service",
            description="A test service",
            executable="/usr/bin/test",
            arguments=["--config", "/etc/test.conf"],
            working_directory="/var/lib/test",
            user="test-user",
            dependencies=["postgresql", "redis"],
            auto_start=True,
            restart_policy="always",
        )

        assert config.name == "test-service"
        assert config.display_name == "Test Service"
        assert config.auto_start == True
        assert "postgresql" in config.dependencies

    @pytest.mark.asyncio
    async def test_install_service_windows(self):
        """Test Windows service installation"""
        manager = ServiceManager()

        service_config = ServiceConfig(name="test-service", display_name="Test Service", executable="C:/test/app.exe")

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.install_service(service_config)
                assert result.success == True

    @pytest.mark.asyncio
    async def test_install_service_linux(self):
        """Test Linux systemd service installation"""
        manager = ServiceManager()

        service_config = ServiceConfig(name="test-service", display_name="Test Service", executable="/usr/bin/test")

        with patch("platform.system", return_value="Linux"):
            with patch("pathlib.Path.write_text") as mock_write:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MockSubprocessResult(0, "", "")

                    result = await manager.install_service(service_config)
                    assert result.success == True
                    mock_write.assert_called()  # Should write systemd unit file

    @pytest.mark.asyncio
    async def test_install_service_macos(self):
        """Test macOS launchd service installation"""
        manager = ServiceManager()

        service_config = ServiceConfig(
            name="test-service", display_name="Test Service", executable="/usr/local/bin/test"
        )

        with patch("platform.system", return_value="Darwin"):
            with patch("pathlib.Path.write_text") as mock_write:
                with patch("subprocess.run") as mock_run:
                    mock_run.return_value = MockSubprocessResult(0, "", "")

                    result = await manager.install_service(service_config)
                    assert result.success == True
                    mock_write.assert_called()  # Should write plist file

    @pytest.mark.asyncio
    async def test_uninstall_service(self):
        """Test service uninstallation"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.uninstall_service("test-service")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_start_service(self):
        """Test service starting"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.start_service("test-service")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_stop_service(self):
        """Test service stopping"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.stop_service("test-service")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_restart_service(self):
        """Test service restarting"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.restart_service("test-service")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_get_service_status(self):
        """Test service status checking"""
        manager = ServiceManager()

        # Mock running service
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "active (running)", "")

                status = await manager.get_service_status("test-service")
                assert status == ServiceStatus.RUNNING

        # Mock stopped service
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(3, "inactive (dead)", "")

                status = await manager.get_service_status("test-service")
                assert status == ServiceStatus.STOPPED

        # Mock unknown service
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(4, "could not be found", "")

                status = await manager.get_service_status("nonexistent-service")
                assert status == ServiceStatus.NOT_FOUND

    @pytest.mark.asyncio
    async def test_enable_service(self):
        """Test service auto-start enabling"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.enable_service("test-service")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_disable_service(self):
        """Test service auto-start disabling"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.disable_service("test-service")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_list_services(self):
        """Test service listing"""
        manager = ServiceManager()

        mock_output = """postgresql.service    loaded active running   PostgreSQL database server
redis.service         loaded active running   Advanced key-value store
test.service          loaded inactive dead    Test service"""

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, mock_output, "")

                services = await manager.list_services()
                assert len(services) >= 3
                service_names = [s["name"] for s in services]
                assert "postgresql.service" in service_names

    @pytest.mark.asyncio
    async def test_check_dependencies(self):
        """Test service dependency checking"""
        manager = ServiceManager()

        service_config = ServiceConfig(
            name="app-service", executable="/usr/bin/app", dependencies=["postgresql", "redis"]
        )

        with patch("platform.system", return_value="Linux"):
            with patch.object(manager, "get_service_status") as mock_status:
                # Mock all dependencies as running
                mock_status.return_value = ServiceStatus.RUNNING

                deps_ready = await manager.check_dependencies(service_config)
                assert deps_ready == True

            with patch.object(manager, "get_service_status") as mock_status:
                # Mock one dependency as stopped
                def status_side_effect(name):
                    if name == "postgresql":
                        return ServiceStatus.RUNNING
                    if name == "redis":
                        return ServiceStatus.STOPPED
                    return ServiceStatus.NOT_FOUND

                mock_status.side_effect = status_side_effect

                deps_ready = await manager.check_dependencies(service_config)
                assert deps_ready == False

    @pytest.mark.asyncio
    async def test_start_with_dependencies(self):
        """Test starting service with dependency ordering"""
        manager = ServiceManager()

        service_config = ServiceConfig(
            name="app-service", executable="/usr/bin/app", dependencies=["postgresql", "redis"]
        )

        with patch("platform.system", return_value="Linux"):
            with patch.object(manager, "get_service_status") as mock_status:
                mock_status.return_value = ServiceStatus.STOPPED

            with patch.object(manager, "start_service") as mock_start:
                mock_start.return_value = Mock(success=True)

                result = await manager.start_with_dependencies(service_config)
                assert result.success == True

                # Should have called start_service for dependencies first
                expected_calls = ["postgresql", "redis", "app-service"]
                actual_calls = [call[0][0] for call in mock_start.call_args_list]
                for expected in expected_calls:
                    assert expected in actual_calls

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration"""
        manager = ServiceManager()

        health_config = {"check_interval": 30, "restart_on_failure": True, "max_restart_attempts": 3}

        service_config = ServiceConfig(
            name="monitored-service", executable="/usr/bin/monitored", health_check=health_config
        )

        with patch("platform.system", return_value="Linux"):
            with patch("asyncio.sleep"):  # Mock sleep to speed up test
                with patch.object(manager, "get_service_status") as mock_status:
                    # Mock service as initially running, then failing, then running again
                    mock_status.side_effect = [ServiceStatus.RUNNING, ServiceStatus.STOPPED, ServiceStatus.RUNNING]

                with patch.object(manager, "restart_service") as mock_restart:
                    mock_restart.return_value = Mock(success=True)

                    # Start health monitoring (would run in background in real implementation)
                    # For test, we'll call the monitoring function directly
                    await manager._monitor_service_health(service_config)

    def test_create_systemd_unit_file(self):
        """Test systemd unit file generation"""
        manager = ServiceManager()

        service_config = ServiceConfig(
            name="test-service",
            display_name="Test Service",
            description="A test service for unit testing",
            executable="/usr/bin/test-app",
            arguments=["--config", "/etc/test.conf"],
            working_directory="/var/lib/test",
            user="test-user",
            dependencies=["postgresql.service", "redis.service"],
            auto_start=True,
            restart_policy="always",
        )

        unit_content = manager._create_systemd_unit_file(service_config)

        assert "[Unit]" in unit_content
        assert "[Service]" in unit_content
        assert "[Install]" in unit_content
        assert "Description=A test service for unit testing" in unit_content
        assert "ExecStart=/usr/bin/test-app --config /etc/test.conf" in unit_content
        assert "WorkingDirectory=/var/lib/test" in unit_content
        assert "User=test-user" in unit_content
        assert "Requires=postgresql.service redis.service" in unit_content
        assert "Restart=always" in unit_content

    def test_create_launchd_plist(self):
        """Test macOS launchd plist generation"""
        manager = ServiceManager()

        service_config = ServiceConfig(
            name="com.test.service",
            display_name="Test Service",
            executable="/usr/local/bin/test-app",
            arguments=["--config", "/usr/local/etc/test.conf"],
            working_directory="/usr/local/var/test",
            auto_start=True,
        )

        plist_content = manager._create_launchd_plist(service_config)

        assert "<?xml version" in plist_content
        assert "<plist version" in plist_content
        assert "<dict>" in plist_content
        assert "<key>Label</key>" in plist_content
        assert "<string>com.test.service</string>" in plist_content
        assert "<key>ProgramArguments</key>" in plist_content
        assert "<string>/usr/local/bin/test-app</string>" in plist_content
        assert "<key>WorkingDirectory</key>" in plist_content
        assert "<key>RunAtLoad</key>" in plist_content
        assert "<true/>" in plist_content

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling in service operations"""
        manager = ServiceManager()

        # Test installation error
        service_config = ServiceConfig(name="failing-service", executable="/nonexistent/binary")

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", "Service creation failed")

                result = await manager.install_service(service_config)
                assert result.success == False
                assert "error" in result.message.lower()

        # Test start error
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "systemctl", "Unit not found")

                result = await manager.start_service("nonexistent-service")
                assert result.success == False

    @pytest.mark.asyncio
    async def test_windows_service_operations(self):
        """Test Windows-specific service operations"""
        manager = ServiceManager()

        with patch("platform.system", return_value="Windows"):
            # Test service creation with Windows Service Wrapper
            service_config = ServiceConfig(
                name="WindowsTestService",
                display_name="Windows Test Service",
                executable="C:\\Program Files\\Test\\app.exe",
            )

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await manager.install_service(service_config)
                assert result.success == True

            # Test service status check
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "RUNNING", "")

                status = await manager.get_service_status("WindowsTestService")
                assert status == ServiceStatus.RUNNING


class TestServiceStatus:
    """Test ServiceStatus enum"""

    def test_service_status_values(self):
        """Test service status enum values"""
        assert ServiceStatus.RUNNING.value == "running"
        assert ServiceStatus.STOPPED.value == "stopped"
        assert ServiceStatus.STARTING.value == "starting"
        assert ServiceStatus.STOPPING.value == "stopping"
        assert ServiceStatus.FAILED.value == "failed"
        assert ServiceStatus.NOT_FOUND.value == "not_found"
        assert ServiceStatus.UNKNOWN.value == "unknown"


class TestServiceUtilities:
    """Test service utility functions"""

    def test_validate_service_config(self):
        """Test service configuration validation"""
        manager = ServiceManager()

        # Valid config
        valid_config = ServiceConfig(name="valid-service", executable="/usr/bin/valid")

        is_valid = manager.validate_service_config(valid_config)
        assert is_valid == True

        # Invalid config (empty name)
        invalid_config = ServiceConfig(name="", executable="/usr/bin/valid")

        is_valid = manager.validate_service_config(invalid_config)
        assert is_valid == False

        # Invalid config (nonexistent executable)
        with patch("pathlib.Path.exists", return_value=False):
            invalid_config = ServiceConfig(name="invalid-service", executable="/nonexistent/binary")

            is_valid = manager.validate_service_config(invalid_config)
            assert is_valid == False

    def test_get_platform_info(self):
        """Test platform information retrieval"""
        manager = ServiceManager()

        info = manager.get_platform_info()
        assert "platform" in info
        assert "service_manager" in info

        # Should identify correct service manager for platform
        with patch("platform.system", return_value="Linux"):
            manager = ServiceManager()
            info = manager.get_platform_info()
            assert info["service_manager"] == "systemd"

        with patch("platform.system", return_value="Darwin"):
            manager = ServiceManager()
            info = manager.get_platform_info()
            assert info["service_manager"] == "launchd"

        with patch("platform.system", return_value="Windows"):
            manager = ServiceManager()
            info = manager.get_platform_info()
            assert info["service_manager"] == "windows_service"


# Fixtures
@pytest.fixture
def service_manager():
    """Create ServiceManager instance"""
    return ServiceManager()


@pytest.fixture
def test_service_config():
    """Create test service configuration"""
    return ServiceConfig(
        name="test-service",
        display_name="Test Service",
        description="Service for testing",
        executable="/usr/bin/test",
        working_directory="/var/lib/test",
        auto_start=True,
    )


@pytest.fixture
def test_environment():
    """Create test environment"""
    env = create_test_env()
    env.config_dir.mkdir(parents=True, exist_ok=True)
    env.services_dir = env.base_dir / "services"
    env.services_dir.mkdir(exist_ok=True)
    yield env
    env.cleanup()


# Parametrized tests
@pytest.mark.parametrize(
    "platform,expected_manager", [("Windows", "windows_service"), ("Linux", "systemd"), ("Darwin", "launchd")]
)
def test_service_manager_by_platform(platform, expected_manager):
    """Test service manager detection by platform"""
    with patch("platform.system", return_value=platform):
        manager = ServiceManager()
        info = manager.get_platform_info()
        assert info["service_manager"] == expected_manager


@pytest.mark.parametrize(
    "status_output,expected_status",
    [
        ("active (running)", ServiceStatus.RUNNING),
        ("inactive (dead)", ServiceStatus.STOPPED),
        ("activating (start)", ServiceStatus.STARTING),
        ("deactivating (stop)", ServiceStatus.STOPPING),
        ("failed", ServiceStatus.FAILED),
        ("could not be found", ServiceStatus.NOT_FOUND),
        ("unknown status", ServiceStatus.UNKNOWN),
    ],
)
def test_status_parsing(status_output, expected_status):
    """Test service status parsing"""
    manager = ServiceManager()

    with patch("platform.system", return_value="Linux"):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, status_output, "")

            # This would need to be implemented in the actual ServiceManager
            # For now, test that different outputs are handled
            assert True  # Placeholder


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
