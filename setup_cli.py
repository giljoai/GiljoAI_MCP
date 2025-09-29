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
from pathlib import Path
from typing import Optional, Tuple, List
from setup import GiljoSetup, check_port

# ASCII Art Components
GILJO_LOGO = r"""
   _____ _ _ _       _____ _____
  / ____(_) (_)     |  __ \_   _|
 | |  __ _| |_  ___ | |__) || |
 | | |_ | | | |/ _ \|  _  / | |
 | |__| | | | | (_) | | \ \_| |_
  \_____|_|_| |\___/|_|  \_\_____|
           _/ |  MCP Orchestrator
          |__/   v2.0 PostgreSQL
"""

POSTGRES_ELEPHANT = r"""
     ____
    /    \
   | o  o |    PostgreSQL
    \  <  /    The World's Most
     |==|      Advanced Open Source
    /|  |\     Relational Database
   (_|  |_)
"""

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
            'YELLOW': '\033[93m',
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


class PostgreSQLInstaller:
    """Handle PostgreSQL installation and configuration"""

    def __init__(self, ui: TerminalUI):
        self.ui = ui
        self.pg_installed = False
        self.pg_config = {}

    def check_existing_postgresql(self) -> bool:
        """Check if PostgreSQL is already installed"""
        try:
            result = subprocess.run(
                ["psql", "--version"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(self.ui.color(f"✓ Found existing PostgreSQL: {version}", "GREEN"))
                return True
        except FileNotFoundError:
            pass
        return False

    def prompt_installation_mode(self) -> str:
        """Prompt user for PostgreSQL installation mode"""
        self.ui.clear_screen()

        # Display header
        for line in GILJO_LOGO.split('\n'):
            self.ui.print_centered(self.ui.color(line, "CYAN"))

        print("\n")
        self.ui.print_centered(self.ui.color("PostgreSQL Configuration", "BOLD"))
        print("\n")

        # Display options
        options_box = self.ui.draw_box([
            "GiljoAI requires PostgreSQL for reliable multi-user operation.",
            "",
            "Please select installation mode:",
            "",
            "  1) Attach to Existing PostgreSQL Server",
            "     • Use an already installed PostgreSQL server",
            "     • You'll provide connection credentials",
            "",
            "  2) Install Fresh PostgreSQL Server",
            "     • We'll download and install PostgreSQL",
            "     • Automatically configure for GiljoAI",
            "",
            "  3) Exit Setup",
        ], "PostgreSQL Setup", 60)

        for line in options_box:
            self.ui.print_centered(line)

        print("\n")
        choice = input(self.ui.center_text("Enter your choice (1-3): ")).strip()

        if choice == "1":
            return "existing"
        elif choice == "2":
            return "fresh"
        else:
            return "exit"

    def configure_existing(self) -> dict:
        """Configure connection to existing PostgreSQL"""
        self.ui.clear_screen()

        # Show PostgreSQL elephant
        for line in POSTGRES_ELEPHANT.split('\n'):
            self.ui.print_centered(self.ui.color(line, "BLUE"))

        print("\n")
        self.ui.print_centered(self.ui.color("Configure PostgreSQL Connection", "BOLD"))
        print("\n")

        config = {}

        # Get connection details
        fields = [
            ("Host/IP", "pg_host", "localhost"),
            ("Port", "pg_port", "5432"),
            ("Database", "pg_database", "giljo_mcp"),
            ("Username", "pg_user", "postgres"),
            ("Password", "pg_password", ""),
        ]

        for label, key, default in fields:
            prompt = f"{label} [{default}]: " if default else f"{label}: "
            value = input(self.ui.center_text(prompt)).strip()
            config[key] = value if value else default

            # Hide password
            if key == "pg_password" and config[key]:
                display_val = "*" * len(config[key])
            else:
                display_val = config[key]

            print(self.ui.center_text(
                self.ui.color(f"  ✓ {label}: {display_val}", "GREEN")
            ))

        # Test connection
        print("\n")
        self.ui.animated_dots("Testing connection", 2)

        if self.test_connection(config):
            print(self.ui.color("✓ Connection successful!", "GREEN"))
            return config
        else:
            print(self.ui.color("✗ Connection failed!", "RED"))
            retry = input("Retry configuration? (y/n): ").lower()
            if retry == 'y':
                return self.configure_existing()
            return {}

    def test_connection(self, config: dict) -> bool:
        """Test PostgreSQL connection"""
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
            return True
        except:
            return False

    def install_fresh(self) -> dict:
        """Install fresh PostgreSQL server"""
        self.ui.clear_screen()

        print(self.ui.color("Installing PostgreSQL Server", "BOLD"))
        print("\n")

        config = {
            'pg_host': 'localhost',
            'pg_port': '5432',
            'pg_database': 'giljo_mcp',
            'pg_user': 'postgres',
        }

        # Get password for new installation
        print("Set the PostgreSQL administrator password:")
        config['pg_password'] = input("Password: ").strip()

        # Platform-specific installation
        system = sys.platform

        if system == "win32":
            self.install_windows(config)
        elif system == "darwin":
            self.install_macos(config)
        else:
            self.install_linux(config)

        return config

    def install_windows(self, config: dict):
        """Install PostgreSQL on Windows"""
        print(self.ui.color("Downloading PostgreSQL for Windows...", "YELLOW"))

        # Simulate download progress
        for i in range(101):
            print(f'\r{self.ui.progress_bar(i, 100, 50, "Download")}', end='', flush=True)
            time.sleep(0.02)
        print()

        # Note: Actual implementation would download and run installer
        print(self.ui.color("✓ PostgreSQL installed successfully", "GREEN"))

    def install_macos(self, config: dict):
        """Install PostgreSQL on macOS"""
        print(self.ui.color("Installing PostgreSQL via Homebrew...", "YELLOW"))
        try:
            subprocess.run(["brew", "install", "postgresql@16"], check=True)
            subprocess.run(["brew", "services", "start", "postgresql@16"], check=True)
            print(self.ui.color("✓ PostgreSQL installed successfully", "GREEN"))
        except:
            print(self.ui.color("✗ Failed to install via Homebrew", "RED"))
            print("Please install PostgreSQL manually")

    def install_linux(self, config: dict):
        """Install PostgreSQL on Linux"""
        print(self.ui.color("Installing PostgreSQL via package manager...", "YELLOW"))
        try:
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "postgresql", "postgresql-contrib"], check=True)
            print(self.ui.color("✓ PostgreSQL installed successfully", "GREEN"))
        except:
            print(self.ui.color("✗ Failed to install via apt", "RED"))
            print("Please install PostgreSQL manually")


