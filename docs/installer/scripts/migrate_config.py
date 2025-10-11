#!/usr/bin/env python3
"""
Configuration Migration Script
Migrates existing .env files to the new harmonized format
"""

import os
import sys
import shutil
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional


class ConfigMigrator:
    """Migrate existing configurations to harmonized format"""

    # Mapping of old variable names to new ones
    VARIABLE_MAPPING = {
        # Port mappings
        'API_PORT': ['GILJO_API_PORT', 'GILJO_PORT'],
        'WEBSOCKET_PORT': None,  # Removed - WebSocket uses same port as API in v2.0
        'DASHBOARD_PORT': ['GILJO_FRONTEND_PORT', 'VITE_FRONTEND_PORT'],

        # Database mappings (keep old, add new)
        'POSTGRES_HOST': ['DB_HOST'],
        'POSTGRES_PORT': ['DB_PORT'],
        'POSTGRES_DB': ['DB_NAME'],
        'POSTGRES_USER': ['DB_USER'],
        'POSTGRES_PASSWORD': ['DB_PASSWORD'],

        # Service binding
        'SERVICE_BIND': ['GILJO_API_HOST'],

        # Environment
        'ENVIRONMENT': [],
        'DEBUG': [],
        'LOG_LEVEL': [],
    }

    # New required variables that might not exist
    NEW_REQUIRED = {
        'DATABASE_URL': None,  # Will be generated from DB vars
        'GILJO_MCP_MODE': 'LOCAL',
        'VITE_API_URL': None,  # Will be generated
        'VITE_WS_URL': None,   # Will be generated
        'VITE_APP_MODE': 'local',
        'VITE_API_PORT': None,  # Will be copied from GILJO_API_PORT

        # Feature flags
        'ENABLE_VISION_CHUNKING': 'true',
        'ENABLE_MULTI_TENANT': 'true',
        'ENABLE_WEBSOCKET': 'true',
        'ENABLE_AUTO_HANDOFF': 'true',
        'ENABLE_DYNAMIC_DISCOVERY': 'true',

        # Agent configuration
        'MAX_AGENTS_PER_PROJECT': '20',
        'AGENT_CONTEXT_LIMIT': '150000',
        'AGENT_HANDOFF_THRESHOLD': '140000',

        # Session configuration
        'SESSION_TIMEOUT': '3600',
        'MAX_CONCURRENT_SESSIONS': '10',
        'SESSION_CLEANUP_INTERVAL': '300',

        # Message queue
        'MAX_QUEUE_SIZE': '1000',
        'MESSAGE_BATCH_SIZE': '10',
        'MESSAGE_RETRY_ATTEMPTS': '3',
        'MESSAGE_RETRY_DELAY': '1.0',
    }

    def __init__(self, env_path: Path = None):
        self.env_path = env_path or Path('.env')
        self.backup_path = None
        self.env_vars = {}
        self.new_vars = {}

    def backup_existing(self) -> bool:
        """Create backup of existing .env file"""
        if not self.env_path.exists():
            print(f"No existing .env file at {self.env_path}")
            return False

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        self.backup_path = self.env_path.with_suffix(f'.backup_{timestamp}')

        try:
            shutil.copy2(self.env_path, self.backup_path)
            print(f"Created backup: {self.backup_path}")
            return True
        except Exception as e:
            print(f"Failed to create backup: {e}")
            return False

    def parse_env_file(self) -> Dict[str, str]:
        """Parse existing .env file"""
        if not self.env_path.exists():
            return {}

        vars = {}
        with open(self.env_path, 'r') as f:
            for line in f:
                line = line.strip()
                # Skip comments and empty lines
                if not line or line.startswith('#'):
                    continue

                # Parse KEY=VALUE
                if '=' in line:
                    key, value = line.split('=', 1)
                    vars[key.strip()] = value.strip()

        self.env_vars = vars
        return vars

    def migrate_variables(self) -> Dict[str, str]:
        """Migrate old variables to new format"""
        new_vars = {}

        # Copy all existing variables
        new_vars.update(self.env_vars)

        # Apply mappings
        for old_var, new_var_list in self.VARIABLE_MAPPING.items():
            if old_var in self.env_vars and new_var_list:
                value = self.env_vars[old_var]
                for new_var in new_var_list:
                    new_vars[new_var] = value

        # Handle special cases

        # 1. Port corrections
        if 'API_PORT' in self.env_vars:
            api_port = self.env_vars['API_PORT']
            # Fix wrong default ports
            if api_port in ['8000', '8080']:
                api_port = '7272'
                print(f"Corrected API port from {self.env_vars['API_PORT']} to 7272")

            new_vars['GILJO_API_PORT'] = api_port
            new_vars['GILJO_PORT'] = api_port
            new_vars['VITE_API_PORT'] = api_port

        if 'DASHBOARD_PORT' in self.env_vars:
            dashboard_port = self.env_vars['DASHBOARD_PORT']
            # Fix wrong default port
            if dashboard_port == '3000':
                dashboard_port = '6000'
                print(f"Corrected frontend port from 3000 to 6000")

            new_vars['GILJO_FRONTEND_PORT'] = dashboard_port
            new_vars['VITE_FRONTEND_PORT'] = dashboard_port

        # 2. Generate DATABASE_URL if not present
        if 'DATABASE_URL' not in new_vars:
            db_user = new_vars.get('DB_USER', new_vars.get('POSTGRES_USER', 'giljo_user'))
            db_pass = new_vars.get('DB_PASSWORD', new_vars.get('POSTGRES_PASSWORD', ''))
            db_host = new_vars.get('DB_HOST', new_vars.get('POSTGRES_HOST', 'localhost'))
            db_port = new_vars.get('DB_PORT', new_vars.get('POSTGRES_PORT', '5432'))
            db_name = new_vars.get('DB_NAME', new_vars.get('POSTGRES_DB', 'giljo_mcp'))

            if db_user and db_pass:
                new_vars['DATABASE_URL'] = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
                print(f"Generated DATABASE_URL")

        # 3. Generate VITE URLs
        bind_host = new_vars.get('GILJO_API_HOST', new_vars.get('SERVICE_BIND', '127.0.0.1'))
        api_port = new_vars.get('GILJO_API_PORT', '7272')

        # For localhost, use 'localhost' in URLs, not 127.0.0.1
        url_host = 'localhost' if bind_host == '127.0.0.1' else bind_host

        new_vars['VITE_API_URL'] = f"http://{url_host}:{api_port}"
        new_vars['VITE_WS_URL'] = f"ws://{url_host}:{api_port}"

        # 4. Add missing required variables
        for var, default_value in self.NEW_REQUIRED.items():
            if var not in new_vars and default_value is not None:
                new_vars[var] = default_value
                print(f"Added missing variable: {var}={default_value}")

        # 5. Determine mode
        if 'GILJO_MCP_MODE' not in new_vars:
            if bind_host == '127.0.0.1':
                new_vars['GILJO_MCP_MODE'] = 'LOCAL'
            elif bind_host == '0.0.0.0':
                new_vars['GILJO_MCP_MODE'] = 'LAN'
            print(f"Set mode to: {new_vars['GILJO_MCP_MODE']}")

        # 6. App mode for Vite
        mode = new_vars.get('GILJO_MCP_MODE', 'LOCAL')
        new_vars['VITE_APP_MODE'] = 'local' if mode == 'LOCAL' else 'server'

        self.new_vars = new_vars
        return new_vars

    def write_migrated_env(self) -> bool:
        """Write migrated .env file"""
        try:
            # Group variables by category
            categories = {
                'PORT CONFIGURATION': [
                    'GILJO_API_PORT', 'GILJO_PORT', 'GILJO_FRONTEND_PORT',
                    'VITE_FRONTEND_PORT', 'POSTGRES_PORT', 'DB_PORT'
                ],
                'DATABASE CONFIGURATION': [
                    'POSTGRES_HOST', 'POSTGRES_PORT', 'POSTGRES_DB',
                    'POSTGRES_USER', 'POSTGRES_PASSWORD',
                    'POSTGRES_OWNER_USER', 'POSTGRES_OWNER_PASSWORD',
                    'DB_TYPE', 'DB_HOST', 'DB_PORT', 'DB_NAME',
                    'DB_USER', 'DB_PASSWORD', 'DATABASE_URL'
                ],
                'SERVER CONFIGURATION': [
                    'GILJO_MCP_MODE', 'GILJO_API_HOST', 'SERVICE_BIND'
                ],
                'FRONTEND CONFIGURATION': [
                    'VITE_API_URL', 'VITE_WS_URL', 'VITE_APP_MODE', 'VITE_API_PORT'
                ],
                'ENVIRONMENT SETTINGS': [
                    'ENVIRONMENT', 'DEBUG', 'LOG_LEVEL', 'LOG_FILE'
                ],
                'SECURITY': [
                    'GILJO_MCP_API_KEY', 'GILJO_MCP_SECRET_KEY',
                    'SECRET_KEY', 'JWT_SECRET', 'SESSION_SECRET'
                ],
                'CORS CONFIGURATION': ['CORS_ORIGINS'],
                'FEATURE FLAGS': [
                    'ENABLE_VISION_CHUNKING', 'ENABLE_MULTI_TENANT',
                    'ENABLE_WEBSOCKET', 'ENABLE_AUTO_HANDOFF',
                    'ENABLE_DYNAMIC_DISCOVERY', 'ENABLE_SSL',
                    'ENABLE_API_KEYS', 'ENABLE_MULTI_USER'
                ],
                'AGENT CONFIGURATION': [
                    'MAX_AGENTS_PER_PROJECT', 'AGENT_CONTEXT_LIMIT',
                    'AGENT_HANDOFF_THRESHOLD'
                ],
                'SESSION CONFIGURATION': [
                    'SESSION_TIMEOUT', 'MAX_CONCURRENT_SESSIONS',
                    'SESSION_CLEANUP_INTERVAL'
                ],
                'MESSAGE QUEUE CONFIGURATION': [
                    'MAX_QUEUE_SIZE', 'MESSAGE_BATCH_SIZE',
                    'MESSAGE_RETRY_ATTEMPTS', 'MESSAGE_RETRY_DELAY'
                ],
                'PATHS': [
                    'DATA_DIR', 'LOGS_DIR', 'UPLOAD_DIR', 'TEMP_DIR'
                ],
                'PERFORMANCE': [
                    'WORKER_COUNT', 'CONNECTION_POOL_SIZE'
                ]
            }

            # Write new .env file
            lines = []
            lines.append("# GiljoAI MCP Environment Configuration")
            lines.append(f"# Migrated: {datetime.now().isoformat()}")
            lines.append(f"# Original backed up to: {self.backup_path.name if self.backup_path else 'N/A'}")
            lines.append("")

            # Track written variables
            written = set()

            # Write categorized variables
            for category, var_list in categories.items():
                category_has_vars = False
                category_lines = []

                for var in var_list:
                    if var in self.new_vars:
                        if not category_has_vars:
                            category_lines.append(f"# {'=' * 77}")
                            category_lines.append(f"# {category}")
                            category_lines.append(f"# {'=' * 77}")
                            category_has_vars = True

                        category_lines.append(f"{var}={self.new_vars[var]}")
                        written.add(var)

                if category_has_vars:
                    lines.extend(category_lines)
                    lines.append("")

            # Write any remaining variables not in categories
            remaining = {k: v for k, v in self.new_vars.items() if k not in written}
            if remaining:
                lines.append("# " + "=" * 77)
                lines.append("# OTHER SETTINGS")
                lines.append("# " + "=" * 77)
                for key, value in sorted(remaining.items()):
                    lines.append(f"{key}={value}")

            # Write to file
            with open(self.env_path, 'w') as f:
                f.write('\n'.join(lines))

            print(f"Successfully migrated .env file")
            return True

        except Exception as e:
            print(f"Failed to write migrated .env: {e}")
            if self.backup_path:
                print(f"Restoring from backup...")
                shutil.copy2(self.backup_path, self.env_path)
            return False

    def validate_migration(self) -> bool:
        """Validate the migrated configuration"""
        required_vars = [
            'GILJO_API_PORT', 'GILJO_PORT', 'DB_HOST', 'DB_NAME',
            'DB_USER', 'DB_PASSWORD', 'VITE_API_URL', 'VITE_WS_URL'
        ]

        missing = []
        for var in required_vars:
            if var not in self.new_vars or not self.new_vars[var]:
                missing.append(var)

        if missing:
            print(f"WARNING: Missing required variables: {', '.join(missing)}")
            return False

        print("Migration validation passed")
        return True

    def migrate(self) -> bool:
        """Run the complete migration process"""
        print("Starting configuration migration...")
        print("-" * 60)

        # Step 1: Backup
        if self.env_path.exists():
            if not self.backup_existing():
                return False

        # Step 2: Parse existing
        self.parse_env_file()
        print(f"Found {len(self.env_vars)} existing variables")

        # Step 3: Migrate
        self.migrate_variables()
        print(f"Migrated to {len(self.new_vars)} variables")

        # Step 4: Write new file
        if not self.write_migrated_env():
            return False

        # Step 5: Validate
        if not self.validate_migration():
            print("WARNING: Migration completed but validation failed")
            print("Please review the .env file manually")

        print("-" * 60)
        print("Migration completed successfully!")
        return True


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='Migrate GiljoAI MCP configuration to harmonized format')
    parser.add_argument('--env-file', type=Path, default=Path('.env'),
                       help='Path to .env file (default: .env)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be migrated without making changes')
    parser.add_argument('--force', action='store_true',
                       help='Force migration even if validation fails')

    args = parser.parse_args()

    migrator = ConfigMigrator(args.env_file)

    if args.dry_run:
        print("DRY RUN MODE - No changes will be made")
        migrator.parse_env_file()
        new_vars = migrator.migrate_variables()

        print("\nMigration Preview:")
        print("-" * 60)
        for key, value in sorted(new_vars.items()):
            old_value = migrator.env_vars.get(key)
            if old_value != value:
                print(f"{key}={value} {'(NEW)' if key not in migrator.env_vars else f'(was: {old_value})'}")
            else:
                print(f"{key}={value}")
    else:
        success = migrator.migrate()
        if not success and not args.force:
            sys.exit(1)


if __name__ == '__main__':
    main()
