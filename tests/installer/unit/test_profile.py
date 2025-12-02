"""
Unit tests for Profile system
"""

# Import the profile system
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from unittest.mock import patch

import pytest


sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

try:
    from installer.core.profile import (
        Profile,
        ProfileConfiguration,
        ProfileDependencies,
        ProfileManager,
        ProfileNotFoundError,
        ProfileType,
        ProfileValidationError,
    )

    HAS_PROFILE = True
except ImportError:
    HAS_PROFILE = False
    pytest.skip("Profile system not available", allow_module_level=True)


class TestProfileType:
    """Test ProfileType enum"""

    def test_profile_type_values(self):
        """Test that all expected profile types exist"""
        assert ProfileType.DEVELOPER.value == "developer"
        assert ProfileType.TEAM.value == "team"
        assert ProfileType.ENTERPRISE.value == "enterprise"
        assert ProfileType.RESEARCH.value == "research"

    def test_profile_type_list(self):
        """Test getting list of all profile types"""
        types = list(ProfileType)
        assert len(types) == 4
        assert ProfileType.DEVELOPER in types
        assert ProfileType.TEAM in types
        assert ProfileType.ENTERPRISE in types
        assert ProfileType.RESEARCH in types


class TestProfileConfiguration:
    """Test ProfileConfiguration dataclass"""

    def test_profile_configuration_creation(self):
        """Test creating profile configuration"""
        config = ProfileConfiguration(
            database_type="postgresql", redis_enabled=True, auth_enabled=True, debug_mode=False
        )

        assert config.database_type == "postgresql"
        assert config.redis_enabled
        assert config.auth_enabled
        assert not config.debug_mode

    def test_profile_configuration_defaults(self):
        """Test default values"""
        config = ProfileConfiguration()

        assert config.database_type == "postgresql"  # Project standardized on PostgreSQL
        assert not config.redis_enabled
        assert not config.auth_enabled
        assert config.debug_mode
        assert config.log_level == "INFO"

    def test_profile_configuration_to_dict(self):
        """Test converting configuration to dictionary"""
        config = ProfileConfiguration(database_type="postgresql", redis_enabled=True)

        config_dict = asdict(config)
        assert isinstance(config_dict, dict)
        assert config_dict["database_type"] == "postgresql"
        assert config_dict["redis_enabled"]


class TestProfileDependencies:
    """Test ProfileDependencies dataclass"""

    def test_profile_dependencies_creation(self):
        """Test creating profile dependencies"""
        deps = ProfileDependencies(requires_postgresql=True, requires_redis=True, requires_docker=False)

        assert deps.requires_postgresql
        assert deps.requires_redis
        assert not deps.requires_docker

    def test_profile_dependencies_defaults(self):
        """Test default dependency values"""
        deps = ProfileDependencies()

        assert not deps.requires_postgresql
        assert not deps.requires_redis
        assert not deps.requires_docker
        assert deps.min_python_version == "3.8"
        assert deps.recommended_memory_gb == 2


class TestProfile:
    """Test Profile dataclass"""

    def test_profile_creation(self):
        """Test creating a profile"""
        config = ProfileConfiguration(database_type="postgresql")
        deps = ProfileDependencies(requires_postgresql=True)

        profile = Profile(
            type=ProfileType.TEAM,
            name="Team Profile",
            description="Profile for team collaboration",
            configuration=config,
            dependencies=deps,
        )

        assert profile.type == ProfileType.TEAM
        assert profile.name == "Team Profile"
        assert profile.configuration.database_type == "postgresql"
        assert profile.dependencies.requires_postgresql

    def test_profile_validation(self):
        """Test profile validation"""
        # Valid profile
        profile = Profile(type=ProfileType.DEVELOPER, name="Developer", description="Development profile")

        assert profile.is_valid()

        # Invalid profile (missing name)
        invalid_profile = Profile(
            type=ProfileType.DEVELOPER,
            name="",  # Empty name should be invalid
            description="Test",
        )

        assert not invalid_profile.is_valid()

    def test_profile_get_dependencies(self):
        """Test getting profile dependencies"""
        deps = ProfileDependencies(requires_postgresql=True, requires_redis=True)

        profile = Profile(
            type=ProfileType.ENTERPRISE, name="Enterprise", description="Enterprise profile", dependencies=deps
        )

        dependencies = profile.get_required_dependencies()
        assert "postgresql" in dependencies
        assert "redis" in dependencies
        assert len(dependencies) == 2


