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
            # Step 1: Create virtual environment
            self.logger.info("Step 1: Creating virtual environment")
            venv_result = self.create_venv()

            if not venv_result['success']:
                result['error'] = "Virtual environment creation failed"
                result['details'] = venv_result.get('errors', [])
                return result

            # Step 2: Setup database
            self.logger.info("Step 2: Setting up database")
            db_result = self.db_installer.setup()

            if not db_result['success']:
                result['error'] = "Database setup failed"
                result['details'] = db_result.get('errors', [])
                return result

            # Store credentials if generated
            if db_result.get('credentials'):
                self.settings.update(db_result['credentials'])
                result['credentials_file'] = db_result.get('credentials_file')

            # Step 3: Generate configuration files
            self.logger.info("Step 3: Generating configuration files")
            config_result = self.config_manager.generate_all()

            if not config_result['success']:
                result['error'] = "Configuration generation failed"
                result['details'] = config_result.get('errors', [])
                return result

            # Step 4: Install dependencies
            self.logger.info("Step 4: Installing Python dependencies")
            deps_result = self.install_dependencies()

            if not deps_result['success']:
                result['error'] = "Dependency installation failed"
                result['details'] = deps_result.get('errors', [])
                return result

            # Step 4.5: Install frontend dependencies
            self.logger.info("Step 4.5: Installing frontend dependencies")
            frontend_result = self.install_frontend_dependencies()

            if not frontend_result['success']:
                # Don't fail installation if frontend deps fail, just warn
                result['warnings'] = result.get('warnings', [])
                result['warnings'].append("Failed to install frontend dependencies - frontend may not work")
                self.logger.warning("Frontend dependency installation failed, but continuing installation")

            # Step 5: Create launchers
            self.logger.info("Step 5: Creating launcher scripts")
            launcher_result = self.create_launchers()

            if not launcher_result['success']:
                result['error'] = "Launcher creation failed"
                result['details'] = launcher_result.get('errors', [])
                return result

            # Step 6: Mode-specific setup
            self.logger.info(f"Step 6: Performing {self.mode}-specific setup")
            mode_result = self.mode_specific_setup()

            if not mode_result['success']:
                result['error'] = f"{self.mode.capitalize()} setup failed"
                result['details'] = mode_result.get('errors', [])
                return result

            # Step 7: Register with Claude Code (MCP)
            if self.settings.get('register_mcp', True):
                self.logger.info("Step 7: Registering with Claude Code MCP")
                mcp_result = self.register_with_claude()

                if not mcp_result['success']:
                    # Don't fail installation if MCP registration fails, just warn
                    result['warnings'] = result.get('warnings', [])
                    result['warnings'].append("Failed to register with Claude Code - you can do this manually later")
                    self.logger.warning("MCP registration failed, but continuing installation")
                else:
                    result['mcp_registered'] = True

            # Step 8: Post-installation validation
            self.logger.info("Step 8: Validating installation")
            validation_result = self.post_validator.validate()

            if not validation_result['valid']:
                result['error'] = "Post-installation validation failed"
                result['details'] = validation_result.get('errors', [])
                return result

            # Success!
            result['success'] = True
            result['details'] = [
                "Virtual environment created",
                "Database created and initialized",
                "Configuration files generated",
                "Dependencies installed",
                "Launcher scripts created",
                "Installation validated"
            ]

            if result.get('mcp_registered'):
                result['details'].append("Registered with Claude Code")

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
            'WebSocket': self.config['services'].get('websocket_port', 7273),
            'Dashboard': self.config['services'].get('dashboard_port', 7274)
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
        ws_port = self.config['services'].get('websocket_port', 7273)
        self.start_service("WebSocket Server", [
            sys.executable, "-m", "giljo_mcp.websocket",
            "--port", str(ws_port)
        ])
        time.sleep(1)

        # Start Dashboard
        dashboard_port = self.config['services'].get('dashboard_port', 7274)
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

REM Set working directory to script location
cd /d "%~dp0"

REM Check if venv exists
if not exist "venv\\Scripts\\python.exe" (
    echo Error: Virtual environment not found
    echo Please run the installer first
    pause
    exit /b 1
)

REM Launch with venv Python
venv\\Scripts\\python.exe start_giljo.py %*

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

# Get script directory and change to it
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Check if venv exists
if [ ! -f "venv/bin/python" ]; then
    echo "Error: Virtual environment not found"
    echo "Please run the installer first"
    exit 1
fi

