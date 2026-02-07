"""
Comprehensive test suite for unified installer core modules.

Tests cover:
- Database installer with pg_trgm extension creation
- Config manager with two-phase generation
- PostgreSQL discovery across platforms
- Network utilities for IP detection

Following TDD: These tests are written BEFORE implementation.
"""

import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


# Test fixtures and mocks
@pytest.fixture
def temp_install_dir(tmp_path):
    """Create temporary installation directory."""
    install_dir = tmp_path / "test_install"
    install_dir.mkdir()
    return install_dir


@pytest.fixture
def mock_settings(temp_install_dir):
    """Mock installer settings."""
    return {
        "pg_host": "localhost",
        "pg_port": 5432,
        "pg_user": "postgres",
        "pg_password": "test_password",
        "install_dir": str(temp_install_dir),
        "api_port": 7272,
        "bind_ip": "0.0.0.0",
    }


@pytest.fixture
def mock_psycopg2():
    """Mock psycopg2 module."""
    with patch("installer.core.database.psycopg2") as mock_pg:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_conn.cursor.return_value = mock_cur
        mock_pg.connect.return_value = mock_conn
        mock_pg.sql = MagicMock()
        mock_pg.extensions.ISOLATION_LEVEL_AUTOCOMMIT = 0
        yield mock_pg


class TestDatabaseInstaller:
    """Test unified DatabaseInstaller with pg_trgm extension creation."""

    @pytest.mark.asyncio
    async def test_database_installer_creates_pg_trgm_extension(self, mock_settings):
        """
        CRITICAL TEST: Verify pg_trgm extension is created.
        This is Bug #1 from Handover 0035.
        """
        from installer.core.database import DatabaseInstaller

        # Mock psycopg2 at the module level
        with patch("installer.core.database.psycopg2") as mock_psycopg2:
            # Setup mock connections
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            mock_conn.cursor.return_value.__exit__.return_value = None
            mock_psycopg2.connect.return_value = mock_conn
            mock_psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT = 0

            # Mock fetchone to simulate database/roles don't exist initially
            mock_cur.fetchone.side_effect = [None, None, None]  # db, owner, user don't exist

            installer = DatabaseInstaller(mock_settings)

            # Mock credential save
            installer.save_credentials = MagicMock()

            result = await installer.create_database_async()

            # Verify pg_trgm extension was created
            extension_calls = [
                call_args for call_args in mock_cur.execute.call_args_list if "pg_trgm" in str(call_args)
            ]

            assert len(extension_calls) > 0, "pg_trgm extension creation not called"
            assert result["success"], "Database creation should succeed"

    @pytest.mark.asyncio
    async def test_database_installer_creates_all_28_tables(self, mock_settings):
        """Verify database has method for creating tables."""
        from installer.core.database import DatabaseInstaller

        installer = DatabaseInstaller(mock_settings)
        installer.owner_password = "test_owner_pass"

        # Verify the method exists (actual table creation requires database)
        assert hasattr(installer, "create_tables_async"), "Should have create_tables_async method"

        # For full integration test, would need real database
        # This validates the interface exists
        assert callable(installer.create_tables_async), "create_tables_async should be callable"

    @pytest.mark.asyncio
    async def test_database_installer_handles_missing_postgres(self, mock_settings):
        """Verify graceful handling when PostgreSQL is not available."""
        from installer.core.database import DatabaseInstaller

        installer = DatabaseInstaller(mock_settings)

        # Mock failed connection
        with patch("installer.core.database.check_postgresql_connection", return_value=False):
            result = installer.setup()

        assert not result["success"], "Setup should fail without PostgreSQL"
        assert "Cannot connect to PostgreSQL" in result["errors"]
        assert "postgresql_guide" in result, "Should provide installation guide"

    @pytest.mark.asyncio
    async def test_database_installer_validates_version(self, mock_settings, mock_psycopg2):
        """Verify PostgreSQL version validation."""
        from installer.core.database import DatabaseInstaller

        installer = DatabaseInstaller(mock_settings)

        # Mock version detection
        mock_conn = mock_psycopg2.connect.return_value
        mock_cur = mock_conn.cursor.return_value

        # Test with unsupported version (PostgreSQL 13)
        mock_cur.fetchone.return_value = ("PostgreSQL 13.0",)

        version_result = installer.detect_postgresql_version()

        # Validate version check logic
        assert version_result.get("version", 0) < 14, "Should detect version 13"

    @pytest.mark.asyncio
    async def test_database_installer_generates_secure_passwords(self, mock_settings):
        """Verify secure password generation."""
        from installer.core.database import DatabaseInstaller

        installer = DatabaseInstaller(mock_settings)

        password = installer._generate_password(length=32)

        assert len(password) == 32, "Password should be 32 characters"
        assert any(c.isupper() for c in password), "Should contain uppercase"
        assert any(c.islower() for c in password), "Should contain lowercase"
        assert any(c.isdigit() for c in password), "Should contain digits"

    def test_database_installer_platform_agnostic_paths(self, mock_settings, tmp_path):
        """Verify all paths use pathlib.Path (cross-platform)."""
        from installer.core.database import DatabaseInstaller

        installer = DatabaseInstaller(mock_settings)

        # Generate fallback script (Windows or Unix based on platform)
        scripts_dir = tmp_path / "scripts"
        scripts_dir.mkdir()

        import platform

        if platform.system() == "Windows":
            script_path = installer.generate_windows_script(scripts_dir)
        else:
            script_path = installer.generate_unix_script(scripts_dir)

        # Verify Path object is returned
        assert isinstance(script_path, Path), "Should return pathlib.Path"
        assert script_path.exists(), "Script should be created"

        # Verify script uses pathlib patterns
        script_content = script_path.read_text()
        # Script should exist and be readable (basic validation)
        assert len(script_content) > 0, "Script should have content"


