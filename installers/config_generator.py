#!/usr/bin/env python3
"""
Configuration Generator for GiljoAI MCP Orchestrator

Generates default config.yaml with sensible defaults that work out-of-the-box.
"""

import os
import sys
import secrets
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

# Try to import installation manifest
try:
    from installation_manifest import InstallationManifest
except ImportError:
    InstallationManifest = None


class ConfigGenerator:
    """Generates default configuration for GiljoAI MCP"""

    def __init__(self, install_dir: Path = None):
        """Initialize config generator

        Args:
            install_dir: Installation directory (defaults to current directory)
        """
        self.install_dir = Path(install_dir) if install_dir else Path.cwd()
        self.config_path = self.install_dir / "config.yaml"
        self.example_path = self.install_dir / "config.yaml.example"

        # Initialize installation manifest if available
        self.manifest = None
        if InstallationManifest:
            try:
                self.manifest = InstallationManifest(self.install_dir)
            except Exception:
                pass

    def generate_default_config(self) -> Dict[str, Any]:
        """Generate default configuration with working defaults

        Returns:
            Configuration dictionary
        """
        # Generate secure random keys
        jwt_secret = secrets.token_urlsafe(32)
        tenant_key = secrets.token_hex(24)  # 192-bit entropy

        # Build default configuration
        config = {
            "# GiljoAI MCP Orchestrator Configuration": None,
            "# Auto-generated default configuration": None,
            "# This configuration works out-of-the-box with no external dependencies": None,
            "": None,
            "database": {
                "# Using SQLite for zero-dependency local operation": None,
                "database_type": "sqlite",
                "path": "./data/giljo.db",
                "# PostgreSQL configuration (uncomment for production)": None,
                "# database_type": "postgresql",
                "# host": "localhost",
                "# port": 5432,
                "# name": "giljo_mcp",
                "# user": "giljo_user",
                "# password": "your_secure_password",
            },
            "server": {
                "# Local mode for single-user desktop operation": None,
                "mode": "local",
                "host": "localhost",
                "debug": False,
                "# Service ports": None,
                "ports": {
                    "mcp": 6001,  # MCP server port
                    "api": 6002,  # REST API port
                    "frontend": 6000,  # Vue frontend port
                },
            },
            "tenant": {
                "# Single-tenant mode for desktop use": None,
                "enable_multi_tenant": False,
                "default_key": tenant_key,
            },
            "app": {
                "name": "GiljoAI MCP Orchestrator",
                "version": "1.0.0",
                "# Directory paths": None,
                "data_dir": "./data",
                "log_dir": "./logs",
                "config_dir": "./config",
                "vision_dir": "./docs/vision",
            },
            "session": {
                "# Vision document processing": None,
                "vision_chunk_size": 50000,
                "vision_overlap": 1000,
                "context_size": 100000,
                "timeout": 3600,
            },
            "mcp": {"# Using stdio mode for simplicity": None, "stdio_mode": True, "transport": "stdio"},
            "api": {
                "# CORS for local development": None,
                "cors_origins": ["http://localhost:6000", "http://localhost:5500", "http://127.0.0.1:6000"],
                "rate_limit": 100,
                "require_api_key": False,
            },
            "websocket": {"heartbeat_interval": 30, "max_connections": 10, "queue_size": 1000},
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
                "file": "./logs/giljo.log",
                "max_bytes": 10485760,  # 10MB
                "backup_count": 5,
                "console": True,
            },
            "agents": {
                "# Pre-configured example agents": None,
                "max_concurrent": 50,
                "timeout": 300,
                "default_capabilities": ["code_analysis", "code_generation", "testing", "documentation"],
                "# Example agent configurations": None,
                "preconfigured": [
                    {
                        "name": "assistant",
                        "role": "General coding assistant",
                        "capabilities": ["code", "documentation", "testing"],
                    },
                    {
                        "name": "analyzer",
                        "role": "Code analysis and review",
                        "capabilities": ["analysis", "review", "refactoring"],
                    },
                    {
                        "name": "builder",
                        "role": "Build and deployment",
                        "capabilities": ["build", "deploy", "configuration"],
                    },
                ],
            },
            "templates": {"cache_enabled": True, "cache_ttl": 3600, "generation_target_ms": 0.1},
            "security": {
                "# Auto-generated secure keys": None,
                "jwt_secret_key": jwt_secret,
                "jwt_algorithm": "HS256",
                "jwt_expiry": 86400,
                "# Relaxed for local development": None,
                "min_password_length": 8,
                "require_special_chars": False,
                "secure_cookies": False,
                "session_cookie_name": "giljo_session",
            },
            "performance": {
                "db_pool_size": 20,
                "db_pool_overflow": 10,
                "enable_cache": True,
                "cache_backend": "memory",
                "max_request_size": 10485760,  # 10MB
            },
            "development": {
                "# Development-friendly settings": None,
                "auto_reload": True,
                "debug_toolbar": False,
                "enable_profiling": False,
            },
        }

        return self._clean_config(config)

    def _clean_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Remove comment entries from config dictionary

        Args:
            config: Configuration with comment entries

        Returns:
            Clean configuration dictionary
        """
        clean = {}
        for key, value in config.items():
            # Skip comment entries
            if key.startswith("#") or value is None:
                continue
            # Recursively clean nested dictionaries
            if isinstance(value, dict):
                clean[key] = self._clean_config(value)
            elif isinstance(value, list):
                # Clean list items if they're dictionaries
                clean[key] = [self._clean_config(item) if isinstance(item, dict) else item for item in value]
            else:
                clean[key] = value
        return clean

    def create_config_file(self, force: bool = False) -> tuple[bool, str]:
        """Create config.yaml file with defaults

        Args:
            force: Overwrite existing config.yaml if True

        Returns:
            Tuple of (success, message)
        """
        # Check if config already exists
        if self.config_path.exists() and not force:
            return False, f"Config file already exists: {self.config_path}"

        try:
            # Generate default configuration
            config = self.generate_default_config()

            # Ensure directories exist
            self.config_path.parent.mkdir(parents=True, exist_ok=True)

            # Write config file with proper formatting
            with open(self.config_path, "w") as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False, width=120, indent=2)

            # Track in manifest
            if self.manifest:
                self.manifest.add_file(self.config_path, category="config", is_user_data=True)
                self.manifest.save_manifest()

            return True, f"Created default config: {self.config_path}"

        except Exception as e:
            return False, f"Failed to create config: {e}"

    def create_required_directories(self) -> tuple[bool, str]:
        """Create all required directories from config

        Returns:
            Tuple of (success, message)
        """
        try:
            # Directories to create
            dirs = [
                self.install_dir / "data",
                self.install_dir / "logs",
                self.install_dir / "config",
                self.install_dir / "docs" / "Vision",
            ]

            for dir_path in dirs:
                dir_path.mkdir(parents=True, exist_ok=True)

                # Track in manifest
                if self.manifest:
                    # Mark data and logs as user data
                    is_user_data = dir_path.name in ["data", "logs"]
                    self.manifest.add_directory(
                        dir_path, category="data" if is_user_data else "general", is_user_data=is_user_data
                    )

            # Save manifest after tracking all directories
            if self.manifest:
                self.manifest.save_manifest()

            return True, "Created all required directories"

        except Exception as e:
            return False, f"Failed to create directories: {e}"

    def validate_config(self, config_path: Path = None) -> tuple[bool, str]:
        """Validate configuration file

        Args:
            config_path: Path to config file (defaults to config.yaml)

        Returns:
            Tuple of (valid, message)
        """
        if config_path is None:
            config_path = self.config_path

        if not config_path.exists():
            return False, f"Config file not found: {config_path}"

        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)

            # Check required sections
            required_sections = ["database", "server", "app", "mcp"]
            missing = [s for s in required_sections if s not in config]

            if missing:
                return False, f"Missing required sections: {', '.join(missing)}"

            # Validate database configuration
            db_config = config.get("database", {})
            db_type = db_config.get("database_type", "sqlite")

            if db_type == "sqlite":
                if "path" not in db_config:
                    return False, "SQLite configuration missing 'path'"
            elif db_type == "postgresql":
                required_pg = ["host", "port", "name", "user", "password"]
                missing_pg = [k for k in required_pg if k not in db_config]
                if missing_pg:
                    return False, f"PostgreSQL configuration missing: {', '.join(missing_pg)}"

            return True, "Configuration is valid"

        except yaml.YAMLError as e:
            return False, f"Invalid YAML: {e}"
        except Exception as e:
            return False, f"Failed to validate config: {e}"

    def merge_with_example(self) -> tuple[bool, str]:
        """Merge current config with example to add any missing keys

        Returns:
            Tuple of (success, message)
        """
        if not self.example_path.exists():
            return False, "Example config not found"

        try:
            # Load current config
            if self.config_path.exists():
                with open(self.config_path, "r") as f:
                    current = yaml.safe_load(f) or {}
            else:
                current = {}

            # Load example config
            with open(self.example_path, "r") as f:
                example = yaml.safe_load(f) or {}

            # Deep merge configurations
            merged = self._deep_merge(example, current)

            # Write merged config
            with open(self.config_path, "w") as f:
                yaml.dump(merged, f, default_flow_style=False, sort_keys=False, width=120, indent=2)

            return True, "Merged configuration with example"

        except Exception as e:
            return False, f"Failed to merge configs: {e}"

    def _deep_merge(self, base: Dict, override: Dict) -> Dict:
        """Deep merge two dictionaries

        Args:
            base: Base dictionary
            override: Override dictionary

        Returns:
            Merged dictionary
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result


def main():
    """Main entry point for config generator"""
    import sys

    print("GiljoAI MCP Configuration Generator")
    print("===================================\n")

    # Get installation directory
    if len(sys.argv) > 1:
        install_dir = Path(sys.argv[1])
    else:
        install_dir = Path.cwd()

    generator = ConfigGenerator(install_dir)

    # Create directories
    success, msg = generator.create_required_directories()
    print(f"{'[OK]' if success else '[FAIL]'} {msg}")

    # Create config file
    success, msg = generator.create_config_file()
    print(f"{'[OK]' if success else '[FAIL]'} {msg}")

    if success:
        # Validate the created config
        valid, msg = generator.validate_config()
        print(f"{'[OK]' if valid else '[FAIL]'} Validation: {msg}")

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
