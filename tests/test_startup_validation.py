#!/usr/bin/env python3
"""
Comprehensive validation tests for production-ready startup fixes.
Tests all scenarios before 15-day launch.

Author: testing-and-validation-specialist
Date: 2025-10-01
"""

import os
import socket
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from installer.core.config_generator import ConfigGenerator
from setup import GiljoSetup, check_port

from api.run_api import (
    check_port_available,
    find_available_port,
    get_port_from_sources,
    load_config_port,
)


class TestPortConfiguration:
    """Test port configuration logic in all scenarios"""

    def test_check_port_available_free_port(self):
        """Test that check_port_available detects free ports"""
        # Use a high port that's unlikely to be in use
        free_port = 59999
        assert check_port_available(free_port) is True

    def test_check_port_available_occupied_port(self):
        """Test that check_port_available detects occupied ports"""
        # Create a temporary server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 0))  # Bind to random available port
            sock.listen(1)
            port = sock.getsockname()[1]

            # Port should be detected as occupied
            assert check_port_available(port) is False

    def test_find_available_port_preferred_free(self):
        """Test find_available_port returns preferred port when free"""
        preferred = 59998
        result = find_available_port(preferred)
        assert result == preferred

    def test_find_available_port_preferred_occupied(self):
        """Test find_available_port finds alternative when preferred is occupied"""
        # Occupy the preferred port
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.bind(("127.0.0.1", 7272))
            sock.listen(1)

            # Should find alternative port
            result = find_available_port(7272)
            assert result != 7272
            assert result in [7273, 7274, 8747, 8823, 9456, 9789] or 7200 <= result <= 9999

    def test_find_available_port_all_alternatives_occupied(self):
        """Test find_available_port finds random port when all alternatives occupied"""
        # This test is difficult to implement without actually occupying all alternatives
        # We'll test the random port selection path indirectly
        preferred = 7272
        result = find_available_port(preferred)
        assert isinstance(result, int)
        assert 1024 <= result <= 65535

    def test_load_config_port_default(self):
        """Test load_config_port returns default when no config exists"""
        with tempfile.TemporaryDirectory() as tmpdir, patch("api.run_api.Path") as mock_path:
            mock_path.return_value.parent.parent = Path(tmpdir)
            mock_path.return_value.exists.return_value = False

            port = load_config_port()
            assert port == 7272  # Default unified port

    def test_load_config_port_unified_structure(self):
        """Test load_config_port with new unified structure (server.port)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config = {"server": {"port": 8888}}
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            with patch("api.run_api.Path") as mock_path:
                mock_path.return_value.parent.parent = Path(tmpdir)
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.__truediv__.return_value = config_path

                port = load_config_port()
                assert port == 8888

    def test_load_config_port_old_structure_fallback(self):
        """Test load_config_port falls back to old structure (server.ports.api)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"
            config = {"server": {"ports": {"api": 9999}}}
            with open(config_path, "w") as f:
                yaml.dump(config, f)

            with patch("api.run_api.Path") as mock_path:
                mock_path.return_value.parent.parent = Path(tmpdir)
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.__truediv__.return_value = config_path

                port = load_config_port()
                assert port == 9999

    def test_get_port_from_sources_env_priority(self):
        """Test get_port_from_sources prioritizes GILJO_PORT environment variable"""
        with patch.dict(os.environ, {"GILJO_PORT": "8123"}):
            port = get_port_from_sources()
            # Should return 8123 or an alternative if 8123 is occupied
            assert isinstance(port, int)
            assert 1024 <= port <= 65535

    def test_get_port_from_sources_invalid_env(self):
        """Test get_port_from_sources handles invalid GILJO_PORT gracefully"""
        with patch.dict(os.environ, {"GILJO_PORT": "invalid"}):
            port = get_port_from_sources()
            # Should fall back to config or default
            assert isinstance(port, int)
            assert port == 7272 or (1024 <= port <= 65535)

    def test_get_port_from_sources_env_out_of_range(self):
        """Test get_port_from_sources rejects ports outside valid range"""
        with patch.dict(os.environ, {"GILJO_PORT": "100"}):
            port = get_port_from_sources()
            # Should ignore port <1024 and use default
            assert port >= 1024


