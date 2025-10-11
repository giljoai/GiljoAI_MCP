"""
CRITICAL FIXES for installer.py
Copy these methods into the appropriate locations in installer.py
"""

# ADD TO IMPORTS SECTION:
import venv
import shutil
from installer.universal_mcp_installer import UniversalMCPInstaller


# ADD THIS METHOD TO BaseInstaller class (around line 143):
def create_venv(self) -> Dict[str, Any]:
    """Create virtual environment in installation directory"""
    result = {'success': False, 'errors': []}

    try:
        venv_path = Path(self.settings.get('install_dir', '.')) / 'venv'

        # Skip if venv already exists
        if venv_path.exists():
            self.logger.info(f"Virtual environment already exists at {venv_path}")
            result['success'] = True
            return result

        self.logger.info(f"Creating virtual environment at {venv_path}")
        venv.create(
            venv_path,
            with_pip=True,
            system_site_packages=False,
            clear=False,
            symlinks=False if platform.system() == "Windows" else True
        )

        # Upgrade pip in the new venv
        if platform.system() == "Windows":
            pip_path = venv_path / "Scripts" / "pip.exe"
            python_path = venv_path / "Scripts" / "python.exe"
        else:
            pip_path = venv_path / "bin" / "pip"
            python_path = venv_path / "bin" / "python"

        # Upgrade pip
        upgrade_cmd = [str(python_path), "-m", "pip", "install", "--upgrade", "pip", "--quiet"]
        subprocess.run(upgrade_cmd, capture_output=True)

        # Store venv paths in settings for later use
        self.settings['venv_path'] = str(venv_path)
        self.settings['venv_python'] = str(python_path)
        self.settings['venv_pip'] = str(pip_path)

        result['success'] = True
        self.logger.info("Virtual environment created successfully")
        return result

    except Exception as e:
        result['errors'].append(f"Failed to create virtual environment: {str(e)}")
        self.logger.error(f"Virtual environment creation failed: {e}")
        return result


# MODIFY install_dependencies METHOD (replace lines 407-436):
def install_dependencies(self) -> Dict[str, Any]:
    """Install Python dependencies in virtual environment"""
    result = {'success': False, 'errors': []}

    try:
        # Copy requirements.txt to installation directory
        req_source = Path(__file__).parent.parent.parent / "requirements.txt"
        req_dest = Path(self.settings.get('install_dir', '.')) / "requirements.txt"

        if req_source.exists():
            self.logger.info(f"Copying requirements.txt to {req_dest}")
            shutil.copy(req_source, req_dest)

        # Check if requirements.txt exists
        if not req_dest.exists():
            self.logger.warning("requirements.txt not found, skipping dependency installation")
            result['success'] = True
            return result

        # Use venv pip if available, otherwise system pip
        if 'venv_pip' in self.settings:
            pip_executable = self.settings['venv_pip']
        else:
            pip_executable = sys.executable

        # Install dependencies
        self.logger.info("Installing Python dependencies...")
        cmd = [pip_executable, "install", "-r", str(req_dest), "--quiet"]

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


# MODIFY install METHOD - Add these steps after Step 1 (around line 80):
# Step 1.5: Create virtual environment
self.logger.info("Step 1.5: Creating virtual environment")
venv_result = self.create_venv()

if not venv_result['success']:
    result['error'] = "Virtual environment creation failed"
    result['details'] = venv_result.get('errors', [])
    return result


# ADD after Step 6 (around line 124):
# Step 7: Register with Claude Code
if self.settings.get('register_mcp', True):
    self.logger.info("Step 7: Registering with Claude Code")
    try:
        mcp_installer = UniversalMCPInstaller()
        # Set the installation directory
        mcp_installer.install_dir = Path(self.settings.get('install_dir', '.'))

        # Register with available tools
        mcp_result = mcp_installer.register_all(
            server_name="giljo-mcp",
            command=self.settings.get('venv_python', sys.executable),
            args=["-m", "giljo_mcp.mcp_adapter"],
            env={"GILJO_MCP_HOME": str(self.settings.get('install_dir', '.'))}
        )

        if not mcp_result.get('claude', False):
            result['warnings'] = result.get('warnings', [])
            result['warnings'].append("Failed to register with Claude Code - manual registration may be required")
        else:
            self.logger.info("Successfully registered with Claude Code")

        # Add notice about tool support
        self.logger.info("NOTE: Currently supporting Claude Code only. Codex and Gemini support coming in 2026.")

    except Exception as e:
        self.logger.warning(f"MCP registration failed: {e}")
        result['warnings'] = result.get('warnings', [])
        result['warnings'].append(f"MCP registration failed: {str(e)}")


