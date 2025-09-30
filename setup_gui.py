#!/usr/bin/env python3
"""
GiljoAI MCP GUI Setup - Tkinter-based wizard interface
Provides a graphical setup wizard as an alternative to CLI mode
"""

import socket
import subprocess
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional
from PIL import Image, ImageTk

# Import base setup class
from setup import PORT_ASSIGNMENTS, GiljoSetup, check_port


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
}


class SplashScreen:
    """Splash screen with GiljoAI logo"""

    def __init__(self, root_window):
        self.root = root_window
        self.splash = tk.Toplevel()
        self.splash.title("GiljoAI MCP")

        # Remove window decorations
        self.splash.overrideredirect(True)

        # Set size and center on screen
        splash_width = 500
        splash_height = 300
        screen_width = self.splash.winfo_screenwidth()
        screen_height = self.splash.winfo_screenheight()
        x = (screen_width - splash_width) // 2
        y = (screen_height - splash_height) // 2
        self.splash.geometry(f"{splash_width}x{splash_height}+{x}+{y}")

        # Set background color
        self.splash.configure(bg=COLORS['bg_primary'])

        # Create frame with border
        frame = tk.Frame(self.splash, bg=COLORS['bg_elevated'],
                        highlightbackground=COLORS['border'],
                        highlightthickness=2)
        frame.pack(fill='both', expand=True, padx=2, pady=2)

        # Try to load logo
        logo_path = Path(__file__).parent / "frontend" / "public" / "giljologo_full.png"
        if logo_path.exists():
            try:
                # Load and resize logo
                img = Image.open(logo_path)
                # Resize to fit splash screen
                img = img.resize((400, 150), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                logo_label = tk.Label(frame, image=photo, bg=COLORS['bg_elevated'])
                logo_label.image = photo  # Keep a reference
                logo_label.pack(pady=30)
            except Exception as e:
                # Fallback to text if image fails
                self._show_text_logo(frame)
        else:
            # Fallback to text logo
            self._show_text_logo(frame)

        # Add loading message
        loading_label = tk.Label(frame,
                                text="Initializing Setup Wizard...",
                                font=('Helvetica', 11),
                                fg=COLORS['text_primary'],
                                bg=COLORS['bg_elevated'])
        loading_label.pack(pady=10)

        # Add version info
        version_label = tk.Label(frame,
                                text="GiljoAI MCP Orchestrator",
                                font=('Helvetica', 9),
                                fg=COLORS['text_secondary'],
                                bg=COLORS['bg_elevated'])
        version_label.pack(pady=5)

        # Bring to front
        self.splash.lift()
        self.splash.attributes('-topmost', True)

    def _show_text_logo(self, parent):
        """Fallback text logo if image not available"""
        logo_text = tk.Label(parent,
                            text="GiljoAI",
                            font=('Helvetica', 48, 'bold'),
                            fg=COLORS['text_primary'],
                            bg=COLORS['bg_elevated'])
        logo_text.pack(pady=30)

        subtitle = tk.Label(parent,
                           text="MCP Orchestrator",
                           font=('Helvetica', 16),
                           fg=COLORS['text_success'],
                           bg=COLORS['bg_elevated'])
        subtitle.pack()

    def destroy(self):
        """Close the splash screen"""
        self.splash.destroy()


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


# REMOVED: WelcomePage was redundant with ProfileSelectionPage
# The "mode" selection duplicated profile selection without affecting installation
# Kept here for reference only

# DEPRECATED - DO NOT USE
# class WelcomePage(WizardPage):
#     # Welcome page with overview - DEPRECATED
#
#     def __init__(self, parent):
#         super().__init__(parent, "Welcome to GiljoAI MCP Setup")

#         # Title
#         title_label = ttk.Label(self, text="GiljoAI MCP Setup Wizard", font=("Helvetica", 16, "bold"))
#         title_label.pack(pady=20)

#         # Description
#         desc_text = '''This wizard will guide you through the initial setup of GiljoAI MCP.

# We'll configure:
# • Database connection (SQLite or PostgreSQL)
# • Server ports and network settings
# • Security keys and API configuration
# • Import settings from AKE-MCP (if detected)
#
# The setup process will:
# 1. Check your system requirements
# 2. Validate port availability
# 3. Create configuration files
# 4. Initialize the database
# 5. Install dependencies
#
# Click 'Next' to begin.'''

#         desc_label = ttk.Label(self, text=desc_text, justify=tk.LEFT)
#         desc_label.pack(padx=20, pady=10)
#
#         # Mode selection
#         self.mode_var = tk.StringVar(value="local")
#         mode_frame = ttk.LabelFrame(self, text="Setup Mode", padding=10)
#         mode_frame.pack(padx=20, pady=10, fill="x")
#
#         ttk.Radiobutton(
#             mode_frame,
#             text="Local Development (Single machine, SQLite, full features)",
#             variable=self.mode_var,
#             value="local",
#         ).pack(anchor="w")
#         ttk.Radiobutton(
#             mode_frame,
#             text="Network Shared (Multi-user, PostgreSQL, LAN accessible)",
#             variable=self.mode_var,
#             value="lan",
#         ).pack(anchor="w")
#         ttk.Radiobutton(
#             mode_frame,
#             text="High Performance (Production-ready, optimized for scale)",
#             variable=self.mode_var,
#             value="wan",
#         ).pack(anchor="w")
#
#     def get_data(self) -> dict:
#         return {"mode": self.mode_var.get()}
# End of deprecated WelcomePage


class ProfileSelectionPage(WizardPage):
    """Welcome and deployment mode selection page"""

    def __init__(self, parent):
        super().__init__(parent, "GiljoAI MCP Server Installation")

        # Welcome Title
        title_label = ttk.Label(self, text="GiljoAI MCP Orchestration Server", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Installation recommendation
        recommend_text = """It is recommended to install the GiljoMCP Server in a separate directory
and not in the project folder."""

        recommend_label = ttk.Label(self, text=recommend_text, justify=tk.LEFT, foreground="orange")
        recommend_label.pack(padx=20, pady=(0, 10))

        # Welcome message
        welcome_text = """What this installer does:
• Installs a standalone MCP server (one-time, system-wide)
• Creates its own Python environment and dependencies
• Configures database and network settings
• Registers globally with Claude (optional)

After installation, you'll connect projects via lightweight config files.

Select your server deployment mode:"""

        desc_label = ttk.Label(self, text=welcome_text, justify=tk.LEFT)
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

        ttk.Label(local_frame, text=local_desc, justify=tk.LEFT, foreground="gray").pack(padx=20, pady=5, anchor="w")

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

        ttk.Label(server_frame, text=server_desc, justify=tk.LEFT, foreground="gray").pack(padx=20, pady=5, anchor="w")

        # Status label for mode details
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(padx=20, pady=10, fill="x")

        self.status_label = ttk.Label(self.status_frame, text="", foreground="blue")
        self.status_label.pack()

        # Set initial status
        self._on_mode_change()

    def _on_mode_change(self):
        """Update status based on selected mode"""
        mode = self.mode_var.get()

        status_messages = {
            "local": "✓ Ready for quick setup with minimal configuration",
            "server": "✓ Will configure database and network settings",
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

        desc_text = """GiljoAI MCP requires PostgreSQL for reliable multi-user operation.
Choose how you want to set up PostgreSQL:"""
        desc_label = ttk.Label(self, text=desc_text, justify=tk.LEFT)
        desc_label.pack(padx=20, pady=5)

        # PostgreSQL setup mode selection
        self.setup_mode_var = tk.StringVar(value="existing")

        mode_frame = ttk.LabelFrame(self, text="PostgreSQL Setup Mode", padding=10)
        mode_frame.pack(padx=20, pady=10, fill="x")

        ttk.Radiobutton(
            mode_frame,
            text="Attach to Existing PostgreSQL Server",
            variable=self.setup_mode_var,
            value="existing",
            command=self._on_mode_change,
        ).pack(anchor="w")

        existing_desc = ttk.Label(
            mode_frame,
            text="   • Use an already installed PostgreSQL server\n   • You'll provide connection credentials",
            foreground="gray"
        )
        existing_desc.pack(anchor="w", padx=20, pady=(0, 10))

        ttk.Radiobutton(
            mode_frame,
            text="Install Fresh PostgreSQL Server",
            variable=self.setup_mode_var,
            value="fresh",
            command=self._on_mode_change,
        ).pack(anchor="w")

        fresh_desc = ttk.Label(
            mode_frame,
            text="   • We'll download and install PostgreSQL\n   • Automatically configure for GiljoAI",
            foreground="gray"
        )
        fresh_desc.pack(anchor="w", padx=20)

        # Connection configuration frame (for both modes)
        self.config_frame = ttk.LabelFrame(self, text="Database Connection Details", padding=10)
        self.config_frame.pack(padx=20, pady=10, fill="x")

        # Network configuration
        network_frame = ttk.Frame(self.config_frame)
        network_frame.pack(fill="x", pady=5)

        ttk.Label(network_frame, text="Network Mode:", width=15).pack(side="left")
        self.network_mode_var = tk.StringVar(value="localhost")
        self.network_combo = ttk.Combobox(
            network_frame,
            textvariable=self.network_mode_var,
            values=["localhost", "network"],
            state="readonly",
            width=27
        )
        self.network_combo.pack(side="left", padx=5)
        self.network_combo.bind("<<ComboboxSelected>>", self._on_network_change)

        # Host/IP (shown for network mode or existing server)
        self.host_frame = ttk.Frame(self.config_frame)
        self.pg_host_var = tk.StringVar(value="localhost")
        ttk.Label(self.host_frame, text="Host/IP:", width=15).pack(side="left")
        self.host_entry = ttk.Entry(self.host_frame, textvariable=self.pg_host_var, width=30)
        self.host_entry.pack(side="left", padx=5)

        # Port
        port_frame = ttk.Frame(self.config_frame)
        port_frame.pack(fill="x", pady=2)
        self.pg_port_var = tk.StringVar(value="5432")
        ttk.Label(port_frame, text="Port:", width=15).pack(side="left")
        self.port_entry = ttk.Entry(port_frame, textvariable=self.pg_port_var, width=30)
        self.port_entry.pack(side="left", padx=5)

        # Check port button (for existing mode)
        self.check_port_btn = ttk.Button(port_frame, text="Check", command=self._check_port, width=10)

        # Database name
        db_frame = ttk.Frame(self.config_frame)
        db_frame.pack(fill="x", pady=2)
        self.pg_database_var = tk.StringVar(value="giljo_mcp")
        ttk.Label(db_frame, text="Database Name:", width=15).pack(side="left")
        ttk.Entry(db_frame, textvariable=self.pg_database_var, width=30).pack(side="left", padx=5)

        db_help = ttk.Label(db_frame, text="(Will be created if doesn't exist)", foreground="gray")
        db_help.pack(side="left", padx=5)

        # Credentials section
        cred_separator = ttk.Separator(self.config_frame, orient="horizontal")
        cred_separator.pack(fill="x", pady=10)

        cred_label = ttk.Label(self.config_frame, text="Database Credentials", font=("Helvetica", 10, "bold"))
        cred_label.pack(anchor="w")

        # Username
        user_frame = ttk.Frame(self.config_frame)
        user_frame.pack(fill="x", pady=2)
        self.pg_user_var = tk.StringVar(value="postgres")
        ttk.Label(user_frame, text="Username:", width=15).pack(side="left")
        self.user_entry = ttk.Entry(user_frame, textvariable=self.pg_user_var, width=30)
        self.user_entry.pack(side="left", padx=5)

        # Password
        pass_frame = ttk.Frame(self.config_frame)
        pass_frame.pack(fill="x", pady=2)
        self.pg_password_var = tk.StringVar()
        ttk.Label(pass_frame, text="Password:", width=15).pack(side="left")
        self.pass_entry = ttk.Entry(pass_frame, textvariable=self.pg_password_var, show="*", width=30)
        self.pass_entry.pack(side="left", padx=5)

        # Show/hide password
        self.show_pass_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pass_frame,
            text="Show",
            variable=self.show_pass_var,
            command=self._toggle_password
        ).pack(side="left", padx=5)

        # Important note for fresh install
        self.note_frame = ttk.Frame(self.config_frame)
        note_label = ttk.Label(
            self.note_frame,
            text="⚠️ IMPORTANT: Write down these credentials! You'll need them to access the database.",
            foreground="red",
            font=("Helvetica", 9, "bold")
        )
        note_label.pack(pady=5)

        # Test connection button (for existing mode)
        self.test_frame = ttk.Frame(self.config_frame)
        self.test_btn = ttk.Button(
            self.test_frame,
            text="Test Connection",
            command=self._test_connection,
            style="Accent.TButton"
        )
        self.test_btn.pack(pady=10)

        self.status_label = ttk.Label(self.test_frame, text="")
        self.status_label.pack()

        # Install note (for fresh mode)
        self.install_note_frame = ttk.Frame(self.config_frame)
        install_note = ttk.Label(
            self.install_note_frame,
            text="PostgreSQL will be downloaded and installed during the installation process.",
            foreground="blue"
        )
        install_note.pack(pady=5)

        # Initialize visibility based on mode
        self._on_mode_change()

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
            self.pass_entry.config(show="")
        else:
            self.pass_entry.config(show="*")

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
                self.status_label.config(text=f"✓ Port {port} is open on {host}", foreground="green")
            else:
                self.status_label.config(text=f"✗ Port {port} is not accessible on {host}", foreground="red")
        except Exception as e:
            self.status_label.config(text=f"✗ Error checking port: {e}", foreground="red")

    def _test_connection(self):
        """Test PostgreSQL connection"""
        self.status_label.config(text="Testing connection...", foreground="blue")
        self.update()

        # Run test in thread to avoid blocking
        def test():
            try:
                import psycopg2

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
                        text=f"✓ Connected successfully! Database '{db_name}' exists.",
                        foreground="green"
                    )
                else:
                    self.status_label.config(
                        text=f"✓ Connection successful! Database '{db_name}' will be created.",
                        foreground="green"
                    )

            except psycopg2.OperationalError as e:
                if "password authentication failed" in str(e):
                    self.status_label.config(text="✗ Invalid credentials", foreground="red")
                elif "could not connect to server" in str(e):
                    self.status_label.config(text="✗ Cannot connect to server", foreground="red")
                elif "timeout expired" in str(e):
                    self.status_label.config(text="✗ Connection timeout", foreground="red")
                else:
                    self.status_label.config(text=f"✗ Connection failed: {e}", foreground="red")
            except Exception as e:
                self.status_label.config(text=f"✗ Error: {e}", foreground="red")

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

        # For existing mode, recommend testing connection
        if self.setup_mode_var.get() == "existing":
            if not hasattr(self, '_connection_tested'):
                result = messagebox.askyesno(
                    "Connection Test",
                    "Would you like to test the database connection before proceeding?"
                )
                if result:
                    self._test_connection()
                    return False  # Don't proceed yet, let user see result

        return True

    def get_data(self) -> dict:
        """Return database configuration"""
        return {
            "db_type": "postgresql",  # Always PostgreSQL now
            "pg_setup_mode": self.setup_mode_var.get(),
            "pg_network_mode": self.network_mode_var.get(),
            "pg_host": self.pg_host_var.get(),
            "pg_port": self.pg_port_var.get(),
            "pg_database": self.pg_database_var.get(),
            "pg_user": self.pg_user_var.get(),
            "pg_password": self.pg_password_var.get(),
            "install_postgresql": self.setup_mode_var.get() == "fresh"
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
            ttk.Button(frame, text="Check", command=lambda s=service: self._check_port(s)).pack(side="left")

        # Check all button
        ttk.Button(ports_frame, text="Check All Ports", command=self._check_all_ports).pack(pady=10)

    def _check_port(self, service: str):
        """Check if a port is available"""
        port = int(self.port_vars[service].get())
        if check_port(port):
            self.status_labels[service].config(text="✗ In use", foreground="red")
        else:
            self.status_labels[service].config(text="✓ Available", foreground="green")

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
            text="📔 For building your own applications and integrating with GiljoAI MCP.\n"
            + "Examples: Custom tools, local LLM integrations, automation scripts.\n"
            + "Note: MCP clients (Claude, etc.) use MCP protocol, not this.",
            foreground="gray",
            wraplength=500,
        )
        api_help.pack(anchor="w", pady=(5, 10))

        self.api_key_var = tk.StringVar()
        self.api_frame_inner = ttk.Frame(api_frame)

        ttk.Label(self.api_frame_inner, text="API Key:").pack(side="left", padx=5)
        ttk.Entry(self.api_frame_inner, textvariable=self.api_key_var, width=40).pack(side="left", padx=5)
        ttk.Button(self.api_frame_inner, text="Generate", command=self._generate_api_key).pack(side="left")

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
            text="🔐 Signs session tokens for the web dashboard. Prevents token tampering.\n"
            + "Auto-generated for security. No need to copy unless integrating SSO.",
            foreground="gray",
            wraplength=500,
        )
        jwt_help.pack(anchor="w", pady=(0, 10))

        self.jwt_secret_var = tk.StringVar()
        jwt_inner = ttk.Frame(jwt_frame)
        jwt_inner.pack(fill="x")

        ttk.Label(jwt_inner, text="JWT Secret:").pack(side="left", padx=5)
        ttk.Entry(jwt_inner, textvariable=self.jwt_secret_var, width=40).pack(side="left", padx=5)
        ttk.Button(jwt_inner, text="Generate", command=self._generate_jwt_secret).pack(side="left")

        # CORS settings (always enabled)
        cors_frame = ttk.LabelFrame(self, text="CORS Origin Configuration (Required for Dashboard)", padding=10)
        cors_frame.pack(padx=20, pady=10, fill="x")

        # CORS explanation
        cors_help = ttk.Label(
            cors_frame,
            text="🌐 Dashboard Access Configuration\n"
            + "Default works for local access. Change for LAN/WAN:\n"
            + "• Local: http://localhost:* (default)\n"
            + "• LAN: http://YOUR-SERVER-IP:* (e.g., http://192.168.1.100:*)\n"
            + "• WAN: https://your-domain.com",
            foreground="gray",
            wraplength=500,
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
            text="💡 Tip: You can change this later in the .env file if your network setup changes",
            foreground="blue",
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

        # Config display
        self.text = tk.Text(text_frame, height=20, width=70, wrap="word")
        self.text.pack(side="left", fill="both", expand=True)

        # Scrollbar
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.text.yview)
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
        if config.get("db_type") == "sqlite":
            self.text.insert(tk.END, "Type: SQLite (Local Development)\n")
            self.text.insert(tk.END, f"Path: {config.get('db_path', 'data/giljo_mcp.db')}\n")
        else:
            self.text.insert(tk.END, "Type: PostgreSQL (Network/High Performance)\n")
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


