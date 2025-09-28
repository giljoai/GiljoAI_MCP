#!/usr/bin/env python3
"""
GiljoAI MCP Universal Bootstrap Installer
==========================================

This is the single entry point for installing GiljoAI MCP on any platform.
It detects the operating system, checks for GUI capability, and launches
the appropriate installer (GUI or CLI).

Requirements: Python 3.8+ (uses only standard library)
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional


class Bootstrap:
    """Universal bootstrap installer for GiljoAI MCP"""

    def __init__(self):
        self.os_type = platform.system().lower()
        self.os_version = platform.version()
        self.python_version = sys.version_info
        self.architecture = platform.machine()
        self.has_gui = None
        self.installer_choice = None
        self.install_dir = Path.cwd()

        # Colors for terminal output (cross-platform)
        self.colors = (
            {
                "HEADER": "\033[95m",
                "BLUE": "\033[94m",
                "GREEN": "\033[92m",
                "YELLOW": "\033[93m",
                "RED": "\033[91m",
                "ENDC": "\033[0m",
                "BOLD": "\033[1m",
            }
            if self.supports_color()
            else {k: "" for k in ["HEADER", "BLUE", "GREEN", "YELLOW", "RED", "ENDC", "BOLD"]}
        )

    def supports_color(self) -> bool:
        """Check if terminal supports color output"""
        if self.os_type == "windows":
            return os.environ.get("ANSICON") is not None or "WT_SESSION" in os.environ
        return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

    def print_header(self):
        """Print welcome header"""
        header = f"""
{self.colors['HEADER']}{'='*60}
   GiljoAI MCP Orchestrator - Universal Installer
{'='*60}{self.colors['ENDC']}
        """
        print(header)

    def print_status(self, message: str, status: str = "info"):
        """Print colored status message"""
        # Use ASCII symbols for better compatibility
        icons = {"info": "[i]", "success": "[OK]", "warning": "[!]", "error": "[X]", "check": "[?]"}

        colors = {
            "info": self.colors["BLUE"],
            "success": self.colors["GREEN"],
            "warning": self.colors["YELLOW"],
            "error": self.colors["RED"],
            "check": self.colors["HEADER"],
        }

        icon = icons.get(status, "")
        color = colors.get(status, "")
        print(f"{color}{icon} {message}{self.colors['ENDC']}")

    def detect_os(self) -> Dict[str, str]:
        """Detect operating system details"""
        os_info = {
            "system": platform.system(),
            "version": platform.version(),
            "release": platform.release(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "python": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
        }

        # Additional OS-specific detection
        if os_info["system"] == "Windows":
            try:
                import winreg

                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion") as key:
                    os_info["windows_build"] = winreg.QueryValueEx(key, "CurrentBuild")[0]
            except:
                pass
        elif os_info["system"] == "Linux":
            # Check for specific distributions
            if Path("/etc/os-release").exists():
                with open("/etc/os-release") as f:
                    for line in f:
                        if line.startswith("ID="):
                            os_info["distribution"] = line.split("=")[1].strip().strip('"')
                        elif line.startswith("VERSION_ID="):
                            os_info["dist_version"] = line.split("=")[1].strip().strip('"')

        return os_info

    def check_gui_capability(self) -> bool:
        """Check if system can run GUI applications"""
        # Removed verbose "Checking GUI capability..." message

        # Try importing tkinter (comes with Python)
        try:
            if self.os_type == "darwin":  # macOS
                # Check if we're in SSH session
                if os.environ.get("SSH_CONNECTION"):
                    self.print_status("SSH session detected - CLI mode", "info")
                    return False
                # macOS generally has GUI
                import tkinter

                self.print_status("GUI capability detected", "success")
                return True

            if self.os_type == "linux":
                # Check for display
                if not os.environ.get("DISPLAY") and not os.environ.get("WAYLAND_DISPLAY"):
                    self.print_status("No display detected - CLI mode", "info")
                    return False
                # Try importing tkinter
                import tkinter

                # Try creating a test window
                root = tkinter.Tk()
                root.withdraw()
                root.destroy()
                self.print_status("GUI capability detected", "success")
                return True

            if self.os_type == "windows":
                # Check if running in pure console mode
                import tkinter

                # Windows typically has GUI unless in SSH/container
                if os.environ.get("SSH_CONNECTION") or os.environ.get("CONTAINER"):
                    return False
                self.print_status("GUI capability detected", "success")
                return True

            return False

        except ImportError:
            self.print_status("tkinter not available - CLI mode", "warning")
            return False
        except Exception as e:
            self.print_status(f"GUI test failed: {str(e)[:50]} - CLI mode", "warning")
            return False

    def test_gui_import(self) -> bool:
        """Test if GUI libraries can be imported"""
        try:
            import tkinter
            import tkinter.ttk
            return True
        except ImportError:
            return False

    def check_python_version(self) -> bool:
        """Check if Python version meets requirements"""
        min_version = (3, 8)
        current = (self.python_version.major, self.python_version.minor)

        if current >= min_version:
            self.print_status(f"Python {self.python_version.major}.{self.python_version.minor} OK", "success")
            return True
        self.print_status(
            f"Python {min_version[0]}.{min_version[1]}+ required (found {current[0]}.{current[1]})", "error"
        )
        return False

    def check_existing_installation(self) -> Optional[Dict]:
        """Check for existing GiljoAI MCP installation"""
        markers = [
            "config.yaml",  # Generated during install
            ".giljo_install_manifest.json",  # Created after install
            "venv",  # Virtual environment
            "data/giljo.db",  # Database created on first run
        ]

        found = []
        for marker in markers:
            if Path(marker).exists():
                found.append(marker)

        if found:
            return {"installed": True, "markers": found, "path": str(Path.cwd())}
        return None

    def prompt_installer_choice(self) -> str:
        """Prompt user for installer preference if GUI is available"""
        print(f"\n{self.colors['BOLD']}Installation Mode Selection{self.colors['ENDC']}")
        print("1. GUI Installer (Recommended for desktop users)")
        print("2. CLI Installer (Recommended for servers/remote sessions)")
        print("3. Exit")

        while True:
            choice = input(f"\n{self.colors['BLUE']}Select installation mode [1-3]: {self.colors['ENDC']}").strip()
            if choice in ["1", "2", "3"]:
                return choice
            print(f"{self.colors['RED']}Invalid choice. Please enter 1, 2, or 3.{self.colors['ENDC']}")

    def show_platform_integration(self):
        """Show instructions for integrating with various coding platforms"""
        print(f"\n{self.colors['HEADER']}{'='*60}")
        print("   Platform Integration - Final Step")
        print(f"{'='*60}{self.colors['ENDC']}")

        print(f"\n{self.colors['BOLD']}To activate GiljoAI-MCP in your coding platform:{self.colors['ENDC']}\n")

        # Get the current directory for path
        install_path = Path.cwd()

        # Claude Desktop
        print(f"{self.colors['BLUE']}For Claude Desktop:{self.colors['ENDC']}")
        print("  1. Locate your Claude configuration file:")
        if self.os_type == "windows":
            print("     %APPDATA%\\Claude\\claude_desktop_config.json")
        elif self.os_type == "darwin":
            print("     ~/Library/Application Support/Claude/claude_desktop_config.json")
        else:
            print("     ~/.config/Claude/claude_desktop_config.json")
        print("  2. Add this to the 'mcpServers' section:")
        print(
            f"""
    "giljo-mcp": {{
      "command": "python",
      "args": ["-m", "src.giljo_mcp.server"],
      "env": {{
        "PYTHONPATH": "{install_path / 'src'}",
        "GILJO_MCP_DB": "{install_path / 'data' / 'giljo_mcp.db'}"
      }}
    }}
