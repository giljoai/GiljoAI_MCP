"""
Configuration Manager for GiljoAI MCP Installer

Handles generation, validation, and management of configuration files
based on profiles and user settings.
"""

import os
import json
import yaml
import shutil
import secrets
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
import hashlib
import base64

# Try to import profile system
try:
    from installer.core.profile import ProfileManager, ProfileType, Profile

    HAS_PROFILE = True
except ImportError:
    HAS_PROFILE = False
    ProfileType = None


class ConfigFormat(Enum):
    """Supported configuration file formats"""

    ENV = ".env"
    YAML = "yaml"
    JSON = "json"
    INI = "ini"
    TOML = "toml"


@dataclass
class ConfigurationValue:
    """Represents a configuration value with metadata"""

    key: str
    value: Any
    description: str = ""
    required: bool = True
    secret: bool = False
    default: Any = None
    validation: Optional[str] = None  # Regex or validation rule
    source: str = "default"  # Where the value came from

    def to_env_line(self) -> str:
        """Convert to .env format line"""
        if self.description:
            lines = [f"# {self.description}"]
        else:
            lines = []

        if self.secret and self.value:
            # Mask secrets in comments
            lines.append(f"# Secret value (masked)")

        # Format the value appropriately
        if self.value is None:
            formatted_value = ""
        elif isinstance(self.value, bool):
            formatted_value = "true" if self.value else "false"
        elif isinstance(self.value, (list, dict)):
            formatted_value = json.dumps(self.value)
        else:
            formatted_value = str(self.value)

        # Quote if contains spaces or special characters
        if " " in formatted_value or '"' in formatted_value:
            formatted_value = f'"{formatted_value}"'

        lines.append(f"{self.key}={formatted_value}")
        return "\n".join(lines)


@dataclass
class Configuration:
    """Complete configuration for an installation"""

    profile_type: str
    values: Dict[str, ConfigurationValue] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    modified_at: Optional[datetime] = None
    version: str = "1.0.0"

    def add_value(self, key: str, value: Any, **kwargs):
        """Add a configuration value"""
        self.values[key] = ConfigurationValue(key=key, value=value, **kwargs)
        self.modified_at = datetime.now()

    def get_value(self, key: str, default=None) -> Any:
        """Get a configuration value"""
        if key in self.values:
            return self.values[key].value
        return default

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "profile_type": self.profile_type,
            "values": {k: v.value for k, v in self.values.items()},
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "modified_at": self.modified_at.isoformat() if self.modified_at else None,
            "version": self.version,
        }

    def to_env(self) -> str:
        """Convert to .env format"""
        lines = [
            "# GiljoAI MCP Configuration",
            f"# Profile: {self.profile_type}",
            f"# Generated: {datetime.now().isoformat()}",
            f"# Version: {self.version}",
            "",
        ]

        # Group configurations by category
        categories = {}
        for key, config_value in self.values.items():
            category = key.split("_")[0].upper()
            if category not in categories:
                categories[category] = []
            categories[category].append(config_value)

        # Write each category
        for category, values in sorted(categories.items()):
            lines.append(f"# ============= {category} Configuration =============")
            for value in sorted(values, key=lambda x: x.key):
                lines.append(value.to_env_line())
            lines.append("")

        return "\n".join(lines)


