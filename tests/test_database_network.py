"""
Unit tests for PostgreSQL network configuration module
Tests network access setup, backup/restore, and configuration modification
"""

import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from installer.core.database_network import DatabaseNetworkConfig


class TestDatabaseNetworkConfig(unittest.TestCase):
    """Test DatabaseNetworkConfig class"""

    def setUp(self):
        """Set up test fixtures"""
        self.test_dir = Path(tempfile.mkdtemp())
        self.config_dir = self.test_dir / "postgresql_config"
        self.config_dir.mkdir()

        # Create mock PostgreSQL config files
        self.postgresql_conf = self.config_dir / "postgresql.conf"
        self.pg_hba_conf = self.config_dir / "pg_hba.conf"

        # Write sample configurations
        self.postgresql_conf.write_text("""
# PostgreSQL configuration file
listen_addresses = 'localhost'
port = 5432
max_connections = 50
""")

        self.pg_hba_conf.write_text("""
# PostgreSQL Client Authentication Configuration File
local   all             all                                     trust
host    all             all             127.0.0.1/32            trust
host    all             all             ::1/128                 trust
""")

        # Test settings
        self.settings = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_user": "postgres",
            "pg_password": "test",
            "mode": "server",
            "bind": "0.0.0.0",
            "ssl_enabled": False,
            "batch": True,  # Suppress interactive prompts
        }

    def tearDown(self):
        """Clean up test fixtures"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_initialization(self):
        """Test DatabaseNetworkConfig initialization"""
        config = DatabaseNetworkConfig(self.settings)

        self.assertEqual(config.pg_host, "localhost")
        self.assertEqual(config.pg_port, 5432)
        self.assertEqual(config.db_name, "giljo_mcp")
        self.assertEqual(config.bind_address, "0.0.0.0")
        self.assertFalse(config.allow_ssl_only)

    def test_default_allowed_networks(self):
        """Test default allowed network ranges"""
        config = DatabaseNetworkConfig(self.settings)

        expected_networks = ["192.168.0.0/16", "10.0.0.0/8", "172.16.0.0/12"]

        self.assertEqual(config.allowed_networks, expected_networks)

    def test_custom_allowed_networks(self):
        """Test custom allowed network ranges"""
        self.settings["allowed_networks"] = ["192.168.1.0/24"]
        config = DatabaseNetworkConfig(self.settings)

        self.assertEqual(config.allowed_networks, ["192.168.1.0/24"])

    def test_backup_configs(self):
        """Test configuration file backup"""
        config = DatabaseNetworkConfig(self.settings)
        config.pg_config_dir = self.config_dir
        config.postgresql_conf = self.postgresql_conf
        config.pg_hba_conf = self.pg_hba_conf

        # Create backup directory
        config.backup_dir = self.test_dir / "backups"
        config.backup_dir.mkdir()

        # Run backup
        result = config.backup_configs()

        self.assertTrue(result["success"])
        self.assertEqual(len(result["backups"]), 2)

        # Verify backup files exist
        self.assertTrue((config.backup_dir / "postgresql.conf").exists())
        self.assertTrue((config.backup_dir / "pg_hba.conf").exists())
        self.assertTrue((config.backup_dir / "README.txt").exists())

    def test_configure_postgresql_conf(self):
        """Test postgresql.conf modification"""
        config = DatabaseNetworkConfig(self.settings)
        config.postgresql_conf = self.postgresql_conf

        # Run configuration
        result = config.configure_postgresql_conf()

        self.assertTrue(result["success"])

        # Verify changes
        content = self.postgresql_conf.read_text()
        self.assertIn("listen_addresses = '*'", content)
        self.assertIn("max_connections = 100", content)
        self.assertIn("GiljoAI MCP Server Mode Configuration", content)

    def test_configure_postgresql_conf_specific_bind(self):
        """Test postgresql.conf with specific bind address"""
        self.settings["bind"] = "192.168.1.10"
        config = DatabaseNetworkConfig(self.settings)
        config.postgresql_conf = self.postgresql_conf

        # Run configuration
        result = config.configure_postgresql_conf()

        self.assertTrue(result["success"])

        # Verify changes
        content = self.postgresql_conf.read_text()
        self.assertIn("listen_addresses = 'localhost,192.168.1.10'", content)

    def test_configure_pg_hba_conf(self):
        """Test pg_hba.conf modification"""
        config = DatabaseNetworkConfig(self.settings)
        config.pg_hba_conf = self.pg_hba_conf

        # Run configuration
        result = config.configure_pg_hba_conf()

        self.assertTrue(result["success"])

        # Verify changes
        content = self.pg_hba_conf.read_text()
        self.assertIn("GiljoAI MCP Server Mode", content)
        self.assertIn("host       giljo_mcp    giljo_user    192.168.0.0/16    scram-sha-256", content)
        self.assertIn("host       giljo_mcp    giljo_user    10.0.0.0/8    scram-sha-256", content)

    def test_configure_pg_hba_conf_ssl_only(self):
        """Test pg_hba.conf with SSL enforcement"""
        self.settings["ssl_enabled"] = True
        config = DatabaseNetworkConfig(self.settings)
        config.allow_ssl_only = True
        config.pg_hba_conf = self.pg_hba_conf

        # Run configuration
        result = config.configure_pg_hba_conf()

        self.assertTrue(result["success"])

        # Verify SSL entries
        content = self.pg_hba_conf.read_text()
        self.assertIn("hostssl    giljo_mcp    giljo_user", content)
        self.assertNotIn("host       giljo_mcp    giljo_user", content)

    def test_configure_pg_hba_conf_warnings(self):
        """Test pg_hba.conf generates warnings for non-SSL"""
        config = DatabaseNetworkConfig(self.settings)
        config.pg_hba_conf = self.pg_hba_conf

        # Run configuration
        result = config.configure_pg_hba_conf()

        self.assertTrue(result["success"])
        self.assertGreater(len(result["warnings"]), 0)
        self.assertTrue(any("SSL" in warning for warning in result["warnings"]))

    def test_restore_configs(self):
        """Test configuration restoration"""
        config = DatabaseNetworkConfig(self.settings)
        config.pg_config_dir = self.config_dir
        config.postgresql_conf = self.postgresql_conf
        config.pg_hba_conf = self.pg_hba_conf

        # Create backup
        config.backup_dir = self.test_dir / "backups"
        config.backup_dir.mkdir()
        backup_result = config.backup_configs()
        config.backups_created = backup_result["backups"]

        # Modify files
        self.postgresql_conf.write_text("modified content")
        self.pg_hba_conf.write_text("modified content")

        # Restore
        result = config.restore_configs()

        self.assertTrue(result["success"])

        # Verify restoration
        self.assertNotEqual(self.postgresql_conf.read_text(), "modified content")
        self.assertNotEqual(self.pg_hba_conf.read_text(), "modified content")

    def test_generate_restore_scripts(self):
        """Test restoration script generation"""
        config = DatabaseNetworkConfig(self.settings)
        config.pg_config_dir = self.config_dir
        config.backup_dir = self.test_dir / "backups"

        # Create scripts directory
        scripts_dir = self.test_dir / "scripts"
        scripts_dir.mkdir()

        # Generate scripts (mock the actual script generation)
        with patch.object(config, "_generate_windows_restore_script") as mock_windows:
            with patch.object(config, "_generate_unix_restore_script") as mock_unix:
                mock_windows.return_value = scripts_dir / "restore.ps1"
                mock_unix.return_value = scripts_dir / "restore.sh"

                result = config.generate_restore_scripts()

                self.assertTrue(result["success"])
                self.assertEqual(len(result["scripts"]), 2)
                mock_windows.assert_called_once()
                mock_unix.assert_called_once()

    @patch("installer.core.database_network.DatabaseNetworkConfig._confirm_network_exposure")
    @patch("installer.core.database_network.DatabaseNetworkConfig.find_pg_config_dir")
    def test_setup_remote_access_user_declined(self, mock_find_config, mock_confirm):
        """Test setup fails when user declines network exposure"""
        mock_confirm.return_value = False

        config = DatabaseNetworkConfig(self.settings)
        result = config.setup_remote_access()

        self.assertFalse(result["success"])
        self.assertGreater(len(result["errors"]), 0)
        self.assertIn("declined", result["errors"][0].lower())

    @patch("installer.core.database_network.DatabaseNetworkConfig._confirm_network_exposure")
    @patch("installer.core.database_network.DatabaseNetworkConfig.find_pg_config_dir")
    def test_setup_remote_access_config_not_found(self, mock_find_config, mock_confirm):
        """Test setup fails when config directory not found"""
        mock_confirm.return_value = True
        mock_find_config.return_value = {"success": False, "errors": ["Config directory not found"]}

        config = DatabaseNetworkConfig(self.settings)
        result = config.setup_remote_access()

        self.assertFalse(result["success"])
        self.assertGreater(len(result["errors"]), 0)

    def test_batch_mode_consent(self):
        """Test batch mode automatically grants consent"""
        self.settings["batch"] = True
        config = DatabaseNetworkConfig(self.settings)

        # Should return True without prompting
        consent = config._confirm_network_exposure()
        self.assertTrue(consent)


class TestConfigurationDetection(unittest.TestCase):
    """Test PostgreSQL configuration directory detection"""

    def setUp(self):
        """Set up test fixtures"""
        self.settings = {"pg_host": "localhost", "pg_port": 5432, "batch": True}

    @patch("platform.system")
    def test_find_pg_config_dir_windows(self, mock_platform):
        """Test config directory detection on Windows"""
        mock_platform.return_value = "Windows"

        config = DatabaseNetworkConfig(self.settings)

        # This will fail in test environment but should return proper structure
        result = config.find_pg_config_dir()

        # Verify result structure
        self.assertIn("success", result)
        if not result["success"]:
            self.assertIn("errors", result)

    @patch("platform.system")
    def test_find_pg_config_dir_linux(self, mock_platform):
        """Test config directory detection on Linux"""
        mock_platform.return_value = "Linux"

        config = DatabaseNetworkConfig(self.settings)
        result = config.find_pg_config_dir()

        # Verify result structure
        self.assertIn("success", result)
        if not result["success"]:
            self.assertIn("errors", result)


if __name__ == "__main__":
    # Run tests
    unittest.main(verbosity=2)