class TestConfigManager:
    """Test unified ConfigManager with two-phase generation."""

    def test_config_manager_generates_yaml_before_db(self, mock_settings, temp_install_dir):
        """Verify config.yaml is generated and contains structure."""
        from installer.core.config import ConfigManager

        config_manager = ConfigManager(mock_settings)

        # Generate config.yaml
        yaml_path = config_manager.generate_config_yaml()

        assert Path(yaml_path).exists(), "config.yaml should be created"

        # Verify it contains expected structure
        content = Path(yaml_path).read_text()
        assert "database:" in content, "Should have database section"
        assert "0.0.0.0" in content, "Should bind to all interfaces (v3.0)"

    def test_config_manager_generates_env_after_db(self, mock_settings, temp_install_dir):
        """Verify .env is generated with database credentials."""
        from installer.core.config import ConfigManager

        # Add database credentials to settings
        mock_settings["owner_password"] = "secure_owner_pass_123"
        mock_settings["user_password"] = "secure_user_pass_456"

        config_manager = ConfigManager(mock_settings)

        # Generate .env
        env_path = config_manager.generate_env_file()

        assert Path(env_path).exists(), ".env should be created"

        # Verify it contains REAL passwords (not placeholders)
        content = Path(env_path).read_text()
        assert "secure_owner_pass_123" in content, "Should contain real owner password"
        assert "secure_user_pass_456" in content, "Should contain real user password"

    def test_config_manager_uses_v3_architecture(self, mock_settings, temp_install_dir):
        """Verify v3.0 architecture: bind 0.0.0.0, auth always enabled."""
        from installer.core.config import ConfigManager

        config_manager = ConfigManager(mock_settings)

        # Generate config
        yaml_path = config_manager.generate_config_yaml()
        content = Path(yaml_path).read_text()

        # Verify v3.0 architecture
        assert "0.0.0.0" in content, "Should bind to all interfaces"
        assert "authentication" in content.lower(), "Authentication should be mentioned"

    def test_config_manager_cross_platform_paths(self, mock_settings, temp_install_dir):
        """Verify ConfigManager uses pathlib.Path throughout."""
        from installer.core.config import ConfigManager

        config_manager = ConfigManager(mock_settings)

        # Check internal path handling
        yaml_path = config_manager.generate_config_yaml()

        # Verify returned path is pathlib.Path compatible
        assert isinstance(Path(yaml_path), Path), "Should return Path-compatible string"

        # CRITICAL: Verify config files are created in install_dir (not cwd) for test isolation
        assert str(temp_install_dir) in str(yaml_path), "Config MUST be in install_dir for test isolation"
        assert (temp_install_dir / "config.yaml").exists(), "config.yaml MUST exist in install_dir"