# ServiceControlPage removed - Installation now completes directly
# The service management functionality has been moved to the main application dashboard
# which provides better real-time monitoring and control capabilities.
# To manage services after installation:
# 1. Run 'start_giljo.bat' to start all services
# 2. Use the dashboard at http://localhost:6000 for monitoring
# 3. Run 'stop_giljo.bat' to stop all services
#
# The ServiceControlPage class has been removed from this file.
# It was used to show service status and control after installation,
# but this functionality is now in the main application dashboard.

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

        self.install_button = ttk.Button(
            button_frame,
            text="Install",
            command=self.start_installation,
            style="Accent.TButton"
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
        scrollbar = ttk.Scrollbar(console_container, command=self.console_text.yview)
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

            # Progress bar
            progress_var = tk.IntVar(value=0)
            progress = ttk.Progressbar(frame, variable=progress_var,
                                      maximum=100, length=200)
            progress.pack(side="left", padx=(0, 10))

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
        """Log message to console"""
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}"

        # Determine tag based on message content
        tag = "info"
        if any(word in message.lower() for word in ["success", "✓", "completed"]):
            tag = "success"
        elif any(word in message.lower() for word in ["error", "failed"]):
            tag = "error"
        elif any(word in message.lower() for word in ["warning", "issue"]):
            tag = "warning"

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
        if any(word in status.lower() for word in ["✓", "success", "completed", "installed"]):
            widget.configure(foreground="green")
        elif any(word in status.lower() for word in ["failed", "error"]):
            widget.configure(foreground="red")
        elif any(word in status.lower() for word in ["warning", "issue"]):
            widget.configure(foreground="orange")
        elif "not required" in status.lower():
            widget.configure(foreground="gray")
        else:
            widget.configure(foreground="black")

    def _update_overall_progress(self):
        """Calculate and update overall progress"""
        applicable = [c for c in self.components.values() if c.get('applicable', True)]
        if applicable:
            total = sum(c['progress_var'].get() for c in applicable)
            overall = total // len(applicable)
            self.progress_var.set(overall)

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
        self.log(f"Installing GiljoAI MCP Server", "system")
        self.log(f"Installation Mode: {profile}", "system")
        self.log("="*60, "system")

        # Update component applicability again with actual config
        self.update_component_applicability(profile, config)

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
                self.log("✓ Virtual environment created", "success")
            else:
                self.log("✓ Virtual environment already exists", "info")
            self.set_progress(100, "venv")
            self.set_status("Virtual environment ready ✓", "venv")
        except Exception as e:
            self.log(f"✗ Failed to create virtual environment: {e}", "error")
            self.set_status(f"Virtual environment failed: {e}", "venv")
            # Don't continue if venv creation failed
            return

        # Step 2: Install Dependencies
        self.set_status("Installing server dependencies...", "dependencies")
        self.set_progress(10, "dependencies")
        self.log("\n[PHASE 2: DEPENDENCIES]", "info")
        self.log("Installing required Python packages...", "system")

        try:
            # Determine pip path
            pip_path = venv_path / ("Scripts" if sys.platform == "win32" else "bin") / "pip"

            # Install requirements
            self.log("Installing from requirements.txt...", "system")
            subprocess.run([str(pip_path), "install", "-r", "requirements.txt"], check=True)
            self.set_progress(50, "dependencies")

            # Install the package itself (skip if environment variable set)
            if not os.environ.get('GILJO_SKIP_EDITABLE_INSTALL'):
                self.log("Installing giljo_mcp package...", "system")
                subprocess.run([str(pip_path), "install", "-e", "."], check=True)
            else:
                self.log("Skipping editable install (GILJO_SKIP_EDITABLE_INSTALL set)", "info")
            self.set_progress(100, "dependencies")

            self.log("✓ All dependencies installed", "success")
            self.set_status("Dependencies installed ✓", "dependencies")
        except Exception as e:
            self.log(f"✗ Failed to install dependencies: {e}", "error")
            self.set_status(f"Dependencies failed: {e}", "dependencies")

        # PostgreSQL is always used now
        pg_setup_mode = config.get("pg_setup_mode", "existing")
        install_postgresql = config.get("install_postgresql", False)

        # Step 2.5: Install PostgreSQL if needed
        if install_postgresql and pg_setup_mode == "fresh":
            self.set_status("Installing PostgreSQL server...", "database")
            self.set_progress(10, "database")
            self.log("\n[PHASE 2.5: POSTGRESQL INSTALLATION]", "info")
            self.log("Downloading and installing PostgreSQL...", "system")

            try:
                # Install PostgreSQL based on platform
                if sys.platform == "win32":
                    # Check for admin privileges on Windows
                    if not is_admin():
                        self.log("⚠ PostgreSQL installation requires Administrator privileges", "warning")
                        self.log("", "system")
                        self.log("Please choose an option:", "system")
                        self.log("  1. Restart installer as Administrator, OR", "system")
                        self.log("  2. Install PostgreSQL manually from: https://www.postgresql.org/download/windows/", "system")
                        self.log("  3. Skip PostgreSQL installation (you can use external PostgreSQL)", "system")
                        self.log("", "system")

                        # Ask user what to do
                        from tkinter import messagebox
                        response = messagebox.askyesnocancel(
                            "Administrator Required",
                            "PostgreSQL installation requires Administrator privileges.\n\n"
                            "• Yes: Skip PostgreSQL (use external installation)\n"
                            "• No: Exit and restart as Administrator\n"
                            "• Cancel: Abort installation",
                            icon=messagebox.WARNING
                        )

                        if response is None:  # Cancel
                            self.log("Installation aborted by user", "error")
                            self.set_status("Installation aborted", "database")
                            return
                        elif response:  # Yes - Skip PostgreSQL
                            self.log("Skipping PostgreSQL installation (will use external PostgreSQL)", "warning")
                            self.set_progress(100, "database")
                            self.set_status("PostgreSQL skipped (external)", "database")
                            # Continue without PostgreSQL install
                            raise Exception("SKIP_POSTGRESQL")
                        else:  # No - Exit
                            self.log("Please restart installer as Administrator", "warning")
                            self.log("Right-click setup_gui.py → Run as Administrator", "info")
                            self.set_status("Waiting for admin restart", "database")
                            return

                    # Windows: Download and run PostgreSQL installer
                    self.log("Downloading PostgreSQL installer for Windows...", "system")
                    import urllib.request
                    import tempfile

                    # Download PostgreSQL installer
                    pg_url = "https://get.enterprisedb.com/postgresql/postgresql-16.1-1-windows-x64.exe"
                    # Note: In production, you should verify SSL certificates and checksums
                    # This is a trusted PostgreSQL download source
                    with tempfile.NamedTemporaryFile(suffix=".exe", delete=False) as tmp:
                        # Use urlopen with context manager for safer downloading
                        with urllib.request.urlopen(pg_url) as response:  # nosec B310 - trusted PostgreSQL source
                            tmp.write(response.read())
                        pg_installer = tmp.name

                    # Run installer silently
                    pg_password = config.get("pg_password", "postgres")
                    pg_port = config.get("pg_port", "5432")

                    install_cmd = [
                        pg_installer,
                        "--mode", "unattended",
                        "--superpassword", pg_password,
                        "--serverport", pg_port,
                        "--enable-components", "server",
                        "--disable-components", "pgAdmin,stackbuilder"
                    ]

                    self.log("Running PostgreSQL installer (this may take a few minutes)...", "system")
                    subprocess.run(install_cmd, check=True)
                    self.log("✓ PostgreSQL installed successfully", "success")

                elif sys.platform == "darwin":
                    # macOS: Use Homebrew
                    self.log("Installing PostgreSQL via Homebrew...", "system")
                    subprocess.run(["brew", "install", "postgresql@16"], check=True)
                    subprocess.run(["brew", "services", "start", "postgresql@16"], check=True)
                    self.log("✓ PostgreSQL installed and started", "success")

                else:
                    # Linux: Use apt/yum based on distribution
                    self.log("Installing PostgreSQL via package manager...", "system")
                    try:
                        # Try apt first (Debian/Ubuntu)
                        subprocess.run(["sudo", "apt", "update"], check=True)
                        subprocess.run(["sudo", "apt", "install", "-y", "postgresql", "postgresql-contrib"], check=True)
                    except:
                        # Try yum (RHEL/CentOS)
                        subprocess.run(["sudo", "yum", "install", "-y", "postgresql-server", "postgresql-contrib"], check=True)
                        subprocess.run(["sudo", "postgresql-setup", "--initdb"], check=True)

                    subprocess.run(["sudo", "systemctl", "start", "postgresql"], check=True)
                    subprocess.run(["sudo", "systemctl", "enable", "postgresql"], check=True)
                    self.log("✓ PostgreSQL installed and started", "success")

                self.set_progress(100, "database")
                self.set_status("PostgreSQL installed ✓", "database")

            except Exception as e:
                if str(e) == "SKIP_POSTGRESQL":
                    # User chose to skip PostgreSQL, continue with external
                    pass  # Already logged, continue installation
                else:
                    self.log(f"✗ Failed to install PostgreSQL: {e}", "error")
                    self.log("Please install PostgreSQL manually and retry", "error")
                    self.set_status(f"PostgreSQL installation failed: {e}", "database")
                    return

        self.log("\n[DATABASE MODE: PostgreSQL]", "system")

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
                self.set_status("Configuration files created ✓", "config")

            # Validate configuration
            is_valid, errors = config_mgr.validate_configuration(config_values)
            if is_valid:
                self.log("SUCCESS: Configuration validated", "system")
            else:
                for error in errors:
                    self.log(f"Configuration error: {error}", "system")

        except Exception as e:
            self.log(f"Configuration error: {e}", "system")
            self.set_status(f"Configuration failed: {e}", "config")

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
            self.set_status("Directories created ✓", "directories")
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
                    if "Collecting" in line:
                        package_name = line.split("Collecting")[-1].strip()
                        package_count += 1
                        self.log(f"  Downloading: {package_name}", "system")
                        # Update progress incrementally (20% to 60% over ~100 packages)
                        progress = min(20 + (package_count * 0.4), 60)
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
                    self.set_status("Python packages installed ✓", "packages")
                else:
                    self.log(f"Warning: giljo-mcp installation completed with return code {process.returncode}", "system")
                    self.set_status("Package installation completed with warnings", "packages")
            else:
                self.log("Skipping editable install (GILJO_SKIP_EDITABLE_INSTALL set)", "system")
                self.set_progress(100, "packages")
                self.set_status("Python packages installed ✓", "packages")

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

                    self.set_status("PostgreSQL installed ✓", "database")
                    self.set_progress(100, "database")

                except Exception as e:
                    self.log(f"PostgreSQL installation error: {e}", "postgresql")
                    self.set_status(f"Failed: {e}", "database")

            pg_thread = threading.Thread(target=install_postgresql)
            threads.append(pg_thread)
        else:
            # SQLite setup
            self.set_status("Setting up SQLite database...", "database")
            self.set_progress(50, "database")
            self.log("Configuring SQLite database...", "system")
            time.sleep(0.5)
            self.set_status("SQLite database ready ✓", "database")
            self.set_progress(100, "database")

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

            if issues:
                self.log(f"WARNING: Issues detected: {', '.join(issues)}", "system")
                self.set_status(f"Completed with warnings: {', '.join(issues)}", "validation")
            else:
                self.log("SUCCESS: All components installed successfully", "system")
                self.set_status("All validations passed ✓", "validation")

            self.set_progress(100, "validation")

            # Update overall status
            self.set_progress(100)
            completion_msg = "✅ Installation completed successfully!" if not issues else "⚠️ Installation completed with warnings"
            self.status_var.set(completion_msg)

            # Log final message
            self.log("\n" + "="*60, "system")
            self.log(completion_msg, "success" if not issues else "warning")
            self.log("Click 'Finish' to complete the setup.", "info")
            self.log("="*60, "system")

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
                from create_shortcuts import create_shortcuts, add_to_startup_windows
                shortcuts = create_shortcuts()
                if shortcuts:
                    self.log(f"✓ Created {len(shortcuts)} desktop shortcuts", "success")
                    self.log("  • Start Server - Launch the MCP server", "info")
                    self.log("  • Stop Server - Shutdown the server", "info")
                    self.log("  • Connect Project - Connect projects to server", "info")
                    self.log("  • Check Status - View server status", "info")
                else:
                    self.log("Desktop shortcuts could not be created", "warning")
            except Exception as shortcut_error:
                self.log(f"Warning: Could not create shortcuts: {shortcut_error}", "warning")

            # Register with Claude if available
            self.log("\nChecking Claude integration...", "system")
            try:
                import subprocess
                import shutil

                # Check if claude CLI is available
                if shutil.which("claude"):
                    self.log("Claude CLI found. Registering MCP server...", "system")

                    # Get the installation directory
                    install_dir = Path.cwd()
                    python_path = install_dir / "venv" / "Scripts" / "python.exe"

                    # Register the MCP server with Claude
                    result = subprocess.run(
                        ["claude", "mcp", "add", "giljo-mcp",
                         f"{python_path} -m giljo_mcp",
                         "--scope", "user"],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )

                    if result.returncode == 0:
                        self.log("✅ Successfully registered with Claude!", "success")
                        self.log("Please restart Claude to activate the MCP server.", "info")
                    else:
                        self.log("Could not auto-register with Claude.", "warning")
                        self.log(f"You can register manually by running: register_claude.bat", "info")
                else:
                    self.log("Claude CLI not found. You can register later by running: register_claude.bat", "info")

            except Exception as claude_error:
                self.log(f"Claude registration skipped: {claude_error}", "warning")
                self.log("You can register manually later by running: register_claude.bat", "info")

        except Exception as e:
            self.log(f"Health check error: {e}", "system")
            self.set_status(f"Validation failed: {e}", "validation")
            self.completed = True

    def validate(self):
        """Check if installation is complete"""
        return self.completed


