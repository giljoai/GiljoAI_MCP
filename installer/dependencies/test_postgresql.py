"""
Test script for PostgreSQL installer on Windows.

This script validates the PostgreSQL installer implementation
without actually performing a full installation.
"""

import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import tempfile

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer.dependencies.postgresql import PostgreSQLInstaller, PostgreSQLConfig, InstallationStatus


class TestPostgreSQLConfig(unittest.TestCase):
    """Test PostgreSQL configuration dataclass."""

    def test_default_config(self):
        """Test default configuration values."""
        config = PostgreSQLConfig()

        self.assertEqual(config.version, "15.4")
        self.assertEqual(config.port, 5432)
        self.assertEqual(config.database_name, "giljo_mcp")
        self.assertEqual(config.database_user, "giljo")
        self.assertEqual(config.superuser, "postgres")
        self.assertTrue(config.enable_service)

    def test_custom_config(self):
        """Test custom configuration values."""
        config = PostgreSQLConfig(version="16.0", port=5433, database_name="test_db", database_user="test_user")

        self.assertEqual(config.version, "16.0")
        self.assertEqual(config.port, 5433)
        self.assertEqual(config.database_name, "test_db")
        self.assertEqual(config.database_user, "test_user")


class TestPostgreSQLInstaller(unittest.TestCase):
    """Test PostgreSQL installer functionality."""

    def setUp(self):
        """Set up test fixtures."""
        self.config = PostgreSQLConfig(
            version="15.4", database_name="test_giljo_mcp", database_user="test_giljo", port=5433
        )
        self.installer = PostgreSQLInstaller(self.config)

    def test_initialization(self):
        """Test installer initialization."""
        self.assertEqual(self.installer.status, InstallationStatus.NOT_STARTED)
        self.assertEqual(self.installer.progress, 0)
        self.assertIsNone(self.installer.connection_string)
        self.assertTrue(self.installer.temp_dir.exists())

    def test_get_system_architecture(self):
        """Test system architecture detection."""
        arch = self.installer.get_system_architecture()
        self.assertIn(arch, ["x86_64", "x86"])

    @patch("installer.dependencies.postgresql.Path.exists")
    def test_is_postgresql_installed_by_directory(self, mock_exists):
        """Test PostgreSQL installation detection by directory."""
        # Test when PostgreSQL is installed
        mock_exists.return_value = True
        self.assertTrue(self.installer.is_postgresql_installed())

        # Test when PostgreSQL is not installed
        mock_exists.return_value = False
        self.assertFalse(self.installer.is_postgresql_installed())

    def test_generate_passwords(self):
        """Test password generation."""
        self.installer.config.superuser_password = ""
        self.installer.config.database_password = ""

        self.installer.generate_passwords()

        # Check passwords were generated
        self.assertNotEqual(self.installer.config.superuser_password, "")
        self.assertNotEqual(self.installer.config.database_password, "")

        # Check password complexity
        self.assertGreaterEqual(len(self.installer.config.superuser_password), 16)
        self.assertGreaterEqual(len(self.installer.config.database_password), 16)

    def test_download_urls(self):
        """Test that download URLs are properly configured."""
        # Check that URLs exist for supported versions
        for version in ["15.4", "15.5", "16.0"]:
            self.assertIn(version, PostgreSQLInstaller.DOWNLOAD_URLS)

            # Check both architectures
            for arch in ["x86_64", "x86"]:
                url = PostgreSQLInstaller.DOWNLOAD_URLS[version][arch]
                self.assertTrue(url.startswith("https://"))
                self.assertIn("postgresql", url.lower())
                self.assertIn(version, url)

    @patch("installer.dependencies.postgresql.urllib.request.urlretrieve")
    def test_download_installer(self, mock_urlretrieve):
        """Test installer download functionality."""

        # Mock successful download
        def side_effect(url, path, hook):
            # Simulate progress callback
            hook(0, 1024, 10240)
            hook(5, 1024, 10240)
            hook(10, 1024, 10240)

            # Create a dummy file
            with open(path, "w") as f:
                f.write("dummy installer content")
            return path

        mock_urlretrieve.side_effect = side_effect

        # Test download
        progress_values = []

        def progress_callback(progress, message):
            progress_values.append(progress)

        result = self.installer.download_installer(progress_callback)

        self.assertIsNotNone(result)
        self.assertEqual(self.installer.status, InstallationStatus.DOWNLOADING)
        self.assertGreater(len(progress_values), 0)

    @patch("installer.dependencies.postgresql.Path.stat")
    def test_verify_installer(self, mock_stat):
        """Test installer verification."""
        # Set up installer path
        self.installer.installer_path = Path(tempfile.gettempdir()) / "test.exe"

        # Create a temporary file
        with open(self.installer.installer_path, "w") as f:
            f.write("x" * (200 * 1024 * 1024))  # Simulate 200MB file

        # Mock file size
        mock_stat_result = Mock()
        mock_stat_result.st_size = 200 * 1024 * 1024
        mock_stat.return_value = mock_stat_result

        # Test verification
        result = self.installer.verify_installer()
        self.assertTrue(result)
        self.assertEqual(self.installer.status, InstallationStatus.VERIFYING)

        # Clean up
        if self.installer.installer_path.exists():
            self.installer.installer_path.unlink()

    def test_get_status(self):
        """Test status reporting."""
        self.installer.status = InstallationStatus.INSTALLING
        self.installer.progress = 50
        self.installer.message = "Installing..."
        self.installer.connection_string = "postgresql://test"

        status = self.installer.get_status()

        self.assertEqual(status["status"], "installing")
        self.assertEqual(status["progress"], 50)
        self.assertEqual(status["message"], "Installing...")
        self.assertEqual(status["connection_string"], "postgresql://test")

        # Check config details
        self.assertEqual(status["config"]["version"], "15.4")
        self.assertEqual(status["config"]["port"], 5433)
        self.assertEqual(status["config"]["database"], "test_giljo_mcp")

    @patch("installer.dependencies.postgresql.subprocess.run")
    def test_configure_postgresql(self, mock_run):
        """Test PostgreSQL configuration."""
        # Mock subprocess results
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        # Generate passwords first
        self.installer.generate_passwords()

        # Test configuration
        result = self.installer.configure_postgresql()

        # Should attempt to create user and database
        self.assertTrue(mock_run.called)
        self.assertEqual(self.installer.status, InstallationStatus.CONFIGURING)

    @patch("installer.dependencies.postgresql.subprocess.run")
    def test_test_connection(self, mock_run):
        """Test connection testing."""
        # Mock successful connection
        mock_run.return_value = Mock(returncode=0, stdout="PostgreSQL 15.4", stderr="")

        # Generate passwords
        self.installer.generate_passwords()

        # Test connection
        success, conn_str = self.installer.test_connection()

        self.assertTrue(success)
        self.assertIsNotNone(conn_str)
        self.assertIn("postgresql://", conn_str)
        self.assertIn(self.installer.config.database_name, conn_str)
        self.assertEqual(self.installer.status, InstallationStatus.COMPLETED)

    @patch("installer.dependencies.postgresql.subprocess.run")
    def test_restart_service(self, mock_run):
        """Test service restart functionality."""
        # Mock successful service commands
        mock_run.return_value = Mock(returncode=0, stdout="", stderr="")

        result = self.installer._restart_service()

        self.assertTrue(result)
        # Should call net stop and net start
        self.assertEqual(mock_run.call_count, 2)