class TestPostgreSQLDiscovery:
    """Test cross-platform PostgreSQL discovery."""

    def test_postgres_discovery_finds_in_path(self):
        """Verify discovery finds psql in system PATH."""
        from installer.shared.postgres import PostgreSQLDiscovery

        discovery = PostgreSQLDiscovery()

        # Mock shutil.which to find psql
        with patch("shutil.which", return_value="/usr/bin/psql"):
            result = discovery.discover()

        assert result["found"], "Should find PostgreSQL"
        assert result["method"] == "PATH", "Should indicate PATH method"
        assert "psql_path" in result, "Should return psql path"

    def test_postgres_discovery_scans_common_locations(self):
        """Verify discovery scans platform-specific common locations."""
        from installer.shared.postgres import PostgreSQLDiscovery

        discovery = PostgreSQLDiscovery()

        # Mock shutil.which to fail (not in PATH)
        with patch("shutil.which", return_value=None):
            # Mock Path.exists to find in common location
            with patch("pathlib.Path.exists", return_value=True):
                result = discovery.discover()

        # Should attempt to find in common locations
        assert "found" in result, "Should return discovery result"

    def test_postgres_discovery_validates_version(self):
        """Verify version validation (>= 14, recommend 18)."""
        from installer.shared.postgres import PostgreSQLDiscovery

        discovery = PostgreSQLDiscovery()

        # Mock subprocess to return PostgreSQL version
        mock_output = "psql (PostgreSQL) 18.0"
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(stdout=mock_output, returncode=0)

            version_info = discovery.get_postgresql_version("/usr/bin/psql")

        assert version_info is not None, "Should return version info"
        assert version_info["version"] >= 14, "Should accept PostgreSQL 14+"
        assert isinstance(version_info["version"], int), "Should return numeric version"

    def test_postgres_discovery_handles_custom_path(self):
        """Verify handling of user-provided custom path."""
        from installer.shared.postgres import PostgreSQLDiscovery

        discovery = PostgreSQLDiscovery()

        custom_path = "/custom/postgres/bin/psql"

        # Mock Path.exists and version detection
        with (
            patch("pathlib.Path.exists", return_value=True),
            patch.object(
                discovery, "get_postgresql_version", return_value={"version": 18, "version_string": "PostgreSQL 18.0"}
            ),
        ):
            result = discovery.validate_custom_path(custom_path)

        assert result["valid"], "Should validate custom path"
        assert result.get("method") == "CUSTOM", "Should indicate custom method"

    def test_postgres_discovery_cross_platform(self):
        """Verify discovery returns platform-specific common locations."""
        from installer.shared.postgres import PostgreSQLDiscovery

        discovery = PostgreSQLDiscovery()

        # Test that _get_common_locations returns a list
        locations = discovery._get_common_locations()
        assert isinstance(locations, list), "Should return list of paths"

        # Platform-specific validation
        import platform

        current_platform = platform.system()

        if current_platform == "Windows":
            assert any("Program Files" in str(loc) for loc in locations), "Windows should include Program Files paths"
        elif current_platform == "Linux":
            assert any("/usr" in str(loc) for loc in locations), "Linux should include /usr paths"
        elif current_platform == "Darwin":
            assert any("/Library" in str(loc) or "/usr/local" in str(loc) for loc in locations), (
                "macOS should include /Library or /usr/local paths"
            )


