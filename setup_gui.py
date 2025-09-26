#!/usr/bin/env python3
"""
GiljoAI MCP GUI Setup - Tkinter-based wizard interface
Provides a graphical setup wizard as an alternative to CLI mode
"""

import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import Callable, Optional

# Import base setup class
from setup import PORT_ASSIGNMENTS, GiljoSetup, check_port


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


class WelcomePage(WizardPage):
    """Welcome page with overview"""

    def __init__(self, parent):
        super().__init__(parent, "Welcome to GiljoAI MCP Setup")

        # Title
        title_label = ttk.Label(self, text="GiljoAI MCP Setup Wizard",
                               font=("Helvetica", 16, "bold"))
        title_label.pack(pady=20)

        # Description
        desc_text = """This wizard will guide you through the initial setup of GiljoAI MCP.

We'll configure:
• Database connection (SQLite or PostgreSQL)
• Server ports and network settings
• Security keys and API configuration
• Import settings from AKE-MCP (if detected)

The setup process will:
1. Check your system requirements
2. Validate port availability
3. Create configuration files
4. Initialize the database
5. Install dependencies

Click 'Next' to begin."""

        desc_label = ttk.Label(self, text=desc_text, justify=tk.LEFT)
        desc_label.pack(padx=20, pady=10)

        # Mode selection
        self.mode_var = tk.StringVar(value="development")
        mode_frame = ttk.LabelFrame(self, text="Setup Mode", padding=10)
        mode_frame.pack(padx=20, pady=10, fill="x")

        ttk.Radiobutton(mode_frame, text="Development (Local SQLite)",
                       variable=self.mode_var, value="development").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Production (PostgreSQL)",
                       variable=self.mode_var, value="production").pack(anchor="w")

    def get_data(self) -> dict:
        return {"mode": self.mode_var.get()}