"""
        )
        print("  3. Restart Claude Desktop\n")

        # VS Code with Continue
        print(f"{self.colors['BLUE']}For VS Code with Continue:{self.colors['ENDC']}")
        print("  1. Open Continue extension settings")
        print("  2. Add to config.json:")
        print(
            f"""    "customCommands": [{{
      "name": "giljo-mcp",
      "command": "python -m src.giljo_mcp.server",
      "cwd": "{install_path}"
    }}]
"""
        )

        # Generic MCP-compatible platforms
        print(f"{self.colors['BLUE']}For other MCP-compatible platforms:{self.colors['ENDC']}")
        print("  Server command: python -m src.giljo_mcp.server")
        print(f"  Working directory: {install_path}")
        print(f"  Python path: {install_path / 'src'}")
        print(f"  Database: {install_path / 'data' / 'giljo_mcp.db'}")

        print(
            f"\n{self.colors['YELLOW']}Note: After adding the configuration, restart your coding platform.{self.colors['ENDC']}"
        )
        print(
            f"{self.colors['GREEN']}GiljoAI-MCP will then be available as 'giljo-mcp' in your platform's MCP servers.{self.colors['ENDC']}\n"
        )

    def post_installation_setup(self) -> bool:
        """Perform post-installation setup tasks"""
        self.print_status("Running post-installation setup...", "info")

        success = True

        # Generate configuration using new Config Manager
        try:
            from installer.config.config_manager import ConfigurationManager
            from installer.core.profile import ProfileManager, ProfileType

            # Initialize configuration manager
            config_manager = ConfigurationManager()

            # Create required directories first
            try:
                # Use existing data directory or create
                data_dir = self.install_dir / "data"
                data_dir.mkdir(exist_ok=True)
                config_dir = self.install_dir / "config"
                config_dir.mkdir(exist_ok=True)
                self.print_status("Created required directories", "success")
            except Exception as e:
                self.print_status(f"Directory creation warning: {e}", "warning")

            # Create default profile if none exists
            if not (self.install_dir / "config.yaml").exists():
                # Generate developer profile by default for bootstrap
                profile_data = {
                    "profile_type": "developer",
                    "database_type": "sqlite",
                    "host": "localhost",
                    "port": 8000,
                    "enable_redis": False,
                    "enable_docker": False,
                    "deployment_mode": "local",
                }

                config = config_manager.generate_configuration(
                    profile_type="developer", user_inputs=profile_data
                )

                # Save the configuration
                config_path = config_manager.save_configuration(config, self.install_dir / ".env")
                config_success = config_path.exists()

                if config_success:
                    self.print_status("Generated configuration files", "success")
                else:
                    self.print_status("Config generation failed", "warning")
                    success = False
            else:
                self.print_status("Using existing config.yaml", "info")
        except ImportError:
            self.print_status("New config manager not available, using fallback", "warning")
            # Keep existing fallback code
            try:
                from installers.config_generator import ConfigGenerator

                config_gen = ConfigGenerator(self.install_dir)
                config_success, config_msg = config_gen.create_config_file()
                if config_success:
                    self.print_status(config_msg, "success")
                else:
                    self.print_status(config_msg, "warning")
                    success = False
            except Exception as e:
                self.print_status(f"Fallback config generation failed: {e}", "warning")
                success = False
        except Exception as e:
            self.print_status(f"Config generation failed: {e}", "warning")
            success = False

        # Set up service management
        try:
            from installer.services.service_manager import get_platform_service_manager

            self.print_status("Setting up service management...", "info")

            service_manager = get_platform_service_manager()

            # Install GiljoAI services (prepare service definitions but don't auto-start)
            service_setup_results = service_manager.setup_services(
                install_dir=self.install_dir,
                auto_start=False,  # Let users control this through GUI
            )

            if service_setup_results:
                self.print_status("Service management configured successfully", "success")
            else:
                self.print_status("Service management setup completed with warnings", "warning")

        except ImportError:
            self.print_status("Service Manager not available, skipping service setup", "warning")
        except Exception as e:
            self.print_status(f"Service setup warning: {e}", "warning")

        # Create launchers and shortcuts
        try:
            # Try new integrated launcher system first
            try:
                from installer.services.service_manager import get_platform_service_manager

                service_mgr = get_platform_service_manager()

                # Create launcher scripts using service manager
                launcher_success = service_mgr.create_launchers(self.install_dir)
                if launcher_success:
                    self.print_status("Created service-based launchers", "success")
                else:
                    raise ImportError("Service-based launcher creation failed")

            except:
                # Fall back to original launcher system
                from installers.launcher_creator import LauncherCreator

                launcher = LauncherCreator(self.install_dir)

                self.print_status("Creating launch scripts and shortcuts...", "info")
                results = launcher.create_all_launchers()

                # Show results
                for name, (result_success, msg) in results.items():
                    if result_success:
                        self.print_status(f"{name}: {msg}", "success")
                    else:
                        self.print_status(f"{name}: {msg}", "warning")

                # Check if critical components were created
                if not results.get("start_script", (False,))[0]:
                    success = False

        except Exception as e:
            self.print_status(f"Launcher creation failed: {e}", "warning")
            success = False

        return success

    def launch_gui_installer(self) -> int:
        """Launch the GUI installer (setup_gui.py)"""
        self.print_status("Launching GUI installer...", "info")

        # Check if setup_gui.py exists
        if not Path("setup_gui.py").exists():
            self.print_status("GUI installer not found, falling back to CLI", "warning")
            return self.launch_cli_installer()

        try:
            # Test GUI capability one more time before launching
            if not self.test_gui_import():
                self.print_status("GUI not available, switching to CLI", "warning")
                return self.launch_cli_installer()

            self.print_status("Opening GUI installer window...", "info")
            print("A GUI window should appear shortly. If no window appears, close this and try CLI mode.")

            # Run setup_gui.py with proper GUI handling
            if self.os_type == "windows":
                # Windows: Launch GUI in separate window
                result = subprocess.run(
                    [sys.executable, "setup_gui.py"],
                    capture_output=False,
                    text=True,
                    check=False
                )
            else:
                # Unix-like: Standard execution
                result = subprocess.run(
                    [sys.executable, "setup_gui.py"],
                    capture_output=False,
                    text=True,
                    check=False
                )

            # If installation succeeded, run post-installation setup
            if result.returncode == 0:
                if self.post_installation_setup():
                    self.print_status("Installation complete!", "success")
                    print(f"\n{self.colors['GREEN']}You can now start GiljoAI MCP using:")
                    if self.os_type == "windows":
                        print("  - Desktop shortcut: GiljoAI MCP Orchestrator")
                        print("  - Start Menu: GiljoAI MCP Orchestrator")
                        print("  - Command line: start_giljo.bat")
                    else:
                        print("  - Desktop shortcut: GiljoAI MCP Orchestrator")
                        print("  - Command line: ./start_giljo.sh")
                    print(f"{self.colors['ENDC']}")

                    # Show platform integration instructions
                    self.show_platform_integration()
                else:
                    self.print_status("Installation completed with warnings", "warning")
                    # Show platform integration even with warnings
                    self.show_platform_integration()

            return result.returncode
        except Exception as e:
            self.print_status(f"GUI installer failed: {e}", "error")
            print("\nFalling back to CLI installer...")
            return self.launch_cli_installer()

    def launch_cli_installer(self) -> int:
        """Launch the CLI installer (setup.py)"""
        self.print_status("Launching CLI installer...", "info")

        # Check if setup.py exists
        if not Path("setup.py").exists():
            self.print_status("setup.py not found!", "error")
            self.print_manual_instructions()
            return 1

        try:
            # Run setup.py in interactive CLI mode (without --non-interactive flag)
            result = subprocess.run([sys.executable, "setup.py"], capture_output=False, text=True, check=False)

            # If installation succeeded, run post-installation setup
            if result.returncode == 0:
                if self.post_installation_setup():
                    self.print_status("Installation complete!", "success")
                    print(f"\n{self.colors['GREEN']}You can now start GiljoAI MCP using:")
                    if self.os_type == "windows":
                        print("  - Desktop shortcut: GiljoAI MCP Orchestrator")
                        print("  - Command line: start_giljo.bat")
                    else:
                        print("  - Desktop shortcut: GiljoAI MCP Orchestrator")
                        print("  - Command line: ./start_giljo.sh")
                    print(f"{self.colors['ENDC']}")

                    # Show platform integration instructions
                    self.show_platform_integration()
                else:
                    self.print_status("Installation completed with warnings", "warning")
                    # Show platform integration even with warnings
                    self.show_platform_integration()

            return result.returncode
        except Exception as e:
            self.print_status(f"CLI installer failed: {e}", "error")
            self.print_manual_instructions()
            return 1

    def print_manual_instructions(self):
        """Print manual installation instructions if automated install fails"""
        instructions = f"""
{self.colors['YELLOW']}Manual Installation Instructions:{self.colors['ENDC']}

