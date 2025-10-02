#!/usr/bin/env python3
"""
GiljoAI Agent Orchestrator MCP ServerGUI Setup - Tkinter-based wizard interface
Provides a graphical setup wizard as an alternative to CLI mode
"""

import platform
import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

# Import base setup class
from setup import PORT_ASSIGNMENTS, GiljoSetup, check_port

# Enable DPI awareness for clearer text on Windows - Method #2
if sys.platform == "win32":
    try:
        import ctypes
        # SetProcessDpiAwareness(2) = Per Monitor DPI Aware V2
        # This provides the best clarity on high DPI displays
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        # Fallback to SetProcessDpiAwareness(1) = System DPI Aware
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            # Final fallback for older Windows versions
            try:
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass  # DPI awareness not available


def is_admin():
    """Check if running with administrator privileges on Windows"""
    if sys.platform != "win32":
        return True  # Not needed on Unix systems

    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


# GiljoAI Official Color Palette
COLORS = {
    'bg_primary': '#0e1c2d',      # Darkest blue - primary background
    'bg_secondary': '#182739',    # Dark blue - secondary background, panels
    'bg_elevated': '#1e3147',     # Medium dark blue - cards, elevated surfaces
    'border': '#315074',          # Medium blue - borders, dividers
    'text_primary': '#ffc300',    # Primary yellow - main text, highlights
    'text_success': '#67bd6d',    # Success green - success states
    'text_error': '#c6298c',      # Alert pink/red - errors
    'text_secondary': '#8f97b7',  # Light blue - secondary text
    'text_light': '#e1e1e1',      # Light gray - text on dark
    'accent_purple': '#8b5cf6',   # Purple - special features
    # Additional color aliases for compatibility
    'error': '#c6298c',           # Same as text_error
    'warning': '#ffc300',         # Same as text_primary (yellow)
    'success': '#67bd6d',         # Same as text_success
}

# Known large packages that take longer to download
LARGE_PACKAGES = {
    'pywin32': 'Windows system libraries',
    'docker': 'Docker container management',
    'openai': 'AI integration libraries',
    'anthropic': 'Claude AI integration',
    'google-generativeai': 'Google AI integration',
    'mkdocs-material': 'Documentation theme',
    'celery': 'Task queue system',
    'tiktoken': 'Token counting data',
    'psycopg2-binary': 'PostgreSQL drivers',
    'psycopg2': 'PostgreSQL drivers',
    'cryptography': 'Encryption libraries',
    'sqlalchemy': 'Database ORM',
    'grpcio': 'gRPC libraries',
    'numpy': 'Numerical computing',
    'pandas': 'Data analysis',
}


def extract_package_name(line):
    """Extract clean package name from pip output line"""
    # Handle "Collecting package_name" or "Downloading package_name-version.whl"
    if "Collecting" in line:
        # Extract after "Collecting "
        parts = line.split("Collecting", 1)
        if len(parts) > 1:
            package_part = parts[1].strip()
            # Remove version specifiers and other constraints
            package_name = package_part.split()[0] if package_part else ""
            # Clean up common separators
            for sep in ['>=', '<=', '==', '>', '<', '[', '(', ' ']:
                if sep in package_name:
                    package_name = package_name.split(sep)[0]
            return package_name.strip()
    elif "Downloading" in line:
        # Extract from "Downloading package-version.whl" or similar
        parts = line.split("Downloading", 1)
        if len(parts) > 1:
            file_part = parts[1].strip()
            # Extract package name from filename
            if '/' in file_part:
                file_part = file_part.split('/')[-1]
            # Remove .whl, .tar.gz, etc and version
            package_name = file_part.split('-')[0] if '-' in file_part else file_part.split('.')[0]
            return package_name.strip()
    return ""


def extract_packages_from_batch(line):
    """Extract package names from 'Installing collected packages:' line"""
    if "Installing collected packages:" in line:
        packages_part = line.split("Installing collected packages:", 1)[1]
        # Split by comma and clean up each package name
        packages = [p.strip() for p in packages_part.split(",") if p.strip()]
        return packages
    return []


class InstallationLogger:
    """Logger for installation process with timestamped file output"""

    def __init__(self, log_dir="install_logs"):
        """Initialize logger with timestamp-based log file"""
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)

        # Create log file with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = self.log_dir / f"install_{timestamp}.log"

        # Write header
        self.write("="*70, raw=True)
        self.write(f"GiljoAI MCP Installation Log", raw=True)
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
        except Exception as e:
            # Silently fail if logging fails (don't interrupt installation)
            pass

    def close(self):
        """Write closing message to log"""
        self.write("")
        self.write("="*70, raw=True)
        self.write(f"Installation completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", raw=True)
        self.write("="*70, raw=True)


class WelcomePage(ttk.Frame):
    """Welcome page with logo - first page of wizard"""

    def __init__(self, parent):
        super().__init__(parent)
        self.title = "Welcome to GiljoAI Agent Orchestrator MCP Server"

        # Main container
        main_frame = ttk.Frame(self)
        main_frame.pack(fill="both", expand=True, padx=40, pady=40)

        # Try to load and display logo
        logo_path = Path(__file__).parent / "frontend" / "public" / "giljologo_full.png"
        if logo_path.exists():
            try:
                # Load PNG directly with tkinter
                photo = tk.PhotoImage(file=str(logo_path))

                # Resize to fit nicely (subsample to make smaller)
                # Get original size and calculate appropriate subsample
                width = photo.width()
                height = photo.height()

                # Target width ~600px for 800px window
                target_width = 600
                subsample_factor = max(1, width // target_width)

                if subsample_factor > 1:
                    photo = photo.subsample(subsample_factor, subsample_factor)

                logo_label = tk.Label(main_frame, image=photo, bg=COLORS['bg_primary'])
                logo_label.image = photo  # Keep reference
                logo_label.pack(pady=(0, 10))

                # Add version subtitle below logo
                version_label = tk.Label(main_frame,
                                        text="v0.2 Beta",
                                        font=('Segoe UI', 14),
                                        fg=COLORS['text_success'],
                                        bg=COLORS['bg_primary'])
                version_label.pack(pady=(0, 30))
            except Exception as e:
                # Fallback to text logo
                logo_text = tk.Label(main_frame,
                                    text="GiljoAI",
                                    font=('Segoe UI', 48, 'bold'),
                                    fg=COLORS['text_primary'],
                                    bg=COLORS['bg_primary'])
                logo_text.pack(pady=(0, 10))

                subtitle = tk.Label(main_frame,
                                   text="Agent Orchestrator MCP Server",
                                   font=('Segoe UI', 20),
                                   fg=COLORS['text_secondary'],
                                   bg=COLORS['bg_primary'])
                subtitle.pack(pady=(0, 5))

                version = tk.Label(main_frame,
                                  text="v0.2 Beta",
                                  font=('Segoe UI', 14),
                                  fg=COLORS['text_success'],
                                  bg=COLORS['bg_primary'])
                version.pack(pady=(0, 30))
        else:
            # Fallback if logo not found
            logo_text = tk.Label(main_frame,
                                text="GiljoAI",
                                font=('Segoe UI', 48, 'bold'),
                                fg=COLORS['text_primary'],
                                bg=COLORS['bg_primary'])
            logo_text.pack(pady=(0, 10))

            subtitle = tk.Label(main_frame,
                               text="Agent Orchestrator MCP Server",
                               font=('Segoe UI', 20),
                               fg=COLORS['text_secondary'],
                               bg=COLORS['bg_primary'])
            subtitle.pack(pady=(0, 5))

            version = tk.Label(main_frame,
                              text="v0.2 Beta",
                              font=('Segoe UI', 14),
                              fg=COLORS['text_success'],
                              bg=COLORS['bg_primary'])
            version.pack(pady=(0, 30))

        # Welcome message
        welcome_label = tk.Label(main_frame,
                                text="Welcome to the Setup Wizard",
                                font=('Segoe UI', 16, 'bold'),
                                fg=COLORS['text_light'],
                                bg=COLORS['bg_primary'])
        welcome_label.pack(pady=(0, 20))

        # Description
        desc_label = tk.Label(main_frame,
                             text="This wizard will guide you through installing\n"
                                  "the GiljoAI Agent Orchestrator MCP Server.\n\n"
                                  "Click Next to begin.",
                             font=('Segoe UI', 11),
                             fg=COLORS['text_secondary'],
                             bg=COLORS['bg_primary'],
                             justify='center')
        desc_label.pack(pady=(0, 30))

        # Footer with contact info
        footer_frame = tk.Frame(main_frame, bg=COLORS['bg_primary'])
        footer_frame.pack(side="bottom", pady=(30, 0))

        website_label = tk.Label(footer_frame,
                                text="www.giljo.ai © 2025",
                                font=('Segoe UI', 9),
                                fg=COLORS['text_secondary'],
                                bg=COLORS['bg_primary'])
        website_label.pack()

        email_label = tk.Label(footer_frame,
                              text="infoteam@giljo.ai",
                              font=('Segoe UI', 9),
                              fg=COLORS['text_secondary'],
                              bg=COLORS['bg_primary'])
        email_label.pack()

    def validate(self) -> bool:
        """Always valid - just a welcome screen"""
        return True

    def get_data(self) -> dict:
        """No data to collect from welcome page"""
        return {}


class WizardPage(ttk.Frame):
    """Base class for wizard pages"""

    def __init__(self, parent, title: str):
        super().__init__(parent)
        self.title = title
        self.parent = parent
        self.validated = False

    def validate(self) -> bool:
        """Override to implement page validation"""
        return True

    def on_enter(self):
        """Called when entering the page"""

    def on_exit(self):
        """Called when leaving the page"""

    def get_data(self) -> dict:
        """Override to return page data"""
        return {}




class ProfileSelectionPage(WizardPage):
    """Welcome and deployment mode selection page"""

    def __init__(self, parent):
        super().__init__(parent, "GiljoAI MCP Server Installation")

        # Welcome Title
        title_label = ttk.Label(self, text="GiljoAI Agent Orchestrator MCP Server", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Installation recommendation
        recommend_text = """It is recommended to install the GiljoAI Agent Orchestrator MCP Server in a separate directory
and not in the project folder."""

        recommend_label = ttk.Label(self, text=recommend_text, justify=tk.LEFT, foreground="orange")
        recommend_label.pack(padx=20, pady=(0, 10))

        # Welcome message with white text
        welcome_text = """What this installer does:
• Installs a standalone MCP server (one-time, system-wide)
• Creates its own Python environment and dependencies
• Configures database and network settings
• Registers globally with Claude (optional)

After installation, you'll connect projects via lightweight config files.

Select your server deployment mode:"""

        # Use tk.Label instead of ttk.Label for white text
        desc_label = tk.Label(self, text=welcome_text, justify=tk.LEFT,
                             fg='#ffffff', bg=COLORS['bg_primary'],
                             font=('Segoe UI', 9))
        desc_label.pack(padx=20, pady=10)

        # Deployment mode selection
        self.mode_var = tk.StringVar(value="local")

        # Create deployment mode frames
        modes_frame = ttk.Frame(self)
        modes_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Local Development Mode
        local_frame = ttk.LabelFrame(modes_frame, text="Local Development", padding=10)
        local_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            local_frame,
            text="Local on Device Mode",
            variable=self.mode_var,
            value="local",
            command=self._on_mode_change,
        ).pack(anchor="w")

        local_desc = """• PostgreSQL database (locally installed)
• No authentication required
• Localhost only (secure by default)
• Up to 20 concurrent agents
• Debug logging for development
• Perfect for individual developers
• Ideal for: Personal projects, learning, prototyping"""

        tk.Label(local_frame, text=local_desc, justify=tk.LEFT,
                fg='#ffffff', bg=COLORS['bg_primary'],
                font=('Segoe UI', 9)).pack(padx=20, pady=5, anchor="w")

        # Server Deployment Mode
        server_frame = ttk.LabelFrame(modes_frame, text="Server Deployment", padding=10)
        server_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            server_frame,
            text="Team/Network Access Mode",
            variable=self.mode_var,
            value="server",
            command=self._on_mode_change,
        ).pack(anchor="w")

        server_desc = """• PostgreSQL database (network ready)
• API key authentication
• Network accessible (LAN/WAN)
• Up to 20 concurrent agents per user
• Multiple users can create projects
• Configurable security settings
• Ideal for: Team servers, CI/CD, remote access"""

        tk.Label(server_frame, text=server_desc, justify=tk.LEFT,
                fg='#ffffff', bg=COLORS['bg_primary'],
                font=('Segoe UI', 9)).pack(padx=20, pady=5, anchor="w")

        # Status label for mode details (yellow text)
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(padx=20, pady=10, fill="x")

        # Use tk.Label for yellow text
        self.status_label = tk.Label(self.status_frame, text="",
                                     fg='#ffc300', bg=COLORS['bg_primary'],
                                     font=('Segoe UI', 9, 'bold'))
        self.status_label.pack()

        # Set initial status
        self._on_mode_change()

    def _on_mode_change(self):
        """Update status based on selected mode"""
        mode = self.mode_var.get()

        status_messages = {
            "local": "[OK] Ready for quick setup with minimal configuration",
            "server": "[OK] Will configure database and network settings",
        }

        self.status_label.config(text=status_messages.get(mode, ""))

    def validate(self) -> bool:
        """Validate deployment mode selection"""
        return True  # Both modes are valid

    def get_data(self) -> dict:
        mode = self.mode_var.get()
        # Map deployment_mode to profile for backward compatibility
        profile_map = {
            "local": "developer",
            "server": "server"
        }
        return {
            "deployment_mode": mode,
            "profile": profile_map.get(mode, "developer")
        }

    def on_enter(self):
        """Called when entering the page"""
        # Could check for existing installation and suggest profile
        pass