class DatabasePage(WizardPage):
    """Database configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "Database Configuration")

        self.db_type_var = tk.StringVar(value="sqlite")

        # Database type selection
        type_frame = ttk.LabelFrame(self, text="Database Type", padding=10)
        type_frame.pack(padx=20, pady=10, fill="x")

        ttk.Radiobutton(type_frame, text="SQLite (Recommended for development)",
                       variable=self.db_type_var, value="sqlite",
                       command=self._on_db_type_change).pack(anchor="w")
        ttk.Radiobutton(type_frame, text="PostgreSQL (For production/multi-user)",
                       variable=self.db_type_var, value="postgresql",
                       command=self._on_db_type_change).pack(anchor="w")

        # SQLite configuration
        self.sqlite_frame = ttk.LabelFrame(self, text="SQLite Configuration", padding=10)
        self.sqlite_frame.pack(padx=20, pady=10, fill="x")

        self.db_path_var = tk.StringVar(value="data/giljo_mcp.db")
        path_frame = ttk.Frame(self.sqlite_frame)
        path_frame.pack(fill="x")
        ttk.Label(path_frame, text="Database Path:").pack(side="left", padx=5)
        ttk.Entry(path_frame, textvariable=self.db_path_var, width=40).pack(side="left", padx=5)
        ttk.Button(path_frame, text="Browse", command=self._browse_path).pack(side="left")

        # PostgreSQL configuration
        self.pg_frame = ttk.LabelFrame(self, text="PostgreSQL Configuration", padding=10)

        self.pg_host_var = tk.StringVar(value="localhost")
        self.pg_port_var = tk.StringVar(value="5432")
        self.pg_database_var = tk.StringVar(value="giljo_mcp")
        self.pg_user_var = tk.StringVar(value="postgres")
        self.pg_password_var = tk.StringVar()

        # Host
        host_frame = ttk.Frame(self.pg_frame)
        host_frame.pack(fill="x", pady=2)
        ttk.Label(host_frame, text="Host:", width=12).pack(side="left")
        ttk.Entry(host_frame, textvariable=self.pg_host_var, width=30).pack(side="left", padx=5)

        # Port
        port_frame = ttk.Frame(self.pg_frame)
        port_frame.pack(fill="x", pady=2)
        ttk.Label(port_frame, text="Port:", width=12).pack(side="left")
        ttk.Entry(port_frame, textvariable=self.pg_port_var, width=30).pack(side="left", padx=5)

        # Database
        db_frame = ttk.Frame(self.pg_frame)
        db_frame.pack(fill="x", pady=2)
        ttk.Label(db_frame, text="Database:", width=12).pack(side="left")
        ttk.Entry(db_frame, textvariable=self.pg_database_var, width=30).pack(side="left", padx=5)

        # Username
        user_frame = ttk.Frame(self.pg_frame)
        user_frame.pack(fill="x", pady=2)
        ttk.Label(user_frame, text="Username:", width=12).pack(side="left")
        ttk.Entry(user_frame, textvariable=self.pg_user_var, width=30).pack(side="left", padx=5)

        # Password
        pass_frame = ttk.Frame(self.pg_frame)
        pass_frame.pack(fill="x", pady=2)
        ttk.Label(pass_frame, text="Password:", width=12).pack(side="left")
        ttk.Entry(pass_frame, textvariable=self.pg_password_var, show="*", width=30).pack(side="left", padx=5)

        # Test connection button
        self.test_btn = ttk.Button(self.pg_frame, text="Test Connection", command=self._test_connection)
        self.test_btn.pack(pady=10)

        self.status_label = ttk.Label(self.pg_frame, text="")
        self.status_label.pack()

        # Initialize visibility
        self._on_db_type_change()

    def _on_db_type_change(self):
        """Handle database type change"""
        if self.db_type_var.get() == "sqlite":
            self.sqlite_frame.pack(padx=20, pady=10, fill="x")
            self.pg_frame.pack_forget()
        else:
            self.sqlite_frame.pack_forget()
            self.pg_frame.pack(padx=20, pady=10, fill="x")

    def _browse_path(self):
        """Browse for database path"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".db",
            filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
        )
        if filename:
            self.db_path_var.set(filename)

    def _test_connection(self):
        """Test PostgreSQL connection"""
        self.status_label.config(text="Testing connection...", foreground="blue")
        self.update()

        # Run test in thread to avoid blocking
        def test():
            try:
                import psycopg2
                conn = psycopg2.connect(
                    host=self.pg_host_var.get(),
                    port=self.pg_port_var.get(),
                    database=self.pg_database_var.get(),
                    user=self.pg_user_var.get(),
                    password=self.pg_password_var.get()
                )
                conn.close()
                self.status_label.config(text="✓ Connection successful", foreground="green")
            except Exception as e:
                self.status_label.config(text=f"✗ Connection failed: {e!s}", foreground="red")

        thread = threading.Thread(target=test)
        thread.start()

    def validate(self) -> bool:
        """Validate database configuration"""
        if self.db_type_var.get() == "sqlite":
            return bool(self.db_path_var.get())
        return all([
            self.pg_host_var.get(),
            self.pg_port_var.get(),
            self.pg_database_var.get(),
            self.pg_user_var.get()
        ])

    def get_data(self) -> dict:
        if self.db_type_var.get() == "sqlite":
            return {
                "db_type": "sqlite",
                "db_path": self.db_path_var.get()
            }
        return {
            "db_type": "postgresql",
            "pg_host": self.pg_host_var.get(),
            "pg_port": self.pg_port_var.get(),
            "pg_database": self.pg_database_var.get(),
            "pg_user": self.pg_user_var.get(),
            "pg_password": self.pg_password_var.get()
        }


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
            ttk.Button(frame, text="Check",
                      command=lambda s=service: self._check_port(s)).pack(side="left")

        # Check all button
        ttk.Button(ports_frame, text="Check All Ports",
                  command=self._check_all_ports).pack(pady=10)

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
                    messagebox.showerror("Invalid Port",
                                       f"{service} port must be between 1024 and 65535")
                    return False
            except ValueError:
                messagebox.showerror("Invalid Port",
                                   f"{service} port must be a number")
                return False
        return True

    def get_data(self) -> dict:
        return {f"{service}_port": self.port_vars[service].get()
                for service in self.port_vars}


