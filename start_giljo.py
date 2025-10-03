#!/usr/bin/env python3
"""
GiljoAI MCP Launcher
Professional service launcher with health checks and recovery
"""

import subprocess
import sys
import os
import time
import json
import signal
import socket
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Try to import psutil, but don't fail if not available
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Service configuration - will be updated from config.yaml
SERVICES = {
    "backend": {
        "name": "GiljoAI Backend (HTTP + WebSocket + MCP)",
        "command": None,  # Will be set dynamically
        "port": 7272,  # Default, will be updated from config
        "health_endpoint": "/health",
        "health_check": "http",
        "startup_time": 10,
        "required": True
    },
    "dashboard": {
        "name": "Dashboard (Frontend)",
        "command": ["npm.cmd" if sys.platform == "win32" else "npm", "run", "dev"],  # Use dev for development
        "cwd": "frontend",
        "port": 7274,  # Default, will be updated from config
        "health_check": "tcp",
        "startup_time": 15,
        "required": False  # Optional - may not have npm installed
    }
    # Note: WebSocket service removed - it's unified in the backend (v2.0 architecture)
}


class ServiceLauncher:
    """Professional service launcher with monitoring"""

    def __init__(self, dev_mode=False):
        self.base_dir = Path(__file__).parent
        self.processes = {}
        self.config = self.load_config()
        self.log_dir = self.base_dir / "logs" / "launcher"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f"launcher_{datetime.now():%Y%m%d_%H%M%S}.log"
        self.dev_mode = dev_mode  # Development mode: disable auto-restart

        # Set the backend command based on the installation
        api_script = self.base_dir / "api" / "run_api.py"
        if api_script.exists():
            SERVICES["backend"]["command"] = [sys.executable, str(api_script)]
        else:
            # Fallback for different directory structures
            SERVICES["backend"]["command"] = [sys.executable, "api/run_api.py"]

        # Update ports from config.yaml if available
        self._update_ports_from_config()

    def _update_ports_from_config(self):
        """Update service ports from config.yaml"""
        if not self.config:
            return

        # Update backend port from config
        if 'services' in self.config:
            services = self.config['services']

            # Backend/API port
            if 'api' in services and 'port' in services['api']:
                SERVICES['backend']['port'] = services['api']['port']

            # Frontend port
            if 'frontend' in services and 'port' in services['frontend']:
                SERVICES['dashboard']['port'] = services['frontend']['port']

    def load_config(self) -> Dict:
        """Load configuration from config.yaml or .env"""
        config = {}

        # Try config.yaml first
        config_file = self.base_dir / "config.yaml"
        if config_file.exists():
            try:
                import yaml
                with open(config_file) as f:
                    config = yaml.safe_load(f)
            except ImportError:
                pass
            except Exception as e:
                print(f"Warning: Failed to load config.yaml: {e}")

        # Try .env as fallback
        env_file = self.base_dir / ".env"
        if env_file.exists():
            try:
                with open(env_file) as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            config[key.strip()] = value.strip()
            except Exception as e:
                print(f"Warning: Failed to load .env: {e}")

        return config

    def log(self, message: str, level: str = "INFO"):
        """Log message to console and file"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] [{level}] {message}"

        # Console output with color
        if level == "ERROR":
            print(f"\033[91m{log_entry}\033[0m")  # Red
        elif level == "WARNING":
            print(f"\033[93m{log_entry}\033[0m")  # Yellow
        elif level == "SUCCESS":
            print(f"\033[92m{log_entry}\033[0m")  # Green
        else:
            print(log_entry)

        # File output
        with open(self.log_file, 'a') as f:
            f.write(log_entry + "\n")

    def check_port_available(self, port: int) -> bool:
        """Check if a port is available"""
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex(('127.0.0.1', port))
        sock.close()
        return result != 0

    def check_service_health(self, service_name: str, config: Dict) -> bool:
        """Check if a service is healthy"""
        port = config.get("port")
        if not port:
            return True  # No port to check

        health_check = config.get("health_check", "tcp")

        if health_check == "tcp":
            # Simple TCP connection check
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            return result == 0

        elif health_check == "http":
            # HTTP health endpoint check
            try:
                import requests
                endpoint = config.get("health_endpoint", "/health")
                response = requests.get(f"http://localhost:{port}{endpoint}", timeout=2)
                return response.status_code == 200
            except:
                return False

        return True

    def start_service(self, name: str, config: Dict) -> Optional[subprocess.Popen]:
        """Start a single service"""
        self.log(f"Starting {config['name']}...")

        # Check port availability
        port = config.get("port")
        if port and not self.check_port_available(port):
            self.log(f"Port {port} is already in use!", "ERROR")
            return None

        # Prepare command
        command = config["command"]
        cwd = self.base_dir / config.get("cwd", ".")

        # Check if command exists
        if not cwd.exists():
            self.log(f"Working directory {cwd} not found", "WARNING")
            if config.get("required", True):
                return None
            else:
                self.log(f"Skipping optional service {name}", "INFO")
                return None

        try:
            # For backend, show live output for debugging
            if name == "backend":
                self.log(f"Starting {config['name']} with VERBOSE output...", "INFO")
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=None,  # Show in console
                    stderr=None,  # Show in console
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                )
            else:
                # Other services can be quiet
                process = subprocess.Popen(
                    command,
                    cwd=cwd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                )

            self.processes[name] = process
            self.log(f"{config['name']} started with PID {process.pid}")

            # Wait for startup
            startup_time = config.get("startup_time", 5)
            self.log(f"Waiting {startup_time}s for {name} to start...")

            for i in range(startup_time):
                time.sleep(1)
                if self.check_service_health(name, config):
                    self.log(f"{config['name']} is healthy!", "SUCCESS")
                    return process

                # Check if process died
                if process.poll() is not None:
                    stdout, stderr = process.communicate()
                    self.log(f"{config['name']} failed to start", "ERROR")
                    if stdout:
                        self.log(f"STDOUT: {stdout}", "ERROR")
                    if stderr:
                        self.log(f"STDERR: {stderr}", "ERROR")
                    return None

            # Final health check
            if self.check_service_health(name, config):
                self.log(f"{config['name']} is healthy!", "SUCCESS")
                return process
            else:
                self.log(f"{config['name']} failed health check", "WARNING")
                return process if not config.get("required", True) else None

        except Exception as e:
            self.log(f"Failed to start {config['name']}: {e}", "ERROR")
            return None

    def stop_service(self, name: str):
        """Stop a single service"""
        if name not in self.processes:
            return

        process = self.processes[name]
        if process.poll() is None:
            self.log(f"Stopping {SERVICES[name]['name']}...")

            if sys.platform == "win32":
                # Windows: send CTRL_BREAK_EVENT
                process.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                # Unix: send SIGTERM
                process.terminate()

            try:
                process.wait(timeout=5)
                self.log(f"{SERVICES[name]['name']} stopped")
            except subprocess.TimeoutExpired:
                self.log(f"Force killing {SERVICES[name]['name']}", "WARNING")
                process.kill()
                process.wait()

        del self.processes[name]

    def stop_all_services(self):
        """Stop all running services"""
        self.log("\nStopping all services...")

        # Stop in reverse order
        for name in reversed(list(self.processes.keys())):
            self.stop_service(name)

        self.log("All services stopped")

    def monitor_services(self):
        """Monitor running services and restart if needed"""
        while True:
            try:
                # Check each service
                for name, process in list(self.processes.items()):
                    if process.poll() is not None:
                        # Process died
                        self.log(f"{SERVICES[name]['name']} crashed!", "ERROR")

                        if self.dev_mode:
                            # In dev mode, don't auto-restart - just report and stop
                            self.log(f"DEV MODE: Not auto-restarting {SERVICES[name]['name']}", "WARNING")
                            self.log("Fix the issue and restart manually", "INFO")
                            return False  # Exit monitor loop
                        elif SERVICES[name].get("required", True):
                            self.log(f"Restarting {SERVICES[name]['name']}...")
                            new_process = self.start_service(name, SERVICES[name])
                            if not new_process:
                                self.log(f"Failed to restart {SERVICES[name]['name']}", "ERROR")
                                return False
                        else:
                            del self.processes[name]

                time.sleep(5)  # Check every 5 seconds

            except KeyboardInterrupt:
                return True

    def run(self):
        """Main launcher execution"""
        print("\n" + "="*60)
        print("   GiljoAI MCP Service Launcher")
        if self.dev_mode:
            print("   [DEVELOPMENT MODE - No Auto-Restart]")
        print("="*60)
        print()

        # Check for required files
        if not (self.base_dir / "config.yaml").exists() and not (self.base_dir / ".env").exists():
            self.log("No configuration found. Please run installer first.", "ERROR")
            return 1

        # Start services in order
        failed = []
        for name, config in SERVICES.items():
            process = self.start_service(name, config)
            if not process and config.get("required", True):
                failed.append(name)

        if failed:
            self.log(f"\nFailed to start required services: {', '.join(failed)}", "ERROR")
            self.stop_all_services()
            return 1

        # Display status
        print("\n" + "="*60)
        print("   Services Running")
        print("="*60)

        if "backend" in self.processes:
            # Get the actual port from SERVICES (which was updated from config)
            port = SERVICES["backend"]["port"]
            print(f"  Backend:   http://localhost:{port}")
            print(f"             - REST API: http://localhost:{port}/docs")
            print(f"             - WebSocket: ws://localhost:{port}/ws/{{client_id}}")
            print(f"             - Health: http://localhost:{port}/health")

        if "dashboard" in self.processes:
            port = SERVICES["dashboard"]["port"]
            print(f"  Dashboard: http://localhost:{port}")

        print()
        print("  Press Ctrl+C to stop all services")
        print("="*60)
        print()

        # Open browser if configured (check frontend config)
        if 'services' in self.config and 'frontend' in self.config['services']:
            frontend_config = self.config['services']['frontend']
            if frontend_config.get('auto_open', False) and "dashboard" in self.processes:
                dashboard_port = SERVICES["dashboard"]["port"]

                # Wait for Vite dev server to be fully ready
                self.log("Waiting for Vite dev server to be ready...")
                vite_ready = False
                for attempt in range(30):  # Try for 30 seconds
                    time.sleep(1)
                    try:
                        # Use socket connection instead of urlopen for security scan compliance
                        import socket
                        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        sock.settimeout(2)
                        result = sock.connect_ex(('127.0.0.1', dashboard_port))
                        sock.close()
                        if result == 0:
                            vite_ready = True
                            break
                    except Exception:
                        pass

                if vite_ready:
                    browser_url = f"http://localhost:{dashboard_port}"
                    self.log(f"Opening dashboard in browser: {browser_url}", "SUCCESS")
                    self.log("IMPORTANT: If you see module errors, clear browser cache (Ctrl+Shift+Delete)", "INFO")
                    import webbrowser
                    webbrowser.open(browser_url)
                else:
                    self.log("Vite dev server not ready yet. Open browser manually.", "WARNING")
                    self.log(f"Dashboard URL: http://localhost:{dashboard_port}", "INFO")

        # Monitor services
        try:
            self.monitor_services()
        except KeyboardInterrupt:
            pass

        # Cleanup
        print()
        self.stop_all_services()
        return 0


def start_services(settings: dict = None):
    """
    Start services after installation (called from installer)

    Args:
        settings: Optional settings dict from installer with config overrides
    """
    launcher = ServiceLauncher()

    # Override config with installation settings if provided
    if settings:
        # Update SERVICES dict with installation settings
        if 'api_port' in settings:
            SERVICES['backend']['port'] = settings['api_port']

        if 'ws_port' in settings:
            SERVICES['websocket']['port'] = settings['ws_port']

        if 'dashboard_port' in settings:
            SERVICES['dashboard']['port'] = settings['dashboard_port']

    # Run the launcher
    return launcher.run()


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="GiljoAI MCP Service Launcher")
    parser.add_argument(
        "--dev",
        action="store_true",
        help="Development mode: disable auto-restart on failures"
    )
    parser.add_argument(
        "--no-restart",
        action="store_true",
        help="Disable auto-restart on failures (alias for --dev)"
    )
    args = parser.parse_args()

    # Check for dev mode from args or environment
    dev_mode = args.dev or args.no_restart or os.getenv("GILJO_DEV_MODE", "").lower() in ("1", "true", "yes")

    launcher = ServiceLauncher(dev_mode=dev_mode)

    if dev_mode:
        print("\n" + "="*60)
        print("   DEVELOPMENT MODE: Auto-restart DISABLED")
        print("   Services will NOT restart on failure")
        print("="*60 + "\n")

    # Set up signal handlers
    def signal_handler(sig, frame):
        launcher.stop_all_services()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if sys.platform == "win32":
        signal.signal(signal.SIGBREAK, signal_handler)

    # Run launcher
    sys.exit(launcher.run())


if __name__ == "__main__":
    main()