class TestIntegrationPoints(unittest.TestCase):
    """Test integration points with other components."""

    def test_connection_string_format(self):
        """Test that connection string follows expected format."""
        config = PostgreSQLConfig(
            database_name="giljo_mcp", database_user="giljo", database_password="test_password", port=5432
        )

        installer = PostgreSQLInstaller(config)
        installer.test_connection()

        expected = "postgresql://giljo:test_password@localhost:5432/giljo_mcp"
        self.assertEqual(installer.connection_string, expected)

    def test_profile_system_compatibility(self):
        """Test compatibility with profile system requirements."""
        from installer.core.profile import ProfileType, ProfileManager

        # Get network shared profile (requires PostgreSQL)
        manager = ProfileManager()
        profile = manager.get_profile(ProfileType.NETWORK_SHARED)

        # Verify PostgreSQL is in external services
        self.assertIn("postgresql", profile.dependencies.external_services)

        # Create installer config based on profile
        config = PostgreSQLConfig(
            database_name="giljo_mcp",
            port=5432,
            max_connections=profile.configuration.performance_settings.get("connection_pool_size", 20),
        )

        installer = PostgreSQLInstaller(config)

        # Verify configuration matches profile requirements
        self.assertEqual(config.database_name, "giljo_mcp")
        self.assertEqual(config.port, 5432)


def suite():
    """Create test suite."""
    loader = unittest.TestLoader()
    test_suite = unittest.TestSuite()

    test_suite.addTests(loader.loadTestsFromTestCase(TestPostgreSQLConfig))
    test_suite.addTests(loader.loadTestsFromTestCase(TestPostgreSQLInstaller))
    test_suite.addTests(loader.loadTestsFromTestCase(TestIntegrationPoints))

    return test_suite


if __name__ == "__main__":
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite())

    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)