class ConfigurationManager:
    """Main configuration manager for the installer"""

    def __init__(self, base_path: Optional[Path] = None):
        """Initialize configuration manager"""
        self.base_path = Path(base_path) if base_path else Path.cwd()
        self.config_dir = self.base_path / "installer" / "config"
        self.templates_dir = self.config_dir / "templates"
        self.backup_dir = self.config_dir / "backups"

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.templates_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)

        # Load profile manager if available
        self.profile_manager = ProfileManager() if HAS_PROFILE else None

    def generate_configuration(
        self,
        profile_type: Union[str, "ProfileType"],
        user_inputs: Optional[Dict[str, Any]] = None,
        connection_strings: Optional[Dict[str, str]] = None,
    ) -> Configuration:
        """
        Generate configuration based on profile and user inputs

        Args:
            profile_type: The profile type to use
            user_inputs: User-provided configuration values
            connection_strings: Database connection strings from installers

        Returns:
            Complete configuration object
        """
        user_inputs = user_inputs or {}
        connection_strings = connection_strings or {}

        # Convert profile type to string if enum
        if hasattr(profile_type, "value"):
            profile_name = profile_type.value
        else:
            profile_name = str(profile_type)

        # Create base configuration
        config = Configuration(profile_type=profile_name)

        # Get profile-specific defaults
        profile_defaults = self._get_profile_defaults(profile_name)

        # Core application settings
        config.add_value("APP_NAME", "GiljoAI_MCP", description="Application name")
        config.add_value("APP_VERSION", "1.0.0", description="Application version")
        config.add_value(
            "APP_ENV", profile_defaults.get("environment", "development"), description="Application environment"
        )
        config.add_value("DEBUG", profile_defaults.get("debug", False), description="Enable debug mode")

        # API Configuration
        config.add_value("API_HOST", user_inputs.get("api_host", "0.0.0.0"), description="API server host")
        config.add_value("API_PORT", user_inputs.get("api_port", 8000), description="API server port")
        config.add_value("API_WORKERS", profile_defaults.get("workers", 1), description="Number of API workers")

        # Frontend Configuration
        config.add_value(
            "FRONTEND_HOST", user_inputs.get("frontend_host", "localhost"), description="Frontend server host"
        )
        config.add_value("FRONTEND_PORT", user_inputs.get("frontend_port", 7274), description="Frontend server port")
        config.add_value(
            "FRONTEND_URL",
            f"http://{user_inputs.get('frontend_host', 'localhost')}:{user_inputs.get('frontend_port', 3000)}",
            description="Frontend URL",
        )

        # WebSocket Configuration
        config.add_value("WEBSOCKET_PORT", user_inputs.get("websocket_port", 7273), description="WebSocket server port")
        config.add_value("WEBSOCKET_ENABLED", True, description="Enable WebSocket support")

        # Database Configuration
        db_type = profile_defaults.get("database", "sqlite")
        if db_type == "postgresql" and "postgresql" in connection_strings:
            config.add_value(
                "DATABASE_URL",
                connection_strings["postgresql"],
                description="PostgreSQL connection string",
                secret=True,
            )
        else:
            # SQLite fallback
            db_path = user_inputs.get("db_path", "data/giljo_mcp.db")
            config.add_value("DATABASE_URL", f"sqlite:///{db_path}", description="Database connection string")

        config.add_value("DATABASE_TYPE", db_type, description="Database type")
        config.add_value(
            "DATABASE_POOL_SIZE", profile_defaults.get("db_pool_size", 5), description="Database connection pool size"
        )

        # Redis Configuration
        if "redis" in connection_strings:
            config.add_value(
                "REDIS_URL", connection_strings["redis"], description="Redis connection string", secret=True
            )
        else:
            redis_host = user_inputs.get("redis_host", "localhost")
            redis_port = user_inputs.get("redis_port", 6379)
            config.add_value("REDIS_URL", f"redis://{redis_host}:{redis_port}/0", description="Redis connection string")

        config.add_value(
            "REDIS_ENABLED", profile_defaults.get("redis_enabled", False), description="Enable Redis caching"
        )

        # Security Configuration
        config.add_value("SECRET_KEY", self._generate_secret_key(), description="Application secret key", secret=True)
        config.add_value("JWT_SECRET", self._generate_secret_key(), description="JWT signing secret", secret=True)
        config.add_value(
            "CORS_ORIGINS",
            user_inputs.get("cors_origins", ["http://localhost:3000"]),
            description="Allowed CORS origins",
        )
        config.add_value(
            "SECURE_COOKIES", profile_defaults.get("secure_cookies", False), description="Use secure cookies"
        )

        # Authentication Configuration
        auth_enabled = profile_defaults.get("auth_enabled", False)
        config.add_value("AUTH_ENABLED", auth_enabled, description="Enable authentication")

        if auth_enabled:
            config.add_value(
                "AUTH_METHOD", profile_defaults.get("auth_method", "api_key"), description="Authentication method"
            )
            if profile_defaults.get("auth_method") == "api_key":
                config.add_value("API_KEY", self._generate_api_key(), description="API authentication key", secret=True)
            elif profile_defaults.get("auth_method") == "oauth":
                config.add_value(
                    "OAUTH_CLIENT_ID",
                    user_inputs.get("oauth_client_id", ""),
                    description="OAuth client ID",
                    required=True,
                )
                config.add_value(
                    "OAUTH_CLIENT_SECRET",
                    user_inputs.get("oauth_client_secret", ""),
                    description="OAuth client secret",
                    secret=True,
                    required=True,
                )

        # Logging Configuration
        config.add_value("LOG_LEVEL", profile_defaults.get("log_level", "INFO"), description="Logging level")
        config.add_value(
            "LOG_FORMAT",
            "json" if profile_name in ["enterprise", "production"] else "text",
            description="Log output format",
        )
        config.add_value("LOG_FILE", user_inputs.get("log_file", "logs/giljo_mcp.log"), description="Log file path")

        # MCP Server Configuration
        config.add_value("MCP_ENABLED", True, description="Enable MCP server")
        config.add_value("MCP_PORT", user_inputs.get("mcp_port", 8002), description="MCP server port")
        config.add_value(
            "MCP_MAX_AGENTS", profile_defaults.get("max_agents", 10), description="Maximum concurrent agents"
        )

        # Profile-specific configurations (simplified - removed unimplemented features)
        if profile_name == "developer":
            pass  # No special config flags for developer mode
        elif profile_name == "team":
            config.add_value("TEAM_NAME", user_inputs.get("team_name", ""), description="Team name", required=True)
            config.add_value("TEAM_SIZE", user_inputs.get("team_size", 5), description="Team size")
        elif profile_name == "enterprise":
            config.add_value(
                "ENTERPRISE_NAME", user_inputs.get("enterprise_name", ""), description="Enterprise name", required=True
            )
        elif profile_name == "research":
            pass  # No special config flags for research mode

        # Docker-specific configurations (for containerized profile)
        if profile_defaults.get("containerized", False):
            config.add_value("DOCKER_NETWORK", "giljo_mcp_network", description="Docker network name")
            config.add_value("DOCKER_VOLUME_DATA", "giljo_mcp_data", description="Docker volume for data")
            config.add_value("DOCKER_VOLUME_LOGS", "giljo_mcp_logs", description="Docker volume for logs")

        # Add metadata
        config.metadata = {
            "installer_version": "1.0.0",
            "generation_method": "installer",
            "profile_used": profile_name,
            "host_system": os.name,
            "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}",
        }

        return config

    def _get_profile_defaults(self, profile_name: str) -> Dict[str, Any]:
        """Get default values for a profile"""
        defaults = {
            "developer": {
                "environment": "development",
                "debug": True,
                "database": "sqlite",
                "workers": 1,
                "redis_enabled": False,
                "auth_enabled": False,
                "log_level": "DEBUG",
                "secure_cookies": False,
                "db_pool_size": 5,
                "max_agents": 5,
                "containerized": False,
            },
            "team": {
                "environment": "staging",
                "debug": False,
                "database": "postgresql",
                "workers": 2,
                "redis_enabled": True,
                "auth_enabled": True,
                "auth_method": "api_key",
                "log_level": "INFO",
                "secure_cookies": False,
                "db_pool_size": 10,
                "max_agents": 20,
                "containerized": False,
            },
            "enterprise": {
                "environment": "production",
                "debug": False,
                "database": "postgresql",
                "workers": 4,
                "redis_enabled": True,
                "auth_enabled": True,
                "auth_method": "oauth",
                "log_level": "WARNING",
                "secure_cookies": True,
                "db_pool_size": 20,
                "max_agents": 100,
                "containerized": True,
            },
            "research": {
                "environment": "research",
                "debug": True,
                "database": "postgresql",
                "workers": 1,
                "redis_enabled": True,
                "auth_enabled": False,
                "log_level": "DEBUG",
                "secure_cookies": False,
                "db_pool_size": 15,
                "max_agents": 50,
                "containerized": False,
            },
            "containerized": {
                "environment": "production",
                "debug": False,
                "database": "postgresql",
                "workers": 4,
                "redis_enabled": True,
                "auth_enabled": True,
                "auth_method": "api_key",
                "log_level": "INFO",
                "secure_cookies": True,
                "db_pool_size": 20,
                "max_agents": 50,
                "containerized": True,
            },
        }
        return defaults.get(profile_name.lower(), defaults["developer"])

    def _generate_secret_key(self, length: int = 32) -> str:
        """Generate a secure secret key"""
        return secrets.token_urlsafe(length)

    def _generate_api_key(self) -> str:
        """Generate an API key"""
        prefix = "gjai"
        key = secrets.token_urlsafe(32)
        return f"{prefix}_{key}"

    def save_configuration(
        self, config: Configuration, output_path: Optional[Path] = None, format: ConfigFormat = ConfigFormat.ENV
    ) -> Path:
        """
        Save configuration to file

        Args:
            config: Configuration to save
            output_path: Where to save (defaults to .env in base path)
            format: Output format

        Returns:
            Path to saved file
        """
        if output_path is None:
            if format == ConfigFormat.ENV:
                output_path = self.base_path / ".env"
            elif format == ConfigFormat.YAML:
                output_path = self.base_path / "config.yaml"
            elif format == ConfigFormat.JSON:
                output_path = self.base_path / "config.json"
            else:
                output_path = self.base_path / f"config.{format.value}"

        output_path = Path(output_path)

        # Backup existing file if it exists
        if output_path.exists():
            self.backup_configuration(output_path)

        # Write new configuration
        if format == ConfigFormat.ENV:
            output_path.write_text(config.to_env())
        elif format == ConfigFormat.YAML:
            with open(output_path, "w") as f:
                yaml.safe_dump(config.to_dict(), f, default_flow_style=False)
        elif format == ConfigFormat.JSON:
            with open(output_path, "w") as f:
                json.dump(config.to_dict(), f, indent=2)
        else:
            # For other formats, use simple key=value
            lines = []
            for key, value in config.values.items():
                lines.append(f"{key}={value.value}")
            output_path.write_text("\n".join(lines))

        return output_path

    def load_configuration(self, config_path: Path) -> Configuration:
        """
        Load configuration from file

        Args:
            config_path: Path to configuration file

        Returns:
            Loaded configuration
        """
        config_path = Path(config_path)

        if not config_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        # Detect format from extension
        ext = config_path.suffix.lower()

        if ext in [".env", ""]:
            return self._load_env_file(config_path)
        elif ext in [".yaml", ".yml"]:
            return self._load_yaml_file(config_path)
        elif ext == ".json":
            return self._load_json_file(config_path)
        else:
            # Try to load as env file
            return self._load_env_file(config_path)

    def _load_env_file(self, path: Path) -> Configuration:
        """Load .env format configuration"""
        config = Configuration(profile_type="unknown")

        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue

                if "=" in line:
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")

                    # Try to parse value type
                    if value.lower() in ["true", "false"]:
                        value = value.lower() == "true"
                    elif value.isdigit():
                        value = int(value)
                    elif value.startswith("[") and value.endswith("]"):
                        try:
                            value = json.loads(value)
                        except:
                            pass

                    config.add_value(key, value)

        return config

    def _load_yaml_file(self, path: Path) -> Configuration:
        """Load YAML format configuration"""
        with open(path, "r") as f:
            data = yaml.safe_load(f)

        config = Configuration(profile_type=data.get("profile_type", "unknown"), version=data.get("version", "1.0.0"))

        for key, value in data.get("values", {}).items():
            config.add_value(key, value)

        config.metadata = data.get("metadata", {})

        return config

    def _load_json_file(self, path: Path) -> Configuration:
        """Load JSON format configuration"""
        with open(path, "r") as f:
            data = json.load(f)

        config = Configuration(profile_type=data.get("profile_type", "unknown"), version=data.get("version", "1.0.0"))

        for key, value in data.get("values", {}).items():
            config.add_value(key, value)

        config.metadata = data.get("metadata", {})

        return config

    def validate_configuration(self, config: Configuration) -> tuple[bool, List[str]]:
        """
        Validate a configuration

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required values
        for key, value in config.values.items():
            if value.required and (value.value is None or value.value == ""):
                errors.append(f"Required value missing: {key}")

        # Validate specific fields
        if config.get_value("API_PORT"):
            port = config.get_value("API_PORT")
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Invalid API_PORT: {port}")

        if config.get_value("FRONTEND_PORT"):
            port = config.get_value("FRONTEND_PORT")
            if not isinstance(port, int) or port < 1 or port > 65535:
                errors.append(f"Invalid FRONTEND_PORT: {port}")

        # Check database URL format
        db_url = config.get_value("DATABASE_URL")
        if db_url:
            if not any(db_url.startswith(prefix) for prefix in ["sqlite://", "postgresql://", "mysql://"]):
                errors.append(f"Invalid DATABASE_URL format: {db_url}")

        # Check Redis URL format if enabled
        if config.get_value("REDIS_ENABLED"):
            redis_url = config.get_value("REDIS_URL")
            if not redis_url or not redis_url.startswith("redis://"):
                errors.append(f"Invalid REDIS_URL format: {redis_url}")

        # Validate auth configuration
        if config.get_value("AUTH_ENABLED"):
            auth_method = config.get_value("AUTH_METHOD")
            if auth_method == "api_key" and not config.get_value("API_KEY"):
                errors.append("API_KEY required when AUTH_METHOD is api_key")
            elif auth_method == "oauth":
                if not config.get_value("OAUTH_CLIENT_ID"):
                    errors.append("OAUTH_CLIENT_ID required for OAuth")
                if not config.get_value("OAUTH_CLIENT_SECRET"):
                    errors.append("OAUTH_CLIENT_SECRET required for OAuth")

        # Check log level
        valid_log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        log_level = config.get_value("LOG_LEVEL")
        if log_level and log_level not in valid_log_levels:
            errors.append(f"Invalid LOG_LEVEL: {log_level}")

        return len(errors) == 0, errors

    def backup_configuration(self, config_path: Path) -> Path:
        """
        Backup an existing configuration file

        Args:
            config_path: Path to configuration file to backup

        Returns:
            Path to backup file
        """
        config_path = Path(config_path)

        if not config_path.exists():
            return None

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{config_path.stem}_{timestamp}{config_path.suffix}"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(config_path, backup_path)

        # Keep only last 10 backups
        self._cleanup_old_backups()

        return backup_path

    def _cleanup_old_backups(self, keep_count: int = 10):
        """Remove old backup files"""
        backups = sorted(self.backup_dir.glob("*"), key=lambda p: p.stat().st_mtime)

        if len(backups) > keep_count:
            for backup in backups[:-keep_count]:
                backup.unlink()

    def restore_configuration(self, backup_path: Path, target_path: Path) -> bool:
        """
        Restore a configuration from backup

        Args:
            backup_path: Path to backup file
            target_path: Where to restore the configuration

        Returns:
            True if successful
        """
        backup_path = Path(backup_path)
        target_path = Path(target_path)

        if not backup_path.exists():
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        # Backup current file if it exists
        if target_path.exists():
            self.backup_configuration(target_path)

        # Restore from backup
        shutil.copy2(backup_path, target_path)

        return True

    def migrate_configuration(self, old_config_path: Path, new_profile: Optional[str] = None) -> Configuration:
        """
        Migrate an existing configuration to new format

        Args:
            old_config_path: Path to old configuration
            new_profile: Optional new profile to apply

        Returns:
            Migrated configuration
        """
        # Load old configuration
        old_config = self.load_configuration(old_config_path)

        # If new profile specified, regenerate with old values as inputs
        if new_profile:
            user_inputs = {key: value.value for key, value in old_config.values.items()}

            # Generate new configuration with migrated values
            new_config = self.generate_configuration(profile_type=new_profile, user_inputs=user_inputs)

            # Preserve any custom values not in new config
            for key, value in old_config.values.items():
                if key not in new_config.values:
                    new_config.add_value(key, value.value, description=f"Migrated from old config", source="migration")
        else:
            new_config = old_config

        # Update metadata
        new_config.metadata["migrated_from"] = str(old_config_path)
        new_config.metadata["migration_date"] = datetime.now().isoformat()
        new_config.modified_at = datetime.now()

        return new_config

    def diff_configurations(self, config1: Configuration, config2: Configuration) -> Dict[str, Any]:
        """
        Compare two configurations and return differences

        Args:
            config1: First configuration
            config2: Second configuration

        Returns:
            Dictionary of differences
        """
        diff = {"added": {}, "removed": {}, "modified": {}, "unchanged": {}}

        all_keys = set(config1.values.keys()) | set(config2.values.keys())

        for key in all_keys:
            if key in config1.values and key not in config2.values:
                diff["removed"][key] = config1.values[key].value
            elif key not in config1.values and key in config2.values:
                diff["added"][key] = config2.values[key].value
            elif config1.values[key].value != config2.values[key].value:
                diff["modified"][key] = {"old": config1.values[key].value, "new": config2.values[key].value}
            else:
                diff["unchanged"][key] = config1.values[key].value

        return diff


# Convenience functions
def generate_config_for_profile(profile: Union[str, "ProfileType"], **kwargs) -> Configuration:
    """
    Quick function to generate configuration for a profile

    Args:
        profile: Profile name or type
        **kwargs: User inputs and connection strings

    Returns:
        Generated configuration
    """
    manager = ConfigurationManager()
    return manager.generate_configuration(profile, **kwargs)


def validate_env_file(env_path: Union[str, Path]) -> tuple[bool, List[str]]:
    """
    Validate an existing .env file

    Args:
        env_path: Path to .env file

    Returns:
        Tuple of (is_valid, errors)
    """
    manager = ConfigurationManager()
    config = manager.load_configuration(Path(env_path))
    return manager.validate_configuration(config)