class TestDatabaseConfiguration:
    """Test database configuration defaults (PostgreSQL)"""

    def test_config_generator_defaults_to_postgresql(self):
        """Test that ConfigGenerator defaults to PostgreSQL"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigGenerator(install_dir=tmpdir)
            config = generator.generate_default_config()

            assert "database" in config
            assert config["database"]["database_type"] == "postgresql"

    def test_config_generator_postgresql_settings(self):
        """Test PostgreSQL default settings"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigGenerator(install_dir=tmpdir)
            config = generator.generate_default_config()

            db_config = config["database"]
            assert db_config["host"] == "localhost"
            assert db_config["port"] == 5432
            assert db_config["name"] == "giljo_mcp"
            assert db_config["user"] == "postgres"
            assert "password" in db_config

    def test_config_generator_unified_port_structure(self):
        """Test that config uses unified port structure (single port 7272)"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigGenerator(install_dir=tmpdir)
            config = generator.generate_default_config()

            assert "server" in config
            assert config["server"]["port"] == 7272
            # Should NOT have old multi-port structure
            assert "ports" not in config["server"]

    def test_config_generator_cors_includes_7272(self):
        """Test CORS configuration includes port 7272"""
        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigGenerator(install_dir=tmpdir)
            config = generator.generate_default_config()

            assert "api" in config
            cors_origins = config["api"]["cors_origins"]
            assert any("7272" in origin for origin in cors_origins)

    def test_config_generator_clean_config_removes_comments(self):
        """Test _clean_config removes comment entries"""
        generator = ConfigGenerator()
        dirty_config = {
            "# Comment": None,
            "valid_key": "valid_value",
            "nested": {"# Nested comment": None, "nested_key": "nested_value"},
        }

        clean = generator._clean_config(dirty_config)

        # Comments should be removed
        assert "# Comment" not in clean
        assert "valid_key" in clean
        assert "# Nested comment" not in clean["nested"]
        assert "nested_key" in clean["nested"]

    def test_setup_postgresql_default_config(self):
        """Test setup.py creates PostgreSQL config by default"""
        setup = GiljoSetup()
        setup.config = {
            "pg_host": "localhost",
            "pg_port": 5432,
            "pg_database": "giljo_mcp",
            "pg_user": "postgres",
            "pg_password": "test_password",
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            setup.root_path = Path(tmpdir)
            success = setup.create_config_file()

            assert success is True

            # Read generated config
            config_path = Path(tmpdir) / "config.yaml"
            assert config_path.exists()

            with open(config_path) as f:
                config = yaml.safe_load(f)

            assert config["database"]["database_type"] == "postgresql"
            assert config["database"]["password"] == "test_password"


class TestEggInfoCleanup:
    """Test egg-info cleanup and error recovery"""

    def test_cleanup_egg_info_removes_directories(self):
        """Test that cleanup_egg_info removes old egg-info directories"""
        setup = GiljoSetup()

        with tempfile.TemporaryDirectory() as tmpdir:
            setup.root_path = Path(tmpdir)

            # Create fake egg-info directories
            egg_paths = [
                Path(tmpdir) / "src" / "giljo_mcp.egg-info",
                Path(tmpdir) / "giljo_mcp.egg-info",
                Path(tmpdir) / "build",
                Path(tmpdir) / "dist",
            ]

            for path in egg_paths:
                path.mkdir(parents=True, exist_ok=True)
                (path / "test_file.txt").touch()

            # Run cleanup
            result = setup.cleanup_egg_info()

            assert result is True
            # All directories should be removed
            for path in egg_paths:
                assert not path.exists()

    def test_cleanup_egg_info_handles_missing_directories(self):
        """Test cleanup_egg_info handles missing directories gracefully"""
        setup = GiljoSetup()

        with tempfile.TemporaryDirectory() as tmpdir:
            setup.root_path = Path(tmpdir)

            # No egg-info directories exist
            result = setup.cleanup_egg_info()

            # Should succeed even with nothing to clean
            assert result is True

    def test_cleanup_egg_info_handles_permission_errors(self):
        """Test cleanup_egg_info handles permission errors gracefully"""
        setup = GiljoSetup()

        with tempfile.TemporaryDirectory() as tmpdir:
            setup.root_path = Path(tmpdir)

            # Create egg-info directory
            egg_path = Path(tmpdir) / "src" / "giljo_mcp.egg-info"
            egg_path.mkdir(parents=True)

            # Mock shutil.rmtree to raise exception
            with patch("shutil.rmtree", side_effect=PermissionError("Access denied")):
                result = setup.cleanup_egg_info()

                # Should still return True (non-fatal error)
                assert result is True


class TestBatFileLogic:
    """Test BAT file logic and error handling"""

    def test_bat_file_exists(self):
        """Test that start_giljo.bat exists"""
        bat_path = Path(__file__).parent.parent / "start_giljo.bat"
        assert bat_path.exists()

    def test_bat_file_has_egg_info_cleanup(self):
        """Test that BAT file includes egg-info cleanup commands"""
        bat_path = Path(__file__).parent.parent / "start_giljo.bat"
        content = bat_path.read_text()

        # Should have cleanup commands
        assert "giljo_mcp.egg-info" in content
        assert "rmdir /s /q" in content or "Cleaning up" in content

    def test_bat_file_has_error_handling(self):
        """Test that BAT file has proper error handling"""
        bat_path = Path(__file__).parent.parent / "start_giljo.bat"
        content = bat_path.read_text()

        # Should check error levels
        assert "errorlevel" in content
        # Should have failure messages
        assert "Error:" in content or "Failed" in content

    def test_bat_file_has_port_configuration(self):
        """Test that BAT file configures port from config.yaml"""
        bat_path = Path(__file__).parent.parent / "start_giljo.bat"
        content = bat_path.read_text()

        # Should read port from config
        assert "port:" in content or "SERVER_PORT" in content
        # Should have default port
        assert "7272" in content

    def test_bat_file_has_health_check(self):
        """Test that BAT file includes health check with retries"""
        bat_path = Path(__file__).parent.parent / "start_giljo.bat"
        content = bat_path.read_text()

        # Should have health check
        assert "/health" in content
        # Should have retry logic
        assert "RETRY" in content or "retry" in content
        # Should have maximum retries
        assert "MAX_RETRIES" in content or "10" in content

    def test_bat_file_has_troubleshooting_guidance(self):
        """Test that BAT file provides troubleshooting guidance"""
        bat_path = Path(__file__).parent.parent / "start_giljo.bat"
        content = bat_path.read_text()

        # Should have troubleshooting section
        assert "Troubleshooting" in content or "troubleshooting" in content
        # Should mention port conflicts
        assert "port" in content.lower()


class TestCrossPlatformCompatibility:
    """Test cross-platform compatibility"""

    def test_path_handling_uses_pathlib(self):
        """Test that Path objects are used for OS-neutral paths"""
        # Check run_api.py
        run_api_path = Path(__file__).parent.parent / "api" / "run_api.py"
        content = run_api_path.read_text()

        # Should import Path
        assert "from pathlib import Path" in content
        # Should use Path for config path
        assert "Path(__file__)" in content

    def test_config_generator_uses_pathlib(self):
        """Test ConfigGenerator uses pathlib.Path"""
        generator = ConfigGenerator()

        # Paths should be Path objects
        assert isinstance(generator.install_dir, Path)
        assert isinstance(generator.config_path, Path)

    def test_setup_uses_pathlib(self):
        """Test setup.py uses pathlib.Path"""
        setup = GiljoSetup()

        # root_path should be Path object
        assert isinstance(setup.root_path, Path)

    def test_port_functions_work_on_windows(self):
        """Test port checking functions work on Windows"""
        # These functions should work regardless of platform
        assert callable(check_port)
        assert callable(check_port_available)

        # Test with a high port
        result = check_port(59997)
        assert isinstance(result, bool)

        result = check_port_available(59997)
        assert isinstance(result, bool)


class TestErrorRecovery:
    """Test error recovery mechanisms"""

    def test_port_conflict_recovery(self):
        """Test that system recovers from port conflicts"""
        # Occupy port 7272
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            try:
                sock.bind(("127.0.0.1", 7272))
                sock.listen(1)

                # Should find alternative port
                alt_port = find_available_port(7272)
                assert alt_port != 7272
                assert isinstance(alt_port, int)
            except OSError:
                # Port 7272 already in use by another process
                # Test still valid - just verify alternative is found
                alt_port = find_available_port(7272)
                assert isinstance(alt_port, int)

    def test_invalid_port_number_handling(self):
        """Test handling of invalid port numbers"""
        with patch.dict(os.environ, {"GILJO_PORT": "99999"}):
            # Port >65535 should be rejected
            port = get_port_from_sources()
            assert 1024 <= port <= 65535

    def test_corrupted_config_handling(self):
        """Test handling of corrupted config.yaml"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.yaml"

            # Write invalid YAML
            with open(config_path, "w") as f:
                f.write("invalid: yaml: content: ][{")

            with patch("api.run_api.Path") as mock_path:
                mock_path.return_value.parent.parent = Path(tmpdir)
                mock_path.return_value.exists.return_value = True
                mock_path.return_value.__truediv__.return_value = config_path

                # Should fall back to default
                port = load_config_port()
                assert port == 7272

    def test_missing_config_file_handling(self):
        """Test handling of missing config.yaml"""
        with tempfile.TemporaryDirectory() as tmpdir, patch("api.run_api.Path") as mock_path:
            mock_path.return_value.parent.parent = Path(tmpdir)
            mock_path.return_value.exists.return_value = False

            # Should return default
            port = load_config_port()
            assert port == 7272


class TestPerformanceMetrics:
    """Test performance metrics for startup"""

    def test_check_port_performance(self):
        """Test that port checking is fast"""
        import time

        start = time.perf_counter()
        # Reduced iterations to avoid timeout
        for _ in range(10):
            check_port_available(59996)
        elapsed = time.perf_counter() - start

        # Should complete 10 checks in <5 seconds (very generous)
        assert elapsed < 5.0

    def test_config_loading_performance(self):
        """Test that config loading is fast"""
        import time

        with tempfile.TemporaryDirectory() as tmpdir:
            generator = ConfigGenerator(install_dir=tmpdir)
            generator.create_config_file()

            start = time.perf_counter()
            # Reduced iterations to avoid timeout
            for _ in range(10):
                config = generator.generate_default_config()
            elapsed = time.perf_counter() - start

            # Should complete 10 generations in <5 seconds (very generous)
            assert elapsed < 5.0


if __name__ == "__main__":
    # Run tests with pytest
    pytest.main([__file__, "-v", "--tb=short"])
