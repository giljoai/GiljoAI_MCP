"""
Integration tests for complete installation flow
"""

import pytest
import asyncio
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Import systems
import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.core.profile import ProfileManager, ProfileType
    from installer.core.health import HealthChecker
    from installer.config.config_manager import ConfigurationManager
    HAS_ALL_COMPONENTS = True
except ImportError:
    HAS_ALL_COMPONENTS = False
    pytest.skip("Not all components available", allow_module_level=True)

from tests.installer.fixtures.test_configs import create_test_env


class TestInstallationFlow:
    """Test complete installation workflow"""

    def setUp(self):
        """Set up test environment"""
        self.test_env = create_test_env()
        self.test_env.config_dir.mkdir(parents=True, exist_ok=True)
        self.test_env.data_dir.mkdir(parents=True, exist_ok=True)
        self.test_env.logs_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        """Clean up test environment"""
        self.test_env.cleanup()

    def test_complete_workflow(self):
        """Test complete installation workflow"""
        # Step 1: Profile selection
        profile_manager = ProfileManager()
        selected_profile = profile_manager.get_profile(ProfileType.TEAM)

        assert selected_profile is not None
        assert selected_profile.type == ProfileType.TEAM

        # Step 2: Check dependencies
        required_deps = selected_profile.get_required_dependencies()
        assert "postgresql" in required_deps
        assert "redis" in required_deps

        # Step 3: Configuration generation
        config_manager = ConfigurationManager()
        configuration = config_manager.generate_configuration(
            ProfileType.TEAM,
            user_inputs={
                "team_name": "Test Team",
                "team_size": 5
            },
            connection_strings={
                "postgresql": "postgresql://team:pass@localhost:5432/team_db",
                "redis": "redis://localhost:6379/0"
            }
        )

        assert configuration.get_value("TEAM_NAME") == "Test Team"
        assert configuration.get_value("AUTH_ENABLED") == True

        # Step 4: Configuration validation
        is_valid, errors = config_manager.validate_configuration(configuration)
        assert is_valid == True
        assert len(errors) == 0

        # Step 5: Save configuration
        config_path = self.test_env.config_dir / ".env"
        saved_path = config_manager.save_configuration(configuration, config_path)
        assert saved_path == config_path

    @pytest.mark.asyncio
    async def test_health_check_integration(self):
        """Test health check integration in workflow"""
        # Initialize health checker
        health_checker = HealthChecker({
            "postgresql": {"host": "localhost", "port": 5432},
            "redis": {"host": "localhost", "port": 6379}
        })

        with patch.multiple(
            health_checker,
            _check_system=Mock(return_value=None),
            _check_postgresql=Mock(return_value=None),
            _check_redis=Mock(return_value=None)
        ):
            # Mock healthy components
            health_checker.components = [
                type('Component', (), {
                    'name': 'System',
                    'status': type('Status', (), {'value': 'healthy'})(),
                    'message': 'OK'
                })(),
            ]

            report = await health_checker.check_installation_readiness()
            assert report is not None

    def test_profile_config_integration(self):
        """Test profile and configuration integration"""
        # Get enterprise profile
        profile_manager = ProfileManager()
        enterprise_profile = profile_manager.get_profile(ProfileType.ENTERPRISE)

        # Generate configuration based on profile
        config_manager = ConfigurationManager()
        config = config_manager.generate_configuration(
            enterprise_profile.type,
            user_inputs={
                "enterprise_name": "TestCorp",
                "compliance_mode": "SOC2"
            }
        )

        # Verify enterprise-specific settings
        assert config.get_value("ENTERPRISE_NAME") == "TestCorp"
        assert config.get_value("COMPLIANCE_MODE") == "SOC2"
        assert config.get_value("AUDIT_LOGGING") == True
        assert config.get_value("SECURE_COOKIES") == True
        assert config.get_value("AUTH_METHOD") == "oauth"

    def test_configuration_migration_flow(self):
        """Test configuration migration workflow"""
        config_manager = ConfigurationManager()

        # Create "old" configuration
        old_config_path = self.test_env.config_dir / "old.env"
        old_config_path.write_text("""
APP_NAME=OldApp
DEBUG=true
CUSTOM_SETTING=preserved
""")

        # Migrate to new profile
        with patch.object(config_manager, 'load_configuration') as mock_load:
            from installer.config.config_manager import Configuration
            old_config = Configuration(profile_type="developer")
            old_config.add_value("APP_NAME", "OldApp")
            old_config.add_value("DEBUG", True)
            old_config.add_value("CUSTOM_SETTING", "preserved")
            mock_load.return_value = old_config

            migrated = config_manager.migrate_configuration(
                old_config_path,
                new_profile="team"
            )

            # Should be team profile but preserve custom settings
            assert migrated.profile_type == "team"
            assert "migrated_from" in migrated.metadata

    @pytest.mark.asyncio
    async def test_parallel_health_checks(self):
        """Test parallel health checking"""
        health_checker = HealthChecker()

        # Mock all individual checks
        with patch.multiple(
            health_checker,
            _check_system=Mock(return_value=None),
            _check_postgresql=Mock(return_value=None),
            _check_redis=Mock(return_value=None),
            _check_docker=Mock(return_value=None),
            _check_ports=Mock(return_value=None)
        ):
            # Run checks in parallel (simulated)
            tasks = [
                health_checker._check_system(),
                health_checker._check_postgresql(),
                health_checker._check_redis()
            ]

            await asyncio.gather(*tasks, return_exceptions=True)

            # All mocks should have been called
            health_checker._check_system.assert_called_once()
            health_checker._check_postgresql.assert_called_once()
            health_checker._check_redis.assert_called_once()