# Launch with venv Python
venv/bin/python start_giljo.py "$@"
'''

    def create_venv(self) -> Dict[str, Any]:
        """Create virtual environment in installation directory"""
        result = {'success': False, 'errors': []}

        try:
            install_dir = Path(self.settings.get('install_dir', Path.cwd()))
            venv_path = install_dir / 'venv'

            # Check if venv already exists
            if venv_path.exists():
                self.logger.info(f"Virtual environment already exists at {venv_path}")
                result['success'] = True
                result['venv_path'] = str(venv_path)
                return result

            # Create virtual environment
            self.logger.info(f"Creating virtual environment at {venv_path}")
            import venv

            # Create venv with pip
            venv.create(venv_path, with_pip=True, clear=False, symlinks=(platform.system() != "Windows"))

            # Verify venv was created successfully
            if platform.system() == "Windows":
                venv_python = venv_path / 'Scripts' / 'python.exe'
            else:
                venv_python = venv_path / 'bin' / 'python'

            if not venv_python.exists():
                result['errors'].append(f"Virtual environment creation failed - python not found at {venv_python}")
                return result

            # Bootstrap pip using ensurepip (more reliable for Python 3.13+)
            self.logger.info("Bootstrapping pip in virtual environment...")
            try:
                ensurepip_cmd = [str(venv_python), "-m", "ensurepip", "--upgrade"]
                ensurepip_result = subprocess.run(ensurepip_cmd, capture_output=True, text=True, timeout=120)

                if ensurepip_result.returncode != 0:
                    self.logger.warning(f"ensurepip failed: {ensurepip_result.stderr}")
                    self.logger.info("Trying to install pip directly...")

                    # Fallback: try to upgrade pip directly
                    pip_install_cmd = [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"]
                    pip_result = subprocess.run(pip_install_cmd, capture_output=True, text=True, timeout=120)

                    if pip_result.returncode != 0:
                        result['errors'].append(f"Failed to install pip: {pip_result.stderr}")
                        return result
                else:
                    self.logger.info("pip bootstrapped successfully")

                # Now upgrade pip to latest version
                self.logger.info("Upgrading pip to latest version...")
                upgrade_cmd = [str(venv_python), "-m", "pip", "install", "--upgrade", "pip"]
                upgrade_result = subprocess.run(upgrade_cmd, capture_output=True, text=True, timeout=120)

                if upgrade_result.returncode != 0:
                    self.logger.warning(f"pip upgrade failed: {upgrade_result.stderr}")
                    self.logger.warning("Continuing with bootstrapped pip version")
                else:
                    self.logger.info("pip upgraded successfully")

            except subprocess.TimeoutExpired:
                self.logger.warning("pip setup timed out, continuing with existing pip version")
            except Exception as e:
                self.logger.warning(f"pip setup error: {e}, will attempt to use existing pip")

            result['success'] = True
            result['venv_path'] = str(venv_path)
            result['venv_python'] = str(venv_python)
            self.logger.info(f"Virtual environment created successfully at {venv_path}")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Virtual environment creation failed: {e}", exc_info=True)
            return result

    def install_dependencies(self) -> Dict[str, Any]:
        """Install Python dependencies in the virtual environment"""
        result = {'success': False, 'errors': []}

        try:
            # Get venv paths
            install_dir = Path(self.settings.get('install_dir', Path.cwd()))
            venv_path = install_dir / 'venv'

            if platform.system() == "Windows":
                venv_python = venv_path / 'Scripts' / 'python.exe'
            else:
                venv_python = venv_path / 'bin' / 'python'

            if not venv_python.exists():
                result['errors'].append(f"Virtual environment python not found at {venv_python}")
                return result

            # Check if requirements.txt exists
            req_file = Path(__file__).parent.parent.parent / "requirements.txt"
            if not req_file.exists():
                self.logger.warning("requirements.txt not found, skipping dependency installation")
                result['success'] = True
                return result

            # Copy requirements.txt to install directory only if they're different files
            dest_req = install_dir / "requirements.txt"
            import shutil

            # Only copy if source and destination are different
            if req_file.resolve() != dest_req.resolve():
                self.logger.info(f"Copying requirements.txt from {req_file} to {dest_req}")
                shutil.copy(req_file, dest_req)
            else:
                self.logger.info(f"Using existing requirements.txt at {dest_req}")

            # Use venv python -m pip to install dependencies (more reliable than pip.exe)
            self.logger.info("Installing Python dependencies in virtual environment...")
            self.logger.info("This may take a few minutes - showing live progress below:")
            print("\n" + "="*60)

            cmd = [str(venv_python), "-m", "pip", "install", "-r", str(dest_req), "--verbose"]

            # Run with live output to terminal (no capture)
            proc = subprocess.run(cmd)

            print("="*60 + "\n")

            if proc.returncode != 0:
                result['errors'].append(f"pip install failed with exit code {proc.returncode}")
                return result

            # Install the giljo_mcp package itself in editable mode
            self.logger.info("Installing giljo_mcp package in development mode...")
            print("\n" + "="*60)
            print("Installing GiljoAI MCP package...")

            # Get the source directory (where setup.py is)
            source_dir = Path(__file__).parent.parent.parent

            # Install in editable mode using python -m pip
            install_cmd = [str(venv_python), "-m", "pip", "install", "-e", str(source_dir)]

            proc2 = subprocess.run(install_cmd, capture_output=True, text=True)

            if proc2.returncode != 0:
                self.logger.warning(f"Editable install failed, trying regular install: {proc2.stderr}")
                # Try regular install as fallback
                install_cmd = [str(venv_python), "-m", "pip", "install", str(source_dir)]
                proc2 = subprocess.run(install_cmd)

                if proc2.returncode != 0:
                    result['errors'].append(f"giljo_mcp package installation failed")
                    return result

            print("✓ GiljoAI MCP package installed successfully")
            print("="*60 + "\n")

            result['success'] = True
            self.logger.info("Dependencies and package installed successfully in virtual environment")
            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Dependency installation failed: {e}")
            return result

    def install_frontend_dependencies(self) -> Dict[str, Any]:
        """Install frontend npm dependencies"""
        result = {'success': False, 'errors': []}

        try:
            install_dir = Path(self.settings.get('install_dir', Path.cwd()))
            frontend_dir = install_dir / 'frontend'

            # Check if frontend directory exists
            if not frontend_dir.exists():
                self.logger.info("Frontend directory not found, skipping frontend dependency installation")
                result['success'] = True
                return result

            # Check if npm is available
            npm_cmd = 'npm.cmd' if platform.system() == "Windows" else 'npm'
            try:
                npm_check = subprocess.run(
                    [npm_cmd, '--version'],
                    capture_output=True,
                    check=True,
                    timeout=10
                )
                npm_version = npm_check.stdout.decode().strip()
                self.logger.info(f"Found npm version {npm_version}")
            except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
                self.logger.warning("npm not found - skipping frontend dependency installation")
                result['errors'].append("npm not installed - install Node.js to enable frontend")
                return result

            # Check if node_modules already exists
            if (frontend_dir / 'node_modules').exists():
                self.logger.info("Frontend dependencies already installed")
                result['success'] = True
                return result

            # Install npm dependencies
            self.logger.info("Installing frontend dependencies (this may take a few minutes)...")
            print("\n" + "="*60)
            print("Installing frontend dependencies...")
            print("="*60 + "\n")

            install_proc = subprocess.run(
                [npm_cmd, 'install'],
                cwd=str(frontend_dir),
                timeout=300  # 5 minute timeout
            )

            print("\n" + "="*60 + "\n")

            if install_proc.returncode != 0:
                result['errors'].append(f"npm install failed with exit code {install_proc.returncode}")
                return result

            result['success'] = True
            self.logger.info("Frontend dependencies installed successfully")
            return result

        except subprocess.TimeoutExpired:
            result['errors'].append("npm install timed out after 5 minutes")
            self.logger.error("Frontend dependency installation timed out")
            return result
        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"Frontend dependency installation failed: {e}")
            return result

    def register_with_claude(self) -> Dict[str, Any]:
        """Register MCP server with Claude Code"""
        result = {'success': False, 'errors': []}

        try:
            # Import the universal MCP installer
            from installer.universal_mcp_installer import UniversalMCPInstaller

            # Get installation directory and venv paths
            install_dir = Path(self.settings.get('install_dir', Path.cwd()))

            if platform.system() == "Windows":
                venv_python = install_dir / 'venv' / 'Scripts' / 'python.exe'
            else:
                venv_python = install_dir / 'venv' / 'bin' / 'python'

            # Create MCP installer
            mcp_installer = UniversalMCPInstaller()

            # Register with all detected tools (currently only Claude Code)
            registration_result = mcp_installer.register_all(
                server_name='giljo-mcp',
                command=str(venv_python),
                args=['-m', 'giljo_mcp'],
                env=None
            )

            # Check if Claude was registered
            if registration_result.get('claude', False):
                result['success'] = True
                result['registered_tools'] = list(registration_result.keys())
                self.logger.info("Successfully registered with Claude Code")
            else:
                result['errors'].append("Failed to register with Claude Code")
                self.logger.warning("Claude Code registration failed")

            return result

        except Exception as e:
            result['errors'].append(str(e))
            self.logger.error(f"MCP registration failed: {e}", exc_info=True)
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
