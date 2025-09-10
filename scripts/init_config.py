#!/usr/bin/env python3
"""
Configuration Initialization Script for GiljoAI MCP
Creates and validates configuration files for different deployment modes
"""

import sys
import os
from pathlib import Path
import argparse
import json
import yaml

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.giljo_mcp.config_manager import (
    ConfigManager, 
    DeploymentMode, 
    ConfigValidationError,
    generate_sample_config
)


def init_local_config():
    """Initialize configuration for local development"""
    print("Initializing LOCAL configuration...")
    
    config = ConfigManager(auto_reload=False)
    config.server.mode = DeploymentMode.LOCAL
    
    # Local defaults
    config.database.type = 'sqlite'
    config.server.api_key = None
    
    config.save_to_file()
    print(f"✓ Created config.yaml for LOCAL mode")
    print(f"  Database: SQLite at {config.database.sqlite_path}")
    print(f"  Dashboard: http://localhost:{config.server.dashboard_port}")
    print(f"  API: http://localhost:{config.server.api_port}")


def init_lan_config():
    """Initialize configuration for LAN deployment"""
    print("Initializing LAN configuration...")
    
    config = ConfigManager(auto_reload=False)
    config.server.mode = DeploymentMode.LAN
    
    # LAN settings
    config.server.api_host = "0.0.0.0"
    config.server.dashboard_host = "0.0.0.0"
    
    # Generate API key
    import secrets
    config.server.api_key = secrets.token_urlsafe(32)
    
    # Prefer PostgreSQL for LAN
    config.database.type = 'postgresql'
    
    config.save_to_file()
    print(f"✓ Created config.yaml for LAN mode")
    print(f"  Database: PostgreSQL at {config.database.pg_host}:{config.database.pg_port}")
    print(f"  Dashboard: http://<your-ip>:{config.server.dashboard_port}")
    print(f"  API: http://<your-ip>:{config.server.api_port}")
    print(f"  API Key: {config.server.api_key}")
    print("\n⚠️  Save your API key securely!")


def init_wan_config():
    """Initialize configuration for WAN deployment"""
    print("Initializing WAN configuration...")
    
    config = ConfigManager(auto_reload=False)
    config.server.mode = DeploymentMode.WAN
    
    # WAN settings
    config.server.api_host = "0.0.0.0"
    config.server.dashboard_host = "0.0.0.0"
    
    # Generate strong keys
    import secrets
    config.server.api_key = secrets.token_urlsafe(32)
    
    # Require PostgreSQL for WAN
    config.database.type = 'postgresql'
    
    config.save_to_file()
    print(f"✓ Created config.yaml for WAN mode")
    print(f"  Database: PostgreSQL (configure in .env)")
    print(f"  API Key: {config.server.api_key}")
    print("\n⚠️  Important for WAN deployment:")
    print("  1. Configure TLS/SSL certificates")
    print("  2. Set up OAuth authentication")
    print("  3. Configure firewall rules")
    print("  4. Save your API key securely!")


def validate_config(config_path: Path = None):
    """Validate existing configuration"""
    print("Validating configuration...")
    
    try:
        config = ConfigManager(config_path=config_path)
        config.validate()
        
        print("✓ Configuration is valid")
        print(f"  Mode: {config.server.mode.value}")
        print(f"  Database: {config.database.type}")
        
        # Test database connection
        if config.database.type == 'postgresql':
            print("  Testing PostgreSQL connection...")
            try:
                db_manager = config.create_database_manager()
                print("  ✓ Database connection successful")
            except Exception as e:
                print(f"  ✗ Database connection failed: {e}")
        
        return True
        
    except ConfigValidationError as e:
        print(f"✗ Configuration validation failed:")
        print(f"  {e}")
        return False
    except Exception as e:
        print(f"✗ Error loading configuration: {e}")
        return False


def show_config(config_path: Path = None):
    """Display current configuration"""
    try:
        config = ConfigManager(config_path=config_path)
        settings = config.get_all_settings()
        
        print("\nCurrent Configuration:")
        print("-" * 50)
        print(yaml.dump(settings, default_flow_style=False, sort_keys=False))
        
    except Exception as e:
        print(f"Error loading configuration: {e}")


