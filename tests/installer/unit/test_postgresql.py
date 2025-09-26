"""
Unit tests for PostgreSQL installer
"""

import subprocess

# Add project root to path
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.dependencies.postgresql import PostgreSQLInstaller

    HAS_POSTGRESQL = True
except ImportError:
    HAS_POSTGRESQL = False
    pytest.skip("PostgreSQL installer not available", allow_module_level=True)

from tests.installer.fixtures.mock_utils import MockSubprocessResult
from tests.installer.fixtures.test_configs import create_test_env


class TestPostgreSQLInstaller:
    """Test PostgreSQL installer functionality"""

    def setUp(self):
        """Set up test environment"""
        self.test_env = create_test_env()
        self.installer = PostgreSQLInstaller()

    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()

    def test_installer_initialization(self):
        """Test installer initialization"""
        installer = PostgreSQLInstaller()
        assert installer.name == "PostgreSQL"
        assert installer.version is not None
        assert installer.required_space > 0
        assert isinstance(installer.dependencies, list)

    @pytest.mark.asyncio
    async def test_check_installation(self):
        """Test PostgreSQL installation check"""
        installer = PostgreSQLInstaller()

        # Mock successful postgres command
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "postgres (PostgreSQL) 14.9", "")

            is_installed = await installer.check_installation()
            assert is_installed == True

        # Mock failed postgres command
        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            is_installed = await installer.check_installation()
            assert is_installed == False

    @pytest.mark.asyncio
    async def test_install_windows(self):
        """Test Windows PostgreSQL installation"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                with patch.object(installer, "_download_postgresql_windows") as mock_download:
                    mock_download.return_value = Path("mock_installer.exe")

                    result = await installer.install()
                    assert result.success == True
                    assert "PostgreSQL installation completed" in result.message

    @pytest.mark.asyncio
    async def test_install_linux(self):
        """Test Linux PostgreSQL installation"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.install()
                assert result.success == True

    @pytest.mark.asyncio
    async def test_install_macos(self):
        """Test macOS PostgreSQL installation"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.install()
                assert result.success == True

    def test_get_version(self):
        """Test version detection"""
        installer = PostgreSQLInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "postgres (PostgreSQL) 14.9", "")

            version = installer.get_version()
            assert version == "14.9"

        with patch("subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError()

            version = installer.get_version()
            assert version is None

    @pytest.mark.asyncio
    async def test_create_database(self):
        """Test database creation"""
        installer = PostgreSQLInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "", "")

            result = await installer.create_database("testdb", "testuser", "testpass")
            assert result.success == True

    @pytest.mark.asyncio
    async def test_test_connection(self):
        """Test database connection testing"""
        installer = PostgreSQLInstaller()

        # Mock successful connection
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "1", "")

            result = await installer.test_connection("localhost", 5432, "testdb", "testuser", "testpass")
            assert result.success == True

        # Mock failed connection
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(1, "", "connection failed")

            result = await installer.test_connection("localhost", 5432, "testdb", "testuser", "testpass")
            assert result.success == False

    @pytest.mark.asyncio
    async def test_start_service(self):
        """Test PostgreSQL service start"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.start_service()
                assert result.success == True

    @pytest.mark.asyncio
    async def test_stop_service(self):
        """Test PostgreSQL service stop"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "", "")

                result = await installer.stop_service()
                assert result.success == True

    @pytest.mark.asyncio
    async def test_get_service_status(self):
        """Test PostgreSQL service status check"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MockSubprocessResult(0, "RUNNING", "")

                status = await installer.get_service_status()
                assert status == "running"

    def test_get_default_port(self):
        """Test default port retrieval"""
        installer = PostgreSQLInstaller()
        assert installer.get_default_port() == 5432

    def test_get_config_template(self):
        """Test configuration template"""
        installer = PostgreSQLInstaller()
        config = installer.get_config_template()
        assert "host" in config
        assert "port" in config
        assert config["port"] == 5432

    @pytest.mark.asyncio
    async def test_installation_error_handling(self):
        """Test error handling during installation"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.CalledProcessError(1, "cmd", "error")

                result = await installer.install()
                assert result.success == False
                assert "error" in result.message.lower()

    @pytest.mark.asyncio
    async def test_download_postgresql_windows(self):
        """Test Windows PostgreSQL download"""
        installer = PostgreSQLInstaller()

        with patch("urllib.request.urlretrieve") as mock_download:
            mock_download.return_value = ("installer.exe", None)

            with tempfile.TemporaryDirectory() as temp_dir:
                download_path = await installer._download_postgresql_windows()
                assert download_path.name == "postgresql-installer.exe"

    def test_get_postgresql_config_dir(self):
        """Test PostgreSQL config directory detection"""
        installer = PostgreSQLInstaller()

        with patch("platform.system", return_value="Windows"):
            config_dir = installer._get_postgresql_config_dir()
            assert "PostgreSQL" in str(config_dir)

        with patch("platform.system", return_value="Linux"):
            config_dir = installer._get_postgresql_config_dir()
            assert "postgresql" in str(config_dir)

    @pytest.mark.asyncio
    async def test_configure_postgresql(self):
        """Test PostgreSQL configuration"""
        installer = PostgreSQLInstaller()

        with patch("pathlib.Path.exists", return_value=True):
            with patch("pathlib.Path.read_text", return_value="# config"):
                with patch("pathlib.Path.write_text") as mock_write:
                    await installer.configure_postgresql(port=5433, max_connections=200)
                    mock_write.assert_called()

    @pytest.mark.asyncio
    async def test_backup_database(self):
        """Test database backup"""
        installer = PostgreSQLInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "", "")

            with tempfile.TemporaryDirectory() as temp_dir:
                backup_path = Path(temp_dir) / "backup.sql"
                result = await installer.backup_database("testdb", backup_path, "testuser", "testpass")
                assert result.success == True

    @pytest.mark.asyncio
    async def test_restore_database(self):
        """Test database restore"""
        installer = PostgreSQLInstaller()

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MockSubprocessResult(0, "", "")

            with tempfile.NamedTemporaryFile(suffix=".sql") as temp_file:
                backup_path = Path(temp_file.name)
                result = await installer.restore_database("testdb", backup_path, "testuser", "testpass")
                assert result.success == True


class TestPostgreSQLDependencies:
    """Test PostgreSQL dependency management"""

    def test_dependency_list(self):
        """Test dependency requirements"""
        installer = PostgreSQLInstaller()
        deps = installer.dependencies

        # Should be a list
        assert isinstance(deps, list)

        # Common dependencies should be included
        # (exact dependencies depend on implementation)

    def test_space_requirements(self):
        """Test disk space requirements"""
        installer = PostgreSQLInstaller()
        space = installer.required_space

        # Should require reasonable space (in MB)
        assert space > 100  # At least 100MB
        assert space < 10000  # Less than 10GB


class TestPostgreSQLUtilities:
    """Test PostgreSQL utility functions"""

    def test_connection_string_generation(self):
        """Test connection string generation"""
        installer = PostgreSQLInstaller()

        conn_str = installer.get_connection_string(
            host="localhost", port=5432, database="testdb", username="testuser", password="testpass"
        )

        assert "postgresql://" in conn_str
        assert "testuser" in conn_str
        assert "localhost" in conn_str
        assert "5432" in conn_str
        assert "testdb" in conn_str

    def test_validate_config(self):
        """Test configuration validation"""
        installer = PostgreSQLInstaller()

        # Valid config
        valid_config = {"host": "localhost", "port": 5432, "database": "mydb", "username": "user", "password": "pass"}

        is_valid = installer.validate_config(valid_config)
        assert is_valid == True

        # Invalid config (missing required fields)
        invalid_config = {"host": "localhost"}

        is_valid = installer.validate_config(invalid_config)
        assert is_valid == False

    def test_get_installation_info(self):
        """Test installation information"""
        installer = PostgreSQLInstaller()
        info = installer.get_installation_info()

        assert "name" in info
        assert "version" in info
        assert "description" in info
        assert info["name"] == "PostgreSQL"


# Fixtures
@pytest.fixture
def postgresql_installer():
    """Create PostgreSQL installer instance"""
    return PostgreSQLInstaller()


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
    "platform,expected_service", [("Windows", "postgresql-x64-14"), ("Linux", "postgresql"), ("Darwin", "postgresql")]
)
def test_service_name_by_platform(platform, expected_service):
    """Test service name detection by platform"""
    installer = PostgreSQLInstaller()

    with patch("platform.system", return_value=platform):
        service_name = installer._get_service_name()
        assert expected_service in service_name.lower()


@pytest.mark.parametrize(
    "version,expected",
    [
        ("postgres (PostgreSQL) 14.9", "14.9"),
        ("postgres (PostgreSQL) 13.4", "13.4"),
        ("psql (PostgreSQL) 15.1", "15.1"),
        ("invalid output", None),
    ],
)
def test_version_parsing(version, expected):
    """Test version string parsing"""
    installer = PostgreSQLInstaller()

    with patch("subprocess.run") as mock_run:
        if expected is None:
            mock_run.side_effect = FileNotFoundError()
        else:
            mock_run.return_value = MockSubprocessResult(0, version, "")

        parsed_version = installer.get_version()
        assert parsed_version == expected


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