class TestProfileManager:
    """Test ProfileManager class"""

    def setUp(self):
        """Set up test environment"""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.manager = ProfileManager(self.temp_dir)

    def tearDown(self):
        """Clean up test environment"""
        import shutil

        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir)

    def test_profile_manager_initialization(self):
        """Test ProfileManager initialization"""
        manager = ProfileManager()
        assert manager is not None

        # Test with custom directory
        temp_dir = Path(tempfile.mkdtemp())
        manager = ProfileManager(temp_dir)
        assert manager.profiles_dir == temp_dir / "profiles"

    def test_create_default_profiles(self):
        """Test creating default profiles"""
        manager = ProfileManager()
        profiles = manager.get_all_profiles()

        # Should have default profiles
        profile_types = {p.type for p in profiles}
        assert ProfileType.DEVELOPER in profile_types
        assert ProfileType.TEAM in profile_types
        assert ProfileType.ENTERPRISE in profile_types
        assert ProfileType.RESEARCH in profile_types

    def test_get_profile_by_type(self):
        """Test getting profile by type"""
        manager = ProfileManager()

        # Get developer profile (project standardized on PostgreSQL)
        dev_profile = manager.get_profile(ProfileType.DEVELOPER)
        assert dev_profile is not None
        assert dev_profile.type == ProfileType.DEVELOPER
        assert dev_profile.configuration.debug_mode
        assert dev_profile.configuration.database_type == "postgresql"  # Project standardized on PostgreSQL

        # Get team profile
        team_profile = manager.get_profile(ProfileType.TEAM)
        assert team_profile is not None
        assert team_profile.type == ProfileType.TEAM
        assert team_profile.configuration.database_type == "postgresql"
        assert team_profile.dependencies.requires_postgresql

    def test_get_nonexistent_profile(self):
        """Test getting non-existent profile"""
        manager = ProfileManager()

        # Should raise exception for invalid profile
        with pytest.raises(ProfileNotFoundError):
            manager.get_profile("nonexistent")

    def test_profile_validation(self):
        """Test profile validation"""
        manager = ProfileManager()

        # Valid profile should pass
        valid_profile = Profile(type=ProfileType.DEVELOPER, name="Valid Profile", description="A valid test profile")

        # Should not raise exception
        manager._validate_profile(valid_profile)

        # Invalid profile should fail
        invalid_profile = Profile(
            type=ProfileType.DEVELOPER,
            name="",  # Empty name
            description="Invalid profile",
        )

        with pytest.raises(ProfileValidationError):
            manager._validate_profile(invalid_profile)

    def test_profile_configuration_inheritance(self):
        """Test that profiles have correct configurations"""
        manager = ProfileManager()

        # Developer profile (project standardized on PostgreSQL)
        dev = manager.get_profile(ProfileType.DEVELOPER)
        assert dev.configuration.debug_mode
        assert not dev.configuration.auth_enabled
        assert dev.configuration.database_type == "postgresql"  # Project standardized on PostgreSQL

        # Enterprise profile
        ent = manager.get_profile(ProfileType.ENTERPRISE)
        assert not ent.configuration.debug_mode
        assert ent.configuration.auth_enabled
        assert ent.configuration.database_type == "postgresql"
        assert ent.dependencies.requires_postgresql
        assert ent.dependencies.requires_redis

    def test_profile_dependencies_check(self):
        """Test checking profile dependencies"""
        manager = ProfileManager()

        # Developer profile - now requires PostgreSQL (project standardized)
        dev = manager.get_profile(ProfileType.DEVELOPER)
        dev_deps = dev.get_required_dependencies()
        assert "postgresql" in dev_deps  # Project standardized on PostgreSQL

        # Enterprise profile - many dependencies
        ent = manager.get_profile(ProfileType.ENTERPRISE)
        ent_deps = ent.get_required_dependencies()
        assert "postgresql" in ent_deps
        assert "redis" in ent_deps

    @patch("pathlib.Path.write_text")
    @patch("pathlib.Path.read_text")
    @patch("pathlib.Path.exists")
    def test_profile_persistence(self, mock_exists, mock_read, mock_write):
        """Test profile saving and loading"""
        mock_exists.return_value = False  # No existing profiles

        ProfileManager()

        # Create custom profile
        Profile(
            type=ProfileType.DEVELOPER,
            name="Custom Developer",
            description="Custom developer profile",
            configuration=ProfileConfiguration(database_type="postgresql", debug_mode=True),
        )

        # Save profile (mocked)
        mock_write.assert_called()  # Should have written default profiles

    def test_profile_comparison(self):
        """Test comparing profiles"""
        manager = ProfileManager()

        dev1 = manager.get_profile(ProfileType.DEVELOPER)
        dev2 = manager.get_profile(ProfileType.DEVELOPER)
        team = manager.get_profile(ProfileType.TEAM)

        # Same profile type should be equal
        assert dev1.type == dev2.type
        assert dev1.name == dev2.name

        # Different profile types should be different
        assert dev1.type != team.type
        assert dev1.configuration.database_type != team.configuration.database_type


