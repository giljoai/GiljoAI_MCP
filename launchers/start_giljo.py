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

        # Check ports
        ports = {
            'API': self.config['services'].get('api_port', 8000),
            'WebSocket': self.config['services'].get('websocket_port', 8001),
            'Dashboard': self.config['services'].get('dashboard_port', 3000)
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
        mode = self.config['installation'].get('mode', 'localhost')
        bind_address = self.config['services'].get('bind', '127.0.0.1')
        ssl_enabled = self.config['features'].get('ssl_enabled', False)

        print("="*60)
        print(f"   Starting GiljoAI MCP Services ({mode.upper()} mode)")
        print("="*60)
        print()

        # Display server mode warning
        if mode == 'server' and bind_address not in ['127.0.0.1', 'localhost']:
            print("SERVER MODE - Network accessible")
            print(f"Binding to: {bind_address}")
            if not ssl_enabled:
                print("WARNING: SSL is DISABLED - traffic is not encrypted!")
            print()

        # Build SSL arguments
        ssl_args = []
        if ssl_enabled and self.config.get('ssl'):
            ssl_args = [
                "--ssl-certfile", self.config['ssl'].get('cert_path', 'certs/server.crt'),
                "--ssl-keyfile", self.config['ssl'].get('key_path', 'certs/server.key')
            ]

        # Start API server
        api_port = self.config['services'].get('api_port', 8000)
        api_cmd = [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", bind_address,
            "--port", str(api_port)
        ]
        api_cmd.extend(ssl_args)

        self.start_service("API Server", api_cmd)
        time.sleep(2)  # Wait for startup

        # Start WebSocket server
        ws_port = self.config['services'].get('websocket_port', 8001)
        self.start_service("WebSocket Server", [
            sys.executable, "-m", "giljo_mcp.websocket",
            "--port", str(ws_port)
        ])
        time.sleep(1)

        # Start Dashboard
        dashboard_port = self.config['services'].get('dashboard_port', 3000)
        self.start_service("Dashboard", [
            sys.executable, "-m", "http.server",
            str(dashboard_port),
            "--directory", "frontend"
        ])

        print()
        print("All services started successfully!")
        print()

        # Determine protocol based on SSL and mode
        protocol = "https" if ssl_enabled else "http"
        ws_protocol = "wss" if ssl_enabled else "ws"
        display_host = bind_address if mode == 'server' else 'localhost'

        print("Access points:")
        print(f"  Dashboard: {protocol}://{display_host}:{dashboard_port}")
        print(f"  API Docs: {protocol}://{display_host}:{api_port}/docs")
        print(f"  WebSocket: {ws_protocol}://{display_host}:{ws_port}")

        if mode == 'server':
            print()
            print("IMPORTANT: Configure your firewall to allow these ports!")
            if self.config.get('firewall_instructions'):
                print(f"  See: {self.config.get('firewall_instructions')}")

        print()

        # Open browser if configured
        if self.config.get('features', {}).get('auto_start_browser', True):
            time.sleep(2)
            url = f"{protocol}://{display_host}:{dashboard_port}"
            webbrowser.open(url)

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
