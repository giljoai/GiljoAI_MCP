#!/usr/bin/env python3
"""
Configuration Initialization Script for GiljoAI MCP
Creates and validates configuration files for different deployment modes
"""

import argparse
import sys
from pathlib import Path


# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

import contextlib
from typing import Optional

from src.giljo_mcp.config_manager import ConfigManager, ConfigValidationError, generate_sample_config


def init_local_config():
    """Initialize configuration for local development (binds 127.0.0.1, HTTP)"""

    config = ConfigManager(auto_reload=False)

    # Local defaults (localhost binds 127.0.0.1 HTTP; bind address derived from install-time network choice)
    config.database.type = "postgresql"
    config.server.api_key = None

    config.save_to_file()


def init_lan_config():
    """Initialize configuration for LAN deployment (binds 0.0.0.0, HTTPS via mkcert)"""

    config = ConfigManager(auto_reload=False)

    # LAN settings (binds 0.0.0.0 with HTTPS via mkcert)
    # Bind address derived from install-time network choice

    # Generate API key
    import secrets

    config.server.api_key = secrets.token_urlsafe(32)

    # Prefer PostgreSQL for LAN
    config.database.type = "postgresql"

    config.save_to_file()


def init_wan_config():
    """Initialize configuration for WAN deployment (binds 0.0.0.0, HTTPS via mkcert)"""

    config = ConfigManager(auto_reload=False)

    # WAN settings (binds 0.0.0.0 with HTTPS via mkcert)
    # Bind address derived from install-time network choice

    # Generate strong keys
    import secrets

    config.server.api_key = secrets.token_urlsafe(32)

    # Require PostgreSQL for WAN
    config.database.type = "postgresql"

    config.save_to_file()


def validate_config(config_path: Optional[Path] = None):
    """Validate existing configuration"""

    try:
        config = ConfigManager(config_path=config_path)
        config.validate()

        # Test database connection
        if config.database.type == "postgresql":
            with contextlib.suppress(Exception):
                config.create_database_manager()

        return True

    except ConfigValidationError:
        return False
    except Exception:
        return False


def show_config(config_path: Optional[Path] = None):
    """Display current configuration"""
    try:
        config = ConfigManager(config_path=config_path)
        config.get_all_settings()

    except Exception:
        pass


def migrate_from_env():
    """Migrate settings from .env file to config.yaml"""

    env_file = Path(".env")
    if not env_file.exists():
        return

    config = ConfigManager(auto_reload=False)

    # Read .env file
    env_vars = {}
    with open(env_file) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()

    # Apply environment variables
    # v3.0: GILJO_MCP_MODE ignored (DeploymentMode removed)

    if "DB_TYPE" in env_vars:
        config.database.type = env_vars["DB_TYPE"]

    if "DB_HOST" in env_vars:
        config.database.host = env_vars["DB_HOST"]

    if "DB_PORT" in env_vars:
        config.database.port = int(env_vars["DB_PORT"])

    if "DB_NAME" in env_vars:
        config.database.database_name = env_vars["DB_NAME"]

    if "DB_USER" in env_vars:
        config.database.username = env_vars["DB_USER"]

    if "DB_PASSWORD" in env_vars:
        config.database.password = env_vars["DB_PASSWORD"]

    if "GILJO_MCP_API_KEY" in env_vars:
        config.server.api_key = env_vars["GILJO_MCP_API_KEY"]

    if "LOG_LEVEL" in env_vars:
        config.logging.level = env_vars["LOG_LEVEL"]

    # Save to config.yaml
    config.save_to_file()


def test_integration():
    """Test configuration integration with database and tenant managers"""

    try:
        config = ConfigManager()

        # Test database manager creation
        config.create_database_manager()

        # Test tenant manager creation
        config.get_tenant_manager()

        # Test tenant-specific database
        if config.features.multi_tenant:
            test_tenant_key = "test_tenant_123"
            config.create_database_manager(tenant_key=test_tenant_key)

        return True

    except Exception:
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Initialize GiljoAI MCP configuration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --mode local     # Initialize for local development
  %(prog)s --mode lan       # Initialize for LAN deployment
  %(prog)s --mode wan       # Initialize for WAN deployment
  %(prog)s --validate       # Validate existing configuration
  %(prog)s --show           # Display current configuration
  %(prog)s --migrate        # Migrate from .env to config.yaml
  %(prog)s --test           # Test configuration integration
  %(prog)s --sample         # Generate sample config.yaml
        """,
    )

    parser.add_argument("--mode", choices=["local", "lan", "wan"], help="Initialize configuration for specified mode")
    parser.add_argument("--validate", action="store_true", help="Validate existing configuration")
    parser.add_argument("--show", action="store_true", help="Display current configuration")
    parser.add_argument("--migrate", action="store_true", help="Migrate from .env to config.yaml")
    parser.add_argument("--test", action="store_true", help="Test configuration integration")
    parser.add_argument("--sample", action="store_true", help="Generate sample config.yaml")
    parser.add_argument("--config", type=Path, help="Path to config.yaml (default: ./config.yaml)")

    args = parser.parse_args()

    # Handle different actions
    if args.mode:
        if args.mode == "local":
            init_local_config()
        elif args.mode == "lan":
            init_lan_config()
        elif args.mode == "wan":
            init_wan_config()
    elif args.validate:
        success = validate_config(args.config)
        sys.exit(0 if success else 1)
    elif args.show:
        show_config(args.config)
    elif args.migrate:
        migrate_from_env()
    elif args.test:
        success = test_integration()
        sys.exit(0 if success else 1)
    elif args.sample:
        generate_sample_config(args.config)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
