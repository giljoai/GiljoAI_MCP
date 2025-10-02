#!/usr/bin/env python3
"""
Launch Validator for GiljoAI MCP
Validates installation completeness before launch
"""

import os
import sys
import socket
import psycopg2
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import click
from dotenv import load_dotenv


class LaunchValidator:
    """Validates installation completeness before launch"""

    def __init__(self, verbose: bool = True):
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.verbose = verbose
        self.config = None
        self.env_loaded = False

    def validate_all(self) -> bool:
        """Complete validation suite"""
        checks = [
            self.check_config_files,
            self.check_database_connection,
            self.check_schema_complete,
            self.check_dependencies,
            self.check_ports_available,
            self.check_permissions
        ]

        if self.verbose:
            click.echo("\n🔍 Validating installation...")

        all_passed = True
        for check in checks:
            name = check.__name__.replace('check_', '').replace('_', ' ').title()
            if self.verbose:
                click.echo(f"  Checking {name}...", nl=False)

            try:
                if check():
                    if self.verbose:
                        click.echo(" ✅")
                else:
                    if self.verbose:
                        click.echo(" ❌")
                    all_passed = False
            except Exception as e:
                if self.verbose:
                    click.echo(f" ❌ ({str(e)})")
                self.errors.append(f"{name}: {str(e)}")
                all_passed = False

        return all_passed

    def check_config_files(self) -> bool:
        """Verify config files exist and are valid"""
        required_files = ['.env', 'config.yaml']

        for file in required_files:
            file_path = Path(file)
            if not file_path.exists():
                self.errors.append(f"Missing {file}")
                return False

            # Verify .env has required vars
            if file == '.env':
                if not self.env_loaded:
                    load_dotenv()
                    self.env_loaded = True

                required_vars = ['POSTGRES_PASSWORD']
                for var in required_vars:
                    if not os.getenv(var):
                        self.errors.append(f"Missing {var} in .env")
                        return False

            # Load and validate config.yaml
            if file == 'config.yaml':
                try:
                    with open(file_path) as f:
                        self.config = yaml.safe_load(f)

                    # Check required sections
                    required_sections = ['installation', 'services', 'features']
                    for section in required_sections:
                        if section not in self.config:
                            self.errors.append(f"Missing '{section}' section in config.yaml")
                            return False
                except Exception as e:
                    self.errors.append(f"Invalid config.yaml: {e}")
                    return False

        return True

    def check_database_connection(self) -> bool:
        """Verify database is accessible"""
        if not self.env_loaded:
            load_dotenv()
            self.env_loaded = True

        try:
            # First check if PostgreSQL is running
            result = os.system('pg_isready -h localhost -p 5432 > NUL 2>&1' if os.name == 'nt' else 'pg_isready -h localhost -p 5432 >/dev/null 2>&1')
            if result != 0:
                self.errors.append("PostgreSQL is not running")
                return False

            # Try to connect to the database
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database='giljo_mcp',
                user='giljo_user',
                password=os.getenv('POSTGRES_PASSWORD')
            )
            conn.close()
            return True

        except psycopg2.OperationalError as e:
            if "database \"giljo_mcp\" does not exist" in str(e):
                self.errors.append("Database 'giljo_mcp' not found - run installer first")
            elif "password authentication failed" in str(e):
                self.errors.append("Database authentication failed - check POSTGRES_PASSWORD")
            else:
                self.errors.append(f"Database not accessible: {e}")
            return False
        except Exception as e:
            self.errors.append(f"Database connection failed: {e}")
            return False

    def check_schema_complete(self) -> bool:
        """Verify all required tables exist"""
        required_tables = [
            'agents', 'messages', 'templates',
            'configurations', 'products', 'tenants'
        ]

        if not self.env_loaded:
            load_dotenv()
            self.env_loaded = True

        try:
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=int(os.getenv('POSTGRES_PORT', 5432)),
                database='giljo_mcp',
                user='giljo_user',
                password=os.getenv('POSTGRES_PASSWORD')
            )
            cur = conn.cursor()

            # Check tables exist
            cur.execute("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
            """)

            existing_tables = [row[0] for row in cur.fetchall()]

            missing_tables = []
            for table in required_tables:
                if table not in existing_tables:
                    missing_tables.append(table)

            cur.close()
            conn.close()

            if missing_tables:
                self.errors.append(f"Missing database tables: {', '.join(missing_tables)}")
                return False

            return True

        except Exception as e:
            # If we can't connect, skip this check (database connection will catch it)
            if "Database not accessible" not in str(self.errors):
                self.errors.append(f"Schema check failed: {e}")
            return False

    def check_dependencies(self) -> bool:
        """Check if required Python packages are installed"""
        required_packages = [
            'click', 'psycopg2', 'pyyaml', 'python-dotenv',
            'cryptography', 'uvicorn', 'fastapi'
        ]

        missing_packages = []
        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
            except ImportError:
                missing_packages.append(package)

        if missing_packages:
            self.errors.append(f"Missing Python packages: {', '.join(missing_packages)}")
            self.errors.append("Run: pip install -r requirements.txt")
            return False

        return True

    def check_ports_available(self) -> bool:
        """Check if required ports are free"""
        if not self.config:
            try:
                with open('config.yaml') as f:
                    self.config = yaml.safe_load(f)
            except:
                self.errors.append("Cannot read config.yaml for port checking")
                return False

        ports_to_check = []

        # Get ports from config
        if 'services' in self.config:
            ports_to_check.append(('API', self.config['services'].get('api_port', 8000)))
            ports_to_check.append(('WebSocket', self.config['services'].get('websocket_port', 8001)))
            ports_to_check.append(('Dashboard', self.config['services'].get('dashboard_port', 3000)))

        blocked_ports = []
        for name, port in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()

            if result == 0:  # Port is in use
                blocked_ports.append(f"{name} (port {port})")

        if blocked_ports:
            self.errors.append(f"Ports already in use: {', '.join(blocked_ports)}")
            return False

        return True

    def check_permissions(self) -> bool:
        """Check file and directory permissions"""
        # Check if we can write to necessary directories
        write_dirs = ['logs', 'uploads', 'temp']

        for dir_name in write_dirs:
            dir_path = Path(dir_name)
            if not dir_path.exists():
                try:
                    dir_path.mkdir(parents=True, exist_ok=True)
                except Exception as e:
                    self.errors.append(f"Cannot create {dir_name} directory: {e}")
                    return False

            # Test write access
            test_file = dir_path / '.write_test'
            try:
                test_file.touch()
                test_file.unlink()
            except Exception as e:
                self.errors.append(f"No write permission for {dir_name}: {e}")
                return False

        return True

    def get_errors(self) -> List[str]:
        """Get list of validation errors"""
        return self.errors

    def get_warnings(self) -> List[str]:
        """Get list of validation warnings"""
        return self.warnings

    def print_summary(self):
        """Print validation summary"""
        if self.errors:
            click.echo("\n❌ Validation failed with errors:")
            for error in self.errors:
                click.echo(f"  • {error}")

        if self.warnings:
            click.echo("\n⚠️  Warnings:")
            for warning in self.warnings:
                click.echo(f"  • {warning}")

        if not self.errors and not self.warnings:
            click.echo("\n✅ All validation checks passed!")


def validate_installation(verbose: bool = True) -> bool:
    """Quick validation function for external use"""
    validator = LaunchValidator(verbose=verbose)
    result = validator.validate_all()

    if verbose and not result:
        validator.print_summary()

    return result


if __name__ == "__main__":
    # Run validation when called directly
    validator = LaunchValidator()
    if validator.validate_all():
        click.echo("\n✅ Installation is ready to launch!")
        sys.exit(0)
    else:
        validator.print_summary()
        sys.exit(1)
