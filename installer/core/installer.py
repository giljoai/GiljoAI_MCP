"""
Main installer orchestration for localhost and server modes
"""

import os
import sys
import platform
import subprocess
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod

from .database import DatabaseInstaller
from .config import ConfigManager
from .validator import PostInstallValidator


class BaseInstaller(ABC):
    """Base installer with common functionality"""

    def __init__(self, settings: Dict[str, Any]):
        self.settings = settings
        self.mode = settings.get('mode', 'localhost')
        self.batch = settings.get('batch', False)

        # Setup logging
        self.setup_logging()

        # Component installers
        self.db_installer = DatabaseInstaller(settings)
        self.config_manager = ConfigManager(settings)
        self.post_validator = PostInstallValidator(settings)

    def setup_logging(self):
        """Configure installation logging"""
        log_dir = Path("install_logs")
        log_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"install_{self.mode}_{timestamp}.log"

        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout) if not self.batch else logging.NullHandler()
            ]
        )

        self.logger = logging.getLogger(self.__class__.__name__)
        self.log_file = log_file
        self.logger.info(f"Starting {self.mode} installation")

    def install(self) -> Dict[str, Any]:
        """Main installation workflow"""
        result = {
            'success': False,
            'mode': self.mode,
            'log_file': str(self.log_file)
        }

        try:
            # Step 1: Setup database
            self.logger.info("Step 1: Setting up database")
            db_result = self.db_installer.setup()

            if not db_result['success']:
                result['error'] = "Database setup failed"
                result['details'] = db_result.get('errors', [])
                return result

            # Store credentials if generated
            if db_result.get('credentials'):
                self.settings.update(db_result['credentials'])
                result['credentials_file'] = db_result.get('credentials_file')

            # Step 2: Generate configuration files
            self.logger.info("Step 2: Generating configuration files")
            config_result = self.config_manager.generate_all()

            if not config_result['success']:
                result['error'] = "Configuration generation failed"
                result['details'] = config_result.get('errors', [])
                return result

            # Step 3: Create launchers
            self.logger.info("Step 3: Creating launcher scripts")
            launcher_result = self.create_launchers()

            if not launcher_result['success']:
                result['error'] = "Launcher creation failed"
                result['details'] = launcher_result.get('errors', [])
                return result

            # Step 4: Mode-specific setup
            self.logger.info(f"Step 4: Performing {self.mode}-specific setup")
            mode_result = self.mode_specific_setup()

            if not mode_result['success']:
                result['error'] = f"{self.mode.capitalize()} setup failed"
                result['details'] = mode_result.get('errors', [])
                return result

            # Step 5: Install dependencies
            self.logger.info("Step 5: Installing Python dependencies")
            deps_result = self.install_dependencies()

            if not deps_result['success']:
                result['error'] = "Dependency installation failed"
                result['details'] = deps_result.get('errors', [])
                return result

            # Step 6: Post-installation validation
            self.logger.info("Step 6: Validating installation")
            validation_result = self.post_validator.validate()

            if not validation_result['valid']:
                result['error'] = "Post-installation validation failed"
                result['details'] = validation_result.get('errors', [])
                return result

            # Success!
            result['success'] = True
            result['details'] = [
                "Database created and initialized",
                "Configuration files generated",
                "Launcher scripts created",
                "Dependencies installed",
                "Installation validated"
            ]

            self.logger.info("Installation completed successfully")
            return result

        except Exception as e:
            self.logger.error(f"Installation failed: {e}", exc_info=True)
            result['error'] = str(e)
            return result

    def create_launchers(self) -> Dict[str, Any]:
        """Create platform-specific launcher scripts"""
        result = {'success': False, 'errors': []}

        try:
            launchers_dir = Path("launchers")
            launchers_dir.mkdir(exist_ok=True)

            # Create universal Python launcher
            launcher_py = launchers_dir / "start_giljo.py"
            launcher_py.write_text(self.generate_python_launcher())
            launcher_py.chmod(0o755) if platform.system() != "Windows" else None

            # Create platform-specific wrappers
            if platform.system() == "Windows":
                launcher_bat = launchers_dir / "start_giljo.bat"
                launcher_bat.write_text(self.generate_windows_launcher())
            else:
                launcher_sh = launchers_dir / "start_giljo.sh"
                launcher_sh.write_text(self.generate_unix_launcher())
                launcher_sh.chmod(0o755)

            result['success'] = True
            self.logger.info("Launcher scripts created successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Launcher creation failed: {e}")
            return result

    def generate_python_launcher(self) -> str:
        """Generate universal Python launcher script"""
        return '''#!/usr/bin/env python3
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
        print("="*60)
        print("   Starting GiljoAI MCP Services")
        print("="*60)
        print()

        # Start API server
        api_port = self.config['services'].get('api_port', 8000)
        self.start_service("API Server", [
            sys.executable, "-m", "uvicorn",
            "api.main:app",
            "--host", "127.0.0.1",
            "--port", str(api_port)
        ])
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
        print("Access points:")
        print(f"  Dashboard: http://localhost:{dashboard_port}")
        print(f"  API Docs: http://localhost:{api_port}/docs")
        print(f"  WebSocket: ws://localhost:{ws_port}")
        print()

        # Open browser if configured
        if self.config.get('features', {}).get('auto_start_browser', True):
            time.sleep(2)
            webbrowser.open(f"http://localhost:{dashboard_port}")

    def shutdown(self, signum=None, frame=None):
        """Gracefully shut down all services"""
        print("\\n" + "="*60)
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
'''

    def generate_windows_launcher(self) -> str:
        """Generate Windows batch launcher"""
        return '''@echo off
REM GiljoAI MCP Windows Launcher

echo ===============================================
echo    GiljoAI MCP Launcher
echo ===============================================
echo.

REM Check Python installation
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python not found in PATH
    echo Please install Python 3.8+ from python.org
    pause
    exit /b 1
)

REM Launch with Python
python launchers\\start_giljo.py %*

if errorlevel 1 (
    echo.
    echo Launch failed. Check the error messages above.
    pause
)
'''

    def generate_unix_launcher(self) -> str:
        """Generate Unix shell launcher"""
        return '''#!/bin/bash
# GiljoAI MCP Unix Launcher

echo "==============================================="
echo "   GiljoAI MCP Launcher"
echo "==============================================="
echo

# Check Python installation
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 not found"
    echo "Please install Python 3.8+ first"
    exit 1
fi

# Launch with Python
python3 launchers/start_giljo.py "$@"
'''

    def install_dependencies(self) -> Dict[str, Any]:
        """Install Python dependencies"""
        result = {'success': False, 'errors': []}

        try:
            # Check if requirements.txt exists
            req_file = Path("requirements.txt")
            if not req_file.exists():
                self.logger.warning("requirements.txt not found, skipping dependency installation")
                result['success'] = True
                return result

            # Use pip to install dependencies
            self.logger.info("Installing Python dependencies...")
            cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt", "--quiet"]

            proc = subprocess.run(cmd, capture_output=True, text=True)

            if proc.returncode != 0:
                result['errors'].append(f"pip install failed: {proc.stderr}")
                return result

            result['success'] = True
            self.logger.info("Dependencies installed successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Dependency installation failed: {e}")
            return result

    @abstractmethod
    def mode_specific_setup(self) -> Dict[str, Any]:
        """Mode-specific setup to be implemented by subclasses"""
        pass