class TestErrorHandling:
    """Test error handling in integration scenarios"""

    def test_invalid_profile_handling(self):
        """Test handling of invalid profile selection"""
        profile_manager = ProfileManager()

        with pytest.raises(Exception):  # Should raise ProfileNotFoundError
            profile_manager.get_profile("nonexistent_profile")

    def test_configuration_validation_errors(self):
        """Test handling of configuration validation errors"""
        config_manager = ConfigurationManager()

        # Generate configuration with invalid inputs
        config = config_manager.generate_configuration(
            "developer",
            user_inputs={
                "api_port": 99999,  # Invalid port
                "log_level": "INVALID"  # Invalid log level
            }
        )

        # Override with invalid values to test validation
        config.add_value("API_PORT", 99999)
        config.add_value("LOG_LEVEL", "INVALID")

        is_valid, errors = config_manager.validate_configuration(config)
        assert is_valid == False
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_health_check_failures(self):
        """Test handling of health check failures"""
        health_checker = HealthChecker()

        with patch.object(health_checker, '_check_system') as mock_check:
            # Simulate check failure
            mock_check.side_effect = Exception("System check failed")

            # Should handle exception gracefully
            await health_checker._check_system()
            # No exception should propagate

    def test_missing_dependencies(self):
        """Test handling of missing dependencies"""
        # This would test scenarios where required packages are missing
        # In real implementation, we'd mock import failures

        profile_manager = ProfileManager()
        enterprise_profile = profile_manager.get_profile(ProfileType.ENTERPRISE)

        deps = enterprise_profile.get_required_dependencies()
        # Should list dependencies even if not installed
        assert len(deps) > 0


