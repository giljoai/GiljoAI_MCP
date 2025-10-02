#!/usr/bin/env python3
"""
GiljoAI MCP Universal Launcher
Starts all services with proper dependency ordering
"""

import sys
import os
import time
import subprocess
import socket
import webbrowser
from pathlib import Path
import yaml
import signal


class GiljoLauncher:
    def __init__(self):
        self.processes = []
        self.config = None
        self.load_config()

    def load_config(self):
        """Load configuration from config.yaml"""
        config_path = Path("config.yaml")
        if not config_path.exists():
            print("Error: config.yaml not found. Please run installer first.")
            sys.exit(1)

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

    def check_port(self, port: int) -> bool:
        """Check if a port is available"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0

    def validate_installation(self) -> bool:
        """Verify installation is complete"""
        required_files = ['.env', 'config.yaml']
        for file in required_files:
            if not Path(file).exists():
                print(f"Error: Missing {file} - installation incomplete")
                return False

        # Check ports - fixed to match actual config structure
        services = self.config.get('services', {})
        ports = {
            'API': services.get('api', {}).get('port', 7272),
            'WebSocket': services.get('websocket', {}).get('port', 8001),
            'Dashboard': services.get('frontend', {}).get('port', 6000)
        }

        for service, port in ports.items():
            if not self.check_port(port):
                print(f"Error: Port {port} ({service}) is already in use")
                return False

        return True

    def start_service(self, name: str, command: list) -> subprocess.Popen:
        """Start a single service"""
        print(f"Starting {name}...")
        env = os.environ.copy()
        env['PYTHONPATH'] = str(Path.cwd())

        proc = subprocess.Popen(
            command,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        self.processes.append(proc)
        return proc

    def start_all_services(self):
        """Start all services in order"""
        print("="*60)
        print("   Starting GiljoAI MCP Services")
        print("="*60)
        print()

        # Start API server - fixed to match actual config structure
        services = self.config.get('services', {})
        api_port = services.get('api', {}).get('port', 7272)
        api_host = services.get('api', {}).get('host', '127.0.0.1')

        self.start_service("API Server", [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", api_host,
            "--port", str(api_port)
        ])
        time.sleep(2)  # Wait for startup

        # Note: In v2.0 architecture, WebSocket is unified with API on same port
        # No separate WebSocket server needed

        # Start Dashboard
        dashboard_port = services.get('frontend', {}).get('port', 6000)
        self.start_service("Dashboard", [
            sys.executable, "-m", "http.server",
            str(dashboard_port),
            "--directory", "frontend"
        ])

        print()
        print("All services started successfully!")
        print()
        print("Access points:")
        print(f"  Dashboard: http://localhost:{dashboard_port}")
        print(f"  API Docs: http://localhost:{api_port}/docs")
        print(f"  WebSocket: ws://localhost:{api_port}")  # Unified with API in v2.0
        print()

        # Open browser if configured
        if self.config.get('features', {}).get('auto_start_browser', True):
            time.sleep(2)
            webbrowser.open(f"http://localhost:{dashboard_port}")

    def shutdown(self, signum=None, frame=None):
        """Gracefully shut down all services"""
        print("\n" + "="*60)
        print("   Shutting down services...")
        print("="*60)

        for proc in self.processes:
            if proc.poll() is None:
                proc.terminate()

        # Wait for graceful shutdown
        time.sleep(2)

        # Force kill if needed
        for proc in self.processes:
            if proc.poll() is None:
                proc.kill()

        print("All services stopped.")
        sys.exit(0)

    def run(self):
        """Main launcher entry point"""
        if not self.validate_installation():
            sys.exit(1)

        # Setup signal handlers
        signal.signal(signal.SIGINT, self.shutdown)
        signal.signal(signal.SIGTERM, self.shutdown)

        try:
            self.start_all_services()

            print("Press Ctrl+C to stop all services")
            print()

            # Keep running
            while True:
                time.sleep(1)
                # Check if any process died
                for proc in self.processes:
                    if proc.poll() is not None:
                        print(f"Warning: A service has stopped unexpectedly")
                        self.shutdown()

        except KeyboardInterrupt:
            self.shutdown()
        except Exception as e:
            print(f"Error: {e}")
            self.shutdown()


if __name__ == "__main__":
    launcher = GiljoLauncher()
    launcher.run()
