#!/usr/bin/env python3
"""
Error Recovery System for GiljoAI MCP
Intelligent error recovery during launch
"""

import os
import sys
import time
import socket
import subprocess
import platform
import psycopg2
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import click
from dotenv import load_dotenv


class ErrorRecovery:
    """Intelligent error recovery during launch"""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        self.config_path = Path("config.yaml")
        self.env_path = Path(".env")
        load_dotenv()

    def recover_port_conflict(self, port: int) -> bool:
        """Handle port already in use"""
        if self.verbose:
            click.echo(f"\n🔧 Attempting to resolve port {port} conflict...")

        # Check if it's our service
        if self.is_our_service(port):
            if self.verbose:
                click.echo(f"  ℹ️  GiljoAI service already on port {port}")
            return True

        # Find alternative port
        alt_port = self.find_free_port(port + 1)

        if alt_port:
            if self.verbose:
                if click.confirm(f"  Use port {alt_port} instead?"):
                    if self.update_config_port(port, alt_port):
                        click.echo(f"  ✅ Configuration updated to use port {alt_port}")
                        return True
            else:
                # Auto-update in non-interactive mode
                if self.update_config_port(port, alt_port):
                    return True

        # Try to identify and optionally kill the process
        if self.verbose:
            process_info = self.get_port_process(port)
            if process_info:
                click.echo(f"  ℹ️  Port {port} is used by: {process_info}")

                if platform.system() == "Windows":
                    click.echo(f"  To free the port, run: netstat -ano | findstr :{port}")
                    click.echo(f"  Then: taskkill /F /PID <process_id>")
                else:
                    click.echo(f"  To free the port, run: sudo lsof -i :{port}")
                    click.echo(f"  Then: sudo kill -9 <process_id>")

        return False

    def recover_database(self) -> bool:
        """Attempt to start PostgreSQL"""
        if self.verbose:
            click.echo("\n🔧 Attempting to start PostgreSQL...")

        # Platform-specific startup commands
        start_commands = {
            "Windows": [
                ['net', 'start', 'postgresql-x64-18'],
                ['net', 'start', 'postgresql-x64-17'],
                ['net', 'start', 'postgresql-x64-16'],
                ['pg_ctl', 'start', '-D', r'C:\Program Files\PostgreSQL\18\data']
            ],
            "Darwin": [
                ['brew', 'services', 'start', 'postgresql@18'],
                ['brew', 'services', 'start', 'postgresql'],
                ['pg_ctl', '-D', '/usr/local/var/postgresql@18', 'start']
            ],
            "Linux": [
                ['sudo', 'systemctl', 'start', 'postgresql-18'],
                ['sudo', 'systemctl', 'start', 'postgresql'],
                ['sudo', 'service', 'postgresql', 'start']
            ]
        }

        system = platform.system()
        commands = start_commands.get(system, [])

        for cmd in commands:
            try:
                if self.verbose:
                    click.echo(f"  Trying: {' '.join(cmd)}")

                result = subprocess.run(cmd, capture_output=True, timeout=10)

                if result.returncode == 0:
                    time.sleep(5)  # Wait for PostgreSQL to fully start

                    # Test connection
                    if self.test_database_connection():
                        if self.verbose:
                            click.echo("  ✅ PostgreSQL started successfully")
                        return True
            except Exception as e:
                if self.verbose:
                    click.echo(f"  ⚠️  Command failed: {e}")
                continue

        # If startup failed, provide guidance
        if self.verbose:
            click.echo("\n❌ Could not start PostgreSQL automatically")
            click.echo("\nPlease start PostgreSQL manually:")

            if system == "Windows":
                click.echo("  1. Open Services (services.msc)")
                click.echo("  2. Find 'postgresql-x64-18' service")
                click.echo("  3. Right-click and select 'Start'")
            elif system == "Darwin":
                click.echo("  Run: brew services start postgresql@18")
            else:
                click.echo("  Run: sudo systemctl start postgresql-18")

        return False

    def test_database_connection(self) -> bool:
        """Test if database connection works"""
        try:
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='giljo_mcp',
                user='giljo_user',
                password=os.getenv('POSTGRES_PASSWORD')
            )
            conn.close()
            return True
        except:
            return False

    def recover_missing_database(self) -> bool:
        """Create missing database and user"""
        if self.verbose:
            click.echo("\n🔧 Attempting to create database...")

        password = os.getenv('POSTGRES_PASSWORD')
        if not password:
            if self.verbose:
                click.echo("  ❌ POSTGRES_PASSWORD not set in .env")
            return False

        try:
            # Connect as postgres superuser
            conn = psycopg2.connect(
                host='localhost',
                port=5432,
                database='postgres',
                user='postgres',
                password=password
            )
            conn.autocommit = True
            cur = conn.cursor()

            # Create user if not exists
            cur.execute("SELECT 1 FROM pg_user WHERE usename = 'giljo_user'")
            if not cur.fetchone():
                cur.execute(f"CREATE USER giljo_user WITH PASSWORD '{password}'")
                if self.verbose:
                    click.echo("  ✅ Created user 'giljo_user'")

            # Create database if not exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'")
            if not cur.fetchone():
                cur.execute("CREATE DATABASE giljo_mcp OWNER giljo_user")
                if self.verbose:
                    click.echo("  ✅ Created database 'giljo_mcp'")

            # Grant privileges
            cur.execute("GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_user")

            cur.close()
            conn.close()

            return True

        except psycopg2.OperationalError as e:
            if "password authentication failed" in str(e):
                if self.verbose:
                    click.echo("  ❌ PostgreSQL password incorrect")
                    click.echo("  Please check POSTGRES_PASSWORD in .env")
            else:
                if self.verbose:
                    click.echo(f"  ❌ Database creation failed: {e}")
            return False
        except Exception as e:
            if self.verbose:
                click.echo(f"  ❌ Unexpected error: {e}")
            return False

    def recover_missing_config(self) -> bool:
        """Recover from missing configuration files"""
        if self.verbose:
            click.echo("\n🔧 Attempting to recover configuration...")

        recovered = True

        # Check for .env file
        if not self.env_path.exists():
            if self.verbose:
                click.echo("  Creating .env file...")

            # Look for backup or example
            env_example = Path(".env.example")
            if env_example.exists():
                import shutil
                shutil.copy(env_example, self.env_path)
                click.echo("  Created .env from .env.example")
            else:
                # Create minimal .env
                with open(self.env_path, 'w') as f:
                    f.write("# GiljoAI MCP Environment Configuration\n")
                    f.write("POSTGRES_PASSWORD=giljo123\n")
                    f.write("API_KEY=your_api_key_here\n")
                click.echo("  Created minimal .env file")
                click.echo("  WARNING: Please update POSTGRES_PASSWORD in .env")
                recovered = False

        # Check for config.yaml
        if not self.config_path.exists():
            if self.verbose:
                click.echo("  Creating config.yaml...")

            # Create minimal config
            config = {
                'installation': {
                    'mode': 'localhost',
                    'timestamp': time.time()
                },
                'services': {
                    'bind': '127.0.0.1',
                    'api_port': 8000,
                    'websocket_port': 7273,
                    'dashboard_port': 7274
                },
                'features': {
                    'ssl_enabled': False,
                    'auto_start_browser': True
                }
            }

            with open(self.config_path, 'w') as f:
                yaml.dump(config, f, default_flow_style=False)

            click.echo("  Created minimal config.yaml")

        return recovered

    def find_free_port(self, start_port: int) -> Optional[int]:
        """Find next available port"""
        for port in range(start_port, start_port + 100):
            if 1024 <= port <= 65535:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                try:
                    sock.bind(('127.0.0.1', port))
                    sock.close()
                    return port
                except OSError:
                    continue
        return None

    def update_config_port(self, old_port: int, new_port: int) -> bool:
        """Update port in configuration"""
        try:
            # Update config.yaml
            with open(self.config_path) as f:
                config = yaml.safe_load(f)

            # Find and update port
            updated = False
            for service_key, service_port in config.get('services', {}).items():
                if service_port == old_port:
                    config['services'][service_key] = new_port
                    updated = True
                    break

            if updated:
                with open(self.config_path, 'w') as f:
                    yaml.dump(config, f, default_flow_style=False)

            # Also update .env if needed
            if self.env_path.exists():
                with open(self.env_path) as f:
                    env_lines = f.readlines()

                with open(self.env_path, 'w') as f:
                    for line in env_lines:
                        if f'={old_port}' in line:
                            line = line.replace(f'={old_port}', f'={new_port}')
                        f.write(line)

            return updated

        except Exception as e:
            if self.verbose:
                click.echo(f"  ❌ Failed to update configuration: {e}")
            return False

    def is_our_service(self, port: int) -> bool:
        """Check if a port is being used by our service"""
        try:
            # Try to connect and send a health check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            sock.connect(('127.0.0.1', port))

            # Try HTTP request (works for API and dashboard)
            request = b"GET /health HTTP/1.1\r\nHost: localhost\r\n\r\n"
            sock.send(request)
            response = sock.recv(1024).decode()
            sock.close()

            # Check if it's our service
            return 'GiljoAI' in response or 'giljo' in response.lower()

        except:
            return False

    def get_port_process(self, port: int) -> Optional[str]:
        """Get information about process using a port"""
        try:
            if platform.system() == "Windows":
                result = subprocess.run(
                    ['netstat', '-ano'],
                    capture_output=True,
                    text=True
                )
                for line in result.stdout.splitlines():
                    if f':{port}' in line and 'LISTENING' in line:
                        parts = line.split()
                        pid = parts[-1]
                        # Try to get process name
                        try:
                            task_result = subprocess.run(
                                ['tasklist', '/FI', f'PID eq {pid}'],
                                capture_output=True,
                                text=True
                            )
                            for task_line in task_result.stdout.splitlines():
                                if pid in task_line:
                                    return task_line.split()[0]
                        except:
                            return f"PID {pid}"
            else:
                # Unix-like systems
                result = subprocess.run(
                    ['lsof', '-i', f':{port}'],
                    capture_output=True,
                    text=True
                )
                lines = result.stdout.splitlines()
                if len(lines) > 1:
                    parts = lines[1].split()
                    return f"{parts[0]} (PID: {parts[1]})"
        except:
            pass

        return None

    def recover_all(self, errors: List[str]) -> bool:
        """Attempt to recover from all errors"""
        if self.verbose:
            click.echo("\n🔧 Attempting automatic recovery...")

        all_recovered = True

        for error in errors:
            recovered = False

            # Port conflicts
            if "Port" in error and "in use" in error:
                # Extract port number
                try:
                    port = int(error.split("port")[1].split(")")[0].strip())
                    recovered = self.recover_port_conflict(port)
                except:
                    pass

            # Database issues
            elif "PostgreSQL is not running" in error:
                recovered = self.recover_database()

            elif "database \"giljo_mcp\" does not exist" in error:
                recovered = self.recover_missing_database()

            elif "Database not accessible" in error:
                recovered = self.recover_database()

            # Missing configuration
            elif "Missing .env" in error:
                recovered = self.recover_missing_config()

            elif "Missing config.yaml" in error:
                recovered = self.recover_missing_config()

            if not recovered:
                all_recovered = False
                if self.verbose:
                    click.echo(f"  ❌ Could not recover: {error}")

        return all_recovered


def create_recovery_handler(verbose: bool = True) -> ErrorRecovery:
    """Factory function to create error recovery handler"""
    return ErrorRecovery(verbose)


if __name__ == "__main__":
    # Test recovery system
    recovery = ErrorRecovery()

    # Test various recovery scenarios
    test_errors = [
        "Port 8000 (API) in use",
        "PostgreSQL is not running",
        "Missing .env"
    ]

    click.echo("Testing error recovery system...")
    for error in test_errors:
        click.echo(f"\nTest error: {error}")
        recovery.recover_all([error])