class DatabasePage(WizardPage):
    """PostgreSQL database configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "PostgreSQL Database Configuration")

        # Title and description
        title_label = ttk.Label(self, text="PostgreSQL Database Setup", font=("Helvetica", 12, "bold"))
        title_label.pack(pady=10)

        desc_text = """GiljoAI MCP requires PostgreSQL. Complete both steps below to configure your database."""
        desc_label = tk.Label(self, text=desc_text, justify=tk.LEFT,
                             fg='#ffffff', bg=COLORS['bg_primary'],
                             font=('Segoe UI', 9))
        desc_label.pack(padx=20, pady=5)

        # STEP 1: PostgreSQL Installation (if needed)
        step1_frame = ttk.LabelFrame(self, text="Step 1: Install PostgreSQL (Skip if already installed)",
                                    style='Yellow.TLabelframe', padding=15)
        step1_frame.pack(padx=20, pady=10, fill="x")

        install_desc = tk.Label(step1_frame,
                              text="Configure these settings BEFORE installing. Write them down - you'll need them!",
                              fg=COLORS['warning'], bg=COLORS['bg_primary'],
                              font=('Segoe UI', 10, 'bold'))
        install_desc.pack(anchor="w", pady=(0, 10))

        # Username field (with default)
        user_frame = ttk.Frame(step1_frame)
        user_frame.pack(fill="x", pady=3)
        self.pg_user_var = tk.StringVar(value="postgres")
        ttk.Label(user_frame, text="Username:", width=15).pack(side="left")
        self.user_entry = ttk.Entry(user_frame, textvariable=self.pg_user_var, width=25)
        self.user_entry.pack(side="left", padx=5)
        tk.Label(user_frame, text="(default: postgres)",
                fg='#888888', bg=COLORS['bg_primary'],
                font=('Segoe UI', 8)).pack(side="left", padx=5)

        # Password field
        pass_frame = ttk.Frame(step1_frame)
        pass_frame.pack(fill="x", pady=3)
        self.pg_password_var = tk.StringVar()
        ttk.Label(pass_frame, text="Password:", width=15).pack(side="left")
        self.password_entry = ttk.Entry(pass_frame, textvariable=self.pg_password_var, width=25, show="*")
        self.password_entry.pack(side="left", padx=5)

        # Show/hide password toggle
        self.show_pass_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(pass_frame,
                       text="Show",
                       variable=self.show_pass_var,
                       command=self._toggle_password).pack(side="left", padx=5)

        # Port field (with default)
        port_frame = ttk.Frame(step1_frame)
        port_frame.pack(fill="x", pady=3)
        self.pg_port_var = tk.StringVar(value="5432")
        ttk.Label(port_frame, text="Port:", width=15).pack(side="left")
        self.port_entry = ttk.Entry(port_frame, textvariable=self.pg_port_var, width=25)
        self.port_entry.pack(side="left", padx=5)
        tk.Label(port_frame, text="(default: 5432)",
                fg='#888888', bg=COLORS['bg_primary'],
                font=('Segoe UI', 8)).pack(side="left", padx=5)

        # Install button
        install_btn_frame = ttk.Frame(step1_frame)
        install_btn_frame.pack(fill="x", pady=(10, 5))

        def open_postgres_download():
            import webbrowser
            webbrowser.open("https://www.postgresql.org/download/")

        self.install_btn = tk.Button(install_btn_frame,
                                    text="Download PostgreSQL Installer",
                                    command=open_postgres_download,
                                    bg=COLORS['bg_elevated'], fg='#ffffff',
                                    font=('Segoe UI', 9), relief='flat', borderwidth=0,
                                    padx=15, pady=6, cursor='hand2',
                                    activebackground=COLORS['border'], activeforeground='#ffffff')
        self.install_btn.pack()

        tk.Label(install_btn_frame,
                text="Click above to download PostgreSQL, then install using YOUR settings from above",
                fg='#ffffff', bg=COLORS['bg_primary'],
                font=('Segoe UI', 9)).pack(pady=(5, 0))

        # STEP 2: Test Database Connection
        step2_frame = ttk.LabelFrame(self, text="Step 2: Test Database Connection",
                                    style='Yellow.TLabelframe', padding=15)
        step2_frame.pack(padx=20, pady=10, fill="x")

        test_desc = tk.Label(step2_frame,
                           text="After installation (or if using existing PostgreSQL), test your connection:",
                           fg='#ffffff', bg=COLORS['bg_primary'],
                           font=('Segoe UI', 9))
        test_desc.pack(anchor="w", pady=(0, 10))

        # Host configuration (hidden by default for localhost)
        self.pg_host_var = tk.StringVar(value="localhost")

        # Note about using same credentials
        note_label = tk.Label(step2_frame,
                            text="NOTE: Use the same Username, Password, and Port from Step 1 (or your existing PostgreSQL)",
                            fg=COLORS['text_primary'], bg=COLORS['bg_primary'],
                            font=('Segoe UI', 9, 'bold'))
        note_label.pack(anchor="w", pady=(0, 10))

        # Database name (fixed)
        self.pg_database_var = tk.StringVar(value="giljo_mcp")

        # Check if psycopg2 is available
        self.psycopg2_available = self._check_psycopg2()

        # Install dependencies button (if psycopg2 not available)
        if not self.psycopg2_available:
            install_deps_frame = ttk.Frame(step2_frame)
            install_deps_frame.pack(fill="x", pady=(5, 5))

            warning_label = tk.Label(install_deps_frame,
                                    text="WARNING: Test dependencies not installed",
                                    fg=COLORS['warning'], bg=COLORS['bg_primary'],
                                    font=('Segoe UI', 9, 'bold'))
            warning_label.pack(pady=(0, 5))

            self.install_deps_btn = tk.Button(install_deps_frame,
                                            text="Install Test Dependencies (psycopg2-binary)",
                                            command=self._install_test_deps,
                                            bg=COLORS['accent_purple'], fg='#ffffff',
                                            font=('Segoe UI', 9), relief='flat', borderwidth=0,
                                            padx=15, pady=6, cursor='hand2',
                                            activebackground='#7c3aed', activeforeground='#ffffff')
            self.install_deps_btn.pack()

            deps_note = tk.Label(install_deps_frame,
                                text="(Required for testing PostgreSQL connections. Takes ~5 seconds)",
                                fg='#888888', bg=COLORS['bg_primary'],
                                font=('Segoe UI', 8))
            deps_note.pack(pady=(2, 0))

        # Test button
        test_btn_frame = ttk.Frame(step2_frame)
        test_btn_frame.pack(fill="x", pady=(10, 5))

        self.test_btn = tk.Button(test_btn_frame,
                                text="Test Connection",
                                command=self._test_connection,
                                bg=COLORS['bg_elevated'], fg='#ffffff',
                                font=('Segoe UI', 9), relief='flat', borderwidth=0,
                                padx=15, pady=6, cursor='hand2',
                                activebackground=COLORS['border'], activeforeground='#ffffff')
        self.test_btn.pack()

        # Connection status label
        self.status_label = tk.Label(step2_frame,
                                    text="Click 'Test Connection' after entering your PostgreSQL credentials",
                                    fg='#888888', bg=COLORS['bg_primary'],
                                    font=('Segoe UI', 9))
        self.status_label.pack(pady=(5, 0))


    def _on_mode_change(self):
        """Handle setup mode change"""
        mode = self.setup_mode_var.get()

        if mode == "existing":
            # Show test connection, host entry, check port
            self.test_frame.pack(fill="x", pady=5)
            self.install_note_frame.pack_forget()
            self.note_frame.pack_forget()
            self.host_frame.pack(fill="x", pady=2, after=self.network_combo.master)
            self.check_port_btn.pack(side="left", padx=5)
            self.host_entry.config(state="normal")
            # Enable network mode selection
            self.network_combo.config(state="readonly")
        else:  # fresh
            # Hide test connection, show install note
            self.test_frame.pack_forget()
            self.install_note_frame.pack(fill="x", pady=5)
            self.note_frame.pack(fill="x", pady=5, after=self.pass_entry.master)
            self.check_port_btn.pack_forget()
            # For fresh install, configure based on network mode
            self._on_network_change()

    def _on_network_change(self, event=None):
        """Handle network mode change"""
        network_mode = self.network_mode_var.get()
        setup_mode = self.setup_mode_var.get()

        if setup_mode == "fresh":
            if network_mode == "localhost":
                # Hide host entry for localhost fresh install
                self.host_frame.pack_forget()
                self.pg_host_var.set("localhost")
            else:
                # Show host entry for network fresh install
                self.host_frame.pack(fill="x", pady=2, after=self.network_combo.master)
                # Get local IP suggestion
                try:
                    hostname = socket.gethostname()
                    local_ip = socket.gethostbyname(hostname)
                    self.pg_host_var.set(local_ip)
                except:
                    self.pg_host_var.set("0.0.0.0")  # nosec B104 - Intentional for network mode

    def _toggle_password(self):
        """Toggle password visibility"""
        if self.show_pass_var.get():
            self.password_entry.config(show="")
        else:
            self.password_entry.config(show="*")

    def _check_psycopg2(self) -> bool:
        """Check if psycopg2 is available"""
        try:
            import psycopg2
            return True
        except ImportError:
            return False

    def _install_test_deps(self):
        """Install test dependencies (psycopg2-binary) in a thread"""
        self.install_deps_btn.config(state='disabled', text="Installing...")
        self.update()

        def install():
            try:
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "psycopg2-binary"],
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    self.status_label.config(
                        text="[OK] Test dependencies installed successfully!",
                        fg=COLORS['text_success']
                    )
                    self.psycopg2_available = True
                    # Hide the install button after success
                    self.install_deps_btn.master.pack_forget()
                else:
                    self.status_label.config(
                        text=f"[ERROR] Installation failed: {result.stderr[:100]}",
                        fg=COLORS['text_error']
                    )
                    self.install_deps_btn.config(state='normal', text="Install Test Dependencies (psycopg2-binary)")
            except Exception as e:
                self.status_label.config(
                    text=f"[ERROR] Error installing dependencies: {str(e)[:100]}",
                    fg=COLORS['text_error']
                )
                self.install_deps_btn.config(state='normal', text="Install Test Dependencies (psycopg2-binary)")

        thread = threading.Thread(target=install, daemon=True)
        thread.start()

    def _check_port(self):
        """Check if PostgreSQL port is accessible"""
        try:
            host = self.pg_host_var.get()
            port = int(self.pg_port_var.get())

            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex((host, port))
            sock.close()

            if result == 0:
                self.status_label.config(text=f"[OK] Port {port} is open on {host}", foreground="green")
            else:
                self.status_label.config(text=f"[ERROR] Port {port} is not accessible on {host}", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"[ERROR] Error checking port: {e}", foreground="red")

    def _test_connection(self):
        """Test PostgreSQL connection"""
        self.status_label.config(text="Testing connection...", foreground=COLORS['text_primary'])  # Yellow
        self.update()

        # Run test in thread to avoid blocking
        def test():
            try:
                import psycopg2
            except ImportError:
                self.status_label.config(
                    text="[ERROR] psycopg2 not installed. Run: pip install psycopg2-binary",
                    foreground="red"
                )
                return

            try:
                # First try to connect to the postgres database to check credentials
                conn = psycopg2.connect(
                    host=self.pg_host_var.get(),
                    port=self.pg_port_var.get(),
                    database="postgres",  # Connect to default database first
                    user=self.pg_user_var.get(),
                    password=self.pg_password_var.get(),
                    connect_timeout=5
                )

                # Check if our database exists
                cur = conn.cursor()
                db_name = self.pg_database_var.get()
                cur.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                db_exists = cur.fetchone() is not None

                cur.close()
                conn.close()

                if db_exists:
                    # Try connecting to the actual database
                    conn2 = psycopg2.connect(
                        host=self.pg_host_var.get(),
                        port=self.pg_port_var.get(),
                        database=db_name,
                        user=self.pg_user_var.get(),
                        password=self.pg_password_var.get(),
                        connect_timeout=5
                    )
                    conn2.close()
                    self.status_label.config(
                        text=f"[OK] Connected successfully! Database '{db_name}' exists.",
                        fg=COLORS['text_success']
                    )
                else:
                    self.status_label.config(
                        text=f"[OK] Connection successful! Database '{db_name}' will be created.",
                        fg=COLORS['text_success']
                    )

            except psycopg2.OperationalError as e:
                if "password authentication failed" in str(e):
                    self.status_label.config(text="[ERROR] Invalid credentials", foreground="red")
                elif "could not connect to server" in str(e):
                    self.status_label.config(text="[ERROR] Cannot connect to server", foreground="red")
                elif "timeout expired" in str(e):
                    self.status_label.config(text="[ERROR] Connection timeout", foreground="red")
                else:
                    self.status_label.config(text=f"[ERROR] Connection failed: {e}", foreground="red")
            except Exception as e:
                self.status_label.config(text=f"[ERROR] Error: {e}", foreground="red")

        thread = threading.Thread(target=test)
        thread.daemon = True
        thread.start()

    def validate(self) -> bool:
        """Validate database configuration"""
        # All fields are required
        if not all([
            self.pg_host_var.get(),
            self.pg_port_var.get(),
            self.pg_database_var.get(),
            self.pg_user_var.get(),
            self.pg_password_var.get()
        ]):
            messagebox.showerror("Validation Error", "All database fields are required.")
            return False

        # Validate port is a number
        try:
            port = int(self.pg_port_var.get())
            if port < 1 or port > 65535:
                messagebox.showerror("Validation Error", "Port must be between 1 and 65535.")
                return False
        except ValueError:
            messagebox.showerror("Validation Error", "Port must be a valid number.")
            return False

        return True

    def get_data(self) -> dict:
        """Return database configuration"""
        return {
            "db_type": "postgresql",  # Always PostgreSQL
            "pg_host": self.pg_host_var.get(),
            "pg_port": self.pg_port_var.get(),
            "pg_database": self.pg_database_var.get(),
            "pg_user": self.pg_user_var.get(),
            "pg_password": self.pg_password_var.get(),
            "install_postgresql": False  # User handles installation manually
        }

    def on_enter(self):
        """Called when entering the page"""
        # Reset connection tested flag
        if hasattr(self, '_connection_tested'):
            delattr(self, '_connection_tested')

        # Get deployment mode from parent
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            deployment_mode = parent.config_data.get("deployment_mode", "local")

            # Set network mode based on deployment
            if deployment_mode == "local":
                self.network_mode_var.set("localhost")
            else:
                self.network_mode_var.set("network")

            self._on_network_change()


class PortsPage(WizardPage):
    """Port configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "Port Configuration")

        # Description
        desc = ttk.Label(self, text="Configure server ports. Default ports are recommended.")
        desc.pack(padx=20, pady=10)

        # Port configuration
        ports_frame = ttk.LabelFrame(self, text="Server Ports", padding=10)
        ports_frame.pack(padx=20, pady=10, fill="both", expand=True)

        self.port_vars = {}
        self.status_labels = {}

        for service, default_port in PORT_ASSIGNMENTS.items():
            # Skip non-port entries like "alternatives" list
            if not isinstance(default_port, int):
                continue

            frame = ttk.Frame(ports_frame)
            frame.pack(fill="x", pady=5)

            # Service name
            ttk.Label(frame, text=f"{service}:", width=20).pack(side="left")

            # Port entry
            var = tk.StringVar(value=str(default_port))
            self.port_vars[service] = var
            entry = ttk.Entry(frame, textvariable=var, width=10)
            entry.pack(side="left", padx=5)

            # Status label
            status = ttk.Label(frame, text="", width=20)
            status.pack(side="left", padx=5)
            self.status_labels[service] = status

            # Check button
            check_btn = tk.Button(frame, text="Check", command=lambda s=service: self._check_port(s),
                                 bg=COLORS['bg_elevated'], fg='#ffffff',
                                 font=('Segoe UI', 9), relief='flat', borderwidth=0,
                                 padx=10, pady=4, cursor='hand2',
                                 activebackground=COLORS['border'], activeforeground='#ffffff')
            check_btn.pack(side="left")

        # Check all button
        check_all_btn = tk.Button(ports_frame, text="Check All Ports", command=self._check_all_ports,
                                  bg=COLORS['bg_elevated'], fg='#ffffff',
                                  font=('Segoe UI', 9), relief='flat', borderwidth=0,
                                  padx=15, pady=6, cursor='hand2',
                                  activebackground=COLORS['border'], activeforeground='#ffffff')
        check_all_btn.pack(pady=10)

    def _check_port(self, service: str):
        """Check if a port is available"""
        port = int(self.port_vars[service].get())

        # Special handling for PostgreSQL - if port responds, it means PostgreSQL is running
        if service == "PostgreSQL":
            if check_port(port):
                self.status_labels[service].config(text="[OK] Detected", foreground="#90ee90")  # Lighter green
            else:
                self.status_labels[service].config(text="[ERROR] Not detected", foreground="#c6298c")  # Pink/red
        else:
            # For other services, in use is bad, available is good
            if check_port(port):
                self.status_labels[service].config(text="[ERROR] In use", foreground="#c6298c")  # Pink/red
            else:
                self.status_labels[service].config(text="[OK] Available", foreground="#90ee90")  # Lighter green

    def _check_all_ports(self):
        """Check all ports"""
        for service in self.port_vars:
            self._check_port(service)

    def validate(self) -> bool:
        """Validate all ports"""
        for service, var in self.port_vars.items():
            try:
                port = int(var.get())
                if port < 1024 or port > 65535:
                    messagebox.showerror("Invalid Port", f"{service} port must be between 1024 and 65535")
                    return False
            except ValueError:
                messagebox.showerror("Invalid Port", f"{service} port must be a number")
                return False
        return True

    def get_data(self) -> dict:
        # Map service names to expected config keys
        port_mapping = {
            "GiljoAI Orchestrator": "api_port",
            "Frontend Dev Server": "dashboard_port",
        }

        result = {}
        for service, var in self.port_vars.items():
            # Use mapped name if available, otherwise use service name with _port suffix
            key = port_mapping.get(service, f"{service}_port")
            result[key] = var.get()
        return result

    def on_enter(self):
        """Adapt port settings based on selected profile"""
        # Access the parent GiljoSetupGUI instance to get config data
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            profile = parent.config_data.get("profile", "developer")

            # Set port recommendations based on profile
            # With unified architecture, we only need one main port
            if profile == "enterprise":
                # Enterprise uses standard ports for production
                if "GiljoAI Orchestrator" in self.port_vars:
                    self.port_vars["GiljoAI Orchestrator"].set("443")
            elif profile == "team":
                # Team uses higher ports to avoid conflicts
                if "GiljoAI Orchestrator" in self.port_vars:
                    self.port_vars["GiljoAI Orchestrator"].set("9000")
            else:
                # Developer and Research use default development ports
                # These are already set in __init__, but we ensure they're correct
                pass

            # Check all ports after setting them
            self._check_all_ports()


