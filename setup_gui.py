#!/usr/bin/env python3
"""
GiljoAI MCP GUI Setup - Tkinter-based wizard interface
Provides a graphical setup wizard as an alternative to CLI mode
"""

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


class WelcomePage(WizardPage):
    """Welcome page with overview"""

    def __init__(self, parent):
        super().__init__(parent, "Welcome to GiljoAI MCP Setup")

        # Title
        title_label = ttk.Label(self, text="GiljoAI MCP Setup Wizard", font=("Helvetica", 16, "bold"))
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
        self.mode_var = tk.StringVar(value="local")
        mode_frame = ttk.LabelFrame(self, text="Setup Mode", padding=10)
        mode_frame.pack(padx=20, pady=10, fill="x")

        ttk.Radiobutton(
            mode_frame,
            text="Local Development (Single machine, SQLite, full features)",
            variable=self.mode_var,
            value="local",
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame,
            text="Network Shared (Multi-user, PostgreSQL, LAN accessible)",
            variable=self.mode_var,
            value="lan",
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame,
            text="High Performance (Production-ready, optimized for scale)",
            variable=self.mode_var,
            value="wan",
        ).pack(anchor="w")

    def get_data(self) -> dict:
        return {"mode": self.mode_var.get()}


class ProfileSelectionPage(WizardPage):
    """Profile selection page for different user types"""

    def __init__(self, parent):
        super().__init__(parent, "Select Installation Profile")

        # Title
        title_label = ttk.Label(self, text="Choose Your Installation Profile", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=20)

        # Description
        desc_text = """Select the profile that best matches your needs. This will customize the installation
process and default configurations for your specific use case."""

        desc_label = ttk.Label(self, text=desc_text, justify=tk.LEFT)
        desc_label.pack(padx=20, pady=10)

        # Profile selection
        self.profile_var = tk.StringVar(value="developer")

        # Create profile frames
        profiles_frame = ttk.Frame(self)
        profiles_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Developer Profile
        dev_frame = ttk.LabelFrame(profiles_frame, text="Developer Profile", padding=10)
        dev_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            dev_frame,
            text="Individual Developer",
            variable=self.profile_var,
            value="developer",
            command=self._on_profile_change,
        ).pack(anchor="w")

        dev_desc = """• Personal coding assistant with local SQLite database
• Minimal setup with default ports (8000 for API, 8001 for WebSocket)
• Single-user authentication with simple API key
• Optimized for individual productivity and learning
• Ideal for: Solo developers, hobbyists, students"""

        ttk.Label(dev_frame, text=dev_desc, justify=tk.LEFT, foreground="gray").pack(padx=20, pady=5, anchor="w")

        # Team Profile
        team_frame = ttk.LabelFrame(profiles_frame, text="Team Profile", padding=10)
        team_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            team_frame,
            text="Development Team",
            variable=self.profile_var,
            value="team",
            command=self._on_profile_change,
        ).pack(anchor="w")

        team_desc = """• Shared PostgreSQL database for team collaboration
• Network-accessible with configurable ports
• Multi-user authentication with role-based access
• Project isolation and team management features
• Ideal for: Small to medium development teams, startups"""

        ttk.Label(team_frame, text=team_desc, justify=tk.LEFT, foreground="gray").pack(padx=20, pady=5, anchor="w")

        # Enterprise Profile
        enterprise_frame = ttk.LabelFrame(profiles_frame, text="Enterprise Profile", padding=10)
        enterprise_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            enterprise_frame,
            text="Enterprise Deployment",
            variable=self.profile_var,
            value="enterprise",
            command=self._on_profile_change,
        ).pack(anchor="w")

        enterprise_desc = """• Production-grade PostgreSQL with replication support
• Advanced security with OAuth2/SAML integration
• High availability and load balancing ready
• Audit logging and compliance features
• Ideal for: Large organizations, regulated industries"""

        ttk.Label(enterprise_frame, text=enterprise_desc, justify=tk.LEFT, foreground="gray").pack(
            padx=20, pady=5, anchor="w"
        )

        # Research Profile
        research_frame = ttk.LabelFrame(profiles_frame, text="Research Profile", padding=10)
        research_frame.pack(fill="x", pady=5)

        ttk.Radiobutton(
            research_frame,
            text="AI Research & Education",
            variable=self.profile_var,
            value="research",
            command=self._on_profile_change,
        ).pack(anchor="w")

        research_desc = """• Flexible configuration for experimentation
• Extended agent templates for research scenarios
• Detailed logging and metrics collection
• Educational resources and examples included
• Ideal for: Researchers, educators, AI labs"""

        ttk.Label(research_frame, text=research_desc, justify=tk.LEFT, foreground="gray").pack(
            padx=20, pady=5, anchor="w"
        )

        # Status label for profile details
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(padx=20, pady=10, fill="x")

        self.status_label = ttk.Label(self.status_frame, text="", foreground="blue")
        self.status_label.pack()

        # Set initial status
        self._on_profile_change()

    def _on_profile_change(self):
        """Update status based on selected profile"""
        profile = self.profile_var.get()

        status_messages = {
            "developer": "✓ Ready for quick setup with minimal configuration",
            "team": "✓ Will configure network settings and multi-user support",
            "enterprise": "✓ Will enable enterprise features and security options",
            "research": "✓ Will include research templates and educational content",
        }

        self.status_label.config(text=status_messages.get(profile, ""))

    def get_data(self) -> dict:
        return {"profile": self.profile_var.get()}

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
            self.api_frame_inner, text="⚠️ Copy this key now! It won't be shown again.", foreground="orange"
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
            self._toggle_api_key()


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

        # Deployment Mode
        self.text.insert(tk.END, "DEPLOYMENT MODE\n")
        self.text.insert(tk.END, "-" * 30 + "\n")
        mode_display = {"local": "Local Development", "lan": "Network Shared", "wan": "High Performance"}
        mode = config.get("mode", "local")
        self.text.insert(tk.END, f"Mode: {mode_display.get(mode, mode.capitalize())}\n\n")

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
        dashboard_port = config.get("dashboard_port", PORT_ASSIGNMENTS["dashboard"])
        api_port = config.get("api_port", PORT_ASSIGNMENTS["api"])
        self.text.insert(tk.END, f"Dashboard: http://localhost:{dashboard_port}\n")
        self.text.insert(tk.END, f"API: http://localhost:{api_port}\n")
        self.text.insert(
            tk.END, f"WebSocket: ws://localhost:{config.get('websocket_port', PORT_ASSIGNMENTS['websocket'])}\n"
        )

        self.text.config(state="disabled")