def migrate_from_env():
    """Migrate settings from .env file to config.yaml"""
    print("Migrating from .env to config.yaml...")
    
    env_file = Path(".env")
    if not env_file.exists():
        print("✗ No .env file found")
        return
    
    config = ConfigManager(auto_reload=False)
    
    # Read .env file
    env_vars = {}
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    # Apply environment variables
    if 'GILJO_MCP_MODE' in env_vars:
        config.server.mode = DeploymentMode(env_vars['GILJO_MCP_MODE'])
    
    if 'DB_TYPE' in env_vars:
        config.database.type = env_vars['DB_TYPE']
    
    if 'DB_HOST' in env_vars:
        config.database.pg_host = env_vars['DB_HOST']
    
    if 'DB_PORT' in env_vars:
        config.database.pg_port = int(env_vars['DB_PORT'])
    
    if 'DB_NAME' in env_vars:
        config.database.pg_database = env_vars['DB_NAME']
    
    if 'DB_USER' in env_vars:
        config.database.pg_user = env_vars['DB_USER']
    
    if 'DB_PASSWORD' in env_vars:
        config.database.pg_password = env_vars['DB_PASSWORD']
    
    if 'GILJO_MCP_API_KEY' in env_vars:
        config.server.api_key = env_vars['GILJO_MCP_API_KEY']
    
    if 'LOG_LEVEL' in env_vars:
        config.logging.level = env_vars['LOG_LEVEL']
    
    # Save to config.yaml
    config.save_to_file()
    print("✓ Migrated settings to config.yaml")
    print("  You can now use config.yaml instead of .env")


def test_integration():
    """Test configuration integration with database and tenant managers"""
    print("Testing configuration integration...")
    
    try:
        config = ConfigManager()
        
        # Test database manager creation
        print("  Testing DatabaseManager creation...")
        db_manager = config.create_database_manager()
        print(f"  ✓ DatabaseManager created (async={db_manager.is_async})")
        
        # Test tenant manager creation
        print("  Testing TenantManager creation...")
        tenant_manager = config.get_tenant_manager()
        print(f"  ✓ TenantManager created (multi_tenant={config.features.multi_tenant})")
        
        # Test tenant-specific database
        if config.features.multi_tenant:
            print("  Testing tenant-specific database...")
            test_tenant_key = "test_tenant_123"
            tenant_db = config.create_database_manager(tenant_key=test_tenant_key)
            print(f"  ✓ Tenant database created for key: {test_tenant_key}")
        
        print("\n✓ All integration tests passed!")
        return True
        
    except Exception as e:
        print(f"\n✗ Integration test failed: {e}")
        return False


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description='Initialize GiljoAI MCP configuration',
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
        """
    )
    
    parser.add_argument(
        '--mode',
        choices=['local', 'lan', 'wan'],
        help='Initialize configuration for specified mode'
    )
    parser.add_argument(
        '--validate',
        action='store_true',
        help='Validate existing configuration'
    )
    parser.add_argument(
        '--show',
        action='store_true',
        help='Display current configuration'
    )
    parser.add_argument(
        '--migrate',
        action='store_true',
        help='Migrate from .env to config.yaml'
    )
    parser.add_argument(
        '--test',
        action='store_true',
        help='Test configuration integration'
    )
    parser.add_argument(
        '--sample',
        action='store_true',
        help='Generate sample config.yaml'
    )
    parser.add_argument(
        '--config',
        type=Path,
        help='Path to config.yaml (default: ./config.yaml)'
    )
    
    args = parser.parse_args()
    
    # Handle different actions
    if args.mode:
        if args.mode == 'local':
            init_local_config()
        elif args.mode == 'lan':
            init_lan_config()
        elif args.mode == 'wan':
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
        path = generate_sample_config(args.config)
        print(f"✓ Generated sample configuration at {path}")
    else:
        parser.print_help()


if __name__ == "__main__":
    main()