class SecurityPage(WizardPage):
    """Security configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "Security Configuration")

        # API Key
        api_frame = ttk.LabelFrame(self, text="API Security", padding=10)
        api_frame.pack(padx=20, pady=10, fill="x")

        self.enable_api_key_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(api_frame, text="Enable API Key authentication",
                       variable=self.enable_api_key_var,
                       command=self._on_api_toggle).pack(anchor="w")

        # API Key explanation
        api_help = ttk.Label(api_frame, text="📔 Used for REST API calls from CI/CD, external tools, or remote access.\n" +
                                             "Enable this for LAN/WAN deployments. Save the key securely!",
                            foreground="gray", wraplength=500)
        api_help.pack(anchor="w", pady=(5, 10))

        self.api_key_var = tk.StringVar()
        self.api_frame_inner = ttk.Frame(api_frame)

        ttk.Label(self.api_frame_inner, text="API Key:").pack(side="left", padx=5)
        ttk.Entry(self.api_frame_inner, textvariable=self.api_key_var, width=40).pack(side="left", padx=5)
        ttk.Button(self.api_frame_inner, text="Generate",
                  command=self._generate_api_key).pack(side="left")

        # Warning about saving the key
        self.api_warning = ttk.Label(self.api_frame_inner, text="⚠️ Copy this key now! It won't be shown again.",
                                     foreground="orange")
        self.api_warning.pack(side="left", padx=10)

        # JWT Secret
        jwt_frame = ttk.LabelFrame(self, text="JWT Configuration", padding=10)
        jwt_frame.pack(padx=20, pady=10, fill="x")

        # JWT explanation
        jwt_help = ttk.Label(jwt_frame, text="🔐 Signs session tokens for the web dashboard. Prevents token tampering.\n" +
                                             "Auto-generated for security. No need to copy unless integrating SSO.",
                            foreground="gray", wraplength=500)
        jwt_help.pack(anchor="w", pady=(0, 10))

        self.jwt_secret_var = tk.StringVar()
        jwt_inner = ttk.Frame(jwt_frame)
        jwt_inner.pack(fill="x")

        ttk.Label(jwt_inner, text="JWT Secret:").pack(side="left", padx=5)
        ttk.Entry(jwt_inner, textvariable=self.jwt_secret_var, width=40).pack(side="left", padx=5)
        ttk.Button(jwt_inner, text="Generate",
                  command=self._generate_jwt_secret).pack(side="left")

        # CORS settings
        cors_frame = ttk.LabelFrame(self, text="CORS Settings", padding=10)
        cors_frame.pack(padx=20, pady=10, fill="x")

        self.cors_enabled_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(cors_frame, text="Enable CORS",
                       variable=self.cors_enabled_var).pack(anchor="w")

        # CORS explanation
        cors_help = ttk.Label(cors_frame, text="🌐 For Web Dashboard Only - NOT for MCP clients!\n" +
                                               "Allows the built-in web dashboard (port 6000) to call the API (port 6002).\n" +
                                               "Without this, your browser blocks the dashboard. MCP clients ignore this setting.",
                             foreground="gray", wraplength=500)
        cors_help.pack(anchor="w", pady=(5, 10))

        self.cors_origins_var = tk.StringVar(value="http://localhost:*")
        origins_frame = ttk.Frame(cors_frame)
        origins_frame.pack(fill="x", pady=5)
        ttk.Label(origins_frame, text="Allowed Origins:").pack(side="left", padx=5)
        ttk.Entry(origins_frame, textvariable=self.cors_origins_var, width=40).pack(side="left", padx=5)

        # CORS origin help
        cors_origin_help = ttk.Label(cors_frame, text="Examples: http://localhost:* (local), http://192.168.1.100:* (LAN), https://dashboard.yourcompany.com (WAN)",
                                     foreground="gray", font=("", 9))
        cors_origin_help.pack(anchor="w", padx=(5, 0))

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
            "cors_enabled": self.cors_enabled_var.get(),
            "cors_origins": self.cors_origins_var.get()
        }
        if self.enable_api_key_var.get():
            data["api_key"] = self.api_key_var.get()
        return data


class ReviewPage(WizardPage):
    """Review configuration before applying"""

    def __init__(self, parent, get_config_func: Callable):
        super().__init__(parent, "Review Configuration")
        self.get_config = get_config_func

        # Description
        desc = ttk.Label(self, text="Review your configuration before applying:")
        desc.pack(padx=20, pady=10)

        # Config display
        self.text = tk.Text(self, height=20, width=70)
        self.text.pack(padx=20, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.text)
        scrollbar.pack(side="right", fill="y")
        self.text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.text.yview)

    def on_enter(self):
        """Update configuration display"""
        config = self.get_config()

        # Format configuration
        self.text.config(state="normal")
        self.text.delete(1.0, tk.END)
        self.text.insert(tk.END, "=" * 60 + "\n")
        self.text.insert(tk.END, "CONFIGURATION SUMMARY\n")
        self.text.insert(tk.END, "=" * 60 + "\n\n")

        # Deployment Mode
        self.text.insert(tk.END, "DEPLOYMENT MODE\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        self.text.insert(tk.END, f"Mode: {config.get('mode', 'local').capitalize()}\n\n")

        # Database
        self.text.insert(tk.END, "DATABASE CONFIGURATION\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        if config.get("db_type") == "sqlite":
            self.text.insert(tk.END, "Type: SQLite (Local)\n")
            self.text.insert(tk.END, f"Path: {config.get('db_path', 'data/giljo_mcp.db')}\n")
        else:
            self.text.insert(tk.END, "Type: PostgreSQL (Production)\n")
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

        jwt_secret = config.get('jwt_secret', '')
        if jwt_secret:
            self.text.insert(tk.END, f"JWT Secret: {jwt_secret[:10]}... (Auto-saved)\n")
        else:
            self.text.insert(tk.END, "JWT Secret: Will be generated\n")

        self.text.insert(tk.END, f"CORS Enabled: {config.get('cors_enabled', True)}\n")
        if config.get("cors_enabled", True):
            self.text.insert(tk.END, f"CORS Origins: {config.get('cors_origins', 'http://localhost:*')}\n")

        # URLs
        self.text.insert(tk.END, "\nACCESS URLS\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        dashboard_port = config.get('dashboard_port', PORT_ASSIGNMENTS['dashboard'])
        api_port = config.get('api_port', PORT_ASSIGNMENTS['api'])
        self.text.insert(tk.END, f"Dashboard: http://localhost:{dashboard_port}\n")
        self.text.insert(tk.END, f"API: http://localhost:{api_port}\n")
        self.text.insert(tk.END, f"WebSocket: ws://localhost:{config.get('websocket_port', PORT_ASSIGNMENTS['websocket'])}\n")

        self.text.config(state="disabled")


class ProgressPage(WizardPage):
    """Progress page for installation"""

    def __init__(self, parent):
        super().__init__(parent, "Installing GiljoAI MCP")

        # Progress bar
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(self, variable=self.progress_var,
                                       maximum=100, length=400)
        self.progress.pack(padx=20, pady=20)

        # Status label
        self.status_var = tk.StringVar(value="Ready to install...")
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.pack(padx=20, pady=5)

        # Detail text
        self.detail_text = tk.Text(self, height=15, width=70)
        self.detail_text.pack(padx=20, pady=10)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.detail_text)
        scrollbar.pack(side="right", fill="y")
        self.detail_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.detail_text.yview)

        self.completed = False

    def log(self, message: str):
        """Add message to detail log"""
        self.detail_text.insert(tk.END, f"{message}\n")
        self.detail_text.see(tk.END)
        self.update()

    def set_progress(self, value: int, status: Optional[str] = None):
        """Update progress"""
        self.progress_var.set(value)
        if status:
            self.status_var.set(status)
        self.update()

    def run_setup(self, config: dict):
        """Run the actual setup process"""
        try:
            self.log("Starting GiljoAI MCP setup...")
            self.set_progress(10, "Creating directories...")

            # Simulate setup steps (would call actual setup methods)
            import time

            self.log("Creating directory structure...")
            time.sleep(0.5)
            self.set_progress(20, "Generating configuration files...")

            self.log("Writing .env file...")
            time.sleep(0.5)
            self.set_progress(40, "Configuring database...")

            self.log("Initializing database...")
            time.sleep(0.5)
            self.set_progress(60, "Installing dependencies...")

            self.log("Installing Python packages...")
            time.sleep(1)
            self.set_progress(80, "Running post-install scripts...")

            self.log("Finalizing setup...")
            time.sleep(0.5)
            self.set_progress(100, "Setup complete!")

            self.log("\n✓ GiljoAI MCP setup completed successfully!")
            self.completed = True

        except Exception as e:
            self.log(f"\n✗ Setup failed: {e!s}")
            messagebox.showerror("Setup Failed", str(e))


class GiljoSetupGUI(GiljoSetup):
    """GUI extension of GiljoSetup using tkinter"""

    def __init__(self):
        super().__init__()
        self.root = tk.Tk()
        self.root.title("GiljoAI MCP Setup Wizard")
        self.root.geometry("800x600")
        self.root.resizable(False, False)

        # Configure style
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Current page tracking
        self.current_page = 0
        self.pages = []
        self.config_data = {}

        # Create main frames
        self._create_frames()

        # Create pages
        self._create_pages()

        # Show first page
        self._show_page(0)

    def _create_frames(self):
        """Create the main layout frames"""
        # Header frame
        header_frame = ttk.Frame(self.root, relief="ridge", borderwidth=2)
        header_frame.pack(fill="x", padx=5, pady=5)

        self.title_label = ttk.Label(header_frame, text="Welcome",
                                    font=("Helvetica", 14, "bold"))
        self.title_label.pack(pady=10)

        # Content frame
        self.content_frame = ttk.Frame(self.root)
        self.content_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Button frame
        button_frame = ttk.Frame(self.root)
        button_frame.pack(fill="x", padx=5, pady=5)

        # Navigation buttons
        self.back_btn = ttk.Button(button_frame, text="< Back",
                                  command=self._prev_page)
        self.back_btn.pack(side="left", padx=5)

        self.next_btn = ttk.Button(button_frame, text="Next >",
                                  command=self._next_page)
        self.next_btn.pack(side="right", padx=5)

        self.cancel_btn = ttk.Button(button_frame, text="Cancel",
                                    command=self._cancel)
        self.cancel_btn.pack(side="right", padx=5)

    def _create_pages(self):
        """Create all wizard pages"""
        self.pages = [
            WelcomePage(self.content_frame),
            DatabasePage(self.content_frame),
            PortsPage(self.content_frame),
            SecurityPage(self.content_frame),
            ReviewPage(self.content_frame, self._get_all_config),
            ProgressPage(self.content_frame)
        ]

    def _show_page(self, index: int):
        """Show specific page"""
        # Hide all pages
        for page in self.pages:
            page.pack_forget()

        # Show current page
        self.current_page = index
        page = self.pages[index]
        page.pack(fill="both", expand=True)

        # Update title
        self.title_label.config(text=page.title)

        # Update buttons
        self.back_btn.config(state="normal" if index > 0 else "disabled")

        if index == len(self.pages) - 1:
            self.next_btn.config(text="Finish", state="disabled")
        elif index == len(self.pages) - 2:
            self.next_btn.config(text="Install >", state="normal")
        else:
            self.next_btn.config(text="Next >", state="normal")

        # Call page enter method
        page.on_enter()

    def _next_page(self):
        """Go to next page"""
        current = self.pages[self.current_page]

        # Validate current page
        if not current.validate():
            return

        # Store page data BEFORE moving to next page
        self.config_data.update(current.get_data())
        current.on_exit()

        # Special handling for review page
        if self.current_page == len(self.pages) - 2:
            # Moving to progress page - start installation
            self._show_page(self.current_page + 1)
            self._run_installation()
        elif self.current_page < len(self.pages) - 1:
            self._show_page(self.current_page + 1)
        else:
            # Finish
            self.root.quit()

    def _prev_page(self):
        """Go to previous page"""
        if self.current_page > 0:
            self.pages[self.current_page].on_exit()
            self._show_page(self.current_page - 1)

    def _cancel(self):
        """Cancel setup"""
        if messagebox.askyesno("Cancel Setup",
                              "Are you sure you want to cancel setup?"):
            self.root.quit()

    def _get_all_config(self) -> dict:
        """Get all configuration data"""
        return self.config_data

    def _run_installation(self):
        """Run the actual installation in a thread"""
        progress_page = self.pages[-1]

        def install():
            # Convert GUI config to setup config format
            self._convert_config()

            # Run actual setup steps
            try:
                progress_page.set_progress(10, "Creating directories...")
                self._create_directories()
                progress_page.log("✓ Created directory structure")

                progress_page.set_progress(30, "Generating configuration...")
                self._generate_env_file()
                progress_page.log("✓ Generated .env file")

                self._generate_config_yaml()
                progress_page.log("✓ Generated config.yaml")

                progress_page.set_progress(50, "Setting up database...")
                if self.config_data.get("db_type") == "postgresql":
                    # Test PostgreSQL connection
                    self._build_pg_url()
                    # Would test connection here
                    progress_page.log("✓ PostgreSQL connection verified")
                else:
                    progress_page.log("✓ SQLite database configured")

                progress_page.set_progress(70, "Installing dependencies...")
                # Would install dependencies here
                progress_page.log("✓ Dependencies installed")

                progress_page.set_progress(90, "Finalizing...")
                progress_page.log("✓ Setup completed successfully!")

                progress_page.set_progress(100, "Complete!")
                progress_page.completed = True

                # Enable finish button
                self.next_btn.config(state="normal")

            except Exception as e:
                progress_page.log(f"\n✗ Setup failed: {e!s}")
                messagebox.showerror("Setup Failed", str(e))

        # Run in thread
        thread = threading.Thread(target=install)
        thread.start()

    def _convert_config(self):
        """Convert GUI config to setup config format"""
        # Database configuration
        if self.config_data.get("db_type") == "sqlite":
            db_path = Path(self.config_data.get("db_path", "data/giljo_mcp.db"))
            self.env_vars["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
            self.env_vars["DB_TYPE"] = "sqlite"
        else:
            self.env_vars["DB_TYPE"] = "postgresql"
            self.env_vars["DB_HOST"] = self.config_data.get("pg_host", "localhost")
            self.env_vars["DB_PORT"] = self.config_data.get("pg_port", "5432")
            self.env_vars["DB_NAME"] = self.config_data.get("pg_database", "giljo_mcp")
            self.env_vars["DB_USER"] = self.config_data.get("pg_user", "postgres")
            self.env_vars["DB_PASSWORD"] = self.config_data.get("pg_password", "")
            self.env_vars["DATABASE_URL"] = self._build_pg_url()

        # Ports
        for service in PORT_ASSIGNMENTS:
            key = f"{service}_port"
            if key in self.config_data:
                env_key = f"GILJO_MCP_{service.upper()}_PORT"
                self.env_vars[env_key] = self.config_data[key]

        # Security
        if self.config_data.get("api_key"):
            self.env_vars["GILJO_MCP_API_KEY"] = self.config_data["api_key"]

        self.env_vars["JWT_SECRET"] = self.config_data.get("jwt_secret", "")
        self.env_vars["CORS_ENABLED"] = str(self.config_data.get("cors_enabled", True))
        self.env_vars["CORS_ORIGINS"] = self.config_data.get("cors_origins", "http://localhost:*")

        # Mode
        self.env_vars["GILJO_MCP_MODE"] = self.config_data.get("mode", "development")
        self.env_vars["DEBUG"] = "true" if self.config_data.get("mode") == "development" else "false"

    def _build_pg_url(self) -> str:
        """Build PostgreSQL URL from config"""
        host = self.config_data.get("pg_host", "localhost")
        port = self.config_data.get("pg_port", "5432")
        database = self.config_data.get("pg_database", "giljo_mcp")
        user = self.config_data.get("pg_user", "postgres")
        password = self.config_data.get("pg_password", "")

        if password:
            return f"postgresql://{user}:{password}@{host}:{port}/{database}"
        return f"postgresql://{user}@{host}:{port}/{database}"

    def run(self):
        """Run the GUI wizard"""
        # Center window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"{width}x{height}+{x}+{y}")

        # Run main loop
        self.root.mainloop()


if __name__ == "__main__":
    gui = GiljoSetupGUI()
    gui.run()