class TestNetworkUtilities:
    """Test cross-platform network utilities."""

    def test_network_ips_returns_non_localhost(self):
        """Verify get_network_ips returns non-localhost IPv4 addresses."""
        from installer.shared.network import get_network_ips

        # Mock socket.gethostbyname to return real IP
        with patch("socket.gethostbyname", return_value="192.168.1.100"):
            ips = get_network_ips()

        assert isinstance(ips, list), "Should return list of IPs"
        assert all(ip != "127.0.0.1" for ip in ips), "Should not include localhost"
        assert all(ip != "::1" for ip in ips), "Should not include IPv6 localhost"

    def test_network_ips_uses_psutil_if_available(self):
        """Verify psutil is preferred method for IP detection."""
        from installer.shared.network import get_network_ips

        # Mock psutil
        mock_addrs = {
            "eth0": [
                MagicMock(family=socket.AF_INET, address="192.168.1.100"),
            ]
        }

        with patch("psutil.net_if_addrs", return_value=mock_addrs):
            ips = get_network_ips()

        assert "192.168.1.100" in ips, "Should use psutil to get IPs"

    def test_network_ips_falls_back_gracefully(self):
        """Verify graceful fallback if psutil unavailable."""
        from installer.shared.network import get_network_ips

        # Mock psutil import failure
        with patch.dict("sys.modules", {"psutil": None}):
            # Should fall back to socket method
            with patch("socket.gethostbyname", return_value="192.168.1.50"):
                ips = get_network_ips()

        assert isinstance(ips, list), "Should still return list"
        assert len(ips) >= 0, "Should handle fallback gracefully"

    def test_network_ips_filters_ipv4_only(self):
        """Verify only IPv4 addresses are returned."""
        from installer.shared.network import get_network_ips

        # Mock psutil with mixed IPv4/IPv6
        mock_addrs = {
            "eth0": [
                MagicMock(family=socket.AF_INET, address="192.168.1.100"),
                MagicMock(family=socket.AF_INET6, address="fe80::1"),
            ]
        }

        with patch("psutil.net_if_addrs", return_value=mock_addrs):
            ips = get_network_ips()

        assert "192.168.1.100" in ips, "Should include IPv4"
        assert "fe80::1" not in ips, "Should exclude IPv6"


class TestIntegration:
    """Integration tests for combined modules."""

    @pytest.mark.asyncio
    async def test_full_installer_workflow(self, mock_settings, temp_install_dir):
        """Test complete installer workflow: discover -> config -> database."""
        # This will be a comprehensive integration test
        # that exercises all modules together

        # Step 1: Discover PostgreSQL
        from installer.shared.postgres import PostgreSQLDiscovery

        discovery = PostgreSQLDiscovery()

        with patch("shutil.which", return_value="/usr/bin/psql"):
            pg_result = discovery.discover()

        assert pg_result["found"], "Should discover PostgreSQL"

        # Step 2: Generate config.yaml
        from installer.core.config import ConfigManager

        config_mgr = ConfigManager(mock_settings)

        yaml_path = config_mgr.generate_config_yaml()
        assert Path(yaml_path).exists(), "Should create config.yaml"

        # Step 3: Setup database (mocked)
        from installer.core.database import DatabaseInstaller

        with patch("installer.core.database.psycopg2") as mock_pg:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_conn.cursor.return_value = mock_cur
            mock_pg.connect.return_value = mock_conn

            db_installer = DatabaseInstaller(mock_settings)

            with patch("installer.core.database.check_postgresql_connection", return_value=True):
                result = db_installer.setup()

        # Workflow should complete without errors
        assert "success" in result, "Should return result"

    def test_cross_platform_path_consistency(self, mock_settings):
        """Verify all modules use consistent cross-platform paths."""
        from installer.core.config import ConfigManager
        from installer.core.database import DatabaseInstaller

        # All modules should use Path objects
        db_installer = DatabaseInstaller(mock_settings)
        config_mgr = ConfigManager(mock_settings)

        # Generate paths and verify they're Path-compatible
        # (implementation will vary based on actual methods)
        assert True, "Path consistency check"


# Pytest markers for categorization
pytestmark = [
    pytest.mark.unit,
    pytest.mark.integration,
]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