class SecurityPage(WizardPage):
    """Security configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "Security Configuration")

        # API Key
        api_frame = ttk.LabelFrame(self, text="API Security", padding=10)
        api_frame.pack(padx=20, pady=10, fill="x")

        self.enable_api_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            api_frame,
            text="Enable API Key authentication",
            variable=self.enable_api_key_var,
            command=self._on_api_toggle,
        ).pack(anchor="w")

        # API Key explanation
        api_help = ttk.Label(
            api_frame,
            text="For building your own applications and integrating with GiljoAI MCP.\n"
            + "Examples: Custom tools, local LLM integrations, automation scripts.\n"
            + "Note: MCP clients (Claude, etc.) use MCP protocol, not this.",
            foreground=COLORS['text_primary'],  # Yellow
            wraplength=800,
        )
        api_help.pack(anchor="w", pady=(5, 10))

        self.api_key_var = tk.StringVar()
        self.api_frame_inner = ttk.Frame(api_frame)

        ttk.Label(self.api_frame_inner, text="API Key:").pack(side="left", padx=5)
        ttk.Entry(self.api_frame_inner, textvariable=self.api_key_var, width=40).pack(side="left", padx=5)
        gen_api_btn = tk.Button(self.api_frame_inner, text="Generate", command=self._generate_api_key,
                               bg=COLORS['bg_elevated'], fg='#ffffff',
                               font=('Segoe UI', 9), relief='flat', borderwidth=0,
                               padx=10, pady=4, cursor='hand2',
                               activebackground=COLORS['border'], activeforeground='#ffffff')
        gen_api_btn.pack(side="left")

        # Warning about saving the key
        self.api_warning = ttk.Label(
            self.api_frame_inner, text="WARNING: Copy this key now! It won't be shown again.", foreground="orange"
        )
        self.api_warning.pack(side="left", padx=10)

        # JWT Secret
        jwt_frame = ttk.LabelFrame(self, text="JWT Configuration", padding=10)
        jwt_frame.pack(padx=20, pady=10, fill="x")

        # JWT explanation
        jwt_help = ttk.Label(
            jwt_frame,
            text="Signs session tokens for the web dashboard. Prevents token tampering.\n"
            + "Auto-generated for security. No need to copy unless integrating SSO.",
            foreground=COLORS['text_primary'],  # Yellow
            wraplength=800,
        )
        jwt_help.pack(anchor="w", pady=(0, 10))

        self.jwt_secret_var = tk.StringVar()
        jwt_inner = ttk.Frame(jwt_frame)
        jwt_inner.pack(fill="x")

        ttk.Label(jwt_inner, text="JWT Secret:").pack(side="left", padx=5)
        ttk.Entry(jwt_inner, textvariable=self.jwt_secret_var, width=40).pack(side="left", padx=5)
        gen_jwt_btn = tk.Button(jwt_inner, text="Generate", command=self._generate_jwt_secret,
                               bg=COLORS['bg_elevated'], fg='#ffffff',
                               font=('Segoe UI', 9), relief='flat', borderwidth=0,
                               padx=10, pady=4, cursor='hand2',
                               activebackground=COLORS['border'], activeforeground='#ffffff')
        gen_jwt_btn.pack(side="left")

        # CORS settings (always enabled)
        cors_frame = ttk.LabelFrame(self, text="CORS Origin Configuration (Required for Dashboard)", padding=10)
        cors_frame.pack(padx=20, pady=10, fill="x")

        # CORS explanation
        cors_help = ttk.Label(
            cors_frame,
            text="Dashboard Access Configuration\n"
            + "Default works for local access. Change for LAN/WAN:\n"
            + "• Local: http://localhost:* (default)\n"
            + "• LAN: http://YOUR-SERVER-IP:* (e.g., http://192.168.1.100:*)\n"
            + "• WAN: https://your-domain.com",
            foreground=COLORS['text_primary'],  # Yellow
            wraplength=800,
        )
        cors_help.pack(anchor="w", pady=(0, 10))

        self.cors_origins_var = tk.StringVar(value="http://localhost:*")
        origins_frame = ttk.Frame(cors_frame)
        origins_frame.pack(fill="x")
        ttk.Label(origins_frame, text="Allowed Origin:").pack(side="left", padx=5)
        ttk.Entry(origins_frame, textvariable=self.cors_origins_var, width=45).pack(side="left", padx=5)

        # Note about editing
        cors_note = ttk.Label(
            cors_frame,
            text="Tip: You can change this later in the .env file if your network setup changes",
            foreground=COLORS['text_primary'],  # Yellow
            font=("", 9),
        )
        cors_note.pack(anchor="w", pady=(5, 0))

        # Initialize
        self._on_api_toggle()
        self._generate_jwt_secret()

    def _on_api_toggle(self):
        """Handle API key toggle"""
        if self.enable_api_key_var.get():
            self.api_frame_inner.pack(fill="x", pady=5)
            if not self.api_key_var.get():
                self._generate_api_key()
        else:
            self.api_frame_inner.pack_forget()

    def _generate_api_key(self):
        """Generate random API key"""
        import secrets

        key = f"gj-{secrets.token_urlsafe(32)}"
        self.api_key_var.set(key)

    def _generate_jwt_secret(self):
        """Generate random JWT secret"""
        import secrets

        secret = secrets.token_urlsafe(48)
        self.jwt_secret_var.set(secret)

    def get_data(self) -> dict:
        data = {
            "jwt_secret": self.jwt_secret_var.get(),
            "cors_enabled": True,  # Always enabled
            "cors_origins": self.cors_origins_var.get(),
        }
        if self.enable_api_key_var.get():
            data["api_key"] = self.api_key_var.get()
        return data

    def on_enter(self):
        """Adapt security settings based on selected profile"""
        # Access the parent GiljoSetupGUI instance to get config data
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            profile = parent.config_data.get("profile", "developer")

            # Set security defaults based on profile
            if profile == "developer":
                # Developer: Simple API key, local CORS
                self.enable_api_key_var.set(True)
                self.cors_origins_var.set("http://localhost:*")

            elif profile == "team":
                # Team: Required API key, network CORS
                self.enable_api_key_var.set(True)
                self.cors_origins_var.set("http://localhost:*, http://192.168.*.*")
                self._generate_api_key()  # Auto-generate for teams

            elif profile == "enterprise":
                # Enterprise: Strong security, specific CORS
                self.enable_api_key_var.set(True)
                self.cors_origins_var.set("https://your-domain.com")
                self._generate_api_key()  # Auto-generate strong key
                self._generate_jwt_secret()  # Auto-generate JWT

            elif profile == "research":
                # Research: Flexible security for experimentation
                self.enable_api_key_var.set(False)  # Optional for local research
                self.cors_origins_var.set("*")  # Allow all for research

            # Update UI state
            self._on_api_toggle()


class ReviewPage(WizardPage):
    """Review configuration before applying"""

    def __init__(self, parent, get_config_func: Callable):
        super().__init__(parent, "Review Configuration")
        self.get_config = get_config_func

        # Description
        desc = ttk.Label(self, text="Review your configuration before applying:")
        desc.pack(padx=20, pady=10)

        # Create frame for text and scrollbar
        text_frame = ttk.Frame(self)
        text_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Config display with #315074 background
        self.text = tk.Text(text_frame, height=20, width=70, wrap="word",
                           bg='#315074', fg='#ffffff',
                           font=('Segoe UI', 9),
                           insertbackground='#ffffff',
                           selectbackground='#1e3147',
                           selectforeground='#ffffff')
        self.text.pack(side="left", fill="both", expand=True)

        # Scrollbar - using tk.Scrollbar for full styling control
        scrollbar = tk.Scrollbar(text_frame, orient="vertical", command=self.text.yview,
                                bg=COLORS['bg_elevated'],  # Bar background
                                troughcolor='#315074',  # Match text widget background
                                activebackground=COLORS['text_primary'],  # Yellow when dragging
                                highlightthickness=0,
                                width=14)
        scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=scrollbar.set)

    def on_enter(self):
        """Update configuration display"""
        config = self.get_config()

        # Format configuration
        self.text.config(state="normal")
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, "=" * 60 + "\n")
        self.text.insert(tk.END, "CONFIGURATION SUMMARY\n")
        self.text.insert(tk.END, "=" * 60 + "\n\n")

        # Installation Profile
        self.text.insert(tk.END, "INSTALLATION PROFILE\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        profile = config.get("profile", "developer")
        profile_display = {
            "developer": "Individual Developer",
            "team": "Development Team",
            "enterprise": "Enterprise Deployment",
            "research": "AI Research & Education",
        }
        self.text.insert(tk.END, f"Profile: {profile_display.get(profile, profile.capitalize())}\n\n")

        # Database
        self.text.insert(tk.END, "DATABASE CONFIGURATION\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        self.text.insert(tk.END, "Type: PostgreSQL\n")
        self.text.insert(tk.END, f"Host: {config.get('pg_host', 'localhost')}\n")
        self.text.insert(tk.END, f"Port: {config.get('pg_port', '5432')}\n")
        self.text.insert(tk.END, f"Database: {config.get('pg_database', 'giljo_mcp')}\n")
        self.text.insert(tk.END, f"User: {config.get('pg_user', 'postgres')}\n")

        # Ports
        self.text.insert(tk.END, "\nSERVER PORTS\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        for service in PORT_ASSIGNMENTS:
            key = f"{service}_port"
            port = config.get(key, PORT_ASSIGNMENTS[service])
            self.text.insert(tk.END, f"{service.capitalize()}: {port}\n")

        # Security
        self.text.insert(tk.END, "\nSECURITY SETTINGS\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        if config.get("api_key"):
            self.text.insert(tk.END, f"API Key: {config['api_key'][:10]}... (SAVE THIS!)\n")
        else:
            self.text.insert(tk.END, "API Key: Disabled (Local mode)\n")

        jwt_secret = config.get("jwt_secret", "")
        if jwt_secret:
            self.text.insert(tk.END, f"JWT Secret: {jwt_secret[:10]}... (Auto-saved)\n")
        else:
            self.text.insert(tk.END, "JWT Secret: Will be generated\n")

        self.text.insert(tk.END, "CORS: Enabled (Required)\n")
        self.text.insert(tk.END, f"CORS Origin: {config.get('cors_origins', 'http://localhost:*')}\n")

        # URLs
        self.text.insert(tk.END, "\nACCESS URLS\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        dashboard_port = config.get("dashboard_port", PORT_ASSIGNMENTS.get("Frontend Dev Server", 6000))
        api_port = config.get("api_port", PORT_ASSIGNMENTS.get("GiljoAI Orchestrator", 7272))
        self.text.insert(tk.END, f"Dashboard: http://localhost:{dashboard_port}\n")
        self.text.insert(tk.END, f"API: http://localhost:{api_port}\n")
        self.text.insert(
            tk.END, f"WebSocket: ws://localhost:{config.get('websocket_port', api_port)}/ws\n"
        )

        self.text.config(state="disabled")

class ProgressPage(WizardPage):
    """Installation progress page with individual component progress bars"""

    def __init__(self, parent):
        super().__init__(parent, "Installation Progress")

        # Track if installation has started
        self.installation_started = False
        self.completed = False

        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Title
        title = ttk.Label(main_frame, text="Ready to Install", font=("Arial", 12, "bold"))
        title.pack(pady=(0, 10))
        self.title_label = title

        # Components frame with individual progress bars
        self.components_frame = ttk.LabelFrame(main_frame, text="Components to Install")
        self.components_frame.pack(fill="both", expand=False, pady=10)

        # Initialize component tracking
        self.components = {}
        self.component_widgets = {}
        self._init_components()

        # Install button frame
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(pady=10)

        self.install_button = tk.Button(
            button_frame,
            text="Install",
            command=self.start_installation,
            bg=COLORS['bg_elevated'], fg='#ffffff',
            font=('Segoe UI', 10, 'bold'), relief='flat', borderwidth=0,
            padx=30, pady=10, cursor='hand2',
            activebackground=COLORS['border'], activeforeground='#ffffff'
        )
        self.install_button.pack()

        # Console output section
        console_frame = ttk.LabelFrame(main_frame, text="Installation Log")
        console_frame.pack(fill="both", expand=True, pady=10)

        # Text widget with scrollbar
        console_container = ttk.Frame(console_frame)
        console_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.console_text = tk.Text(console_container, height=8, width=80, wrap=tk.WORD,
                                   bg=COLORS['bg_primary'],
                                   fg=COLORS['text_primary'],
                                   font=('Consolas', 9),
                                   insertbackground=COLORS['text_primary'],
                                   selectbackground=COLORS['bg_elevated'],
                                   selectforeground=COLORS['text_primary'])
        # Using tk.Scrollbar for full styling control
        scrollbar = tk.Scrollbar(console_container, command=self.console_text.yview,
                                bg=COLORS['bg_elevated'],  # Bar background
                                troughcolor=COLORS['bg_primary'],  # Trough background
                                activebackground=COLORS['text_primary'],  # Yellow when dragging
                                highlightthickness=0,
                                width=14)
        self.console_text.configure(yscrollcommand=scrollbar.set)

        self.console_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Configure text tags with GiljoAI colors
        self.console_text.tag_config("info", foreground=COLORS['text_light'])
        self.console_text.tag_config("success", foreground=COLORS['text_success'])
        self.console_text.tag_config("warning", foreground=COLORS['text_primary'])
        self.console_text.tag_config("error", foreground=COLORS['text_error'])
        self.console_text.tag_config("system", foreground=COLORS['text_secondary'])

        # Overall status
        self.status_var = tk.StringVar(value="Preparing installation...")
        overall_status = ttk.Label(main_frame, textvariable=self.status_var,
                                 font=("Arial", 10, "bold"))
        overall_status.pack(pady=10)

        # Overall progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(main_frame, variable=self.progress_var,
                                       maximum=100, length=400)
        self.progress.pack(pady=(0, 20))

        # Legacy compatibility - create hidden notebook elements
        self.notebook = None
        self.pg_text = self.console_text
        # Redis removed
        # Docker removed - not needed
        self.system_text = self.console_text
        self.pg_progress_var = tk.IntVar(value=0)
        # Redis progress removed
        # Docker progress removed
        self.pg_status_var = tk.StringVar()
        # Redis status removed
        # Docker status removed

        self.completed = False

    def _init_components(self):
        """Initialize component list - will be updated based on profile"""
        component_list = [
            ('venv', 'Python Virtual Environment'),
            ('dependencies', 'Server Dependencies'),
            ('config', 'Server Configuration'),
            ('database', 'Database Initialization'),
            ('registration', 'MCP Registration')
        ]

        for comp_id, label in component_list:
            # Create frame for component
            frame = ttk.Frame(self.components_frame)
            frame.pack(fill="x", padx=10, pady=5)

            # Component label
            name_label = ttk.Label(frame, text=label, width=25)
            name_label.pack(side="left", padx=(0, 10))

            # Progress bar (moved 30px to the right)
            progress_var = tk.IntVar(value=0)
            progress = ttk.Progressbar(frame, variable=progress_var,
                                      maximum=100, length=200)
            progress.pack(side="left", padx=(30, 10))

            # Status label
            status_var = tk.StringVar(value="Pending")
            status_label = ttk.Label(frame, textvariable=status_var, width=35)
            status_label.pack(side="left")

            # Store references
            self.components[comp_id] = {
                'label': label,
                'progress_var': progress_var,
                'status_var': status_var,
                'applicable': True
            }

            self.component_widgets[comp_id] = {
                'frame': frame,
                'progress': progress,
                'status': status_label,
                'name': name_label
            }

    def update_component_applicability(self, profile: str, config: dict = None):
        """Update which components are applicable based on profile and config"""
        # Database is always PostgreSQL now
        if config:
            pg_setup_mode = config.get('pg_setup_mode', 'existing')
            if pg_setup_mode == 'fresh':
                database_label = 'PostgreSQL Server Installation'
            else:
                database_label = 'PostgreSQL Database Configuration'
        else:
            database_label = 'PostgreSQL Database'

        rules = {
            'database': (database_label, True),
        }

        profile_rules = rules

        for comp_id, (label, applicable) in profile_rules.items():
            if comp_id in self.components:
                self.components[comp_id]['applicable'] = applicable
                self.components[comp_id]['label'] = label

                # Update UI
                widget = self.component_widgets[comp_id]
                widget['name'].configure(text=label)

                if not applicable:
                    self.components[comp_id]['status_var'].set("Not required for this profile")
                    widget['status'].configure(foreground="gray")
                    # Progress bars don't have a state parameter, skip configuration

    def log(self, message: str, target: str = "system"):
        """Log message to console and file"""
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"

        # Determine tag based on message content
        tag = "info"
        if any(word in message.lower() for word in ["success", "[OK]", "completed"]):
            tag = "success"
        elif any(word in message.lower() for word in ["error", "failed", "[ERROR]"]):
            tag = "error"
        elif any(word in message.lower() for word in ["warning", "issue"]):
            tag = "warning"

        # Write to file logger if available
        if hasattr(self, 'install_logger') and self.install_logger:
            # Determine log level
            if tag == "error":
                level = "ERROR"
            elif tag == "warning":
                level = "WARNING"
            elif tag == "success":
                level = "SUCCESS"
            elif target == "info":
                level = "INFO"
            else:
                level = "DEBUG" if target == "system" else "INFO"

            # Write to log file (remove formatting characters for cleaner logs)
            clean_message = message.replace("[OK]", "[OK]").replace("[ERROR]", "[FAIL]").replace("•", "-")
            self.install_logger.write(clean_message, level)

        # Display in GUI console
        self.console_text.insert(tk.END, formatted + "\n", tag)
        self.console_text.see(tk.END)
        self.update_idletasks()

    def set_progress(self, value: int, target: str = "main"):
        """Update progress for specific target"""
        if target == "main":
            self.progress_var.set(value)
        elif target == "postgresql":
            self.pg_progress_var.set(value)
            if 'database' in self.components:
                self.components['database']['progress_var'].set(value)
        # Redis removed - no longer needed
        # Docker progress removed
        elif target in self.components:
            self.components[target]['progress_var'].set(value)

        self._update_overall_progress()
        self.update_idletasks()

    def set_status(self, status: str, target: str = "main"):
        """Update status for specific target"""
        if target == "main":
            self.status_var.set(status)
        elif target == "postgresql":
            self.pg_status_var.set(status)
            if 'database' in self.components:
                self._update_component_status('database', status)
        # Redis removed - no longer needed
        # Docker status removed
        elif target in self.components:
            self._update_component_status(target, status)

        self.update_idletasks()

    def _update_component_status(self, comp_id: str, status: str):
        """Update component status with color coding"""
        if comp_id not in self.components:
            return

        self.components[comp_id]['status_var'].set(status)
        widget = self.component_widgets[comp_id]['status']

        # Color based on status
        if any(word in status.lower() for word in ["[OK]", "success", "completed", "installed"]):
            widget.configure(foreground="green")
        elif any(word in status.lower() for word in ["failed", "error"]):
            widget.configure(foreground="red")
        elif any(word in status.lower() for word in ["warning", "issue"]):
            widget.configure(foreground="orange")
        elif "not required" in status.lower():
            widget.configure(foreground="gray")
        else:
            widget.configure(foreground='#ffffff')  # White for default text on blue background

    def _update_overall_progress(self):
        """Calculate and update overall progress"""
        applicable = [c for c in self.components.values() if c.get('applicable', True)]
        if applicable:
            total = sum(c['progress_var'].get() for c in applicable)
            overall = total // len(applicable)
            self.progress_var.set(overall)

    def finalize_installation(self):
        """Finalize installation when a critical failure occurs"""
        # Log failure summary
        self.log("\n" + "="*60, "system")
        self.log("INSTALLATION FAILED", "error")
        self.log("="*60, "system")

        self.log("\nFailed Phases:", "error")
        for phase, status in self.phase_status.items():
            if not status and phase != 'registration':  # Registration is optional
                self.log(f"  - {phase.upper()}: FAILED", "error")

        if self.failure_reasons:
            self.log("\nFailure Details:", "error")
            for reason in self.failure_reasons:
                self.log(f"  - {reason}", "error")

        self.log("\nRecovery Instructions:", "info")
        self.log("1. Exit this installer", "info")
        self.log("2. Navigate to the project folder", "info")
        self.log("3. Run: python devuninstall.py", "info")
        self.log("4. Select option 2 to remove all files and databases", "info")
        self.log("5. Run the installer again: python bootstrap.py", "info")

        # Set final status
        self.set_progress(100)
        self.status_var.set("Installation FAILED - See log for details")

        # Close the installation logger
        if hasattr(self, 'install_logger') and self.install_logger:
            self.install_logger.close()
            self.log(f"\nFull log saved to: {self.install_logger.log_file}", "info")

        self.completed = True
        self.installation_failed = True

        # Re-enable navigation
        if hasattr(self.master, 'master') and hasattr(self.master.master, 'update_navigation'):
            self.master.master.after(100, self.master.master.update_navigation)

    def create_installation_manifest(self, config: dict, postgresql_installed: bool, redis_installed: bool=False):
        """Create installation manifest for uninstaller to track what was installed"""
        try:
            import json
            import subprocess
            from datetime import datetime

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

            # Determine PostgreSQL installation location based on platform
            pg_location = None
            pg_service = None
            if postgresql_installed:
                if sys.platform == "win32":
                    pg_location = "C:/PostgreSQL/16"
                    pg_service = "postgresql-x64-16"
                elif sys.platform == "darwin":
                    pg_location = "/usr/local/opt/postgresql@16"
                    pg_service = "postgresql"
                else:
                    pg_location = "/usr/lib/postgresql/16"
                    pg_service = "postgresql"

            manifest = {
                "version": "2.0",
                "installation_date": datetime.now().isoformat(),
                "installation_type": "gui",
                "deployment_mode": config.get("deployment_mode", "local"),
                "profile": config.get("profile", "developer"),  # Keep for compatibility
                "install_directory": str(Path.cwd()),
                "postgresql": {
                    "mode": "fresh" if postgresql_installed else "existing",
                    "installed": postgresql_installed,
                    "host": config.get("pg_host", "localhost"),
                    "port": config.get("pg_port", "5432"),
                    "database": config.get("pg_database", "giljo_mcp"),
                    "user": config.get("pg_user", "postgres"),
                    "network_mode": config.get("pg_network_mode", "localhost")
                },
                "dependencies": {
                    "postgresql": {
                        "installed": postgresql_installed,
                        "location": pg_location,
                        "service_name": pg_service
                    },
                    "python_packages": installed_packages
                },
                "configuration": {
                    "database_type": "postgresql",  # Always PostgreSQL now
                    "ports": {
                        "api": config.get("api_port", 7272),
                        "dashboard": config.get("dashboard_port", 6000),
                        "websocket": config.get("websocket_port", 6003),
                    }
                },
                "directories_created": [
                    "venv", "data", "logs", "backups",
                    ".giljo_mcp", ".giljo-config"
                ],
                "config_files_created": [
                    ".env", "config.yaml", ".giljo_install_manifest.json"
                ],
                "shortcuts_created": [
                    "Start GiljoAI Server.lnk",
                    "Stop GiljoAI Server.lnk",
                    "GiljoAI Dashboard.lnk"
                ] if sys.platform == "win32" else []
            }

            manifest_path = Path(".giljo_install_manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            self.log(f"Created installation manifest: {manifest_path}", "system")

        except Exception as e:
            self.log(f"Warning: Could not create installation manifest: {e}", "system")

    def start_installation(self):
        """Start the installation when user clicks Install"""
        if not self.installation_started:
            self.installation_started = True
            self.install_button.config(state="disabled", text="Installing...")
            self.title_label.config(text="Installing Components")
            self.components_frame.config(text="Installation Progress")

            # Run installation in thread
            import threading
            install_thread = threading.Thread(target=self.run_setup_internal, args=(self.config_data,))
            install_thread.daemon = True
            install_thread.start()

    def run_setup(self, config: dict):
        """Store config and update display, but don't start installation"""
        self.config_data = config
        profile = config.get("profile", "developer")

        # Update component display based on actual config
        self.update_component_applicability(profile, config)

        # Update component labels to show what will be installed
        for comp_id in self.components:
            if comp_id in self.component_widgets:
                label_text = self.components[comp_id]['label']
                self.component_widgets[comp_id]['name'].config(text=label_text)

        self.log(f"Ready to install for {profile} profile", "info")
        self.log("Click 'Install' to begin installation", "info")

    def run_setup_internal(self, config: dict):
        """Actually run installation based on profile and configuration"""
        import threading
        import time
        import subprocess
        import sys
        import os
        from pathlib import Path

        # Set environment variable to skip editable install (prevents Unicode errors)
        os.environ['GILJO_SKIP_EDITABLE_INSTALL'] = 'true'

        profile = config.get("profile", "developer")

        # Initialize installation logger
        self.install_logger = InstallationLogger()
        self.log(f"Installation log: {self.install_logger.log_file}", "info")
        self.log("", "system")  # Empty line for clarity

        self.log(f"Installing GiljoAI MCP Server", "system")
        self.log(f"Installation Mode: {profile}", "system")
        self.log("="*60, "system")

        # Update component applicability again with actual config
        self.update_component_applicability(profile, config)

        # Track installation success for all 5 required phases
        self.phase_status = {
            'venv': False,           # Phase 1: Virtual Environment
            'dependencies': False,   # Phase 2: Dependencies
            'config': False,         # Phase 3: Configuration
            'database': False,       # Phase 4: Database Setup
            'registration': False    # Phase 5: MCP Registration (optional but tracked)
        }
        self.installation_failed = False
        self.failure_reasons = []

        # Step 1: Create Python Virtual Environment
        self.set_status("Creating Python virtual environment...", "venv")
        self.set_progress(10, "venv")
        self.log("\n[PHASE 1: VIRTUAL ENVIRONMENT]", "info")
        self.log("Creating isolated Python environment for MCP server...", "system")

        # Define venv_path outside try block so it's accessible later
        venv_path = Path.cwd() / "venv"

        try:
            if not venv_path.exists():
                subprocess.run([sys.executable, "-m", "venv", "venv"], check=True)
                self.log("[OK] Virtual environment created", "success")
            else:
                self.log("[OK] Virtual environment already exists", "info")
            self.set_progress(100, "venv")
            self.set_status("Virtual environment ready [OK]", "venv")
            self.phase_status['venv'] = True
        except Exception as e:
            self.log(f"[ERROR] Failed to create virtual environment: {e}", "error")
            self.set_status(f"Virtual environment failed: {e}", "venv")
            self.installation_failed = True
            self.failure_reasons.append(f"Virtual Environment: {e}")
            # Don't continue if venv creation failed
            self.finalize_installation()
            return

        # Step 2: Install Dependencies
        self.set_status("Installing server dependencies...", "dependencies")
        self.set_progress(10, "dependencies")
        self.log("\n[PHASE 2: DEPENDENCIES]", "info")
        self.log("Installing required Python packages...", "system")

        try:
            # Determine pip path
            pip_path = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "pip"

            # Install requirements with streaming output and progress updates
            self.log("Installing from requirements.txt (this may take 2-5 minutes)...", "system")
            self.set_progress(15, "dependencies")

            # Start subprocess with live output streaming
            process = subprocess.Popen(
                [str(pip_path), "install", "-r", "requirements.txt"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Use threading for a timer-based progress update as fallback
            import threading
            current_progress = 15
            stop_timer = threading.Event()

            def update_progress_timer():
                nonlocal current_progress
                while not stop_timer.is_set() and current_progress < 45:
                    time.sleep(2)  # Update every 2 seconds
                    if not stop_timer.is_set():
                        current_progress = min(current_progress + 2, 45)
                        self.set_progress(current_progress, "dependencies")

            timer_thread = threading.Thread(target=update_progress_timer)
            timer_thread.daemon = True
            timer_thread.start()

            # Stream output and update progress
            package_count = 0
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Update progress based on package installation stages
                    if "Collecting" in line or "Downloading" in line:
                        package_count += 1
                        # Extract package name for display
                        package_name = extract_package_name(line)

                        # Progress from 15% to 45% during requirements.txt
                        progress = min(15 + (package_count * 0.5), 45)
                        current_progress = max(current_progress, progress)
                        self.set_progress(int(current_progress), "dependencies")

                        # Display package name with large package warning if applicable
                        if package_name:
                            # Check if it's a large package
                            is_large = False
                            for large_pkg in LARGE_PACKAGES:
                                if large_pkg.lower() in package_name.lower():
                                    is_large = True
                                    break

                            if is_large:
                                self.log(f"  Downloading: {package_name} (large package, please wait)", "info")
                            else:
                                self.log(f"  Downloading: {package_name}", "system")
                        elif package_count % 5 == 0:  # Fallback for unrecognized format
                            self.log(f"  Installing package {package_count}...", "system")
                    elif "Installing collected packages:" in line:
                        # Handle batch installation
                        packages = extract_packages_from_batch(line)
                        if packages:
                            package_count_batch = len(packages)
                            # Check for large packages in the batch
                            large_in_batch = []
                            for pkg in packages[:20]:  # Check first 20 packages
                                for large_pkg in LARGE_PACKAGES:
                                    if large_pkg.lower() in pkg.lower():
                                        large_in_batch.append(pkg)
                                        break

                            if large_in_batch:
                                self.log(f"Installing batch of {package_count_batch} packages (including large: {', '.join(large_in_batch[:3])}{'...' if len(large_in_batch) > 3 else ''})", "info")
                                self.log("This batch installation may take several minutes, please wait...", "warning")
                            else:
                                self.log(f"Installing batch of {package_count_batch} packages...", "info")
                                self.log("Processing dependencies, this may take a few minutes...", "system")

                            # Jump progress to show we're in batch mode
                            current_progress = max(current_progress, 35)
                            self.set_progress(current_progress, "dependencies")
                    elif "Successfully installed" in line:
                        self.log(f"  {line}", "system")
                    elif "ERROR" in line or "error" in line:
                        self.log(f"  {line}", "error")

            stop_timer.set()
            timer_thread.join(timeout=1)
            process.wait()
            if process.returncode != 0:
                raise Exception(f"pip install failed with code {process.returncode}")

            self.set_progress(50, "dependencies")

            # Install the package itself (skip if environment variable set)
            if not os.environ.get('GILJO_SKIP_EDITABLE_INSTALL'):
                self.log("Installing giljo_mcp package in editable mode...", "system")
                self.set_progress(55, "dependencies")

                process = subprocess.Popen(
                    [str(pip_path), "install", "-e", "."],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Timer-based progress for editable install
                current_editable_progress = 55
                stop_editable_timer = threading.Event()

                def update_editable_progress():
                    nonlocal current_editable_progress
                    while not stop_editable_timer.is_set() and current_editable_progress < 95:
                        time.sleep(1)  # Update every second
                        if not stop_editable_timer.is_set():
                            current_editable_progress = min(current_editable_progress + 3, 95)
                            self.set_progress(current_editable_progress, "dependencies")

                editable_timer = threading.Thread(target=update_editable_progress)
                editable_timer.daemon = True
                editable_timer.start()

                # Update progress during editable install
                stage_count = 0
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        if "Building" in line or "Installing" in line or "Processing" in line:
                            stage_count += 1
                            # Progress from 55% to 95% during editable install
                            progress = min(55 + (stage_count * 10), 95)
                            current_editable_progress = max(current_editable_progress, progress)
                            self.set_progress(current_editable_progress, "dependencies")
                        if "Successfully installed" in line or "ERROR" in line:
                            self.log(f"  {line}", "system")

                stop_editable_timer.set()
                editable_timer.join(timeout=1)
                process.wait()
                if process.returncode != 0:
                    raise Exception(f"Editable install failed with code {process.returncode}")

                self.set_progress(100, "dependencies")
            else:
                self.log("Skipping editable install (GILJO_SKIP_EDITABLE_INSTALL set)", "info")
                self.set_progress(100, "dependencies")

            self.log("All dependencies installed successfully", "success")
            self.set_status("Dependencies installed", "dependencies")
            self.phase_status['dependencies'] = True
        except Exception as e:
            self.log(f"Failed to install dependencies: {e}", "error")
            self.set_status(f"Dependencies failed: {e}", "dependencies")
            self.installation_failed = True
            self.failure_reasons.append(f"Dependencies: {e}")

        # PostgreSQL is always used, but user installs it manually
        # (Logging moved to after schema initialization for proper status tracking)

        # Step 3: Create configuration files
        self.set_status("Creating server configuration...", "config")
        self.set_progress(10, "config")
        self.log("\n[PHASE 3: SERVER CONFIGURATION]", "info")
        self.log("Creating configuration files...", "system")

        try:
            from setup_config import ConfigurationManager

            config_mgr = ConfigurationManager()

            # Prepare config values - PostgreSQL only now
            config_values = {
                "database_type": "postgresql",  # Always PostgreSQL
                "api_port": config.get("api_port", 7272),
                "websocket_port": config.get("websocket_port", 6003),
                "dashboard_port": config.get("dashboard_port", 6000),
                "server_port": config.get("server_port", 6001),
                "redis_enabled": False,  # Redis removed - not needed
                "redis_host": "",
                "redis_port": 0,
                "jwt_secret": config.get("jwt_secret", ""),
                "api_key": config.get("api_key", ""),
                "api_key_enabled": profile in ["team", "enterprise"],
                # PostgreSQL configuration
                "pg_host": config.get("pg_host", "localhost"),
                "pg_port": config.get("pg_port", 5432),
                "pg_database": config.get("pg_database", "giljo_mcp"),
                "pg_user": config.get("pg_user", "postgres"),
                "pg_password": config.get("pg_password", ""),
            }

            # Generate .env file
            env_result = config_mgr.generate_from_profile(profile, config_values)
            if env_result:
                self.log("SUCCESS: Generated .env file", "system")
                self.set_progress(50, "config")

            # Generate config.yaml
            yaml_result = config_mgr.generate_yaml_config(config_values)
            if yaml_result:
                self.log("SUCCESS: Generated config.yaml", "system")
                self.set_progress(100, "config")
                self.set_status("Configuration files created [OK]", "config")

            # Validate configuration
            is_valid, errors = config_mgr.validate_configuration(config_values)
            if is_valid:
                self.log("SUCCESS: Configuration validated", "system")
                self.phase_status['config'] = True
            else:
                for error in errors:
                    self.log(f"Configuration error: {error}", "system")
                self.installation_failed = True
                self.failure_reasons.append(f"Configuration validation: {', '.join(errors)}")

        except Exception as e:
            self.log(f"Configuration error: {e}", "system")
            self.set_status(f"Configuration failed: {e}", "config")
            self.installation_failed = True
            self.failure_reasons.append(f"Configuration: {e}")

        # Setup directories
        self.set_status("Setting up directories...", "directories")
        self.set_progress(10, "directories")
        self.log("Setting up directories...", "system")

        try:
            from pathlib import Path

            directories = [
                "data", "logs", "backups", "temp",
                "src/giljo_mcp", "api", "frontend/dist",
                "scripts", "docker", "tests"
            ]

            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)
                self.set_progress(min(100, 10 + (90 * directories.index(directory) // len(directories))), "directories")

            self.log("SUCCESS: Directory structure created", "system")
            self.set_status("Directories created [OK]", "directories")
            self.set_progress(100, "directories")

        except Exception as e:
            self.log(f"Directory setup error: {e}", "system")
            self.set_status(f"Directory setup failed: {e}", "directories")

        # Install Python packages
        self.set_status("Installing Python packages...", "packages")
        self.set_progress(10, "packages")
        self.log("Installing Python packages...", "system")

        try:
            import subprocess
            import threading

            # Install requirements.txt with live output
            self.log("Installing requirements.txt (this may take 2-5 minutes)...", "system")
            self.log("Downloading and installing packages...", "system")
            self.set_progress(20, "packages")

            # Start subprocess with live output streaming
            process = subprocess.Popen(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )

            # Stream output line by line
            package_count = 0
            for line in process.stdout:
                line = line.strip()
                if line:
                    # Show condensed output for key operations
                    if "Collecting" in line or "Downloading" in line:
                        # Extract clean package name
                        package_name = extract_package_name(line)
                        package_count += 1

                        # Display package name with large package warning if applicable
                        if package_name:
                            # Check if it's a large package
                            is_large = False
                            for large_pkg in LARGE_PACKAGES:
                                if large_pkg.lower() in package_name.lower():
                                    is_large = True
                                    break

                            if is_large:
                                self.log(f"  Downloading: {package_name} (large package, please wait)", "info")
                            else:
                                self.log(f"  Downloading: {package_name}", "system")
                        else:
                            # Fallback if extraction failed
                            self.log(f"  Downloading package {package_count}...", "system")

                        # Update progress incrementally (20% to 60% over ~100 packages)
                        progress = min(20 + (package_count * 0.4), 60)
                        self.set_progress(int(progress), "packages")
                    elif "Installing collected packages:" in line:
                        # Handle batch installation
                        packages = extract_packages_from_batch(line)
                        if packages:
                            package_count_batch = len(packages)
                            # Check for large packages in the batch
                            large_in_batch = []
                            for pkg in packages[:20]:  # Check first 20 packages
                                for large_pkg in LARGE_PACKAGES:
                                    if large_pkg.lower() in pkg.lower():
                                        large_in_batch.append(pkg)
                                        break

                            if large_in_batch:
                                self.log(f"Installing batch of {package_count_batch} packages (including large: {', '.join(large_in_batch[:3])}{'...' if len(large_in_batch) > 3 else ''})", "info")
                                self.log("This batch installation may take several minutes, please wait...", "warning")
                            else:
                                self.log(f"Installing batch of {package_count_batch} packages...", "info")
                                self.log("Processing dependencies, this may take a few minutes...", "system")

                            # Jump progress to show we're in batch mode
                            progress = min(50, progress + 5)
                            self.set_progress(int(progress), "packages")
                    elif "Installing" in line and "collected" in line:
                        self.log(f"  {line}", "system")
                    elif "Successfully installed" in line:
                        self.log(f"  {line}", "system")
                    elif "ERROR" in line or "error" in line:
                        self.log(f"  {line}", "system")

            process.wait()

            if process.returncode == 0:
                self.log("SUCCESS: All requirements installed", "system")
                self.set_progress(60, "packages")
            else:
                self.log(f"Warning: Requirements installation completed with return code {process.returncode}", "system")

            # Install giljo-mcp package in editable mode (skip if environment variable set)
            if not os.environ.get('GILJO_SKIP_EDITABLE_INSTALL'):
                self.log("Installing giljo-mcp package in development mode...", "system")
                self.set_progress(70, "packages")

                process = subprocess.Popen(
                    [sys.executable, "-m", "pip", "install", "-e", ".", "--no-deps"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    universal_newlines=True
                )

                # Stream editable install output
                for line in process.stdout:
                    line = line.strip()
                    if line:
                        if "Successfully installed" in line or "Preparing" in line or "Building" in line:
                            self.log(f"  {line}", "system")

                process.wait()

                if process.returncode == 0:
                    self.log("SUCCESS: giljo-mcp package installed", "system")
                    self.set_progress(100, "packages")
                    self.set_status("Python packages installed [OK]", "packages")
                else:
                    self.log(f"Warning: giljo-mcp installation completed with return code {process.returncode}", "system")
                    self.set_status("Package installation completed with warnings", "packages")
            else:
                self.log("Skipping editable install (GILJO_SKIP_EDITABLE_INSTALL set)", "system")
                self.set_progress(100, "packages")
                self.set_status("Python packages installed [OK]", "packages")

        except Exception as e:
            self.log(f"Package installation error: {e}", "system")
            self.set_status(f"Package installation failed: {e}", "packages")

        # Initialize database schema
        self.set_status("Initializing database schema...", "schema")
        self.set_progress(10, "schema")
        self.log("Initializing database schema...", "system")

        try:
            # Try to import and initialize database
            try:
                # Database models will be initialized on first run
                # No need to import here as package may not be installed yet
                self.log("Database schema will be initialized on first run", "system")
                self.set_status("Database schema ready for initialization", "schema")
            except ImportError as ie:
                # If models don't exist yet, that's okay for initial installation
                self.log("Database models not yet configured (this is normal for first installation)", "system")
                self.set_status("Database schema will be initialized on first run", "schema")
            self.set_progress(100, "schema")

        except Exception as e:
            self.log(f"Database schema error: {e}", "system")
            self.set_status(f"Schema initialization warning: {e}", "schema")
            self.set_progress(100, "schema")  # Continue anyway

        # PostgreSQL database configuration - mark as complete since user configured it
        self.log("\n[DATABASE MODE: PostgreSQL]", "system")
        self.log("Using PostgreSQL database (user-installed and configured)", "system")
        self.set_status("PostgreSQL configured [OK]", "database")
        self.set_progress(100, "database")
        self.phase_status['database'] = True  # Mark database phase as complete

        # PostgreSQL installation is now manual (not automatic)
        # Users install PostgreSQL themselves using the Database Configuration page
        run_postgresql = False

        # Run parallel installations
        threads = []

        if run_postgresql:

            def install_postgresql():
                try:
                    from installer.dependencies.postgresql import PostgreSQLInstaller, PostgreSQLConfig

                    self.set_status("Installing PostgreSQL...", "database")

                    pg_config = PostgreSQLConfig(
                        version="16.0",
                        port=int(config.get("pg_port", 5432)),
                        data_dir="C:/PostgreSQL/16/data",
                        install_dir="C:/PostgreSQL/16",
                    )

                    def postgresql_progress(progress, message):
                        self.set_progress(progress, "database")
                        self.log(message, "postgresql")

                    installer = PostgreSQLInstaller(pg_config, progress_callback=postgresql_progress)

                    if installer.is_postgresql_installed():
                        self.log("PostgreSQL already installed, verifying...", "postgresql")
                        if installer.test_connection():
                            self.log("PostgreSQL connection successful", "postgresql")
                            self.set_progress(100, "database")
                        else:
                            self.log("PostgreSQL connection failed, reinstalling...", "postgresql")
                            installer.install()
                    else:
                        result = installer.install()
                        self.log(f"PostgreSQL installed: {result.connection_string}", "postgresql")

                    self.set_status("PostgreSQL installed [OK]", "database")
                    self.set_progress(100, "database")

                except Exception as e:
                    self.log(f"PostgreSQL installation error: {e}", "postgresql")
                    self.set_status(f"Failed: {e}", "database")

            pg_thread = threading.Thread(target=install_postgresql)
            threads.append(pg_thread)

        # Redis removed - not needed for simplified installation

        # Start all installation threads
        for thread in threads:
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Verify installations
        self.set_status("Verifying installations...", "validation")
        self.set_progress(10, "validation")
        self.log("Verifying installations...", "system")

        try:
            from installer.health_checker import HealthChecker

            checker = HealthChecker()

            self.log("Health check: Starting health checks...", "system")

            # Check PostgreSQL
            self.log("Health check: Checking PostgreSQL...", "system")
            self.set_progress(25, "validation")
            pg_status, pg_msg = checker.check_postgresql(run_postgresql)

            # Redis check removed - not needed
            self.set_progress(50, "validation")
            redis_status, redis_msg = "SUCCESS", "Redis not required (removed from installation)"

            # Check Ports
            self.log("Health check: Checking Ports...", "system")
            self.set_progress(75, "validation")
            ports_status, ports_msg = checker.check_ports(config)

            # Check File System
            self.log("Health check: Checking File System...", "system")
            self.set_progress(90, "validation")
            fs_status, fs_msg = checker.check_filesystem()

            self.log("Health check: Health checks complete", "system")

            # Log results
            results = [
                ("PostgreSQL", pg_status, pg_msg),
                ("Port Configuration", ports_status, ports_msg),
                ("File System", fs_status, fs_msg)
            ]

            all_success = True
            issues = []

            for component, status, message in results:
                status_str = "SUCCESS" if status else "FAILED"
                self.log(f"  {status_str} {component}: {message}", "system")
                if not status and component != "File System":  # File system warnings are acceptable
                    all_success = False
                    issues.append(component)

                # Track PostgreSQL status for phase 4
                if component == "PostgreSQL":
                    self.phase_status['database'] = status
                    if not status:
                        self.installation_failed = True
                        self.failure_reasons.append(f"Database: {message}")

            if issues:
                self.log(f"WARNING: Issues detected: {', '.join(issues)}", "system")
                self.set_status(f"Completed with warnings: {', '.join(issues)}", "validation")
            else:
                self.log("SUCCESS: All components installed successfully", "system")
                self.set_status("All validations passed [OK]", "validation")

            self.set_progress(100, "validation")

            # Update overall status - check all critical phases
            critical_phases_ok = (
                self.phase_status.get('venv', False) and
                self.phase_status.get('dependencies', False) and
                self.phase_status.get('config', False) and
                self.phase_status.get('database', False)
            )

            # Ensure main progress bar reaches 100%
            self.set_progress(100)
            self.progress_var.set(100)  # Explicitly set main progress to 100%
            if critical_phases_ok and not self.installation_failed:
                completion_msg = "Installation completed successfully!"
                self.status_var.set(completion_msg)
            else:
                completion_msg = "Installation FAILED - See log for details"
                self.status_var.set(completion_msg)
                self.installation_failed = True

            # Log final message
            self.log("\n" + "="*60, "system")
            if self.installation_failed:
                self.log(completion_msg, "error")
                self.log("Click 'Finish' to see failure details and recovery instructions.", "error")
            else:
                self.log(completion_msg, "success" if not issues else "warning")
                self.log("Click 'Finish' to complete the setup.", "info")
            self.log("="*60, "system")

            # Close the installation logger
            if hasattr(self, 'install_logger') and self.install_logger:
                self.install_logger.close()
                self.log(f"\nFull installation log saved to: {self.install_logger.log_file}", "info")

            self.completed = True

            # Re-enable navigation
            if hasattr(self.master, 'master') and hasattr(self.master.master, 'update_navigation'):
                self.master.master.after(100, self.master.master.update_navigation)

            # Create installation manifest for uninstaller
            try:
                self.create_installation_manifest(config, run_postgresql, False)
            except Exception as manifest_error:
                self.log(f"Warning: Could not create manifest: {manifest_error}", "system")
                # Not critical - continue

            # Create desktop shortcuts
            self.log("\nCreating desktop shortcuts...", "system")
            try:
                # First check if pywin32 is available (required for Windows shortcuts)
                if platform.system() == "Windows":
                    try:
                        import win32com.client
                        pywin32_available = True
                    except ImportError:
                        pywin32_available = False
                        self.log("Note: pywin32 not available for creating shortcuts", "warning")
                        self.log("You can create shortcuts manually from the installation folder", "info")
                else:
                    pywin32_available = True  # Not needed on other platforms

                if pywin32_available:
                    from create_shortcuts import create_shortcuts, add_to_startup_windows
                    shortcuts = create_shortcuts()
                    if shortcuts:
                        self.log(f"[OK] Created {len(shortcuts)} desktop shortcuts", "success")
                        self.log("  • Start Server - Launch the MCP server", "info")
                        self.log("  • Stop Server - Shutdown the server", "info")
                        self.log("  • Connect Project - Connect projects to server", "info")
                        self.log("  • Check Status - View server status", "info")
                    else:
                        self.log("Desktop shortcuts could not be created", "warning")
                        self.log("You can use the batch files in the installation folder instead", "info")
            except ImportError as import_error:
                self.log(f"Note: Could not import shortcuts module: {import_error}", "warning")
                self.log("Desktop shortcuts can be created manually from the installation folder", "info")
            except Exception as shortcut_error:
                self.log(f"Warning: Could not create shortcuts: {shortcut_error}", "warning")
                self.log("You can use the batch files in the installation folder instead", "info")

            # Register with AI CLI tools using UniversalMCPInstaller
            self.log("\nChecking AI tool integration...", "system")
            try:
                from installer.universal_mcp_installer import UniversalMCPInstaller

                installer = UniversalMCPInstaller()

                # Detect installed AI CLI tools
                detected_tools = installer.detect_installed_tools()

                if not detected_tools:
                    self.log("No AI CLI tools detected - skipping MCP registration", "info")
                    self.log("You can register AI tools later using: python register_ai_tools.py", "info")
                    # Mark registration as complete (optional step)
                    self.set_status("[WARNING] No AI tools detected - Optional", "registration")
                    self.set_progress(100, "registration")
                else:
                    tool_display_names = {
                        'claude': 'Claude Code',
                        # TECHDEBT: Multi-tool support disabled - see TECHDEBT.md
                        # 'codex': 'Codex CLI (OpenAI)',
                        # 'gemini': 'Gemini CLI (Google)'
                    }

                    self.log(f"Detected {len(detected_tools)} AI CLI tool(s):", "system")
                    for tool in detected_tools:
                        self.log(f"  * {tool_display_names.get(tool, tool)}", "info")

                    # Prepare server configuration - access parent GiljoSetupGUI instance
                    parent = self.parent
                    while parent and not hasattr(parent, "config_data"):
                        parent = parent.master

                    server_url = 'http://localhost:8000'
                    if parent and hasattr(parent, "config_data"):
                        deployment_mode = parent.config_data.get('deployment_mode', 'LOCAL')
                        if deployment_mode == 'SERVER':
                            host = parent.config_data.get('host', 'localhost')
                            port = parent.config_data.get('server_port', 8000)
                            server_url = f"http://{host}:{port}"
                    else:
                        deployment_mode = 'LOCAL'

                    # Register with all detected tools
                    self.log("\nRegistering GiljoAI MCP server...", "system")
                    results = installer.register_all(
                        server_name="giljo-mcp",
                        command="python",
                        args=["-m", "giljo_mcp"],
                        env={
                            "GILJO_SERVER_URL": server_url,
                            "GILJO_MODE": deployment_mode
                        }
                    )

                    # Report results
                    success_count = 0
                    self.log("\nRegistration results:", "system")
                    for tool, success in results.items():
                        tool_name = tool_display_names.get(tool, tool)
                        if success:
                            self.log(f"  [OK] {tool_name}: Successfully registered", "success")
                            success_count += 1
                        else:
                            self.log(f"  [WARNING] {tool_name}: Registration failed", "warning")

                    if success_count > 0:
                        self.log(f"\nSuccessfully registered with {success_count} tool(s)!", "success")
                        self.log("Please restart your AI CLI tool(s) to activate the MCP server.", "info")
                        # Update registration component status
                        self.set_status("[OK] Completed", "registration")
                        self.set_progress(100, "registration")
                    else:
                        self.log("MCP registration failed for all tools", "warning")
                        self.log("You can register manually later: python register_ai_tools.py", "info")
                        # Update registration component status as optional failure
                        self.set_status("[WARNING] Optional - Manual registration available", "registration")
                        self.set_progress(100, "registration")

            except Exception as e:
                self.log(f"MCP registration error: {e}", "warning")
                self.log("You can register manually later: python register_ai_tools.py", "info")
                # Update registration component status as optional failure
                self.set_status("[WARNING] Optional - Manual registration available", "registration")
                self.set_progress(100, "registration")

        except Exception as e:
            self.log(f"Health check error: {e}", "system")
            self.set_status(f"Validation failed: {e}", "validation")
            self.completed = True


class GiljoSetupGUI:
    """Main GUI setup wizard"""

    def __init__(self, root):
        self.root = root
        self.root.title("GiljoAI MCP Setup Wizard")
        self.root.geometry("1200x1050")  # Increased by 50% for DPI scaling
        self.root.resizable(True, True)

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (1200 // 2)
        y = (self.root.winfo_screenheight() // 2) - (1050 // 2)
        self.root.geometry(f"1200x1050+{x}+{y}")  # Increased by 50% for DPI scaling

        # Configure GiljoAI color theme
        style = ttk.Style()
        # Use default theme as base (better Windows compatibility)

        # Fix font rendering - use system default fonts for crisp text
        import tkinter.font as tkfont
        default_font = tkfont.nametofont("TkDefaultFont")
        default_font.configure(family="Segoe UI", size=9)  # Windows default
        text_font = tkfont.nametofont("TkTextFont")
        text_font.configure(family="Segoe UI", size=9)

        # Configure root window background
        self.root.configure(bg=COLORS['bg_primary'])

        # Configure ttk widget styles
        style.configure('TFrame', background=COLORS['bg_primary'])
        style.configure('TLabel',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'])
        style.configure('TLabelframe',
                       background=COLORS['bg_primary'],
                       foreground='#ffffff',  # White text for frame labels
                       bordercolor='#ffc300',  # Yellow borders
                       relief='solid')
        style.configure('TLabelframe.Label',
                       background=COLORS['bg_primary'],
                       foreground='#ffffff',  # White text
                       font=('Segoe UI', 9, 'bold'))

        # Specific style for yellow-bordered frames
        style.configure('Yellow.TLabelframe',
                       background=COLORS['bg_primary'],
                       foreground='#ffffff',
                       bordercolor='#ffc300',
                       borderwidth=2,
                       relief='solid')
        style.configure('Yellow.TLabelframe.Label',
                       background=COLORS['bg_primary'],
                       foreground='#ffffff',
                       font=('Segoe UI', 9, 'bold'))

        # Button styles - #1e3147 background with white text
        style.configure('TButton',
                       background='#1e3147',
                       foreground='#ffffff',  # White text
                       bordercolor='#1e3147',
                       lightcolor='#1e3147',
                       darkcolor='#1e3147',
                       relief='raised',
                       font=('Segoe UI', 9))
        style.map('TButton',
                 background=[('active', '#315074'), ('pressed', '#0e1c2d')],
                 foreground=[('active', '#ffffff'), ('pressed', '#ffffff')])

        # Entry/Input styles - #315074 background with black text
        style.configure('TEntry',
                       fieldbackground='#315074',
                       foreground='#000000',  # Black text
                       insertcolor='#000000',  # Black cursor
                       bordercolor='#ffc300',
                       font=('Segoe UI', 9))

        # Radiobutton styles
        style.configure('TRadiobutton',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'])

        # Checkbutton styles
        style.configure('TCheckbutton',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'])

        # Progress bar styles
        style.configure('Horizontal.TProgressbar',
                       background=COLORS['text_primary'],
                       troughcolor=COLORS['bg_elevated'],
                       bordercolor=COLORS['border'],
                       lightcolor=COLORS['text_primary'],
                       darkcolor=COLORS['text_primary'])

        # Scrollbar styles - #1e3147 bar with yellow indicators
        style.configure('Vertical.TScrollbar',
                       background='#1e3147',  # Bar color
                       troughcolor=COLORS['bg_primary'],
                       bordercolor='#1e3147',
                       arrowcolor='#ffc300')  # Yellow arrows
        style.map('Vertical.TScrollbar',
                 background=[('active', '#ffc300')],  # Yellow when active
                 arrowcolor=[('active', '#ffc300')])

        # Set window icon (if available)
        try:
            icon_path = Path("frontend/public/favicon.ico")
            if icon_path.exists():
                self.root.iconbitmap(str(icon_path))
        except:
            pass

        self.config_data = {}
        self.current_page_index = 0

        # Main container
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Content area with scrollbar support
        self.content_container = ttk.Frame(self.main_frame)
        self.content_container.pack(fill="both", expand=True)

        # Add canvas and scrollbar for scrollable content
        self.canvas = tk.Canvas(self.content_container,
                               highlightthickness=0,
                               bg=COLORS['bg_primary'])
        # Using tk.Scrollbar for full styling control
        self.scrollbar = tk.Scrollbar(self.content_container, orient="vertical", command=self.canvas.yview,
                                     bg=COLORS['bg_elevated'],  # Bar background
                                     troughcolor=COLORS['bg_primary'],  # Trough (track) background
                                     activebackground=COLORS['text_primary'],  # Yellow when dragging
                                     highlightthickness=0,
                                     width=14)
        self.content_frame = ttk.Frame(self.canvas)

        # Configure canvas
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas_window = self.canvas.create_window(0, 0, anchor="nw", window=self.content_frame)

        # Pack canvas and scrollbar
        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Bind to configure scrollregion when content changes
        self.content_frame.bind("<Configure>", self._on_frame_configure)
        self.canvas.bind("<Configure>", self._on_canvas_configure)

        # Bind mouse wheel for scrolling
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        # Create pages with correct parent (content_frame)
        self.pages = [
            WelcomePage(self.content_frame),  # New welcome page with logo
            ProfileSelectionPage(self.content_frame),
            DatabasePage(self.content_frame),
            PortsPage(self.content_frame),
            SecurityPage(self.content_frame),
            ReviewPage(self.content_frame, lambda: self.config_data),
            ProgressPage(self.content_frame)
        ]

        # Navigation buttons
        self.nav_frame = ttk.Frame(self.main_frame)
        self.nav_frame.pack(fill="x", pady=(10, 0))

        # Using tk.Button instead of ttk.Button for full styling control
        button_style = {
            'bg': COLORS['bg_elevated'],  # #1e3147
            'fg': '#ffffff',  # White text
            'font': ('Segoe UI', 9),
            'relief': 'flat',
            'borderwidth': 0,
            'padx': 20,
            'pady': 8,
            'cursor': 'hand2',
            'activebackground': COLORS['border'],  # Slightly lighter on hover
            'activeforeground': '#ffffff'
        }

        self.back_btn = tk.Button(self.nav_frame, text="< Back", command=self.go_back, **button_style)
        self.back_btn.pack(side="left")

        self.next_btn = tk.Button(self.nav_frame, text="Next >", command=self.go_next, **button_style)
        self.next_btn.pack(side="right")

        self.cancel_btn = tk.Button(self.nav_frame, text="Cancel", command=self.cancel_setup, **button_style)
        self.cancel_btn.pack(side="right", padx=(0, 10))

        # Show first page
        self.show_page(0)

    def _on_frame_configure(self, event):
        """Update scroll region when frame size changes"""
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        """Update canvas window width when canvas size changes"""
        canvas_width = event.width
        self.canvas.itemconfig(self.canvas_window, width=canvas_width)

    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def show_page(self, index):
        """Display a specific page"""
        # Hide current page
        for page in self.pages:
            page.pack_forget()

        # Show new page
        if 0 <= index < len(self.pages):
            self.current_page_index = index
            page = self.pages[index]
            page.pack(fill="both", expand=True, in_=self.content_frame)

            # Call page enter event
            if hasattr(page, 'on_enter'):
                page.on_enter()

            # Update navigation buttons
            self.update_navigation()

            # Update window title
            self.root.title(f"GiljoAI MCP Setup - {page.title}")

            # Reset scroll position to top
            self.canvas.yview_moveto(0)

    def update_navigation(self):
        """Update navigation button states"""
        # Back button
        if self.current_page_index == 0:
            self.back_btn.config(state="disabled")
        else:
            self.back_btn.config(state="normal")

        # Next button
        current_page = self.pages[self.current_page_index]

        if self.current_page_index == len(self.pages) - 1:
            self.next_btn.config(text="Finish", state="normal")
        elif isinstance(current_page, ProgressPage):
            # Enable/disable Next based on installation status
            if hasattr(current_page, 'completed') and current_page.completed:
                self.next_btn.config(text="Next >", state="normal")
            elif hasattr(current_page, 'installation_started') and current_page.installation_started:
                self.next_btn.config(state="disabled")  # Disable during installation
            else:
                self.next_btn.config(state="disabled")  # Disable until installation starts
        else:
            self.next_btn.config(text="Next >", state="normal")

    def go_back(self):
        """Go to previous page"""
        if self.current_page_index > 0:
            # Save current page data
            current_page = self.pages[self.current_page_index]
            if hasattr(current_page, 'on_exit'):
                current_page.on_exit()

            self.show_page(self.current_page_index - 1)

    def go_next(self):
        """Go to next page"""
        current_page = self.pages[self.current_page_index]

        # Validate current page
        if hasattr(current_page, 'validate') and not current_page.validate():
            messagebox.showerror("Validation Error", "Please correct the errors on this page before continuing.")
            return

        # Save page data
        if hasattr(current_page, 'get_data'):
            page_data = current_page.get_data()
            self.config_data.update(page_data)

        if hasattr(current_page, 'on_exit'):
            current_page.on_exit()

        # Handle special pages
        if self.current_page_index == len(self.pages) - 1:
            # Finish button clicked
            self.finish_setup()
            return
        elif isinstance(current_page, ReviewPage):
            # Move to progress page and prepare for installation
            progress_page = self.pages[self.current_page_index + 1]
            if isinstance(progress_page, ProgressPage):
                self.show_page(self.current_page_index + 1)
                # Just prepare the installation, don't start it
                progress_page.run_setup(self.config_data)
                return

        # Normal page transition
        if self.current_page_index < len(self.pages) - 1:
            self.show_page(self.current_page_index + 1)

    # run_installation method removed - installation now starts via Install button

    def cancel_setup(self):
        """Cancel the setup wizard"""
        if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel the setup?"):
            self.root.quit()
            self.root.destroy()
            sys.exit(1)

    def show_failure_window(self, progress_page):
        """Show failure window with recovery instructions"""
        install_path = Path.cwd()

        # Build failure message
        message = "GiljoAI MCP Installation Failed\n"
        message += "="*50 + "\n\n"
        message += "The installation could not be completed due to the following errors:\n\n"

        # Show which phases failed
        message += "FAILED PHASES:\n"
        for phase, status in progress_page.phase_status.items():
            if not status and phase != 'registration':  # Registration is optional
                phase_name = phase.replace('_', ' ').title()
                message += f"  [X] {phase_name}\n"

        message += "\nFAILURE DETAILS:\n"
        if progress_page.failure_reasons:
            for reason in progress_page.failure_reasons[:5]:  # Show first 5 reasons
                message += f"  - {reason}\n"
        else:
            message += "  - Check the installation log for details\n"

        message += "\n" + "="*50 + "\n"
        message += "RECOVERY INSTRUCTIONS:\n\n"
        message += "1. Close this installer\n\n"
        message += "2. Open a terminal/command prompt\n\n"
        message += f"3. Navigate to: {install_path}\n\n"
        message += "4. Run the uninstaller:\n"
        message += "   python devuninstall.py\n\n"
        message += "5. Select option 2 to remove all files and databases\n\n"
        message += "6. Run the installer again:\n"
        message += "   python bootstrap.py\n\n"
        message += "="*50 + "\n"
        message += f"Installation log: {install_path}\\install.log\n"
        message += "\nContact support: infoteam@giljo.ai"

        # Show failure dialog
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("Installation Failed")
            dialog.transient(self.root)
            dialog.resizable(False, False)

            # Size and center the dialog
            dialog.update_idletasks()
            w = 700
            h = 750
            x = (dialog.winfo_screenwidth() // 2) - (w // 2)
            y = (dialog.winfo_screenheight() // 2) - (h // 2)
            dialog.geometry(f"{w}x{h}+{x}+{y}")

            # Create scrollable text widget for the message
            body = ttk.Frame(dialog, padding=(20, 20))
            body.pack(fill="both", expand=True)

            # Use Text widget for better formatting and scrolling
            text_widget = tk.Text(body,
                                 wrap=tk.WORD,
                                 width=80,
                                 height=35,
                                 bg=COLORS.get('bg_secondary', '#182739'),
                                 fg=COLORS.get('text_error', '#c6298c'),
                                 font=('Consolas', 10))
            text_widget.pack(fill="both", expand=True)

            # Insert the message
            text_widget.insert("1.0", message)
            text_widget.config(state="disabled")  # Make read-only

            # Add scrollbar
            scrollbar = ttk.Scrollbar(text_widget, command=text_widget.yview)
            scrollbar.pack(side="right", fill="y")
            text_widget.config(yscrollcommand=scrollbar.set)

            # Exit button
            s = ttk.Style(dialog)
            s.configure('FailureExit.TButton', foreground='#000000')
            s.map('FailureExit.TButton', foreground=[('active', '#000000'), ('pressed', '#000000')])

            exit_btn = ttk.Button(dialog,
                                text="Exit Installer",
                                command=lambda: [dialog.destroy(), self.root.quit()],
                                style='FailureExit.TButton')
            exit_btn.pack(pady=(10, 20))

            # Make modal
            dialog.grab_set()
            self.root.wait_window(dialog)

        except Exception as e:
            # Fallback to messagebox
            messagebox.showerror("Installation Failed", message)
            self.root.quit()

        # Exit with error code
        self.root.destroy()
        sys.exit(1)

    def finish_setup(self):
        """Complete the setup process"""
        # Check if installation failed
        progress_page = None
        for page in self.pages:
            if isinstance(page, ProgressPage):
                progress_page = page
                break

        if progress_page and hasattr(progress_page, 'installation_failed') and progress_page.installation_failed:
            self.show_failure_window(progress_page)
            return

        # Get installation path and port number
        install_path = Path.cwd()
        server_port = self.config_data.get('server_port', 7272)

        # Create completion message with updated text
        message = f"""GiljoAI Agent Orchestration MCP Server
Installation Complete!

SERVER INSTALLED AT: {install_path}

This is a standalone MCP orchestration server that will coordinate multiple AI agents across all your development projects.

NEXT STEPS:
            ════════════════════

1. CONNECT YOUR AI CODING AGENT:

Only Claude Code is currently supported.
The installer attempted auto configuration for you.

If registration failed, please run:
• python {install_path}\\register_ai_tools.py

Note: Support for Codex CLI and Gemini CLI in 2026

Documentation:
{install_path}\\docs

2. START THE SERVER:
Run: {install_path}\\start_giljo.bat
Server will run at http://localhost:{server_port}

3. VERIFY INTEGRATION:
Open your AI tool and check for "giljo-mcp" tools

             ────────────────────
Thank you for installing GiljoAI Agent Orchestrator MCP Server!
www.giljo.ai 2025, v0.2 beta
infoteam@giljo.ai"""

        # Show a custom, centered dialog so the message (including
        # "Thank you for installing GiljoAI MCP!") can be centered.
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("Installation Complete")
            dialog.transient(self.root)
            dialog.resizable(False, False)

            # Size and center the dialog on screen
            dialog.update_idletasks()
            w = 840  # Narrowed by 10% from 820
            h = 1240  # Increased by 50% from 720 to show full message
            x = (dialog.winfo_screenwidth() // 2) - (w // 2)
            y = (dialog.winfo_screenheight() // 2) - (h // 2)
            dialog.geometry(f"{w}x{h}+{x}+{y}")

            # Use a Label with centered justification and wrapping so the
            # content appears centered. This reliably centers text inside
            # the dialog (unlike the system messagebox which typically
            # left-aligns multiline text).
            body = ttk.Frame(dialog, padding=(20, 20))
            body.pack(fill="both", expand=True)

            # Fallback to a single centered label for the full message
            label = tk.Label(body,
                             text=message,
                             justify="center",
                             anchor="center",
                             bg=COLORS.get('bg_primary', None),
                             fg=COLORS.get('text_primary', None),
                             font=('Segoe UI', 9),
                             wraplength=w-80)
            label.pack(fill="both", expand=True)

            # OK button to close the dialog
            # Ensure the button text is readable on dark backgrounds by forcing
            # a black foreground for this specific button via a dedicated style.
            s = ttk.Style(dialog)
            s.configure('InstallOK.TButton', foreground='#000000')
            # Also map active/pressed states to keep text readable
            s.map('InstallOK.TButton', foreground=[('active', '#000000'), ('pressed', '#000000')])

            ok_btn = ttk.Button(dialog, text="OK", command=dialog.destroy, style='InstallOK.TButton')
            ok_btn.pack(pady=(0, 18))

            # Make modal
            dialog.grab_set()
            self.root.wait_window(dialog)

        except Exception:
            # Fallback: if anything goes wrong creating the custom dialog,
            # use the default messagebox as before.
            messagebox.showinfo("Installation Complete", message)

        # Close the main window and exit with success code
        self.root.quit()
        self.root.destroy()
        return 0


def gui():
    """GUI wrapper function for compatibility with test_gui.py"""
    return main()


def main():
    """Main entry point for GUI installer"""
    try:
        # Create root window
        root = tk.Tk()

        # Create and run the setup GUI
        app = GiljoSetupGUI(root)

        # Start the GUI event loop
        root.mainloop()

        return 0

    except ImportError as e:
        print(f"GUI dependencies not available: {e}")
        print("Please install tkinter or run in CLI mode.")
        return 1

    except Exception as e:
        print(f"GUI installer failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