class LocalhostInstaller(BaseInstaller):
    """Localhost mode installer"""

    def mode_specific_setup(self) -> Dict[str, Any]:
        """Localhost-specific setup"""
        result = {'success': True}

        try:
            # Localhost mode: ensure binding to 127.0.0.1 only
            self.logger.info("Configuring localhost-only access")

            # No additional setup needed for localhost
            # Everything is handled in config generation

            return result

        except Exception as e:
            result['success'] = False
            result['errors'] = [str(e)]
            return result


class ServerInstaller(BaseInstaller):
    """Server mode installer with network configuration"""

    def mode_specific_setup(self) -> Dict[str, Any]:
        """Server-specific setup including network configuration"""
        result = {'success': False, 'errors': [], 'warnings': []}

        try:
            # Import server mode modules
            from .network import NetworkManager
            from .security import SecurityManager
            from .firewall import FirewallManager

            # Server mode: setup network access
            self.logger.info("Configuring server mode network access")

            # Step 1: Network configuration
            network_mgr = NetworkManager(self.settings)
            network_result = network_mgr.configure()

            if not network_result['success']:
                result['errors'].extend(network_result.get('errors', []))
                return result

            # Collect warnings
            result['warnings'].extend(network_result.get('warnings', []))

            # Store network config results
            if network_result.get('ssl_cert'):
                self.settings['ssl_cert_path'] = network_result['ssl_cert']
                self.settings['ssl_key_path'] = network_result['ssl_key']

            # Step 2: Security configuration
            security_mgr = SecurityManager(self.settings)
            security_result = security_mgr.configure()

            if not security_result['success']:
                result['errors'].extend(security_result.get('errors', []))
                return result

            # Store security results
            if security_result.get('admin_user'):
                result['admin_user'] = security_result['admin_user']

            if security_result.get('api_key'):
                result['api_key'] = security_result['api_key']
                result['api_key_file'] = security_result.get('api_key_file')

            # Step 3: Generate firewall rules
            firewall_mgr = FirewallManager(self.settings)
            firewall_result = firewall_mgr.generate_firewall_rules()

            if firewall_result['success']:
                result['firewall_files'] = firewall_result.get('files', [])

            # Step 4: Display security warnings and firewall instructions
            if not self.batch:
                # Network security warning
                warning = network_mgr.print_network_warning()
                if warning:
                    print(warning)

                # Firewall instructions
                firewall_instructions = firewall_mgr.print_firewall_instructions()
                if firewall_instructions:
                    print(firewall_instructions)

            result['success'] = True
            self.logger.info("Server mode setup completed successfully")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Server setup failed: {e}")
            return result
