#!/usr/bin/env python3
"""
Service Manager for GiljoAI MCP
Manages service startup with dependencies and health checks
"""

import os
import sys
import time
import subprocess
import platform
import socket
import signal
from pathlib import Path
from typing import Dict, List, Optional, Any
import yaml
import click
from dotenv import load_dotenv


class ServiceManager:
    """Manages service startup with dependencies"""

    # Define service startup order
    SERVICE_ORDER = [
        'database',
        'api',
        'websocket',
        'dashboard'
    ]

    def __init__(self, config_path: str = "config.yaml"):
        self.processes: Dict[str, subprocess.Popen] = {}
        self.config = self.load_config(config_path)
        self.verbose = True
        self.retry_attempts = 3
        self.startup_timeout = 30  # seconds

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from YAML file"""
        config_file = Path(config_path)
        if not config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {config_path}")

        with open(config_file) as f:
            return yaml.safe_load(f)

    def start_all(self) -> bool:
        """Start all services in dependency order"""
        click.echo("\n🚀 Starting services...")

        for service in self.SERVICE_ORDER:
            click.echo(f"  Starting {service}...", nl=False)

            success = False
            for attempt in range(self.retry_attempts):
                if self.start_service(service):
                    click.echo(" ✅")
                    success = True
                    time.sleep(2)  # Wait for service to stabilize
                    break
                else:
                    if attempt < self.retry_attempts - 1:
                        click.echo(f" ⚠️  Retry {attempt + 1}/{self.retry_attempts - 1}", nl=False)
                        time.sleep(3)
                    else:
                        click.echo(" ❌")

            if not success:
                click.echo(f"\n❌ Failed to start {service} after {self.retry_attempts} attempts")
                self.stop_all()
                return False

        return True

    def start_service(self, service: str) -> bool:
        """Start individual service"""
        try:
            if service == 'database':
                return self.ensure_database_running()

            elif service == 'api':
                return self.start_api_service()

            elif service == 'websocket':
                return self.start_websocket_service()

            elif service == 'dashboard':
                return self.start_dashboard_service()

            else:
                click.echo(f"\n⚠️  Unknown service: {service}")
                return False

        except Exception as e:
            if self.verbose:
                click.echo(f"\n❌ Error starting {service}: {e}")
            return False

    def ensure_database_running(self) -> bool:
        """Ensure PostgreSQL is running"""
        # Check with pg_isready
        cmd = ['pg_isready', '-h', 'localhost', '-p', '5432']

        try:
            result = subprocess.run(cmd, capture_output=True, timeout=5)
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

        # Try to start PostgreSQL based on platform
        click.echo("\n  PostgreSQL not running, attempting to start...")

        start_commands = {
            "Windows": ['net', 'start', 'postgresql-x64-18'],
            "Darwin": ['brew', 'services', 'start', 'postgresql@18'],
            "Linux": ['sudo', 'systemctl', 'start', 'postgresql-18']
        }

        system = platform.system()
        if system in start_commands:
            try:
                subprocess.run(start_commands[system], capture_output=True, timeout=10)
                time.sleep(5)

                # Check again
                result = subprocess.run(cmd, capture_output=True, timeout=5)
                return result.returncode == 0
            except:
                pass

        return False

    def start_api_service(self) -> bool:
        """Start the API service"""
        load_dotenv()

        # Build command
        bind_address = self.config['services'].get('bind', '127.0.0.1')
        api_port = self.config['services'].get('api_port', 8000)

        cmd = [
            sys.executable, '-m', 'uvicorn',
            'api.app:app',
            '--host', bind_address,
            '--port', str(api_port)
        ]

        # Add SSL if enabled
        if self.config.get('features', {}).get('ssl_enabled', False):
            ssl_config = self.config.get('ssl', {})
            if ssl_config.get('cert_path') and ssl_config.get('key_path'):
                cmd.extend([
                    '--ssl-certfile', ssl_config['cert_path'],
                    '--ssl-keyfile', ssl_config['key_path']
                ])

        # Start process
        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path.cwd())

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            self.processes['api'] = proc

            # Wait and check if process started successfully
            time.sleep(2)
            if proc.poll() is not None:
                # Process died immediately
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                if self.verbose:
                    click.echo(f"\n❌ API failed to start: {stderr[:200]}")
                return False

            # Test if service is responding
            return self.wait_for_service('localhost', api_port, timeout=10)

        except Exception as e:
            if self.verbose:
                click.echo(f"\n❌ Failed to start API: {e}")
            return False

    def start_websocket_service(self) -> bool:
        """Start the WebSocket service"""
        ws_port = self.config['services'].get('websocket_port', 7273)
        bind_address = self.config['services'].get('bind', '127.0.0.1')

        cmd = [
            sys.executable, '-m', 'giljo_mcp.websocket',
            '--host', bind_address,
            '--port', str(ws_port)
        ]

        try:
            env = os.environ.copy()
            env['PYTHONPATH'] = str(Path.cwd())

            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )
            self.processes['websocket'] = proc

            # Wait and check
            time.sleep(1)
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                if self.verbose:
                    click.echo(f"\n❌ WebSocket failed to start: {stderr[:200]}")
                return False

            return True

        except Exception as e:
            if self.verbose:
                click.echo(f"\n❌ Failed to start WebSocket: {e}")
            return False

    def start_dashboard_service(self) -> bool:
        """Start the Dashboard service"""
        dashboard_port = self.config['services'].get('dashboard_port', 7274)
        bind_address = self.config['services'].get('bind', '127.0.0.1')

        # Check if frontend directory exists
        frontend_path = Path('frontend')
        if not frontend_path.exists():
            if self.verbose:
                click.echo("\n⚠️  Frontend directory not found, skipping dashboard")
            return False

        # Check if built frontend exists
        dist_path = frontend_path / 'dist'
        if dist_path.exists():
            # Serve pre-built frontend with Python's http.server
            if self.verbose:
                click.echo(f"\n📦 Serving built frontend from {dist_path}")

            cmd = [
                sys.executable, '-m', 'http.server',
                str(dashboard_port),
                '--bind', bind_address,
                '--directory', str(dist_path)
            ]
            cwd = None
        else:
            # Try to use npm run dev (development server)
            if self.verbose:
                click.echo("\n⚠️  Built frontend not found. Starting development server...")

            # Check if npm is available
            npm_cmd = 'npm.cmd' if os.name == 'nt' else 'npm'
            try:
                subprocess.run([npm_cmd, '--version'], capture_output=True, check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                if self.verbose:
                    click.echo("\n❌ npm not found. Please install Node.js to run frontend")
                return False

            # Check if node_modules exists
            if not (frontend_path / 'node_modules').exists():
                if self.verbose:
                    click.echo("\n📦 Installing frontend dependencies...")
                install_result = subprocess.run([npm_cmd, 'install'], cwd=str(frontend_path), capture_output=True)
                if install_result.returncode != 0:
                    if self.verbose:
                        click.echo("\n❌ Failed to install frontend dependencies")
                    return False

            cmd = [npm_cmd, 'run', 'dev', '--', '--port', str(dashboard_port), '--host', bind_address]
            cwd = str(frontend_path)

        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd
            )
            self.processes['dashboard'] = proc

            # Wait and check
            time.sleep(2)
            if proc.poll() is not None:
                stderr = proc.stderr.read().decode() if proc.stderr else ""
                if self.verbose:
                    click.echo(f"\n❌ Dashboard failed to start: {stderr[:200]}")
                return False

            return self.wait_for_service('localhost', dashboard_port, timeout=5)

        except Exception as e:
            if self.verbose:
                click.echo(f"\n❌ Failed to start Dashboard: {e}")
            return False

    def wait_for_service(self, host: str, port: int, timeout: int = 10) -> bool:
        """Wait for a service to become available"""
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                sock.close()

                if result == 0:
                    return True

            except:
                pass

            time.sleep(0.5)

        return False

    def check_service_health(self, service: str) -> bool:
        """Check if a service is healthy"""
        if service == 'database':
            try:
                result = subprocess.run(
                    ['pg_isready', '-h', 'localhost', '-p', '5432'],
                    capture_output=True,
                    timeout=2
                )
                return result.returncode == 0
            except:
                return False

        elif service in self.processes:
            proc = self.processes[service]
            # Check if process is still running
            return proc.poll() is None

        return False

    def restart_service(self, service: str) -> bool:
        """Restart a specific service"""
        click.echo(f"\n🔄 Restarting {service}...")

        # Stop the service if running
        if service in self.processes:
            self.stop_service(service)
            time.sleep(2)

        # Start the service
        return self.start_service(service)

    def stop_service(self, service: str):
        """Stop a specific service"""
        if service in self.processes:
            proc = self.processes[service]
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            del self.processes[service]

    def stop_all(self):
        """Stop all running services"""
        click.echo("\n🛑 Stopping all services...")

        # Stop in reverse order
        for service in reversed(self.SERVICE_ORDER):
            if service in self.processes:
                click.echo(f"  Stopping {service}...", nl=False)
                self.stop_service(service)
                click.echo(" ✅")

    def get_service_status(self) -> Dict[str, bool]:
        """Get status of all services"""
        status = {}
        for service in self.SERVICE_ORDER:
            status[service] = self.check_service_health(service)
        return status

    def monitor_services(self, callback=None):
        """Monitor services and restart if they fail"""
        click.echo("\n👁️  Monitoring services...")

        while True:
            try:
                for service in self.SERVICE_ORDER:
                    if service != 'database':  # Don't restart database automatically
                        if service in self.processes:
                            if not self.check_service_health(service):
                                click.echo(f"\n⚠️  Service {service} stopped unexpectedly")

                                if callback:
                                    if not callback(service):
                                        continue

                                # Attempt restart
                                if self.restart_service(service):
                                    click.echo(f"✅ {service} restarted successfully")
                                else:
                                    click.echo(f"❌ Failed to restart {service}")

                time.sleep(5)  # Check every 5 seconds

            except KeyboardInterrupt:
                break
            except Exception as e:
                if self.verbose:
                    click.echo(f"\n❌ Monitoring error: {e}")
                time.sleep(5)


def create_service_manager(config_path: str = "config.yaml") -> ServiceManager:
    """Factory function to create a service manager"""
    return ServiceManager(config_path)


if __name__ == "__main__":
    # Test service manager
    manager = ServiceManager()

    if manager.start_all():
        click.echo("\n✅ All services started successfully!")
        click.echo("\nPress Ctrl+C to stop all services")

        try:
            manager.monitor_services()
        except KeyboardInterrupt:
            pass
        finally:
            manager.stop_all()
    else:
        click.echo("\n❌ Failed to start services")
        sys.exit(1)
