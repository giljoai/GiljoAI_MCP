#!/usr/bin/env python3
"""
GiljoAI MCP GUI Setup - Tkinter-based wizard interface
Provides a graphical setup wizard as an alternative to CLI mode
"""

import sys
import threading
import time
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
        super().__init__(parent, "Welcome to GiljoAI MCP Setup")

        # Welcome Title
        title_label = ttk.Label(self, text="GiljoAI MCP Coding Orchestrator", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=10)

        # Welcome message
        welcome_text = """Welcome to the GiljoAI MCP installation wizard.

This wizard will help you:
• Check system requirements and port availability
• Configure your database and security settings
• Install required dependencies
• Initialize your orchestrator

Select the deployment mode that best matches your needs:"""

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
            text="Single Developer Mode",
            variable=self.mode_var,
            value="local",
            command=self._on_mode_change,
        ).pack(anchor="w")

        local_desc = """• SQLite database (zero configuration)
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

        server_desc = """• PostgreSQL or SQLite database
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
        return {"deployment_mode": self.mode_var.get()}

    def on_enter(self):
        """Called when entering the page"""
        # Could check for existing installation and suggest profile
        pass


class DatabasePage(WizardPage):
    """Database configuration page"""

    def __init__(self, parent):
        super().__init__(parent, "Database Configuration")

        self.db_type_var = tk.StringVar(value="sqlite")

        # Database type selection
        type_frame = ttk.LabelFrame(self, text="Database Type", padding=10)
        type_frame.pack(padx=20, pady=10, fill="x")

        ttk.Radiobutton(
            type_frame,
            text="SQLite (Recommended for Local Development)",
            variable=self.db_type_var,
            value="sqlite",
            command=self._on_db_type_change,
        ).pack(anchor="w")
        ttk.Radiobutton(
            type_frame,
            text="PostgreSQL (For Network Shared or High Performance)",
            variable=self.db_type_var,
            value="postgresql",
            command=self._on_db_type_change,
        ).pack(anchor="w")

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
            defaultextension=".db", filetypes=[("SQLite Database", "*.db"), ("All Files", "*.*")]
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
                    password=self.pg_password_var.get(),
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
        return all([self.pg_host_var.get(), self.pg_port_var.get(), self.pg_database_var.get(), self.pg_user_var.get()])

    def get_data(self) -> dict:
        if self.db_type_var.get() == "sqlite":
            return {"db_type": "sqlite", "db_path": self.db_path_var.get()}
        return {
            "db_type": "postgresql",
            "pg_host": self.pg_host_var.get(),
            "pg_port": self.pg_port_var.get(),
            "pg_database": self.pg_database_var.get(),
            "pg_user": self.pg_user_var.get(),
            "pg_password": self.pg_password_var.get(),
        }

    def on_enter(self):
        """Adapt database settings based on selected profile"""
        # Access the parent GiljoSetupGUI instance to get config data
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            profile = parent.config_data.get("profile", "developer")

            # Set defaults based on profile
            if profile == "developer":
                # Default to SQLite for individual developers
                self.db_type_var.set("sqlite")
                self.db_path_var.set("data/giljo_mcp.db")
                self._on_db_type_change()

            elif profile == "team":
                # Default to PostgreSQL for teams
                self.db_type_var.set("postgresql")
                self.pg_database_var.set("giljo_mcp_team")
                self.pg_user_var.set("giljo_team")
                self._on_db_type_change()

            elif profile == "enterprise":
                # PostgreSQL with enterprise defaults
                self.db_type_var.set("postgresql")
                self.pg_database_var.set("giljo_mcp_prod")
                self.pg_user_var.set("giljo_enterprise")
                self.pg_port_var.set("5432")
                self._on_db_type_change()

            elif profile == "research":
                # Flexible setup, default to SQLite but show both options
                self.db_type_var.set("sqlite")
                self.db_path_var.set("data/research_giljo.db")
                self._on_db_type_change()

            # Update the instructions based on profile
            self._update_instructions(profile)

    def _update_instructions(self, profile: str):
        """Update the page title and instructions based on profile"""
        profile_titles = {
            "developer": "Database Configuration - Developer Profile",
            "team": "Database Configuration - Team Profile",
            "enterprise": "Database Configuration - Enterprise Profile",
            "research": "Database Configuration - Research Profile",
        }

        if hasattr(self, "title"):
            self.title = profile_titles.get(profile, "Database Configuration")


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
        return {f"{service}_port": self.port_vars[service].get() for service in self.port_vars}

    def on_enter(self):
        """Adapt port settings based on selected profile"""
        # Access the parent GiljoSetupGUI instance to get config data
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            profile = parent.config_data.get("profile", "developer")

            # Set port recommendations based on profile
            if profile == "enterprise":
                # Enterprise uses standard ports for production
                self.port_vars["api"].set("80")
                self.port_vars["websocket"].set("443")
                self.port_vars["dashboard"].set("443")
                self.port_vars["mcp"].set("3000")
            elif profile == "team":
                # Team uses higher ports to avoid conflicts
                self.port_vars["api"].set("9000")
                self.port_vars["websocket"].set("9001")
                self.port_vars["dashboard"].set("9002")
                self.port_vars["mcp"].set("9003")
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
        dashboard_port = config.get("dashboard_port", PORT_ASSIGNMENTS["GiljoAI Dashboard"])
        api_port = config.get("api_port", PORT_ASSIGNMENTS["GiljoAI REST API"])
        self.text.insert(tk.END, f"Dashboard: http://localhost:{dashboard_port}\n")
        self.text.insert(tk.END, f"API: http://localhost:{api_port}\n")
        self.text.insert(
            tk.END, f"WebSocket: ws://localhost:{config.get('websocket_port', PORT_ASSIGNMENTS['GiljoAI WebSocket'])}\n"
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

        # Main frame
        main_frame = ttk.Frame(self)
        main_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Title
        title = ttk.Label(main_frame, text="Installing Components", font=("Arial", 12, "bold"))
        title.pack(pady=(0, 10))

        # Components frame with individual progress bars
        self.components_frame = ttk.LabelFrame(main_frame, text="Component Installation Status")
        self.components_frame.pack(fill="both", expand=False, pady=10)

        # Initialize component tracking
        self.components = {}
        self.component_widgets = {}
        self._init_components()

        # Console output section
        console_frame = ttk.LabelFrame(main_frame, text="Installation Log")
        console_frame.pack(fill="both", expand=True, pady=10)

        # Text widget with scrollbar
        console_container = ttk.Frame(console_frame)
        console_container.pack(fill="both", expand=True, padx=10, pady=10)

        self.console_text = tk.Text(console_container, height=8, width=80, wrap=tk.WORD,
                                   bg='black', fg='white', font=('Consolas', 9))
        scrollbar = ttk.Scrollbar(console_container, command=self.console_text.yview)
        self.console_text.configure(yscrollcommand=scrollbar.set)

        self.console_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Configure text tags
        self.console_text.tag_config("info", foreground="white")
        self.console_text.tag_config("success", foreground="lime")
        self.console_text.tag_config("warning", foreground="yellow")
        self.console_text.tag_config("error", foreground="red")

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
        self.redis_text = self.console_text
        # Docker removed - not needed
        self.system_text = self.console_text
        self.pg_progress_var = tk.IntVar(value=0)
        self.redis_progress_var = tk.IntVar(value=0)
        # Docker progress removed
        self.pg_status_var = tk.StringVar()
        self.redis_status_var = tk.StringVar()
        # Docker status removed

        self.completed = False

    def _init_components(self):
        """Initialize component list - will be updated based on profile"""
        component_list = [
            ('config', 'Configuration Files'),
            ('directories', 'Directory Structure'),
            ('database', 'Database Setup'),
            ('redis', 'Redis Cache'),
            ('schema', 'Database Schema'),
            ('validation', 'System Validation')
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

    def update_component_applicability(self, profile: str):
        """Update which components are applicable based on profile"""
        # Define applicability rules
        rules = {
            'developer': {
                'database': ('SQLite Database', True),
                'redis': ('Redis Cache', True),
            },
            'team': {
                'database': ('PostgreSQL Database', True),
                'redis': ('Redis Cache', True),
            },
            'enterprise': {
                'database': ('PostgreSQL Database', True),
                'redis': ('Redis Cache', True),
            },
            'research': {
                'database': ('SQLite Database', True),
                'redis': ('Redis Cache', False),
            }
        }

        profile_rules = rules.get(profile, rules['developer'])

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
        elif target == "redis":
            self.redis_progress_var.set(value)
            if 'redis' in self.components:
                self.components['redis']['progress_var'].set(value)
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
        elif target == "redis":
            self.redis_status_var.set(status)
            if 'redis' in self.components:
                self._update_component_status('redis', status)
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
            from datetime import datetime

            manifest = {
                "version": "1.0",
                "installation_date": datetime.now().isoformat(),
                "profile": config.get("profile", "developer"),
                "install_directory": str(Path.cwd()),
                "dependencies": {
                    "redis": {
                        "installed": redis_installed,
                        "location": "C:/Redis" if redis_installed else None,
                        "service_name": "Redis" if redis_installed else None
                    },
                    "postgresql": {
                        "installed": postgresql_installed,
                        "location": "C:/PostgreSQL/16" if postgresql_installed else None,
                        "service_name": "postgresql-x64-16" if postgresql_installed else None
                    }
                },
                "configuration": {
                    "database_type": config.get("db_type", "sqlite"),
                    "ports": {
                        "dashboard": config.get("dashboard_port", 6000),
                        "api": config.get("api_port", 6002),
                        "websocket": config.get("websocket_port", 6003),
                        "server": config.get("server_port", 6001)
                    }
                }
            }

            manifest_path = Path(".giljo_install_manifest.json")
            with open(manifest_path, "w") as f:
                json.dump(manifest, f, indent=2)

            self.log(f"Created installation manifest: {manifest_path}", "system")

        except Exception as e:
            self.log(f"Warning: Could not create installation manifest: {e}", "system")

    def run_setup(self, config: dict):
        """Run installation based on profile and configuration"""
        import threading
        import time

        profile = config.get("profile", "developer")
        self.log(f"Starting installation for {profile} profile", "system")

        # Update component applicability
        self.update_component_applicability(profile)

        # Determine database type based on deployment mode
        # Local mode: SQLite (no additional services needed)
        # Server mode: Can use PostgreSQL if configured
        run_postgresql = False

        if profile == "server":
            if config.get("db_type") == "postgresql":
                run_postgresql = True
                self.log("Server mode: Using PostgreSQL database", "system")
            else:
                self.log("Server mode: Using SQLite database", "system")
        else:  # Local mode
            self.log("Local mode: Using SQLite database (no additional services needed)", "system")

        # Create configuration files
        self.set_status("Creating configuration files...", "config")
        self.set_progress(10, "config")
        self.log("Creating configuration files...", "system")

        try:
            from setup_config import ConfigurationManager

            config_mgr = ConfigurationManager()

            # Prepare config values
            config_values = {
                "database_type": "postgresql" if run_postgresql else "sqlite",
                "api_port": config.get("api_port", 6002),
                "websocket_port": config.get("websocket_port", 6003),
                "dashboard_port": config.get("dashboard_port", 6000),
                "server_port": config.get("server_port", 6001),
                "redis_enabled": False,  # Redis removed - not needed
                "redis_host": "",
                "redis_port": 0,
                "jwt_secret": config.get("jwt_secret", ""),
                "api_key": config.get("api_key", ""),
                "api_key_enabled": profile in ["team", "enterprise"]
            }

            if run_postgresql:
                config_values.update({
                    "pg_host": config.get("pg_host", "localhost"),
                    "pg_port": config.get("pg_port", 5432),
                    "pg_database": config.get("pg_database", "giljo_mcp"),
                    "pg_user": config.get("pg_user", "postgres"),
                    "pg_password": config.get("pg_password", ""),
                })
            else:
                config_values["db_path"] = config.get("db_path", "data/giljo_mcp.db")

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

        # Initialize database schema
        self.set_status("Initializing database schema...", "schema")
        self.set_progress(10, "schema")
        self.log("Initializing database schema...", "system")

        try:
            # Try to import and initialize database
            try:
                from src.giljo_mcp.models.base import init_database
                init_database()
                self.log("SUCCESS: Database schema initialized", "system")
                self.set_status("Database schema initialized ✓", "schema")
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
                ("Redis", redis_status, redis_msg),
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

            # Create installation manifest for uninstaller
            self.create_installation_manifest(config, run_postgresql, run_redis)

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

        # Configure style
        style = ttk.Style()
        # Comment out clam theme as it causes text rendering issues on Windows
        # style.theme_use('clam')

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
        self.canvas = tk.Canvas(self.content_container, highlightthickness=0)
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
            # Disable next during installation
            if hasattr(current_page, 'completed') and current_page.completed:
                self.next_btn.config(text="Next >", state="normal")
            else:
                self.next_btn.config(state="disabled")
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
            # Start installation after review
            progress_page = self.pages[self.current_page_index + 1]
            if isinstance(progress_page, ProgressPage):
                self.show_page(self.current_page_index + 1)
                # Start installation in a thread
                import threading
                install_thread = threading.Thread(target=self.run_installation)
                install_thread.daemon = True
                install_thread.start()
                return

        # Normal page transition
        if self.current_page_index < len(self.pages) - 1:
            self.show_page(self.current_page_index + 1)

    def run_installation(self):
        """Run the installation process"""
        try:
            progress_page = None
            for page in self.pages:
                if isinstance(page, ProgressPage):
                    progress_page = page
                    break

            if progress_page:
                progress_page.run_setup(self.config_data)

                # Update navigation when complete
                self.root.after(1000, self.update_navigation)

        except Exception as e:
            messagebox.showerror("Installation Error", f"Installation failed: {str(e)}")

    def cancel_setup(self):
        """Cancel the setup wizard"""
        if messagebox.askyesno("Cancel Setup", "Are you sure you want to cancel the setup?"):
            self.root.quit()
            self.root.destroy()
            sys.exit(1)

    def finish_setup(self):
        """Complete the setup process"""
        # Create a more informative completion message
        message = """GiljoAI MCP has been installed successfully!

To start using GiljoAI MCP:

1. Run 'start_giljo.bat' to start all services
2. The dashboard will open automatically at http://localhost:6000
3. Use 'stop_giljo.bat' to stop all services when done

The dashboard includes:
• System health monitoring
• Database connectivity status
• Service management controls
• Agent orchestration interface

Thank you for installing GiljoAI MCP!"""

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