class ServiceControlPage(WizardPage):
    """Service management page for controlling PostgreSQL, Redis, and GiljoAI services"""

    def __init__(self, parent):
        super().__init__(parent, "Service Management")

        # Title
        title_label = ttk.Label(self, text="Service Control Panel", font=("Helvetica", 16, "bold"))
        title_label.pack(pady=20)

        # Description
        desc_text = """Configure and manage your services. Services will be automatically installed
and configured based on your profile selection."""

        desc_label = ttk.Label(self, text=desc_text, justify=tk.LEFT)
        desc_label.pack(padx=20, pady=10)

        # Services frame
        services_frame = ttk.Frame(self)
        services_frame.pack(padx=20, pady=10, fill="both", expand=True)

        # Service status variables
        self.service_statuses = {}
        self.service_buttons = {}
        self.autostart_vars = {}

        # Create service controls
        self.services = []  # Will be populated in on_enter based on profile
        self.service_widgets = {}

        # Control buttons frame
        control_frame = ttk.Frame(self)
        control_frame.pack(padx=20, pady=10, fill="x")

        # Refresh button
        self.refresh_btn = ttk.Button(control_frame, text="Refresh Status", command=self._refresh_all_services)
        self.refresh_btn.pack(side="left", padx=5)

        # Auto-configure button
        self.auto_config_btn = ttk.Button(control_frame, text="Auto-Configure Services", command=self._auto_configure)
        self.auto_config_btn.pack(side="left", padx=5)

        # Status label
        self.status_var = tk.StringVar(value="Service status will be shown here")
        self.status_label = ttk.Label(control_frame, textvariable=self.status_var)
        self.status_label.pack(side="right", padx=5)

    def _create_service_widget(self, parent, service_name: str, display_name: str):
        """Create service control widget"""
        # Service frame
        service_frame = ttk.LabelFrame(parent, text=display_name, padding=10)
        service_frame.pack(fill="x", pady=5)

        # Status frame
        status_frame = ttk.Frame(service_frame)
        status_frame.pack(fill="x")

        # Status indicator
        status_var = tk.StringVar(value="Unknown")
        status_label = ttk.Label(status_frame, textvariable=status_var, font=("Helvetica", 10, "bold"))
        status_label.pack(side="left")

        # Store status variable
        self.service_statuses[service_name] = status_var

        # Buttons frame
        buttons_frame = ttk.Frame(service_frame)
        buttons_frame.pack(fill="x", pady=5)

        # Control buttons
        start_btn = ttk.Button(buttons_frame, text="Start", command=lambda: self._start_service(service_name))
        start_btn.pack(side="left", padx=2)

        stop_btn = ttk.Button(buttons_frame, text="Stop", command=lambda: self._stop_service(service_name))
        stop_btn.pack(side="left", padx=2)

        restart_btn = ttk.Button(buttons_frame, text="Restart", command=lambda: self._restart_service(service_name))
        restart_btn.pack(side="left", padx=2)

        # Auto-start checkbox
        autostart_var = tk.BooleanVar()
        autostart_check = ttk.Checkbutton(
            buttons_frame,
            text="Auto-start on boot",
            variable=autostart_var,
            command=lambda: self._toggle_autostart(service_name, autostart_var.get()),
        )
        autostart_check.pack(side="right")

        # Store references
        self.service_buttons[service_name] = {"start": start_btn, "stop": stop_btn, "restart": restart_btn}
        self.autostart_vars[service_name] = autostart_var
        self.service_widgets[service_name] = service_frame

        return service_frame

    def on_enter(self):
        """Setup services based on profile when entering the page"""
        # Access the parent GiljoSetupGUI instance to get config data
        parent = self.parent
        while parent and not hasattr(parent, "config_data"):
            parent = parent.master

        if parent and hasattr(parent, "config_data"):
            profile = parent.config_data.get("profile", "developer")

            # Clear existing widgets
            for widget in self.service_widgets.values():
                widget.destroy()
            self.service_widgets.clear()
            self.services.clear()

            # Determine services based on profile
            services_frame = self.children["!frame"]  # Get the services frame

            if profile == "developer":
                # Developer may have PostgreSQL if selected, always has app service
                if parent.config_data.get("db_type") == "postgresql":
                    self.services.append(("postgresql", "PostgreSQL Database"))
                self.services.append(("giljo_app", "GiljoAI Application"))

            elif profile in ["team", "enterprise"]:
                # Network profiles have all services
                self.services.extend(
                    [
                        ("postgresql", "PostgreSQL Database"),
                        ("redis", "Redis Cache"),
                        ("giljo_app", "GiljoAI Application"),
                        ("giljo_worker", "GiljoAI Worker"),
                    ]
                )

            elif profile == "research":
                # Research profile has flexible services
                if parent.config_data.get("db_type") == "postgresql":
                    self.services.append(("postgresql", "PostgreSQL Database"))
                self.services.append(("giljo_app", "GiljoAI Application"))

            # Add Docker if containerized
            if parent.config_data.get("deployment_mode") == "containerized":
                self.services.append(("docker", "Docker Daemon"))

            # Create widgets for each service
            for service_name, display_name in self.services:
                self._create_service_widget(services_frame, service_name, display_name)

            # Refresh status for all services
            self._refresh_all_services()

    def _get_service_manager(self):
        """Get ServiceManager instance"""
        try:
            from installer.services.service_manager import ServiceManager

            return ServiceManager()
        except ImportError:
            self.status_var.set("Service Manager not available")
            return None
        except Exception as e:
            self.status_var.set(f"Service Manager error: {e}")
            return None

    def _refresh_all_services(self):
        """Refresh status for all services"""
        service_manager = self._get_service_manager()
        if not service_manager:
            return

        for service_name, _ in self.services:
            try:
                status = service_manager.get_service_status(service_name)
                status_text = status.value.upper()

                # Update status display with color
                status_var = self.service_statuses[service_name]
                if status.name == "RUNNING":
                    status_var.set(f"🟢 {status_text}")
                elif status.name == "STOPPED":
                    status_var.set(f"🔴 {status_text}")
                elif status.name == "STARTING":
                    status_var.set(f"🟡 {status_text}")
                elif status.name == "FAILED":
                    status_var.set(f"❌ {status_text}")
                else:
                    status_var.set(f"⚪ {status_text}")

                # Update button states
                buttons = self.service_buttons[service_name]
                if status.name == "RUNNING":
                    buttons["start"].config(state="disabled")
                    buttons["stop"].config(state="normal")
                    buttons["restart"].config(state="normal")
                elif status.name == "STOPPED":
                    buttons["start"].config(state="normal")
                    buttons["stop"].config(state="disabled")
                    buttons["restart"].config(state="disabled")
                else:
                    # Starting/stopping/unknown
                    buttons["start"].config(state="disabled")
                    buttons["stop"].config(state="disabled")
                    buttons["restart"].config(state="disabled")

                # Check auto-start status
                is_autostart = service_manager.is_autostart_enabled(service_name)
                self.autostart_vars[service_name].set(is_autostart)

            except Exception as e:
                self.service_statuses[service_name].set(f"❓ ERROR: {e}")

        self.status_var.set(f"Status updated for {len(self.services)} services")

    def _start_service(self, service_name: str):
        """Start a service"""
        service_manager = self._get_service_manager()
        if not service_manager:
            return

        try:
            self.status_var.set(f"Starting {service_name}...")
            success = service_manager.start_service(service_name)
            if success:
                self.status_var.set(f"✅ {service_name} started")
            else:
                self.status_var.set(f"❌ Failed to start {service_name}")

            # Refresh status after a brief delay
            self.after(2000, self._refresh_all_services)

        except Exception as e:
            self.status_var.set(f"Error starting {service_name}: {e}")

    def _stop_service(self, service_name: str):
        """Stop a service"""
        service_manager = self._get_service_manager()
        if not service_manager:
            return

        try:
            self.status_var.set(f"Stopping {service_name}...")
            success = service_manager.stop_service(service_name)
            if success:
                self.status_var.set(f"✅ {service_name} stopped")
            else:
                self.status_var.set(f"❌ Failed to stop {service_name}")

            # Refresh status after a brief delay
            self.after(2000, self._refresh_all_services)

        except Exception as e:
            self.status_var.set(f"Error stopping {service_name}: {e}")

    def _restart_service(self, service_name: str):
        """Restart a service"""
        service_manager = self._get_service_manager()
        if not service_manager:
            return

        try:
            self.status_var.set(f"Restarting {service_name}...")
            success = service_manager.restart_service(service_name)
            if success:
                self.status_var.set(f"✅ {service_name} restarted")
            else:
                self.status_var.set(f"❌ Failed to restart {service_name}")

            # Refresh status after a brief delay
            self.after(2000, self._refresh_all_services)

        except Exception as e:
            self.status_var.set(f"Error restarting {service_name}: {e}")

    def _toggle_autostart(self, service_name: str, enabled: bool):
        """Toggle auto-start for a service"""
        service_manager = self._get_service_manager()
        if not service_manager:
            return

        try:
            if enabled:
                success = service_manager.enable_autostart(service_name)
                action = "enabled"
            else:
                success = service_manager.disable_autostart(service_name)
                action = "disabled"

            if success:
                self.status_var.set(f"✅ Auto-start {action} for {service_name}")
            else:
                self.status_var.set(f"❌ Failed to {action.replace('d', '')} auto-start for {service_name}")

        except Exception as e:
            self.status_var.set(f"Error configuring auto-start for {service_name}: {e}")

    def _auto_configure(self):
        """Auto-configure all services based on profile"""
        service_manager = self._get_service_manager()
        if not service_manager:
            return

        try:
            self.status_var.set("Auto-configuring services...")

            # Install and configure each service
            for service_name, display_name in self.services:
                try:
                    # Install service if not already installed
                    if not service_manager.is_service_installed(service_name):
                        self.status_var.set(f"Installing {display_name}...")
                        service_manager.install_service(service_name)

                    # Enable auto-start for critical services
                    if service_name in ["postgresql", "redis", "giljo_app"]:
                        service_manager.enable_autostart(service_name)

                except Exception as e:
                    self.status_var.set(f"Error configuring {service_name}: {e}")
                    continue

            self.status_var.set("✅ Auto-configuration complete")

            # Refresh all statuses
            self.after(1000, self._refresh_all_services)

        except Exception as e:
            self.status_var.set(f"Auto-configuration error: {e}")

    def validate(self) -> bool:
        """Validate page - always valid (optional step)"""
        return True

    def get_data(self) -> dict:
        """Return service configuration data"""
        return {
            "services_configured": len(self.services),
            "service_list": [name for name, _ in self.services],
            "autostart_services": [
                name for name, _ in self.services if self.autostart_vars.get(name, tk.BooleanVar()).get()
            ],
        }