1. Create virtual environment:
   {self.colors['BLUE']}python -m venv venv{self.colors['ENDC']}

2. Activate virtual environment:
   - Windows: {self.colors['BLUE']}venv\\Scripts\\activate{self.colors['ENDC']}
   - Mac/Linux: {self.colors['BLUE']}source venv/bin/activate{self.colors['ENDC']}

3. Install dependencies:
   {self.colors['BLUE']}pip install -r requirements.txt{self.colors['ENDC']}

4. Copy configuration:
   {self.colors['BLUE']}cp config.yaml.example config.yaml{self.colors['ENDC']}
   {self.colors['BLUE']}cp .env.example .env{self.colors['ENDC']}

5. Run the application:
   {self.colors['BLUE']}python -m src.giljo_mcp.mcp_server{self.colors['ENDC']}

For detailed instructions, see INSTALL.md
        """
        print(instructions)

    def print_system_info(self):
        """Print detected system information"""
        os_info = self.detect_os()

        print(f"\n{self.colors['BOLD']}System Information:{self.colors['ENDC']}")
        print(f"  OS: {os_info['system']} {os_info.get('release', '')}")
        print(f"  Version: {os_info.get('version', 'Unknown')[:50]}...")
        print(f"  Architecture: {os_info['machine']}")
        print(f"  Python: {os_info['python']}")

        if "distribution" in os_info:
            print(f"  Distribution: {os_info['distribution']} {os_info.get('dist_version', '')}")

    def check_dependencies(self) -> bool:
        """Run comprehensive dependency checker and show report"""
        self.print_status("Running comprehensive dependency check...", "check")

        # First check basic requirements
        basic_check = self._check_basic_dependencies()

        try:
            # Try new integrated dependency checker if available
            success = self._check_integrated_dependencies()
            return basic_check and success

        except ImportError:
            self.print_status("Integrated dependency checker not available, using basic check", "warning")
            return basic_check
        except Exception as e:
            self.print_status(f"Dependency check failed: {e}", "error")
            response = input(
                f"\n{self.colors['YELLOW']}Continue without full dependency check? [y/N]: {self.colors['ENDC']}"
            ).lower()
            return basic_check and response == "y"

    def _check_basic_dependencies(self) -> bool:
        """Check basic Python and system dependencies"""
        print(f"\n{self.colors['BOLD']}Checking Python environment...{self.colors['ENDC']}")

        # Check core Python modules (these should always be available)
        required_modules = ["pathlib", "json", "sqlite3", "subprocess"]
        missing_required = []

        for module in required_modules:
            try:
                __import__(module)
            except ImportError:
                missing_required.append(module)
                self.print_status(f"Python module '{module}' missing", "error")

        if missing_required:
            print(f"\n{self.colors['RED']}Critical Python modules missing: {', '.join(missing_required)}{self.colors['ENDC']}")
            print(f"{self.colors['RED']}Your Python installation may be incomplete.{self.colors['ENDC']}")
            return False

        self.print_status("Python environment ready", "success")
        return True

    def _check_integrated_dependencies(self) -> bool:
        """Check installer components availability"""
        try:
            # Just check if key installer components are available
            print(f"\n{self.colors['BOLD']}Checking installer components...{self.colors['ENDC']}")

            # Check critical components only
            critical_components = {
                "config_manager": "installer.config.config_manager.ConfigurationManager",
                "service_manager": "installer.services.service_manager.ServiceManager"
            }

            missing = []
            for name, module_path in critical_components.items():
                try:
                    module_name, class_name = module_path.rsplit(".", 1)
                    module = __import__(module_name, fromlist=[class_name])
                except ImportError:
                    missing.append(name)

            if missing:
                self.print_status(f"Some installer components missing: {', '.join(missing)}", "warning")
                # Not critical - can continue
            else:
                self.print_status("Installer components ready", "success")

            return True

        except ImportError as e:
            self.print_status(f"Health checker not available: {e}", "warning")
            return True

    def run(self) -> int:
        """Main bootstrap execution"""
        self.print_header()

        # Check Python version first
        if not self.check_python_version():
            print(f"\n{self.colors['RED']}Please install Python 3.8 or higher and try again.{self.colors['ENDC']}")
            print(f"Download from: {self.colors['BLUE']}https://www.python.org/downloads/{self.colors['ENDC']}")
            return 1

        # Print system information
        self.print_system_info()

        # Check for existing installation
        existing = self.check_existing_installation()
        if existing:
            self.print_status(f"Existing installation detected at: {existing['path']}", "warning")
            print(f"Found: {', '.join(existing['markers'])}")
            response = input(
                f"\n{self.colors['YELLOW']}Continue with reinstall/upgrade? [y/N]: {self.colors['ENDC']}"
            ).lower()
            if response != "y":
                self.print_status("Installation cancelled", "info")
                return 0

        # Run dependency check
        if not self.check_dependencies():
            self.print_status("Installation cancelled due to dependency issues", "info")
            return 1

        # Check GUI capability
        self.has_gui = self.check_gui_capability()

        # Determine installer to use
        if self.has_gui:
            choice = self.prompt_installer_choice()

            if choice == "1":
                return self.launch_gui_installer()
            if choice == "2":
                return self.launch_cli_installer()
            self.print_status("Installation cancelled", "info")
            return 0
        self.print_status("Running in CLI mode", "info")
        return self.launch_cli_installer()


def main():
    """Main entry point"""
    try:
        bootstrap = Bootstrap()
        return bootstrap.run()
    except KeyboardInterrupt:
        print("\n\nInstallation cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n[X] Unexpected error: {e}")
        print("\nPlease report this issue at:")
        print("https://github.com/yourusername/giljo-mcp/issues")
        return 1


if __name__ == "__main__":
    sys.exit(main())