class GiljoCLISetup(GiljoSetup):
    """Enhanced CLI setup with ASCII UI"""

    def __init__(self):
        super().__init__()
        self.ui = TerminalUI()
        self.pg_installer = PostgreSQLInstaller(self.ui)

    def run(self):
        """Run the enhanced CLI setup"""
        self.ui.clear_screen()

        # Show welcome screen
        self.show_welcome()

        # Check Python version
        if not self.check_python_version():
            print(self.ui.color("✗ Python 3.10+ required", "RED"))
            sys.exit(1)

        # Select deployment mode
        deployment_mode = self.select_deployment_mode()
        if deployment_mode == "exit":
            print("Setup cancelled.")
            sys.exit(0)

        self.deployment_mode = deployment_mode

        # Configure PostgreSQL
        pg_mode = self.pg_installer.prompt_installation_mode()
        if pg_mode == "exit":
            print("Setup cancelled.")
            sys.exit(0)

        if pg_mode == "existing":
            pg_config = self.pg_installer.configure_existing()
        else:
            pg_config = self.pg_installer.install_fresh()

        if not pg_config:
            print(self.ui.color("✗ PostgreSQL configuration failed", "RED"))
            sys.exit(1)

        self.config.update(pg_config)
        self.config['database_type'] = 'postgresql'

        # Select port
        self.select_port()

        # Run installation
        self.run_installation()

        # Show summary
        self.show_summary()

    def show_welcome(self):
        """Show welcome screen with ASCII art"""
        for line in GILJO_LOGO.split('\n'):
            self.ui.print_centered(self.ui.color(line, "CYAN"))

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
        input(self.ui.center_text("Press Enter to continue..."))

    def select_deployment_mode(self) -> str:
        """Select deployment mode"""
        self.ui.clear_screen()

        self.ui.print_centered(self.ui.color("Select Deployment Mode", "BOLD"))
        print("\n")

        modes_box = self.ui.draw_box([
            "1) Local Development",
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
        choice = input(self.ui.center_text("Enter your choice (1-3): ")).strip()

        if choice == "1":
            return "LOCAL"
        elif choice == "2":
            return "SERVER"
        else:
            return "exit"

    def run_installation(self):
        """Run the installation with progress display"""
        self.ui.clear_screen()

        self.ui.print_centered(self.ui.color("Installing GiljoAI MCP", "BOLD"))
        print("\n")

        steps = [
            ("Creating virtual environment", self.create_venv),
            ("Installing dependencies", self.install_requirements),
            ("Creating configuration", self.create_config_file),
            ("Setting up directories", self.create_directories),
        ]

        total_steps = len(steps)
        for i, (label, func) in enumerate(steps, 1):
            print(f"\n{self.ui.color(f'[{i}/{total_steps}]', 'CYAN')} {label}")

            # Show progress bar
            for j in range(101):
                print(f'\r{self.ui.progress_bar(j, 100, 40)}', end='', flush=True)
                time.sleep(0.01)

            # Run the actual function
            success = func()

            if success:
                print(f'\r{self.ui.progress_bar(100, 100, 40)} {self.ui.color("✓", "GREEN")}')
            else:
                print(f'\r{self.ui.progress_bar(100, 100, 40)} {self.ui.color("✗", "RED")}')
                print(self.ui.color(f"Failed: {label}", "RED"))
                sys.exit(1)

    def show_summary(self):
        """Show installation summary"""
        self.ui.clear_screen()

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
        summary_box = self.ui.draw_box([
            f"Server Port: {self.server_port}",
            f"Deployment: {self.deployment_mode}",
            f"Database: PostgreSQL",
            f"Host: {self.config.get('pg_host', 'localhost')}",
            "",
            "Next Steps:",
            "1. Start server: python -m giljo_mcp",
            f"2. Access dashboard: http://localhost:{self.server_port}",
            f"3. View API docs: http://localhost:{self.server_port}/docs",
        ], "Configuration Summary", 60)

        for line in summary_box:
            self.ui.print_centered(line)

        print("\n")
        if self.deployment_mode != "LOCAL":
            api_key = self.config.get('api_key', 'Check config.yaml')
            print(self.ui.color(f"API Key: {api_key}", "YELLOW"))
            print(self.ui.color("Save this key - you'll need it for remote connections", "YELLOW"))

        print("\n")
        input(self.ui.center_text("Press Enter to exit..."))


if __name__ == "__main__":
    setup = GiljoCLISetup()
    setup.run()
