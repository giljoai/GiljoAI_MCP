#!/usr/bin/env python3
"""
GiljoAI MCP CLI Setup - Enhanced ASCII Art Terminal Interface
PostgreSQL-only installation with beautiful terminal UI
"""

import os
import sys
import time
import shutil
import subprocess
import socket
import json
import logging
from pathlib import Path
from typing import Optional, Tuple, List, Dict
from datetime import datetime
from setup import GiljoSetup, check_port

# ASCII Art Components
GILJO_LOGO = """[..]GiljoAI
MCP Orchestrator v0.2 Beta"""

POSTGRES_ELEPHANT = r"""
     ____
    /    \
   | o  o |    PostgreSQL
    \  <  /    The World's Most
     |==|      Advanced Open Source
    /|  |\     Relational Database
   (_|  |_)
"""

class InstallationLogger:
    """Logger for installation process with timestamped file output"""

    def __init__(self, log_dir="install_logs"):
        """Initialize logger with timestamp-based log file"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"cli_install_{timestamp}.log"

        # Write header
        self.write("="*70, raw=True)
        self.write(f"GiljoAI MCP CLI Installation Log", raw=True)
        self.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", raw=True)
        self.write("="*70, raw=True)
        self.write("")

    def write(self, message, level="INFO", raw=False):
        """Write message to log file with timestamp and level"""
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                if raw:
                    # Write without timestamp for headers/separators
                    f.write(f"{message}\n")
                else:
                    # Include milliseconds for precise timing
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
                    f.write(f"[{timestamp}] [{level:7s}] {message}\n")
                f.flush()  # Ensure immediate write
        except Exception:
            # Silently fail if logging fails (don't interrupt installation)
            pass

    def close(self):
        """Write closing message to log"""
        self.write("")
        self.write("="*70, raw=True)
        self.write(f"Installation completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", raw=True)
        self.write("="*70, raw=True)


class TerminalUI:
    """Enhanced terminal UI with ASCII art and formatting"""

    def __init__(self):
        self.term_width = shutil.get_terminal_size().columns
        self.term_height = shutil.get_terminal_size().lines

        # ANSI color codes
        self.COLORS = {
            'RESET': '\033[0m',
            'BOLD': '\033[1m',
            'RED': '\033[91m',
            'GREEN': '\033[92m',
            'YELLOW': '\033[33m',  # Dark yellow/gold
            'BLUE': '\033[94m',
            'MAGENTA': '\033[95m',
            'CYAN': '\033[96m',
            'WHITE': '\033[97m',
            'GRAY': '\033[90m',
        }

        # Check if terminal supports colors
        self.use_colors = sys.stdout.isatty() and os.name != 'nt'
        if os.name == 'nt':
            try:
                import colorama
                colorama.init()
                self.use_colors = True
            except ImportError:
                pass

    def color(self, text: str, color: str) -> str:
        """Apply color to text if supported"""
        if self.use_colors and color in self.COLORS:
            return f"{self.COLORS[color]}{text}{self.COLORS['RESET']}"
        return text

    def clear_screen(self):
        """Clear the terminal screen"""
        # Print newlines to simulate clearing screen (safer than shell commands)
        print('\n' * self.term_height)

    def draw_box(self, content: List[str], title: str = "", width: Optional[int] = None) -> List[str]:
        """Draw a box around content"""
        if width is None:
            width = max(len(line) for line in content) + 4

        box = []

        # Top border
        if title:
            title_str = f" {title} "
            padding = (width - len(title_str) - 2) // 2
            top = "╔" + "═" * padding + title_str + "═" * (width - padding - len(title_str) - 2) + "╗"
        else:
            top = "╔" + "═" * (width - 2) + "╗"
        box.append(top)

        # Content
        for line in content:
            padding = width - len(line) - 4
            box.append(f"║ {line}{' ' * padding} ║")

        # Bottom border
        box.append("╚" + "═" * (width - 2) + "╝")

        return box

    def center_text(self, text: str, width: Optional[int] = None) -> str:
        """Center text within given width"""
        if width is None:
            width = self.term_width
        return text.center(width)

    def print_centered(self, text: str):
        """Print text centered on screen"""
        print(self.center_text(text))

    def progress_bar(self, current: int, total: int, width: int = 50, label: str = "") -> str:
        """Create an ASCII progress bar"""
        percent = current / total if total > 0 else 0
        filled = int(width * percent)
        bar = "█" * filled + "░" * (width - filled)

        if label:
            return f"{label}: [{bar}] {percent*100:.1f}%"
        return f"[{bar}] {percent*100:.1f}%"

    def animated_dots(self, message: str, duration: float = 3.0):
        """Show animated dots for loading effect"""
        import itertools
        import threading

        done = False
        def animate():
            for c in itertools.cycle(['   ', '.  ', '.. ', '...']):
                if done:
                    break
                print(f'\r{message}{c}', end='', flush=True)
                time.sleep(0.5)

        t = threading.Thread(target=animate)
        t.daemon = True
        t.start()
        time.sleep(duration)
        done = True
        print(f'\r{message}... Done!', flush=True)


class PostgreSQLDetector:
    """Handle PostgreSQL detection and configuration"""

    def __init__(self, ui: TerminalUI, logger: InstallationLogger):
        self.ui = ui
        self.logger = logger
        self.pg_detected = False
        self.detection_details = {}

    def detect_postgresql(self) -> Tuple[bool, Dict]:
        """
        Comprehensive PostgreSQL detection
        Returns: (is_detected, details_dict)
        """
        self.logger.write("Starting PostgreSQL detection", "INFO")
        details = {
            'psql_command': False,
            'registry': False,
            'service_running': False,
            'port_open': False,
            'version': None,
            'install_dir': None
        }

        # 1. Check psql command
        try:
            result = subprocess.run(
                ["psql", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                details['psql_command'] = True
                details['version'] = result.stdout.strip()
                self.logger.write(f"Found psql command: {details['version']}", "INFO")
        except (FileNotFoundError, subprocess.TimeoutExpired):
            self.logger.write("psql command not found in PATH", "DEBUG")

        # 2. Windows Registry check
        if sys.platform == "win32":
            try:
                import winreg
                key_path = r"SOFTWARE\PostgreSQL\Installations"
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                    i = 0
                    while True:
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            details['registry'] = True

                            # Try to get installation directory
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    install_dir, _ = winreg.QueryValueEx(subkey, "Base Directory")
                                    details['install_dir'] = install_dir
                                    self.logger.write(f"Found PostgreSQL in registry at: {install_dir}", "INFO")
                                except WindowsError:
                                    pass
                            break
                        except OSError:
                            break
                        i += 1
            except Exception as e:
                self.logger.write(f"Registry check failed: {e}", "DEBUG")

        # 3. Check if PostgreSQL service is running (Windows)
        if sys.platform == "win32":
            try:
                result = subprocess.run(
                    ["sc", "query", "postgresql-x64-18"],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if "RUNNING" in result.stdout:
                    details['service_running'] = True
                    self.logger.write("PostgreSQL service is running", "INFO")
            except Exception:
                pass

        # 4. Check port 5432
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("localhost", 5432))
            sock.close()
            if result == 0:
                details['port_open'] = True
                self.logger.write("PostgreSQL port 5432 is open", "INFO")
        except Exception as e:
            self.logger.write(f"Port check failed: {e}", "DEBUG")

        # Determine if PostgreSQL is detected
        is_detected = any([
            details['psql_command'],
            details['registry'],
            details['service_running'],
            details['port_open']
        ])

        self.logger.write(f"PostgreSQL detection result: {is_detected}", "INFO")
        self.logger.write(f"Detection details: {json.dumps(details, indent=2)}", "DEBUG")

        return is_detected, details

    def test_connection(self, config: dict) -> bool:
        """Test PostgreSQL connection with given credentials"""
        self.logger.write(f"Testing PostgreSQL connection to {config['pg_host']}:{config['pg_port']}", "INFO")
        try:
            import psycopg2
            conn = psycopg2.connect(
                host=config['pg_host'],
                port=config['pg_port'],
                database='postgres',  # Connect to default DB first
                user=config['pg_user'],
                password=config['pg_password'],
                connect_timeout=5
            )
            conn.close()
            self.logger.write("PostgreSQL connection successful", "INFO")
            return True
        except Exception as e:
            self.logger.write(f"PostgreSQL connection failed: {e}", "ERROR")
            return False


class GiljoCLISetup(GiljoSetup):
    """Enhanced CLI setup with ASCII UI aligned to GUI workflow"""

    def __init__(self):
        super().__init__()
        self.ui = TerminalUI()
        self.logger = InstallationLogger()
        self.pg_detector = PostgreSQLDetector(self.ui, self.logger)
        self.collected_config = {}  # Store all configuration upfront

    def run(self):
        """Run the enhanced CLI setup following GUI workflow"""
        self.ui.clear_screen()

        # Phase 1: System Readiness Check
        self.logger.write("Phase 1: System Readiness Check", "INFO")
        self.show_welcome()

        # Check Python version
        if not self.check_python_version():
            print(self.ui.color("✗ Python 3.10+ required", "RED"))
            self.logger.write("Python version check failed", "ERROR")
            sys.exit(1)

        # Check disk space and permissions
        if not self.check_system_requirements():
            sys.exit(1)

        # Phase 2: Configuration Collection (All Upfront)
        self.logger.write("Phase 2: Configuration Collection", "INFO")
        if not self.collect_all_configuration():
            print(self.ui.color("✗ Configuration cancelled", "RED"))
            self.logger.write("Configuration cancelled by user", "INFO")
            sys.exit(0)

        # Phase 3: PostgreSQL Installation Guidance
        self.logger.write("Phase 3: PostgreSQL Setup", "INFO")
        if not self.setup_postgresql():
            print(self.ui.color("✗ PostgreSQL setup failed", "RED"))
            self.logger.write("PostgreSQL setup failed", "ERROR")
            sys.exit(1)

        # Phase 4: Installation Summary Review
        self.logger.write("Phase 4: Configuration Review", "INFO")
        if not self.review_configuration():
            print(self.ui.color("✗ Installation cancelled", "RED"))
            self.logger.write("Installation cancelled at review", "INFO")
            sys.exit(0)

        # Phase 5: Full Installation Execution
        self.logger.write("Phase 5: Installation Execution", "INFO")
        self.run_installation()

        # Phase 6: Diagnostic Report
        self.logger.write("Phase 6: Diagnostic Report", "INFO")
        self.show_diagnostic_report()

        # Close logger
        self.logger.close()

    def check_system_requirements(self) -> bool:
        """Check disk space and write permissions"""
        self.logger.write("Checking system requirements", "INFO")

        # Check disk space (require at least 500MB)
        try:
            if sys.platform == "win32":
                import shutil
                stat = shutil.disk_usage(Path.cwd())
                free_mb = stat.free / (1024 * 1024)
                if free_mb < 500:
                    print(self.ui.color(f"✗ Insufficient disk space: {free_mb:.1f}MB (need 500MB)", "RED"))
                    self.logger.write(f"Insufficient disk space: {free_mb:.1f}MB", "ERROR")
                    return False
                print(self.ui.color(f"✓ Disk space available: {free_mb:.1f}MB", "GREEN"))
        except Exception as e:
            self.logger.write(f"Disk space check failed: {e}", "WARNING")

        # Check write permissions
        try:
            test_file = Path("test_write_permission.tmp")
            test_file.write_text("test")
            test_file.unlink()
            print(self.ui.color("✓ Write permissions confirmed", "GREEN"))
            self.logger.write("Write permissions confirmed", "INFO")
        except Exception as e:
            print(self.ui.color(f"✗ No write permissions in current directory", "RED"))
            self.logger.write(f"Write permission check failed: {e}", "ERROR")
            return False

        return True

    def collect_all_configuration(self) -> bool:
        """Collect all configuration upfront before any installation"""
        self.ui.clear_screen()
        self.ui.print_centered(self.ui.color("Configuration Setup", "BOLD"))
        print("\n")

        # Deployment mode selection
        deployment_mode = self.select_deployment_mode()
        if deployment_mode == "exit":
            return False
        self.collected_config['deployment_mode'] = deployment_mode
        self.deployment_mode = deployment_mode

        # PostgreSQL configuration
        print("\n")
        self.ui.print_centered(self.ui.color("PostgreSQL Configuration", "CYAN"))
        print("\n")

        pg_fields = [
            ("Username", "pg_user", "postgres"),
            ("Password", "pg_password", ""),
            ("Port", "pg_port", "5432"),
            ("Database", "pg_database", "giljo_mcp"),
        ]

        for label, key, default in pg_fields:
            if key == "pg_password":
                # Special handling for password
                prompt = f"{label}: "
                import getpass
                try:
                    print(self.ui.center_text(prompt), end='', flush=True)
                    value = getpass.getpass('')
                except KeyboardInterrupt:
                    return False
                self.collected_config[key] = value
                if value:
                    display_val = "*" * len(value)
                    print(self.ui.center_text(self.ui.color(f"  ✓ {label}: {display_val}", "GREEN")))
            else:
                prompt = f"{label} [{default}]: " if default else f"{label}: "
                print(self.ui.center_text(prompt), end='', flush=True)
                value = input().strip()
                self.collected_config[key] = value if value else default
                print(self.ui.center_text(self.ui.color(f"  ✓ {label}: {self.collected_config[key]}", "GREEN")))

        # Always localhost for PostgreSQL host
        self.collected_config['pg_host'] = 'localhost'

        # Server port selection
        print("\n")
        available_port = self.find_available_port()
        if available_port:
            prompt = f"Server Port [{available_port}]: "
            print(self.ui.center_text(prompt), end='', flush=True)
            port_input = input().strip()
            if port_input:
                try:
                    port = int(port_input)
                    if check_port(port):
                        print(self.ui.color(f"✗ Port {port} is already in use", "RED"))
                        return False
                    self.server_port = port
                except ValueError:
                    print(self.ui.color("✗ Invalid port number", "RED"))
                    return False
            else:
                self.server_port = available_port
        else:
            print(self.ui.color("✗ No available ports found", "RED"))
            return False

        self.collected_config['server_port'] = self.server_port
        print(self.ui.center_text(self.ui.color(f"  ✓ Server Port: {self.server_port}", "GREEN")))

        # If server mode, collect additional configuration
        if deployment_mode.lower() == "server":
            print("\n")
            self.ui.print_centered(self.ui.color("Server Mode Configuration", "CYAN"))
            print("\n")

            # API Key
            prompt = "API Key (press Enter to auto-generate): "
            print(self.ui.center_text(prompt), end='', flush=True)
            api_key = input().strip()
            if not api_key:
                import secrets
                api_key = secrets.token_urlsafe(32)
                print(self.ui.color(f"  ✓ Generated API Key: {api_key}", "YELLOW"))
            self.collected_config['api_key'] = api_key

            # CORS Origins
            prompt = "\nCORS Allowed Origins (comma-separated, Enter for defaults): "
            print(self.ui.center_text(prompt), end='', flush=True)
            cors_input = input().strip()
            if cors_input:
                self.collected_config['cors_origins'] = [o.strip() for o in cors_input.split(',')]
            else:
                self.collected_config['cors_origins'] = ["http://localhost:*", "http://127.0.0.1:*"]

            # Network binding
            print("\nNetwork Binding:")
            print("  1) Localhost only (127.0.0.1)")
            print("  2) All interfaces (0.0.0.0)")
            prompt = "Choice [1]: "
            print(self.ui.center_text(prompt), end='', flush=True)
            binding_choice = input().strip()
            if binding_choice == "2":
                self.collected_config['bind_host'] = "0.0.0.0"
                print(self.ui.color("  ⚠ Warning: Server will be accessible from network", "YELLOW"))
            else:
                self.collected_config['bind_host'] = "127.0.0.1"

        self.logger.write(f"Configuration collected: {json.dumps(self.collected_config, indent=2)}", "INFO")
        return True

    def setup_postgresql(self) -> bool:
        """Handle PostgreSQL detection and setup"""
        self.ui.clear_screen()
        self.ui.print_centered(self.ui.color("PostgreSQL Setup", "BOLD"))
        print("\n")

        # Detect PostgreSQL
        print("Checking for existing PostgreSQL installation...")
        is_detected, details = self.pg_detector.detect_postgresql()

        if is_detected:
            # PostgreSQL detected
            print("\n")
            print(self.ui.color("✓ PostgreSQL detected on your system", "GREEN"))

            if details.get('version'):
                print(f"  Version: {details['version']}")
            if details.get('install_dir'):
                print(f"  Location: {details['install_dir']}")
            if details.get('port_open'):
                print(f"  Port 5432: Open")

            print("\n")
            print("Testing connection with your credentials...")

            # Test connection with collected credentials
            if self.pg_detector.test_connection(self.collected_config):
                print(self.ui.color("✓ PostgreSQL connection successful!", "GREEN"))
                self.collected_config['pg_configured'] = True
                time.sleep(2)
                return True
            else:
                # Connection failed
                print(self.ui.color("✗ Could not connect to PostgreSQL", "RED"))
                print("\nPossible issues:")
                print("  1. PostgreSQL service is not running")
                print("  2. Credentials are incorrect")
                print("  3. Database server is not accepting connections")
                print("\nOptions:")
                print("  1) Retry with same credentials")
                print("  2) Re-enter credentials")
                print("  3) Exit setup")

                prompt = "\nChoice [1-3]: "
                print(prompt, end='', flush=True)
                choice = input().strip()
                if choice == "1":
                    return self.setup_postgresql()  # Retry
                elif choice == "2":
                    # Re-collect PostgreSQL credentials only
                    return self.recollect_pg_credentials() and self.setup_postgresql()
                else:
                    return False
        else:
            # PostgreSQL not detected
            print(self.ui.color("✗ PostgreSQL not detected on your system", "YELLOW"))
            print("\n")

            # Show PostgreSQL elephant art
            for line in POSTGRES_ELEPHANT.split('\n'):
                self.ui.print_centered(self.ui.color(line, "BLUE"))

            print("\n")
            print(self.ui.color("PostgreSQL Installation Required", "BOLD"))
            print("\n")

            # Display the credentials user will need during PostgreSQL installation
            credentials_box = self.ui.draw_box([
                "Install PostgreSQL with these settings:",
                "",
                f"Username: {self.collected_config['pg_user']}",
                f"Password: {'*' * len(self.collected_config['pg_password']) if self.collected_config['pg_password'] else '(set one)'}",
                f"Port: {self.collected_config['pg_port']}",
                "",
                "Remember these settings!",
                "You'll need them during PostgreSQL installation."
            ], "Your PostgreSQL Settings", 50)

            for line in credentials_box:
                self.ui.print_centered(line)

            print("\n")
            print(self.ui.color("Installation Instructions:", "CYAN"))
            print("1. Download PostgreSQL from: https://www.postgresql.org/download/")
            print("2. Run the installer")
            print("3. Use the settings shown above during installation")
            print("4. Complete the installation")
            print("5. Return here and press ENTER")

            print("\n")
            prompt = "Press ENTER after PostgreSQL installation is complete..."
            print(self.ui.center_text(prompt), end='', flush=True)
            input()

            # Re-check after user installs
            print("\nVerifying PostgreSQL installation...")
            return self.setup_postgresql()  # Recursive call to re-check

    def recollect_pg_credentials(self) -> bool:
        """Re-collect PostgreSQL credentials"""
        print("\n")
        self.ui.print_centered(self.ui.color("Re-enter PostgreSQL Credentials", "CYAN"))
        print("\n")

        pg_fields = [
            ("Username", "pg_user", self.collected_config.get('pg_user', 'postgres')),
            ("Password", "pg_password", ""),
            ("Port", "pg_port", self.collected_config.get('pg_port', '5432')),
            ("Database", "pg_database", self.collected_config.get('pg_database', 'giljo_mcp')),
        ]

        for label, key, default in pg_fields:
            if key == "pg_password":
                prompt = f"{label}: "
                import getpass
                try:
                    print(self.ui.center_text(prompt), end='', flush=True)
                    value = getpass.getpass('')
                except KeyboardInterrupt:
                    return False
                self.collected_config[key] = value
            else:
                prompt = f"{label} [{default}]: "
                print(self.ui.center_text(prompt), end='', flush=True)
                value = input().strip()
                self.collected_config[key] = value if value else default

        return True

    def review_configuration(self) -> bool:
        """Display configuration review before installation"""
        self.ui.clear_screen()
        self.ui.print_centered(self.ui.color("Installation Summary", "BOLD"))
        print("\n")

        # Build configuration summary
        config_lines = [
            "Configuration to be installed:",
            "",
            f"Deployment Mode: {self.collected_config['deployment_mode']}",
            f"Server Port: {self.collected_config['server_port']}",
            "",
            "PostgreSQL Configuration:",
            f"  Host: localhost",
            f"  Port: {self.collected_config['pg_port']}",
            f"  Database: {self.collected_config['pg_database']}",
            f"  Username: {self.collected_config['pg_user']}",
            f"  Password: {'*' * len(self.collected_config['pg_password']) if self.collected_config['pg_password'] else '(not set)'}",
        ]

        if self.collected_config['deployment_mode'].lower() == 'server':
            config_lines.extend([
                "",
                "Server Mode Settings:",
                f"  API Key: {self.collected_config.get('api_key', 'Will be generated')}",
                f"  Network Binding: {self.collected_config.get('bind_host', '127.0.0.1')}",
                f"  CORS Origins: {', '.join(self.collected_config.get('cors_origins', []))}",
            ])

        config_lines.extend([
            "",
            "What will be installed:",
            "  • Python dependencies",
            "  • Database schema",
            "  • Configuration files",
            "  • Project structure",
        ])

        summary_box = self.ui.draw_box(config_lines, "Review Configuration", 65)

        for line in summary_box:
            self.ui.print_centered(line)

        print("\n")
        print(self.ui.color("Options:", "CYAN"))
        print("  1) Continue with installation")
        print("  2) Modify configuration")
        print("  3) Cancel installation")
        print("\n")

        prompt = "Choice [1-3]: "
        print(self.ui.center_text(prompt), end='', flush=True)
        choice = input().strip()

        if choice == "1":
            # Update main config with collected values
            self.config.update(self.collected_config)
            self.config['database_type'] = 'postgresql'
            return True
        elif choice == "2":
            # Go back to configuration collection
            if self.collect_all_configuration():
                return self.review_configuration()
            return False
        else:
            return False

    def select_deployment_mode(self) -> str:
        """Select deployment mode with standardized naming"""
        self.ui.clear_screen()

        self.ui.print_centered(self.ui.color("Select Deployment Mode", "BOLD"))
        print("\n")

        modes_box = self.ui.draw_box([
            "1) Localhost Development",
            "   • Single user",
            "   • Localhost only",
            "   • No authentication",
            "",
            "2) Server Deployment",
            "   • Multi-user",
            "   • Network accessible",
            "   • API key authentication",
            "",
            "3) Exit Setup",
        ], "Deployment Modes", 50)

        for line in modes_box:
            self.ui.print_centered(line)

        print("\n")
        prompt = "Enter your choice (1-3): "
        print(self.ui.center_text(prompt), end='', flush=True)
        choice = input().strip()

        if choice == "1":
            return "localhost"  # Standardized naming
        elif choice == "2":
            return "server"  # Standardized naming
        else:
            return "exit"

    def find_available_port(self) -> Optional[int]:
        """Find an available port for the server"""
        preferred = 7272
        alternatives = [7273, 7274, 8000, 8080, 8747, 8823, 9456]

        if not check_port(preferred):
            return preferred

        for port in alternatives:
            if not check_port(port):
                return port

        return None

    def run_installation(self):
        """Run the installation with progress display"""
        self.ui.clear_screen()

        self.ui.print_centered(self.ui.color("Installing GiljoAI MCP", "BOLD"))
        print("\n")

        steps = [
            ("Creating virtual environment", self.create_venv),
            ("Installing dependencies", self.install_requirements_with_progress),
            ("Creating database", self.create_database),
            ("Creating configuration", self.create_config_file),
            ("Setting up directories", self.create_directories),
            ("Creating installation manifest", self.create_installation_manifest),
        ]

        total_steps = len(steps)
        for i, (label, func) in enumerate(steps, 1):
            print(f"\n{self.ui.color(f'[{i}/{total_steps}]', 'CYAN')} {label}")
            self.logger.write(f"Starting: {label}", "INFO")

            # Run the actual function
            success = func()

            if success:
                print(f'{self.ui.color("✓ Complete", "GREEN")}')
                self.logger.write(f"Completed: {label}", "INFO")
            else:
                print(f'{self.ui.color("✗ Failed", "RED")}')
                self.logger.write(f"Failed: {label}", "ERROR")
                print(self.ui.color(f"Failed: {label}", "RED"))
                print(f"\nCheck log file for details: {self.logger.log_file}")
                sys.exit(1)

    def install_requirements_with_progress(self) -> bool:
        """Install Python requirements with package-level progress tracking"""
        try:
            # Read requirements file to get package count
            req_file = Path("requirements.txt")
            if not req_file.exists():
                self.logger.write("requirements.txt not found", "ERROR")
                return False

            requirements = req_file.read_text().strip().split('\n')
            # Filter out comments and empty lines
            packages = [r.strip() for r in requirements if r.strip() and not r.strip().startswith('#')]
            total_packages = len(packages)

            self.logger.write(f"Installing {total_packages} packages", "INFO")

            # Install packages with progress tracking
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            current_package = 0
            for line in process.stdout:
                line = line.strip()
                if line:
                    self.logger.write(f"pip: {line}", "DEBUG")

                    # Track progress
                    if "Collecting" in line or "Requirement already satisfied" in line:
                        current_package += 1
                        package_name = self.extract_package_name(line)
                        if package_name:
                            progress = int((current_package / total_packages) * 100)
                            print(f'\r  {self.ui.progress_bar(current_package, total_packages, 40, f"Installing packages")}', end='', flush=True)

            process.wait()
            print()  # New line after progress bar

            if process.returncode != 0:
                self.logger.write("pip install failed", "ERROR")
                return False

            self.logger.write("All packages installed successfully", "INFO")
            return True

        except Exception as e:
            self.logger.write(f"Error installing requirements: {e}", "ERROR")
            return False

    def extract_package_name(self, line: str) -> str:
        """Extract package name from pip output line"""
        if "Collecting" in line:
            parts = line.split("Collecting", 1)
            if len(parts) > 1:
                package_part = parts[1].strip()
                # Remove version specifiers
                for sep in ['>=', '<=', '==', '>', '<', '[', '(', ' ']:
                    if sep in package_part:
                        package_part = package_part.split(sep)[0]
                return package_part.strip()
        elif "Requirement already satisfied" in line:
            parts = line.split(":", 1)
            if len(parts) > 1:
                package_part = parts[1].strip()
                for sep in ['>=', '<=', '==', '>', '<', '[', '(', ' ', 'in']:
                    if sep in package_part:
                        package_part = package_part.split(sep)[0]
                return package_part.strip()
        return ""

    def create_database(self) -> bool:
        """Create PostgreSQL database"""
        try:
            import psycopg2
            from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

            # Connect to postgres database to create our database
            conn = psycopg2.connect(
                host=self.config['pg_host'],
                port=self.config['pg_port'],
                database='postgres',
                user=self.config['pg_user'],
                password=self.config['pg_password']
            )
            conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
            cursor = conn.cursor()

            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.config['pg_database'],)
            )

            if not cursor.fetchone():
                cursor.execute(f"CREATE DATABASE {self.config['pg_database']}")
                self.logger.write(f"Created database: {self.config['pg_database']}", "INFO")
            else:
                self.logger.write(f"Database already exists: {self.config['pg_database']}", "INFO")

            cursor.close()
            conn.close()
            return True

        except Exception as e:
            self.logger.write(f"Error creating database: {e}", "ERROR")
            return False

    def create_installation_manifest(self) -> bool:
        """Create installation manifest for uninstaller"""
        try:
            # Get list of installed Python packages
            installed_packages = []
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "freeze"],
                    capture_output=True,
                    text=True
                )
                if result.returncode == 0:
                    installed_packages = result.stdout.strip().split('\n')
            except:
                pass

            manifest = {
                "version": "0.2-beta",
                "installation_date": datetime.now().isoformat(),
                "installation_type": "cli",
                "deployment_mode": self.deployment_mode,
                "install_directory": str(Path.cwd()),
                "postgresql": {
                    "installed": False,  # We don't auto-install PostgreSQL
                    "host": self.config.get('pg_host', 'localhost'),
                    "port": self.config.get('pg_port', '5432'),
                    "database": self.config.get('pg_database', 'giljo_mcp'),
                    "user": self.config.get('pg_user', 'postgres'),
                },
                "dependencies": {
                    "postgresql": {
                        "installed": False,
                        "location": None,
                        "service_name": "postgresql-x64-18" if sys.platform == "win32" else "postgresql"
                    },
                    "python_packages": installed_packages
                },
                "configuration": {
                    "database_type": "postgresql",
                    "ports": {
                        "api": self.server_port,
                    }
                },
                "directories_created": [
                    "venv", "data", "logs", "backups",
                    ".giljo_mcp", ".giljo-config", "install_logs"
                ],
                "config_files_created": [
                    ".env", "config.yaml"
                ],
                "log_file": str(self.logger.log_file)
            }

            manifest_path = Path(".giljo_install_manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            self.logger.write(f"Created installation manifest: {manifest_path}", "INFO")
            return True

        except Exception as e:
            self.logger.write(f"Warning: Could not create manifest: {e}", "WARNING")
            return True  # Don't fail installation

    def show_diagnostic_report(self):
        """Show final diagnostic report"""
        self.ui.clear_screen()

        # Check if installation succeeded
        success = self.verify_installation()

        if success:
            # Success banner
            success_art = r"""
         _____ _    _  _____ _____ ______  _____ _____ _
        / ____| |  | |/ ____/ ____|  ____|/ ____/ ____| |
       | (___ | |  | | |   | |    | |__  | (___| (___ | |
        \___ \| |  | | |   | |    |  __|  \___ \\___ \| |
        ____) | |__| | |___| |____| |____ ____) |___) |_|
       |_____/ \____/ \_____\_____|______|_____/_____/(_)
        """

            for line in success_art.split('\n'):
                self.ui.print_centered(self.ui.color(line, "GREEN"))

            print("\n")
            self.ui.print_centered(self.ui.color("Installation Complete!", "BOLD"))
            print("\n")

            # Configuration summary
            summary_lines = [
                f"Server Port: {self.server_port}",
                f"Deployment: {self.deployment_mode}",
                f"Database: PostgreSQL",
                f"Host: {self.config.get('pg_host', 'localhost')}:{self.config.get('pg_port', '5432')}",
                "",
                "Next Steps:",
                "1. Register AI tools: python register_ai_tools.py",
                "2. Read integration guide: docs/AI_TOOL_INTEGRATION.md",
                "3. Start server: python -m giljo_mcp",
                f"4. Access dashboard: http://localhost:{self.server_port}",
            ]

            if self.deployment_mode.lower() == "server":
                summary_lines.extend([
                    "",
                    f"API Key: {self.config.get('api_key', 'Check config.yaml')}",
                    "Save this key - you'll need it for remote connections",
                ])

            summary_lines.extend([
                "",
                f"Installation log: {self.logger.log_file}",
            ])

            summary_box = self.ui.draw_box(summary_lines, "Installation Summary", 65)

            for line in summary_box:
                self.ui.print_centered(line)
        else:
            # Failure report
            print(self.ui.color("Installation encountered issues", "RED"))
            print("\n")
            print("Diagnostic Information:")
            print(f"  • Installation log: {self.logger.log_file}")
            print(f"  • Current directory: {Path.cwd()}")
            print("\n")
            print("Suggested Actions:")
            print("  1. Review the installation log for error details")
            print("  2. Ensure PostgreSQL is properly installed and running")
            print("  3. Verify you have write permissions in current directory")
            print("  4. Check that required ports are not in use")
            print("\n")
            print("For help, visit: https://github.com/Giljo/GiljoAI_MCP/issues")

        print("\n")
        prompt = "Press Enter to exit..."
        print(self.ui.center_text(prompt), end='', flush=True)
        input()

    def verify_installation(self) -> bool:
        """Verify that installation completed successfully"""
        try:
            # Check critical files exist
            critical_files = [
                Path(".env"),
                Path("config.yaml"),
                Path(".giljo_install_manifest.json")
            ]

            for file in critical_files:
                if not file.exists():
                    self.logger.write(f"Critical file missing: {file}", "ERROR")
                    return False

            # Check PostgreSQL connection
            if not self.pg_detector.test_connection(self.config):
                self.logger.write("PostgreSQL connection verification failed", "ERROR")
                return False

            self.logger.write("Installation verification successful", "INFO")
            return True

        except Exception as e:
            self.logger.write(f"Installation verification error: {e}", "ERROR")
            return False

    def show_welcome(self):
        """Show welcome screen with simplified logo"""
        for line in GILJO_LOGO.split('\n'):
            self.ui.print_centered(self.ui.color(line, "YELLOW"))

        print("\n")
        self.ui.print_centered(self.ui.color("Welcome to GiljoAI MCP Setup", "BOLD"))
        self.ui.print_centered("Multi-Agent Orchestration System")
        print("\n")

        features_box = self.ui.draw_box([
            "✓ Multi-agent orchestration",
            "✓ PostgreSQL database",
            "✓ HTTP/WebSocket APIs",
            "✓ Real-time monitoring",
            "✓ Claude integration",
        ], "Key Features", 40)

        for line in features_box:
            self.ui.print_centered(line)

        print("\n")
        prompt = "Press Enter to continue..."
        print(self.ui.center_text(prompt), end='', flush=True)
        input()


if __name__ == "__main__":
    setup = GiljoCLISetup()
    setup.run()