class GiljoSetupGUI:
    """Main GUI setup wizard"""

    def __init__(self, root):
        self.root = root
        self.root.title("GiljoAI MCP Setup Wizard")
        self.root.geometry("800x600")
        self.root.resizable(True, True)

        # Center window
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (800 // 2)
        y = (self.root.winfo_screenheight() // 2) - (600 // 2)
        self.root.geometry(f"800x600+{x}+{y}")

        # Configure GiljoAI color theme
        style = ttk.Style()
        # Use default theme as base (better Windows compatibility)

        # Configure root window background
        self.root.configure(bg=COLORS['bg_primary'])

        # Configure ttk widget styles
        style.configure('TFrame', background=COLORS['bg_primary'])
        style.configure('TLabel',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'])
        style.configure('TLabelframe',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'],
                       bordercolor=COLORS['border'])
        style.configure('TLabelframe.Label',
                       background=COLORS['bg_primary'],
                       foreground=COLORS['text_primary'])

        # Button styles
        style.configure('TButton',
                       background=COLORS['bg_elevated'],
                       foreground=COLORS['text_primary'],
                       bordercolor=COLORS['border'],
                       lightcolor=COLORS['border'],
                       darkcolor=COLORS['border'])
        style.map('TButton',
                 background=[('active', COLORS['border'])],
                 foreground=[('active', COLORS['text_primary'])])

        # Entry/Input styles
        style.configure('TEntry',
                       fieldbackground=COLORS['bg_elevated'],
                       foreground=COLORS['text_primary'],
                       bordercolor=COLORS['border'])

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

        # Scrollbar styles
        style.configure('Vertical.TScrollbar',
                       background=COLORS['bg_elevated'],
                       troughcolor=COLORS['bg_primary'],
                       bordercolor=COLORS['border'],
                       arrowcolor=COLORS['text_primary'])
        style.map('Vertical.TScrollbar',
                 background=[('active', COLORS['text_primary'])])

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
        self.scrollbar = ttk.Scrollbar(self.content_container, orient="vertical", command=self.canvas.yview)
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
            # WelcomePage removed - ProfileSelection now serves as welcome
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

        self.back_btn = ttk.Button(self.nav_frame, text="< Back", command=self.go_back)
        self.back_btn.pack(side="left")

        self.next_btn = ttk.Button(self.nav_frame, text="Next >", command=self.go_next)
        self.next_btn.pack(side="right")

        self.cancel_btn = ttk.Button(self.nav_frame, text="Cancel", command=self.cancel_setup)
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

    def finish_setup(self):
        """Complete the setup process"""
        # Get installation path
        install_path = Path.cwd()

        # Create a more informative completion message
        message = f"""GiljoAI MCP Server Installation Complete!

✅ SERVER INSTALLED AT: {install_path}

This is a standalone MCP orchestration server that will coordinate
multiple AI agents across all your development projects.

NEXT STEPS:
═══════════════════════════════════════════════════════════

1. CONNECT YOUR AI CODING AGENT:

   We've created integration helpers for all major AI tools.
   Run the universal wizard to configure all detected tools:

   Run: python {install_path}\\register_ai_tools.py

   Or register individual tools:
   • Claude Code:  {install_path}\\register_claude.bat
   • Codex CLI:    python {install_path}\\register_codex.py
   • Gemini CLI:   python {install_path}\\register_gemini.py
   • Grok CLI:     python {install_path}\\register_grok.py

   📖 Detailed instructions: {install_path}\\docs\\AI_TOOL_INTEGRATION.md

2. START THE SERVER:
   Run: {install_path}\\start_giljo.bat
   Server will run at http://localhost:8000

3. VERIFY INTEGRATION:
   Open your AI tool and check for "giljo-mcp" tools

IMPORTANT:
• This server can handle multiple projects simultaneously
• Register once, use across all your projects
• The server runs independently from your projects

Documentation: {install_path}\\INSTALLATION.md"""

        messagebox.showinfo("Installation Complete", message)
        self.root.quit()
        self.root.destroy()
        # Exit with success code
        return 0


def gui():
    """GUI wrapper function for compatibility with test_gui.py"""
    return main()


def main():
    """Main entry point for GUI installer"""
    try:
        # Create hidden root window for splash
        root = tk.Tk()
        root.withdraw()  # Hide main window initially

        # Show splash screen
        splash = SplashScreen(root)
        root.update()

        # Wait 2.5 seconds to show splash
        root.after(2500, splash.destroy)
        root.after(2500, root.deiconify)  # Show main window after splash

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