class TestProfileIntegration:
    """Integration tests for profile system"""

    def test_profile_workflow(self):
        """Test complete profile workflow"""
        # Initialize manager
        manager = ProfileManager()

        # Get all profiles
        all_profiles = manager.get_all_profiles()
        assert len(all_profiles) == 4

        # Get specific profile
        team_profile = manager.get_profile(ProfileType.TEAM)

        # Check configuration
        config = team_profile.configuration
        assert config.database_type == "postgresql"
        assert config.auth_enabled

        # Check dependencies
        deps = team_profile.get_required_dependencies()
        assert "postgresql" in deps

    def test_profile_selection_scenario(self):
        """Test profile selection scenario like GUI would use"""
        manager = ProfileManager()

        # Simulate user selecting enterprise profile
        selected_type = ProfileType.ENTERPRISE
        profile = manager.get_profile(selected_type)

        # Verify enterprise requirements
        assert profile.dependencies.requires_postgresql
        assert profile.dependencies.requires_redis
        assert profile.configuration.auth_enabled
        assert profile.configuration.secure_cookies

        # Get installation requirements
        deps = profile.get_required_dependencies()
        assert "postgresql" in deps
        assert "redis" in deps

        # Verify configuration would be production-ready
        assert not profile.configuration.debug_mode
        assert profile.configuration.log_level in ["WARNING", "ERROR"]


# Pytest fixtures
@pytest.fixture
def profile_manager():
    """Create a ProfileManager for testing"""
    return ProfileManager()


@pytest.fixture
def temp_profiles_dir():
    """Create temporary directory for profile testing"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    import shutil

    if temp_dir.exists():
        shutil.rmtree(temp_dir)


# Parameterized tests
@pytest.mark.parametrize(
    ("profile_type", "expected_db"),
    [
        (ProfileType.DEVELOPER, "postgresql"),  # Project standardized on PostgreSQL
        (ProfileType.TEAM, "postgresql"),
        (ProfileType.ENTERPRISE, "postgresql"),
        (ProfileType.RESEARCH, "postgresql"),
    ],
)
def test_profile_database_types(profile_manager, profile_type, expected_db):
    """Test that profiles have correct database types (project standardized on PostgreSQL)"""
    profile = profile_manager.get_profile(profile_type)
    assert profile.configuration.database_type == expected_db


@pytest.mark.parametrize(
    ("profile_type", "requires_auth"),
    [
        (ProfileType.DEVELOPER, False),
        (ProfileType.TEAM, True),
        (ProfileType.ENTERPRISE, True),
        (ProfileType.RESEARCH, False),
    ],
)
def test_profile_auth_requirements(profile_manager, profile_type, requires_auth):
    """Test that profiles have correct auth requirements"""
    profile = profile_manager.get_profile(profile_type)
    assert profile.configuration.auth_enabled == requires_auth


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