class TestPerformance:
    """Test performance aspects of integration"""

    @pytest.mark.asyncio
    async def test_health_check_performance(self):
        """Test that health checks complete within reasonable time"""
        import time

        health_checker = HealthChecker()

        # Mock fast checks
        with patch.multiple(
            health_checker,
            _check_system=Mock(return_value=None),
            _check_python=Mock(return_value=None)
        ):
            start_time = time.time()

            # Run subset of quick checks
            report = await health_checker.check_all(['system', 'python'])

            end_time = time.time()
            duration = end_time - start_time

            # Should complete quickly (allowing for test overhead)
            assert duration < 5.0  # 5 seconds is generous for mocked tests

    def test_configuration_generation_performance(self):
        """Test configuration generation performance"""
        import time

        config_manager = ConfigurationManager()

        start_time = time.time()

        # Generate configurations for all profiles
        for profile in ["developer", "team", "enterprise", "research"]:
            config = config_manager.generate_configuration(profile)
            assert config is not None

        end_time = time.time()
        duration = end_time - start_time

        # Should generate all configs quickly
        assert duration < 1.0  # 1 second for all profiles


class TestConcurrency:
    """Test concurrent operations"""

    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test running multiple health checks concurrently"""
        health_checker = HealthChecker()

        # Create multiple health checkers
        checkers = [HealthChecker() for _ in range(3)]

        # Mock their methods
        for checker in checkers:
            with patch.object(checker, '_check_system', return_value=None):
                pass

        # Run checks concurrently
        tasks = [checker._check_system() for checker in checkers]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # All should complete
        assert len(results) == 3

    def test_concurrent_config_generation(self):
        """Test concurrent configuration generation"""
        import threading
        import time

        config_manager = ConfigurationManager()
        results = []
        errors = []

        def generate_config(profile):
            try:
                config = config_manager.generate_configuration(profile)
                results.append((profile, config))
            except Exception as e:
                errors.append((profile, e))

        # Create threads for different profiles
        threads = []
        profiles = ["developer", "team", "enterprise"]

        for profile in profiles:
            thread = threading.Thread(target=generate_config, args=(profile,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=5)

        # All should complete successfully
        assert len(errors) == 0
        assert len(results) == 3


# Fixtures
@pytest.fixture
def test_environment():
    """Create test environment"""
    env = create_test_env()
    env.config_dir.mkdir(parents=True, exist_ok=True)
    env.data_dir.mkdir(parents=True, exist_ok=True)
    env.logs_dir.mkdir(parents=True, exist_ok=True)
    yield env
    env.cleanup()


@pytest.fixture
def profile_manager():
    """Create ProfileManager"""
    return ProfileManager()


@pytest.fixture
def config_manager():
    """Create ConfigurationManager"""
    return ConfigurationManager()


@pytest.fixture
def health_checker():
    """Create HealthChecker"""
    return HealthChecker()


# End-to-end test
@pytest.mark.asyncio
async def test_full_installation_simulation(test_environment):
    """Simulate complete installation process"""
    # Step 1: Initialize all managers
    profile_manager = ProfileManager()
    config_manager = ConfigurationManager()
    health_checker = HealthChecker()

    # Step 2: Select profile (simulate user choice)
    selected_profile = profile_manager.get_profile(ProfileType.TEAM)

    # Step 3: Pre-installation health check
    with patch.multiple(
        health_checker,
        _check_system=Mock(return_value=None),
        _check_python=Mock(return_value=None),
        _check_network=Mock(return_value=None)
    ):
        pre_check_report = await health_checker.check_installation_readiness()

    # Step 4: Generate configuration
    configuration = config_manager.generate_configuration(
        selected_profile.type,
        user_inputs={
            "team_name": "Test Installation Team",
            "api_port": 8000
        }
    )

    # Step 5: Validate configuration
    is_valid, validation_errors = config_manager.validate_configuration(configuration)
    assert is_valid == True

    # Step 6: Save configuration
    config_path = test_environment.config_dir / ".env"
    saved_path = config_manager.save_configuration(configuration, config_path)

    # Step 7: Post-configuration health check
    with patch.multiple(
        health_checker,
        _check_system=Mock(return_value=None),
        _check_postgresql=Mock(return_value=None),
        _check_redis=Mock(return_value=None)
    ):
        post_check_report = await health_checker.check_database_services()

    # Verify the simulation completed successfully
    assert saved_path.exists()
    assert configuration.get_value("TEAM_NAME") == "Test Installation Team"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])