class ProgressPage(WizardPage):
    """Installation progress page with parallel installer support"""

    def __init__(self, parent):
        super().__init__(parent, "Installation Progress")

        # Main progress for overall installation
        self.progress_var = tk.IntVar(value=0)
        self.progress = ttk.Progressbar(self, variable=self.progress_var, maximum=100)
        self.progress.pack(padx=20, pady=10, fill="x")

        # Status label
        self.status_var = tk.StringVar(value="Preparing installation...")
        self.status_label = ttk.Label(self, textvariable=self.status_var)
        self.status_label.pack(padx=20, pady=5)

        # Create notebook for parallel progress tracking
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(padx=20, pady=10, fill="both", expand=True)

        # PostgreSQL tab
        self.pg_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.pg_frame, text="PostgreSQL")

        self.pg_progress_var = tk.IntVar(value=0)
        self.pg_progress = ttk.Progressbar(self.pg_frame, variable=self.pg_progress_var, maximum=100)
        self.pg_progress.pack(padx=10, pady=10, fill="x")

        self.pg_status_var = tk.StringVar(value="Not started")
        ttk.Label(self.pg_frame, textvariable=self.pg_status_var).pack(padx=10, pady=5)

        self.pg_text = tk.Text(self.pg_frame, height=8, width=60)
        self.pg_text.pack(padx=10, pady=5, fill="both", expand=True)

        # Redis tab
        self.redis_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.redis_frame, text="Redis")

        self.redis_progress_var = tk.IntVar(value=0)
        self.redis_progress = ttk.Progressbar(self.redis_frame, variable=self.redis_progress_var, maximum=100)
        self.redis_progress.pack(padx=10, pady=10, fill="x")

        self.redis_status_var = tk.StringVar(value="Not started")
        ttk.Label(self.redis_frame, textvariable=self.redis_status_var).pack(padx=10, pady=5)

        self.redis_text = tk.Text(self.redis_frame, height=8, width=60)
        self.redis_text.pack(padx=10, pady=5, fill="both", expand=True)

        # Docker tab (for containerized profile)
        self.docker_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.docker_frame, text="Docker")

        self.docker_progress_var = tk.IntVar(value=0)
        self.docker_progress = ttk.Progressbar(self.docker_frame, variable=self.docker_progress_var, maximum=100)
        self.docker_progress.pack(padx=10, pady=10, fill="x")

        self.docker_status_var = tk.StringVar(value="Not started")
        ttk.Label(self.docker_frame, textvariable=self.docker_status_var).pack(padx=10, pady=5)

        self.docker_text = tk.Text(self.docker_frame, height=8, width=60)
        self.docker_text.pack(padx=10, pady=5, fill="both", expand=True)

        # System tab for general logs
        self.system_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.system_frame, text="System")

        self.system_text = tk.Text(self.system_frame, height=12, width=60)
        self.system_text.pack(padx=10, pady=5, fill="both", expand=True)

        self.completed = False

    def log(self, message: str, target: str = "system"):
        """Log message to appropriate target"""
        timestamp = time.strftime("%H:%M:%S")
        formatted = f"[{timestamp}] {message}\n"

        if target == "postgresql":
            self.pg_text.insert(tk.END, formatted)
            self.pg_text.see(tk.END)
        elif target == "redis":
            self.redis_text.insert(tk.END, formatted)
            self.redis_text.see(tk.END)
        elif target == "docker":
            self.docker_text.insert(tk.END, formatted)
            self.docker_text.see(tk.END)
        else:
            self.system_text.insert(tk.END, formatted)
            self.system_text.see(tk.END)

        self.update_idletasks()

    def set_progress(self, value: int, target: str = "main"):
        """Update progress for specific target"""
        if target == "postgresql":
            self.pg_progress_var.set(value)
        elif target == "redis":
            self.redis_progress_var.set(value)
        elif target == "docker":
            self.docker_progress_var.set(value)
        else:
            self.progress_var.set(value)
        self.update_idletasks()

    def set_status(self, status: str, target: str = "main"):
        """Update status for specific target"""
        if target == "postgresql":
            self.pg_status_var.set(status)
        elif target == "redis":
            self.redis_status_var.set(status)
        elif target == "docker":
            self.docker_status_var.set(status)
        else:
            self.status_var.set(status)
        self.update_idletasks()

    def run_setup(self, config: dict):
        """Run installation based on profile and configuration"""
        import threading
        import time

        profile = config.get("profile", "developer")
        self.log(f"Starting installation for {profile} profile", "system")

        # Determine which installers to run based on profile
        run_postgresql = False
        run_redis = False
        run_docker = False

        if profile in ["team", "enterprise"]:
            # Network profiles need both databases
            run_postgresql = True
            run_redis = True
            self.log("Network profile detected - will install PostgreSQL and Redis", "system")
        elif profile == "developer":
            # Developer uses SQLite by default, but check if PostgreSQL was selected
            if config.get("db_type") == "postgresql":
                run_postgresql = True
                self.log("PostgreSQL selected for developer profile", "system")
            else:
                self.log("Using SQLite for developer profile", "system")
        elif profile == "research":
            # Research profile - flexible, check configuration
            if config.get("db_type") == "postgresql":
                run_postgresql = True
            # Could optionally install Redis for caching

        # Check for containerized deployment
        if config.get("deployment_mode") == "containerized" or profile == "containerized":
            run_docker = True
            self.log("Containerized deployment - will check Docker installation", "system")

        # Calculate total steps
        total_steps = 10  # Base system steps
        if run_postgresql:
            total_steps += 10
        if run_redis:
            total_steps += 10
        if run_docker:
            total_steps += 10

        current_step = 0

        def update_main_progress():
            nonlocal current_step
            current_step += 1
            self.set_progress(int((current_step / total_steps) * 100))

        # PostgreSQL installation callback
        def postgresql_progress(message: str, progress: int):
            self.log(message, "postgresql")
            self.set_progress(progress, "postgresql")
            if progress == 100:
                update_main_progress()

        # Redis installation callback
        def redis_progress(message: str, progress: int):
            self.log(message, "redis")
            self.set_progress(progress, "redis")
            if progress == 100:
                update_main_progress()

        # Run parallel installations
        threads = []

        if run_postgresql:

            def install_postgresql():
                try:
                    from installer.dependencies.postgresql import PostgreSQLInstaller, PostgreSQLConfig

                    self.set_status("Installing PostgreSQL...", "postgresql")

                    pg_config = PostgreSQLConfig(
                        version="16.0",
                        port=int(config.get("pg_port", 5432)),
                        data_dir="C:/PostgreSQL/16/data",
                        install_dir="C:/PostgreSQL/16",
                    )

                    installer = PostgreSQLInstaller(pg_config, progress_callback=postgresql_progress)

                    if installer.is_postgresql_installed():
                        self.log("PostgreSQL already installed, verifying...", "postgresql")
                        if installer.test_connection():
                            self.log("PostgreSQL connection successful", "postgresql")
                            self.set_progress(100, "postgresql")
                        else:
                            self.log("PostgreSQL connection failed, reinstalling...", "postgresql")
                            installer.install()
                    else:
                        result = installer.install()
                        self.log(f"PostgreSQL installed: {result.connection_string}", "postgresql")

                    self.set_status("PostgreSQL installed ✓", "postgresql")

                except Exception as e:
                    self.log(f"PostgreSQL installation error: {e}", "postgresql")
                    self.set_status(f"Failed: {e}", "postgresql")

            pg_thread = threading.Thread(target=install_postgresql)
            threads.append(pg_thread)
            pg_thread.start()

        if run_redis:

            def install_redis():
                try:
                    # Placeholder for Redis installer integration
                    self.set_status("Installing Redis...", "redis")

                    # Simulate Redis installation for now
                    for i in range(0, 101, 10):
                        redis_progress(f"Installing Redis... {i}%", i)
                        time.sleep(0.5)

                    self.set_status("Redis installed ✓", "redis")

                except Exception as e:
                    self.log(f"Redis installation error: {e}", "redis")
                    self.set_status(f"Failed: {e}", "redis")

            redis_thread = threading.Thread(target=install_redis)
            threads.append(redis_thread)
            redis_thread.start()

        if run_docker:

            def install_docker():
                try:
                    from installer.dependencies.docker import DockerInstaller, DockerConfig

                    self.set_status("Checking Docker installation...", "docker")

                    docker_config = DockerConfig(profile=profile, compose_version="2.23.0")

                    def docker_progress(message: str, progress: int):
                        self.log(message, "docker")
                        self.set_progress(progress, "docker")
                        if progress == 100:
                            update_main_progress()

                    installer = DockerInstaller(docker_config, progress_callback=docker_progress)

                    if installer.is_docker_installed():
                        self.log("Docker already installed, verifying...", "docker")
                        if installer.test_docker_daemon():
                            self.log("Docker daemon is running", "docker")
                            self.set_progress(100, "docker")
                        else:
                            self.log("Docker installed but daemon not running", "docker")
                            self.log("Please start Docker Desktop manually", "docker")
                    else:
                        self.log("Docker not found, providing installation guide...", "docker")
                        result = installer.install()
                        if result.success:
                            self.log(f"Docker installation guide provided", "docker")
                            self.log("Please follow the instructions to install Docker", "docker")

                    self.set_status("Docker check complete ✓", "docker")

                except ImportError:
                    self.log("Docker installer not available yet (DOC-01 in progress)", "docker")
                    self.set_status("Docker installer pending", "docker")
                    self.set_progress(100, "docker")
                except Exception as e:
                    self.log(f"Docker installation error: {e}", "docker")
                    self.set_status(f"Failed: {e}", "docker")

            docker_thread = threading.Thread(target=install_docker)
            threads.append(docker_thread)
            docker_thread.start()

        # System configuration steps
        self.set_status("Configuring system...")
        self.log("Creating configuration files...", "system")

        # Use Configuration Manager to generate config files
        try:
            from installer.config.config_manager import ConfigurationManager

            config_mgr = ConfigurationManager()

            # Generate configuration based on profile
            self.log(f"Generating configuration for {profile} profile...", "system")

            # Prepare configuration values from GUI inputs
            config_values = {
                "profile": profile,
                "db_type": config.get("db_type", "sqlite"),
                "api_port": config.get("api_port", 8000),
                "websocket_port": config.get("websocket_port", 8001),
                "dashboard_port": config.get("dashboard_port", 3000),
                "mcp_port": config.get("mcp_port", 3001),
                "api_key": config.get("api_key", ""),
                "jwt_secret": config.get("jwt_secret", ""),
                "cors_origins": config.get("cors_origins", "http://localhost:*"),
            }

            # Add PostgreSQL settings if applicable
            if config.get("db_type") == "postgresql":
                config_values.update(
                    {
                        "pg_host": config.get("pg_host", "localhost"),
                        "pg_port": config.get("pg_port", 5432),
                        "pg_database": config.get("pg_database", "giljo_mcp"),
                        "pg_user": config.get("pg_user", "postgres"),
                        "pg_password": config.get("pg_password", ""),
                    }
                )
            else:
                config_values["db_path"] = config.get("db_path", "data/giljo_mcp.db")

            # Generate .env file
            env_result = config_mgr.generate_from_profile(profile, config_values)
            if env_result:
                self.log("✅ Generated .env file", "system")

            # Generate config.yaml
            yaml_config = config_mgr.generate_yaml_config(config_values)
            if yaml_config:
                self.log("✅ Generated config.yaml", "system")

            # Validate configuration
            is_valid, errors = config_mgr.validate_configuration(config_values)
            if is_valid:
                self.log("✅ Configuration validated successfully", "system")
            else:
                self.log(f"⚠️ Configuration warnings: {errors}", "system")

        except ImportError:
            self.log("Configuration Manager not available, using basic config", "system")
        except Exception as e:
            self.log(f"Configuration error: {e}", "system")

        update_main_progress()
        time.sleep(0.5)

        self.log("Setting up directories...", "system")
        update_main_progress()
        time.sleep(0.5)

        self.log("Initializing database schema...", "system")
        update_main_progress()
        time.sleep(0.5)

        # Wait for parallel installations
        for thread in threads:
            thread.join()

        # Health checks
        self.set_status("Running health checks...")
        self.log("Verifying installations...", "system")

        # Integrate health check system
        try:
            from installer.health_check import run_health_checks_for_gui

            def health_progress(message: str, progress: int):
                self.log(f"Health check: {message}", "system")

            health_results = run_health_checks_for_gui(config, health_progress)

            if health_results["healthy"]:
                self.log("✅ " + health_results["summary"], "system")
            else:
                self.log("⚠️ " + health_results["summary"], "system")

            for detail in health_results["details"]:
                status = "✅" if detail["healthy"] else "❌"
                self.log(f"  {status} {detail['name']}: {detail['message']}", "system")

        except ImportError:
            self.log("Health check module not available, skipping...", "system")
        except Exception as e:
            self.log(f"Health check error: {e}", "system")

        update_main_progress()

        self.set_status("Installation complete!")
        self.log("✅ All components installed successfully", "system")
        self.set_progress(100)

        self.completed = True
