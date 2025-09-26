"""
Unit tests for Redis installer
"""

import subprocess

# Add project root to path
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.dependencies.redis import RedisInstaller

    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    pytest.skip("Redis installer not available", allow_module_level=True)

from tests.installer.fixtures.mock_utils import MockSubprocessResult
from tests.installer.fixtures.test_configs import create_test_env


class TestRedisInstaller:
    """Test Redis installer functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_env = create_test_env()
        self.installer = RedisInstaller()

    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()

    def test_installer_initialization(self):
        """Test installer initialization"""
        installer = RedisInstaller()
        assert installer.name == "Redis"
        assert installer.version is not None
        assert installer.required_space > 0
        assert isinstance(installer.dependencies, list)

    @pytest.mark.asyncio
    async def test_check_installation(self):
        """Test Redis installation check"""
        installer = RedisInstaller()

        # Mock successful redis-server command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "Redis server v=6.2.7", "")

            is_installed = await installer.check_installation()
            assert is_installed == True

        # Mock failed redis-server command
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            is_installed = await installer.check_installation()
            assert is_installed == False

    @pytest.mark.asyncio
    async def test_install_windows(self):
        """Test Windows Redis installation"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                with patch.object(installer, "_download_redis_windows") as mock_download:
                    mock_download.return_value = Path("mock_redis.zip")

                with patch.object(installer, "_extract_redis_windows"):
                    with patch.object(installer, "_create_redis_service"):
                        result = await installer.install()
                        assert result.success == True
                        assert "Redis installation completed" in result.message

    @pytest.mark.asyncio
    async def test_install_linux(self):
        """Test Linux Redis installation"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.install()
                assert result.success == True

    @pytest.mark.asyncio
    async def test_install_macos(self):
        """Test macOS Redis installation via Homebrew"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.install()
                assert result.success == True

    def test_get_version(self):
        """Test version detection"""
        installer = RedisInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "Redis server v=6.2.7", "")

            version = installer.get_version()
            assert version == "6.2.7"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            version = installer.get_version()
            assert version is None

    @pytest.mark.asyncio
    async def test_test_connection(self):
        """Test Redis connection testing"""
        installer = RedisInstaller()

        # Mock successful connection
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "PONG", "")

            result = await installer.test_connection("localhost", 6379)
            assert result.success == True

        # Mock failed connection
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(1, "", "Could not connect")

            result = await installer.test_connection("localhost", 6379)
            assert result.success == False

    @pytest.mark.asyncio
    async def test_start_service(self):
        """Test Redis service start"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.start_service()
                assert result.success == True

    @pytest.mark.asyncio
    async def test_stop_service(self):
        """Test Redis service stop"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.stop_service()
                assert result.success == True

    @pytest.mark.asyncio
    async def test_get_service_status(self):
        """Test Redis service status check"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "RUNNING", "")

                status = await installer.get_service_status()
                assert status == "running"

    def test_get_default_port(self):
        """Test default port retrieval"""
        installer = RedisInstaller()
        assert installer.get_default_port() == 6379

    def test_get_config_template(self):
        """Test configuration template"""
        installer = RedisInstaller()
        config = installer.get_config_template()
        assert "host" in config
        assert "port" in config
        assert config["port"] == 6379

    @pytest.mark.asyncio
    async def test_installation_error_handling(self):
        """Test error handling during installation"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", "error")

                result = await installer.install()
                assert result.success == False
                assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_download_redis_windows(self):
        """Test Windows Redis download"""
        installer = RedisInstaller()

        with patch("urllib.request.urlretrieve") as mock_download:
            mock_download.return_value = ("redis.zip", None)

            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = await installer._download_redis_windows()
                assert download_path.suffix == ".zip"

    @pytest.mark.asyncio
    async def test_extract_redis_windows(self):
        """Test Windows Redis extraction"""
        installer = RedisInstaller()

        with patch("zipfile.ZipFile") as mock_zip:
            mock_zip_instance = MagicMock()
            mock_zip.return_value.__enter__.return_value = mock_zip_instance

            with tempfile.TemporaryDirectory() as temp_dir:
                zip_path = Path(temp_dir) / "redis.zip"
                install_dir = await installer._extract_redis_windows(zip_path)
                mock_zip_instance.extractall.assert_called()

    @pytest.mark.asyncio
    async def test_create_redis_service_windows(self):
        """Test Windows Redis service creation"""
        installer = RedisInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "", "")

            redis_dir = Path("C:/Redis")
            await installer._create_redis_service(redis_dir)
            mock_run.assert_called()

    @pytest.mark.asyncio
    async def test_configure_redis(self):
        """Test Redis configuration"""
        installer = RedisInstaller()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="# Redis config"):
                with patch("pathlib.Path.write_text") as mock_write:
                    await installer.configure_redis(port=6380, maxmemory="256mb")
                    mock_write.assert_called()

    def test_get_redis_config_path(self):
        """Test Redis config path detection"""
        installer = RedisInstaller()

        with patch("platform.system", return_value="Windows"):
            config_path = installer._get_redis_config_path()
            assert "redis.conf" in config_path.name

        with patch("platform.system", return_value="Linux"):
            config_path = installer._get_redis_config_path()
            assert "redis.conf" in config_path.name

    @pytest.mark.asyncio
    async def test_backup_redis_data(self):
        """Test Redis data backup"""
        installer = RedisInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "OK", "")

            with patch("shutil.copy2") as mock_copy:
                with tempfile.TemporaryDirectory() as temp_dir:
                    backup_path = Path(temp_dir) / "backup"
                    result = await installer.backup_redis_data(backup_path)
                    assert result.success == True

    @pytest.mark.asyncio
    async def test_restore_redis_data(self):
        """Test Redis data restore"""
        installer = RedisInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "OK", "")

            with patch("shutil.copy2") as mock_copy:
                with tempfile.TemporaryDirectory() as temp_dir:
                    backup_path = Path(temp_dir) / "dump.rdb"
                    backup_path.touch()
                    result = await installer.restore_redis_data(backup_path)
                    assert result.success == True

    @pytest.mark.asyncio
    async def test_flush_redis_data(self):
        """Test Redis data flush"""
        installer = RedisInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "OK", "")

            result = await installer.flush_redis_data()
            assert result.success == True

    @pytest.mark.asyncio
    async def test_get_redis_info(self):
        """Test Redis info retrieval"""
        installer = RedisInstaller()

        mock_info = """# Server
redis_version:6.2.7
uptime_in_seconds:12345
"""

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, mock_info, "")

            info = await installer.get_redis_info()
            assert "redis_version" in info
            assert "uptime_in_seconds" in info