# UPDATE generate_python_launcher method to use venv python:
def generate_python_launcher(self) -> str:
    """Generate universal Python launcher script"""
    venv_python = "venv/Scripts/python.exe" if platform.system() == "Windows" else "venv/bin/python"

    return f'''#!/usr/bin/env python3
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
        self.install_dir = Path(__file__).parent.parent
        self.venv_python = self.install_dir / "{venv_python}"
        self.load_config()

    def load_config(self):
        """Load configuration from config.yaml"""
        config_path = self.install_dir / "config.yaml"
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
        required_files = ['.env', 'config.yaml', 'requirements.txt']
        for file in required_files:
            if not (self.install_dir / file).exists():
                print(f"Error: Missing {{file}} - installation incomplete")
                return False

        # Check if venv exists
        if not self.venv_python.exists():
            print("Error: Virtual environment not found - please run installer")
            return False

        # Check ports
        services = self.config.get('services', {{}})
        ports = {{
            'API': services.get('api', {{}}).get('port', 7272),
            'WebSocket': services.get('websocket', {{}}).get('port', 7273),
            'Dashboard': services.get('frontend', {{}}).get('port', 7274)
        }}

        for service, port in ports.items():
            if not self.check_port(port):
                print(f"Error: Port {{port}} ({{service}}) is already in use")
                return False

        return True

    def start_service(self, name: str, command: list) -> subprocess.Popen:
        """Start a single service"""
        print(f"Starting {{name}}...")
        env = os.environ.copy()
        env['PYTHONPATH'] = str(self.install_dir)

        proc = subprocess.Popen(
            command,
            env=env,
            cwd=str(self.install_dir),
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
        print("NOTE: Currently supporting Claude Code only.")
        print("Codex and Gemini support coming in 2026.")
        print()

        # Use venv Python for all services
        python_exe = str(self.venv_python)

        # Start API server
        services = self.config.get('services', {{}})
        api_port = services.get('api', {{}}).get('port', 7272)
        api_host = services.get('api', {{}}).get('host', '127.0.0.1')

        self.start_service("API Server", [
            python_exe, "-m", "uvicorn",
            "api.main:app",
            "--host", api_host,
            "--port", str(api_port)
        ])
        time.sleep(2)  # Wait for startup

        # Start WebSocket server
        ws_port = services.get('websocket', {{}}).get('port', 7273)
        self.start_service("WebSocket Server", [
            python_exe, "-m", "giljo_mcp.websocket",
            "--port", str(ws_port)
        ])
        time.sleep(1)

        # Start Dashboard
        dashboard_port = services.get('frontend', {{}}).get('port', 7274)
        self.start_service("Dashboard", [
            python_exe, "-m", "http.server",
            str(dashboard_port),
            "--directory", "frontend"
        ])

        print()
        print("All services started successfully!")
        print()
        print("Access points:")
        print(f"  Dashboard: http://localhost:{{dashboard_port}}")
        print(f"  API Docs: http://localhost:{{api_port}}/docs")
        print(f"  WebSocket: ws://localhost:{{ws_port}}")
        print()

        # Open browser if configured
        if self.config.get('features', {{}}).get('auto_start_browser', True):
            time.sleep(2)
            webbrowser.open(f"http://localhost:{{dashboard_port}}")

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
            print(f"Error: {{e}}")
            self.shutdown()


# Add standalone function for CLI installer
def start_services(settings: Dict[str, Any]):
    """Start services after installation (called from CLI installer)"""
    launcher = GiljoLauncher()
    # Override config with installation settings if needed
    if 'api_port' in settings:
        launcher.config = {{
            'services': {{
                'api': {{'port': settings.get('api_port', 7272), 'host': '127.0.0.1'}},
                'websocket': {{'port': settings.get('ws_port', 7273)}},
                'frontend': {{'port': settings.get('dashboard_port', 7274)}}
            }},
            'features': {{
                'auto_start_browser': settings.get('open_browser', True)
            }}
        }}
    launcher.start_all_services()


if __name__ == "__main__":
    launcher = GiljoLauncher()
    launcher.run()
'''