class TestRedisDependencies:
    """Test Redis dependency management"""

    def test_dependency_list(self):
        """Test dependency requirements"""
        installer = RedisInstaller()
        deps = installer.dependencies

        # Should be a list (may be empty for Redis)
        assert isinstance(deps, list)

    def test_space_requirements(self):
        """Test disk space requirements"""
        installer = RedisInstaller()
        space = installer.required_space

        # Should require reasonable space (in MB)
        assert space > 10  # At least 10MB
        assert space < 1000  # Less than 1GB


class TestRedisUtilities:
    """Test Redis utility functions"""

    def test_connection_string_generation(self):
        """Test connection string generation"""
        installer = RedisInstaller()

        conn_str = installer.get_connection_string(host="localhost", port=6379, password="secret")

        assert "redis://" in conn_str
        assert "localhost" in conn_str
        assert "6379" in conn_str

    def test_validate_config(self):
        """Test configuration validation"""
        installer = RedisInstaller()

        # Valid config
        valid_config = {"host": "localhost", "port": 6379}

        is_valid = installer.validate_config(valid_config)
        assert is_valid == True

        # Invalid config (invalid port)
        invalid_config = {"host": "localhost", "port": "invalid"}

        is_valid = installer.validate_config(invalid_config)
        assert is_valid == False

    def test_get_installation_info(self):
        """Test installation information"""
        installer = RedisInstaller()
        info = installer.get_installation_info()

        assert "name" in info
        assert "version" in info
        assert "description" in info
        assert info["name"] == "Redis"


# Fixtures
@pytest.fixture
def redis_installer():
    """Create Redis installer instance"""
    return RedisInstaller()


@pytest.fixture
def test_environment():
    """Create test environment"""
    env = create_test_env()
    env.config_dir.mkdir(parents=True, exist_ok=True)
    env.data_dir.mkdir(parents=True, exist_ok=True)
    yield env
    env.cleanup()


# Parametrized tests
@pytest.mark.parametrize(
    "platform,expected_service", [("Windows", "Redis"), ("Linux", "redis-server"), ("Darwin", "redis")]
)
def test_service_name_by_platform(platform, expected_service):
    """Test service name detection by platform"""
    installer = RedisInstaller()

    with patch("platform.system", return_value=platform):
        service_name = installer._get_service_name()
        assert expected_service.lower() in service_name.lower()


@pytest.mark.parametrize(
    "version_output,expected",
    [
        ("Redis server v=6.2.7", "6.2.7"),
        ("Redis server v=5.0.8", "5.0.8"),
        ("Redis server v=7.0.2", "7.0.2"),
        ("invalid output", None),
    ],
)
def test_version_parsing(version_output, expected):
    """Test version string parsing"""
    installer = RedisInstaller()

    with patch("subprocess.run") as mock_run:
        if expected is None:
            mock_run.side_effect = FileNotFoundError()
        else:
            mock_run.return_value = MockSubprocessResult(0, version_output, "")

        parsed_version = installer.get_version()
        assert parsed_version == expected


@pytest.mark.parametrize(
    "config_option,value", [("port", 6380), ("maxmemory", "512mb"), ("timeout", 300), ("save", "900 1")]
)
def test_config_options(config_option, value):
    """Test Redis configuration options"""
    installer = RedisInstaller()

    config_template = installer.get_config_template()

    # Should be able to set various config options
    config_template[config_option] = value

    # Validate config should handle these options
    is_valid = installer.validate_config(config_template)
    assert is_valid == True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
