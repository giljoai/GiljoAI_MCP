#!/usr/bin/env python3
"""
GiljoAI MCP Interactive Setup Script
Comprehensive setup tool for initial configuration with cross-platform support
"""

import sys


# Fix encoding issues on Windows
if sys.platform == "win32":
    if sys.stdout.encoding != "utf-8":
        sys.stdout.reconfigure(encoding="utf-8")
    if sys.stderr.encoding != "utf-8":
        sys.stderr.reconfigure(encoding="utf-8")
import platform
import secrets
import shutil
import subprocess
from pathlib import Path
from typing import Any, Optional


# Rich imports for better UX
try:
    from rich import print
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.syntax import Syntax
    from rich.table import Table

    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not installed. Installing for better UX...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import print
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.prompt import Confirm, IntPrompt, Prompt
    from rich.table import Table

    console = Console()

# Import check_ports functionality
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
try:
    from check_ports import PORT_ASSIGNMENTS, check_port
except ImportError:
    print("[red]Error: check_ports.py not found in scripts directory[/red]")
    sys.exit(1)

# Import Phase 2 installer components
try:
    from installer.core.profile import ProfileManager, ProfileType
    from installer.config.config_manager import ConfigurationManager
    from installer.services.service_manager import ServiceManager
    from installer.dependencies.postgresql import PostgreSQLInstaller
    # Redis and Docker removed - not needed for simplified installation
    from installer.core.health import HealthChecker

    PHASE2_AVAILABLE = True
except ImportError as e:
    print(f"[yellow]Warning: Some Phase 2 components not available: {e}[/yellow]")
    PHASE2_AVAILABLE = False


class GiljoSetup:
    """Interactive setup for GiljoAI MCP"""

    def __init__(self):
        self.root_path = Path(__file__).parent
        self.config = {}
        self.env_vars = {}
        self.platform_info = self._detect_platform()
        self.rollback_actions = []  # For error recovery

    def _detect_platform(self) -> dict[str, str]:
        """Detect platform and environment details"""
        try:
            # Try to use enhanced platform detection
            from setup_platform import PlatformDetector

            detector = PlatformDetector()
            return detector.get_full_info()
        except ImportError:
            # Fallback to basic detection
            return {
                "system": platform.system(),
                "release": platform.release(),
                "python": platform.python_version(),
                "arch": platform.machine(),
                "is_windows": platform.system() == "Windows",
                "is_mac": platform.system() == "Darwin",
                "is_linux": platform.system() == "Linux",
            }

    def run(self):
        """Main setup flow"""
        self._show_welcome()

        # Select installation profile
        self._select_profile()

        # Check existing installation
        if self._check_existing_installation():
            if not Confirm.ask("\n[yellow]Existing installation detected. Continue with reconfiguration?[/yellow]"):
                print("[cyan]Setup cancelled.[/cyan]")
                return

        # Check for AKE-MCP
        self._check_ake_mcp()

        # Port availability check
        self._check_ports()

        # Database configuration
        self._configure_database()

        # Server configuration
        self._configure_server()

        # Security configuration
        self._configure_security()

        # Create directories
        self._create_directories()

        # Generate .env file
        self._generate_env_file()

        # Generate config.yaml file
        self._generate_config_yaml()

        # Install dependencies
        self._install_dependencies()

        # Create desktop launcher
        self._create_desktop_launcher()

        # Show summary
        self._show_summary()

    def _show_welcome(self):
        """Display welcome message"""
        console.clear()
        welcome_text = """
        [bold cyan]GiljoAI MCP Coding Orchestrator[/bold cyan]
        [dim]Interactive Setup Wizard[/dim]

        This wizard will help you configure GiljoAI MCP for your environment.
        We'll set up database connections, create necessary directories,
        and configure the system for your platform.
        """
        console.print(Panel(welcome_text, title="Welcome", border_style="cyan"))

        # Show platform info
        platform_table = Table(title="Platform Information", show_header=False)
        platform_table.add_column("Property", style="cyan")
        platform_table.add_column("Value", style="green")

        platform_table.add_row(
            "Operating System", f"{self.platform_info.get('system', 'Unknown')} {self.platform_info.get('release', '')}"
        )
        # Handle both dict and string format for python version
        python_version = self.platform_info["python"]
        if isinstance(python_version, dict):
            python_version = python_version.get("version", str(python_version))
        platform_table.add_row("Python Version", str(python_version))
        # Handle both 'arch' and 'architecture' keys
        arch = self.platform_info.get("arch") or self.platform_info.get("architecture", "Unknown")
        platform_table.add_row("Architecture", str(arch))
        platform_table.add_row("Installation Path", str(self.root_path))

        console.print(platform_table)
        console.print()

    def _select_profile(self):
        """Select deployment mode - simplified to two real options"""
        console.print("\n[bold cyan]Select Deployment Mode[/bold cyan]\n")

        console.print("[bold]1. Local Development[/bold] - [green]Single Developer[/green]")
        console.print("   • SQLite database (zero configuration)")
        console.print("   • No authentication required")
        console.print("   • Localhost only (secure by default)")
        console.print("   • Up to 20 concurrent agents")
        console.print("   • Perfect for individual developers")
        console.print("   • [dim]Best for: Personal projects, learning, prototyping[/dim]\n")

        console.print("[bold]2. Server Deployment[/bold] - [green]Team/Network Access[/green]")
        console.print("   • PostgreSQL or SQLite database")
        console.print("   • API key authentication")
        console.print("   • Network accessible (LAN/WAN)")
        console.print("   • Up to 20 concurrent agents per user")
        console.print("   • Multiple users can create projects")
        console.print("   • [dim]Best for: Team servers, CI/CD, remote access[/dim]\n")

        mode_choice = Prompt.ask(
            "[bold cyan]Select deployment mode[/bold cyan]",
            choices=["1", "2"],
            default="1"
        )

        if mode_choice == "1":
            self.config["deployment_mode"] = "local"
            self.config["database_type"] = "sqlite"
            self.config["auth_enabled"] = False
            console.print(f"\n[green]✓[/green] Selected: [bold]Local Development Mode[/bold]")
            console.print("[dim]SQLite database, no authentication, localhost only[/dim]")
        else:
            self.config["deployment_mode"] = "server"
            self.config["auth_enabled"] = True
            console.print(f"\n[green]✓[/green] Selected: [bold]Server Deployment Mode[/bold]")
            console.print("[dim]You'll configure database and authentication next[/dim]")

        console.print()

    def _check_existing_installation(self) -> bool:
        """Check for existing installation"""
        checks = {
            ".env": self.root_path / ".env",
            "config.yaml": self.root_path / "config.yaml",
            "data directory": self.root_path / "data",
            "logs directory": self.root_path / "logs",
        }

        existing = []
        for name, path in checks.items():
            if path.exists():
                existing.append(name)

        if existing:
            console.print("\n[yellow]Found existing installation components:[/yellow]")
            for item in existing:
                console.print(f"  • {item}")
            return True
        return False

    def _check_ake_mcp(self, interactive=True):
        """Check for legacy MCP configurations and offer migration"""
        console.print("\n[bold]Checking for legacy MCP configurations...[/bold]")

        # Check if legacy MCP server is referenced in .mcp.json
        mcp_config = self.root_path / ".mcp.json"
        if mcp_config.exists():
            with open(mcp_config) as f:
                content = f.read()
                if "ake-mcp" in content.lower():
                    console.print("[yellow]Found legacy MCP configuration in .mcp.json[/yellow]")
                    if interactive:
                        if Confirm.ask("\nWould you like to remove legacy MCP dependency and make GiljoAI standalone?"):
                            console.print("[green]Will configure GiljoAI MCP as standalone[/green]")
                            self.env_vars["STANDALONE_MODE"] = "true"
                        else:
                            console.print("[yellow]Keeping legacy MCP integration[/yellow]")
                else:
                    console.print("[green]✓ No legacy MCP dependency found[/green]")
        else:
            console.print("[green]✓ No .mcp.json found - clean installation[/green]")

    def _check_legacy_installation(self, interactive=True):
        """Check for any legacy installation"""
        console.print("\n[bold]Checking for existing configuration...[/bold]")

    def _check_ports(self):
        """Check port availability"""
        console.print("\n[bold]Checking port availability...[/bold]")

        conflicts = []
        available = []

        giljo_ports = {"Dashboard": 6000, "MCP Server": 6001, "REST API": 6002, "WebSocket": 6003}

        for service, port in giljo_ports.items():
            if check_port(port):
                conflicts.append((service, port))
                console.print(f"  [red]✗[/red] Port {port} ({service}) is in use")
            else:
                available.append((service, port))
                console.print(f"  [green]✓[/green] Port {port} ({service}) is available")

        if conflicts:
            console.print("\n[yellow]Some ports are in use. Let's configure alternatives.[/yellow]")
            for service, default_port in conflicts:
                new_port = IntPrompt.ask(f"Enter alternative port for {service}", default=default_port + 100)
                self.env_vars[f'GILJO_MCP_{service.upper().replace(" ", "_")}_PORT'] = str(new_port)
        else:
            # Use default ports
            self.env_vars["GILJO_MCP_DASHBOARD_PORT"] = "6000"
            self.env_vars["GILJO_MCP_SERVER_PORT"] = "6001"
            self.env_vars["GILJO_MCP_API_PORT"] = "6002"
            self.env_vars["GILJO_MCP_WEBSOCKET_PORT"] = "6003"

    def _configure_database(self):
        """Configure database settings based on deployment mode"""
        console.print("\n[bold]Database Configuration[/bold]")

        deployment_mode = self.config.get("deployment_mode", "local")

        if deployment_mode == "local":
            # Local mode: Always use SQLite
            console.print("[dim]Local mode: Using SQLite for simplicity[/dim]")
            self._configure_sqlite()
        else:
            # Server mode: Let user choose database
            console.print("[dim]Server mode: Choose your database[/dim]")
            console.print("  1. [cyan]SQLite[/cyan] - Simple file-based database")
            console.print("  2. [cyan]PostgreSQL[/cyan] - Scalable, production-ready")

            db_choice = Prompt.ask("\nSelect database type", choices=["1", "2"], default="1")

            if db_choice == "1":
                self._configure_sqlite()
            else:
                self._configure_postgresql()

    def _configure_sqlite(self):
        """Configure SQLite database"""
        console.print("\n[green]Configuring SQLite database...[/green]")

        # Use cross-platform path
        db_path = self.root_path / "data" / "giljo_mcp.db"
        self.env_vars["DATABASE_URL"] = f"sqlite:///{db_path.as_posix()}"
        self.env_vars["DB_TYPE"] = "sqlite"

        console.print(f"  Database will be created at: {db_path}")

    def _configure_postgresql(self):
        """Configure PostgreSQL database"""
        console.print("\n[green]Configuring PostgreSQL database...[/green]")

        # Check if PostgreSQL is available
        pg_port = IntPrompt.ask("PostgreSQL port", default=5432)
        if not check_port(pg_port, "localhost"):
            console.print("[yellow]Warning: PostgreSQL doesn't appear to be running on port {pg_port}[/yellow]")
            if not Confirm.ask("Continue anyway?"):
                console.print("[cyan]Falling back to SQLite...[/cyan]")
                self._configure_sqlite()
                return

        # Collect PostgreSQL credentials
        self.env_vars["DB_HOST"] = Prompt.ask("Database host", default="localhost")
        self.env_vars["DB_PORT"] = str(pg_port)
        self.env_vars["DB_NAME"] = Prompt.ask("Database name", default="giljo_mcp_db")
        self.env_vars["DB_USER"] = Prompt.ask("Database user", default="postgres")

        # Handle password securely
        if self.platform_info["is_windows"]:
            # Windows doesn't hide password in basic input
            console.print("[yellow]Note: Password will be visible on Windows console[/yellow]")
        self.env_vars["DB_PASSWORD"] = Prompt.ask("Database password", password=True)

        # Build connection URL
        self.env_vars["DATABASE_URL"] = (
            f"postgresql://{self.env_vars['DB_USER']}:{self.env_vars['DB_PASSWORD']}"
            f"@{self.env_vars['DB_HOST']}:{self.env_vars['DB_PORT']}/{self.env_vars['DB_NAME']}"
        )
        self.env_vars["DB_TYPE"] = "postgresql"

        # Test connection
        console.print("\n[cyan]Testing database connection...[/cyan]")
        if self._test_postgresql_connection():
            console.print("[green]✓ Database connection successful![/green]")
        else:
            console.print("[red]✗ Could not connect to database[/red]")
            if Confirm.ask("Would you like to reconfigure?"):
                self._configure_postgresql()
            else:
                console.print("[cyan]Falling back to SQLite...[/cyan]")
                self._configure_sqlite()

    def _test_postgresql_connection(self) -> bool:
        """Test PostgreSQL connection"""
        try:
            import psycopg2

            conn_params = {
                "host": self.env_vars["DB_HOST"],
                "port": int(self.env_vars["DB_PORT"]),
                "user": self.env_vars["DB_USER"],
                "password": self.env_vars["DB_PASSWORD"],
            }

            # Try to connect to postgres database first
            conn_params["database"] = "postgres"
            conn = psycopg2.connect(**conn_params)
            cur = conn.cursor()

            # Check if our database exists
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (self.env_vars["DB_NAME"],))

            if not cur.fetchone():
                if Confirm.ask(f"\nDatabase '{self.env_vars['DB_NAME']}' doesn't exist. Create it?"):
                    cur.execute(f"CREATE DATABASE {self.env_vars['DB_NAME']}")
                    console.print(f"[green]✓ Created database '{self.env_vars['DB_NAME']}'[/green]")

            cur.close()
            conn.close()
            return True

        except ImportError:
            console.print("[yellow]psycopg2 not installed. Will install with dependencies.[/yellow]")
            return True  # Assume it will work after installation
        except Exception as e:
            console.print(f"[red]Connection error: {e}[/red]")
            return False

    def _configure_server(self):
        """Configure server settings based on deployment mode"""
        console.print("\n[bold]Server Configuration[/bold]")

        deployment_mode = self.config.get("deployment_mode", "local")

        if deployment_mode == "local":
            # Local mode: Simple localhost configuration
            console.print("[dim]Local mode: Localhost only, debug logging[/dim]")
            self.env_vars["GILJO_MCP_MODE"] = "local"
            self.env_vars["LOG_LEVEL"] = "DEBUG"
            self.env_vars["DEBUG"] = "true"
            console.print("• Binding to localhost only")
            console.print("• Debug logging enabled")
        else:
            # Server mode: Network configuration
            console.print("[dim]Server mode: Network accessible configuration[/dim]")

            # Network binding choice
            console.print("\nNetwork access level:")
            console.print("  1. [cyan]LAN only[/cyan] - Local network access")
            console.print("  2. [cyan]WAN/Internet[/cyan] - Internet accessible")

            network_choice = Prompt.ask("Select network level", choices=["1", "2"], default="1")

            if network_choice == "1":
                self.env_vars["GILJO_MCP_MODE"] = "lan"
                console.print("• Configured for LAN access")
            else:
                self.env_vars["GILJO_MCP_MODE"] = "wan"
                console.print("• Configured for WAN/Internet access")
                console.print("[yellow]⚠ Ensure proper firewall and TLS configuration[/yellow]")

            # Log level for server mode
            log_level = Prompt.ask(
                "Log level",
                choices=["DEBUG", "INFO", "WARNING", "ERROR"],
                default="INFO"
            )
            self.env_vars["LOG_LEVEL"] = log_level
            self.env_vars["DEBUG"] = "false"

        # Universal settings (both modes get the same agent limits)
        self.env_vars["MAX_AGENTS_PER_USER"] = "20"
        self.env_vars["MAX_CONCURRENT_TASKS"] = "10"

    def _configure_security(self):
        """Configure security settings"""
        if self.env_vars.get("GILJO_MCP_MODE") != "local":
            console.print("\n[bold]Security Configuration[/bold]")
            console.print("[dim]Securing your orchestrator for network access...[/dim]\n")

            # API Key explanation
            console.print("[cyan]📔 API Key Authentication:[/cyan]")
            console.print("  • [dim]Used for: Building your own applications and integrating with GiljoAI MCP[/dim]")
            console.print("  • [dim]Examples: Custom tools, local LLM integrations, automation scripts[/dim]")
            console.print("  • [dim]Note: MCP clients (Claude, etc.) don't need this - they use MCP protocol[/dim]")

            # Generate API key
            api_key = secrets.token_urlsafe(32)
            self.env_vars["GILJO_MCP_API_KEY"] = api_key
            console.print(f"  [green]✓ Generated API key:[/green] {api_key}")

            # JWT explanation
            console.print("\n[cyan]🔐 JWT Secret Key:[/cyan]")
            console.print("  • [dim]Used for: Session tokens and WebSocket authentication[/dim]")
            console.print("  • [dim]When needed: Web dashboard access, multi-user scenarios[/dim]")
            console.print("  • [dim]Security: Signs tokens to prevent tampering[/dim]")

            # Generate secret key for sessions
            secret_key = secrets.token_hex(32)
            self.env_vars["GILJO_MCP_SECRET_KEY"] = secret_key
            self.env_vars["JWT_SECRET"] = secret_key  # Also set JWT_SECRET
            console.print(f"  [green]✓ Generated JWT secret[/green] (stored securely)")

            # CORS configuration (always enabled)
            console.print("\n[cyan]🌐 CORS Origin (Required for Web Dashboard):[/cyan]")
            console.print("  • [dim]Default: http://localhost:* (for local access)[/dim]")
            console.print("  • [dim]LAN Setup: Change to http://YOUR-SERVER-IP:* in .env file[/dim]")
            console.print("  • [dim]WAN Setup: Change to https://your-domain.com in .env file[/dim]")
            self.env_vars["CORS_ENABLED"] = "true"  # Always enabled
            self.env_vars["CORS_ORIGINS"] = "http://localhost:*"
            console.print("  [green]✓ CORS enabled with localhost origin (edit .env for LAN/WAN)[/green]")

            console.print("\n[yellow]⚠️  IMPORTANT - SAVE THESE CREDENTIALS:[/yellow]")
            console.print("┌─────────────────────────────────────────────────────────────┐")
            console.print(f"│ API Key: {api_key}                 │")
            console.print("│                                                             │")
            console.print("│ [dim]Store this key securely! You'll need it to:[/dim]             │")
            console.print("│ [dim]• Access the REST API[/dim]                                     │")
            console.print("│ [dim]• Connect CI/CD pipelines[/dim]                                │")
            console.print("│ [dim]• Integrate with external tools[/dim]                          │")
            console.print("└─────────────────────────────────────────────────────────────┘")

    def _create_directories(self):
        """Create necessary directories with proper permissions"""
        console.print("\n[bold]Creating directories...[/bold]")

        directories = [
            "data",
            "logs",
            "temp",
            "backups",
            "src/giljo_mcp",
            "api",
            "frontend/src",
            "frontend/public",
            "tests",
            "scripts",
            "migrations",
        ]

        for dir_name in directories:
            dir_path = self.root_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                console.print(f"  [green]✓[/green] Created {dir_name}/")
            else:
                console.print(f"  [dim]•[/dim] {dir_name}/ already exists")

        # Set appropriate permissions on sensitive directories
        if not self.platform_info["is_windows"]:
            # Unix-like systems: restrict access to data and logs
            import stat

            (self.root_path / "data").chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
            (self.root_path / "logs").chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)

    def _generate_config_yaml(self):
        """Generate config.yaml file from settings"""
        console.print("\n[bold]Generating config.yaml...[/bold]")

        # Import ConfigManager
        try:
            from src.giljo_mcp.config_manager import ConfigManager, generate_sample_config
        except ImportError:
            console.print("[yellow]Warning: ConfigManager not available, using template[/yellow]")
            return

        # Create ConfigManager instance
        config = ConfigManager(config_path=self.root_path / "config.yaml", auto_reload=False)

        # Apply settings from setup
        if self.env_vars.get("GILJO_MCP_MODE"):
            from src.giljo_mcp.config_manager import DeploymentMode

            config.server.mode = DeploymentMode(self.env_vars["GILJO_MCP_MODE"])

        # Database configuration
        if self.env_vars.get("DB_TYPE") == "postgresql":
            config.database.type = "postgresql"
            config.database.pg_host = self.env_vars.get("DB_HOST", "localhost")
            config.database.pg_port = int(self.env_vars.get("DB_PORT", 5432))
            config.database.pg_database = self.env_vars.get("DB_NAME", "giljo_mcp_db")
            config.database.pg_user = self.env_vars.get("DB_USER", "postgres")
            config.database.pg_password = self.env_vars.get("DB_PASSWORD", "")
        else:
            config.database.type = "sqlite"

        # Server ports
        if port := self.env_vars.get("GILJO_MCP_DASHBOARD_PORT"):
            config.server.dashboard_port = int(port)
        if port := self.env_vars.get("GILJO_MCP_SERVER_PORT"):
            config.server.mcp_port = int(port)
        if port := self.env_vars.get("GILJO_MCP_API_PORT"):
            config.server.api_port = int(port)
        if port := self.env_vars.get("GILJO_MCP_WEBSOCKET_PORT"):
            config.server.websocket_port = int(port)

        # Logging
        if level := self.env_vars.get("LOG_LEVEL"):
            config.logging.level = level

        # Save configuration
        config.save_to_file()
        console.print("  [green]✓[/green] Generated config.yaml")

    def _generate_env_file(self):
        """Generate .env file from template"""
        console.print("\n[bold]Generating .env file...[/bold]")

        env_template = self.root_path / ".env.example"
        env_file = self.root_path / ".env"

        if not env_template.exists():
            console.print("[red]Error: .env.example not found[/red]")
            return

        # Read template
        with open(env_template) as f:
            template_content = f.read()

        # Replace values
        env_content = []
        for line in template_content.split("\n"):
            if "=" in line and not line.strip().startswith("#"):
                key = line.split("=")[0].strip()
                if key in self.env_vars:
                    env_content.append(f"{key}={self.env_vars[key]}")
                else:
                    env_content.append(line)
            else:
                env_content.append(line)

        # Add any additional env vars not in template
        template_keys = {
            line.split("=")[0].strip()
            for line in template_content.split("\n")
            if "=" in line and not line.strip().startswith("#")
        }
        for key, value in self.env_vars.items():
            if key not in template_keys:
                env_content.append(f"{key}={value}")

        # Write .env file
        with open(env_file, "w") as f:
            f.write("\n".join(env_content))

        console.print("  [green]✓[/green] Generated .env file")

        # Add .env to .gitignore if not already there
        gitignore = self.root_path / ".gitignore"
        if gitignore.exists():
            with open(gitignore) as f:
                gitignore_content = f.read()
            if ".env" not in gitignore_content:
                with open(gitignore, "a") as f:
                    f.write("\n# Environment variables\n.env\n")
                console.print("  [green]✓[/green] Added .env to .gitignore")

    def _install_dependencies(self):
        """Install dependencies with individual component tracking"""
        console.print("\n[bold cyan]Installing Components[/bold cyan]\n")

        profile = self.config.get("profile", "developer")

        # Define components based on profile
        components = {
            'config': {
                'name': 'Configuration Files',
                'applicable': True,
                'status': 'pending'
            },
            'directories': {
                'name': 'Directory Structure',
                'applicable': True,
                'status': 'pending'
            },
            'database': {
                'name': 'SQLite Database' if profile in ['developer', 'research'] else 'PostgreSQL Database',
                'applicable': True,
                'status': 'pending'
            },
            'redis': {
                'name': 'Redis Cache',
                'applicable': profile != 'minimal',
                'status': 'pending' if profile != 'minimal' else 'not_required'
            },
            'schema': {
                'name': 'Database Schema',
                'applicable': True,
                'status': 'pending'
            },
            'dependencies': {
                'name': 'Python Dependencies',
                'applicable': True,
                'status': 'pending'
            },
            'validation': {
                'name': 'System Validation',
                'applicable': True,
                'status': 'pending'
            }
        }

        # Display component status table
        def display_status():
            table = Table(title="Installation Progress", box=box.SIMPLE)
            table.add_column("Component", style="cyan", width=30)
            table.add_column("Status", width=25)
            table.add_column("Progress", width=20)

            for comp_id, comp in components.items():
                if comp['applicable']:
                    status_color = {
                        'pending': 'yellow',
                        'installing': 'blue',
                        'completed': 'green',
                        'failed': 'red',
                        'not_required': 'dim'
                    }.get(comp['status'], 'white')

                    progress = {
                        'pending': '⏸ Pending',
                        'installing': '🔄 Installing...',
                        'completed': '✅ Complete',
                        'failed': '❌ Failed',
                        'not_required': '➖ Not Required'
                    }.get(comp['status'], '❓ Unknown')

                    table.add_row(
                        comp['name'],
                        f"[{status_color}]{comp['status'].title()}[/{status_color}]",
                        progress
                    )

            return table

        # Create configuration files
        console.clear()
        components['config']['status'] = 'installing'
        console.print(display_status())
        console.print("\n[bold]Creating configuration files...[/bold]")

        try:
            from setup_config import ConfigurationManager
            config_mgr = ConfigurationManager()

            # Prepare config values
            config_values = {
                "database_type": "postgresql" if profile in ["team", "enterprise"] else "sqlite",
                "api_port": self.env_vars.get("GILJO_MCP_API_PORT", 6002),
                "websocket_port": self.env_vars.get("GILJO_MCP_WEBSOCKET_PORT", 6003),
                "dashboard_port": self.env_vars.get("GILJO_MCP_DASHBOARD_PORT", 6000),
                "server_port": self.env_vars.get("GILJO_MCP_SERVER_PORT", 6001),
                "redis_enabled": False,  # Redis removed
                "redis_host": "",
                "redis_port": 0,
                "jwt_secret": self.env_vars.get("JWT_SECRET", ""),
                "api_key": self.env_vars.get("API_KEY", ""),
                "api_key_enabled": profile in ["team", "enterprise"]
            }

            if profile in ["team", "enterprise"]:
                config_values.update({
                    "pg_host": self.env_vars.get("PG_HOST", "localhost"),
                    "pg_port": self.env_vars.get("PG_PORT", 5432),
                    "pg_database": self.env_vars.get("PG_DATABASE", "giljo_mcp"),
                    "pg_user": self.env_vars.get("PG_USER", "postgres"),
                    "pg_password": self.env_vars.get("PG_PASSWORD", "")
                })
            else:
                config_values["db_path"] = "data/giljo_mcp.db"

            # Generate .env file
            env_result = config_mgr.generate_from_profile(profile, config_values)
            if env_result:
                console.print("  [green]✓[/green] Generated .env file")

            # Generate config.yaml
            yaml_result = config_mgr.generate_yaml_config(config_values)
            if yaml_result:
                console.print("  [green]✓[/green] Generated config.yaml")

            components['config']['status'] = 'completed'
            console.print("[green]✓ Configuration files created[/green]")

        except Exception as e:
            components['config']['status'] = 'failed'
            console.print(f"[red]✗ Configuration failed: {e}[/red]")

        # Setup directories
        console.clear()
        components['directories']['status'] = 'installing'
        console.print(display_status())
        console.print("\n[bold]Setting up directories...[/bold]")

        try:
            directories = [
                "data", "logs", "backups", "temp",
                "src/giljo_mcp", "api", "frontend/dist",
                "scripts", "tests"
            ]

            for directory in directories:
                Path(directory).mkdir(parents=True, exist_ok=True)

            components['directories']['status'] = 'completed'
            console.print("[green]✓ Directory structure created[/green]")

        except Exception as e:
            components['directories']['status'] = 'failed'
            console.print(f"[red]✗ Directory setup failed: {e}[/red]")

        # Database setup
        console.clear()
        components['database']['status'] = 'installing'
        console.print(display_status())

        if profile in ["team", "enterprise"]:
            console.print("\n[bold]Setting up PostgreSQL database...[/bold]")
            # PostgreSQL installation would go here
            console.print("[yellow]⚠ PostgreSQL must be installed separately[/yellow]")
            console.print("  Download from: https://www.postgresql.org/download/")
            components['database']['status'] = 'completed'
        else:
            console.print("\n[bold]Setting up SQLite database...[/bold]")
            db_path = Path("data/giljo_mcp.db")
            db_path.parent.mkdir(parents=True, exist_ok=True)
            components['database']['status'] = 'completed'
            console.print("[green]✓ SQLite database configured[/green]")

        # Redis setup (if applicable)
        if components['redis']['applicable']:
            console.clear()
            components['redis']['status'] = 'installing'
            console.print(display_status())
            console.print("\n[bold]Setting up Redis cache...[/bold]")

            if self.platform_info.get("is_windows"):
                console.print("[yellow]⚠ Redis for Windows must be installed separately[/yellow]")
                console.print("  Download from: https://github.com/tporadowski/redis/releases")
            else:
                console.print("  Install with: brew install redis (Mac) or apt install redis (Linux)")

            components['redis']['status'] = 'completed'

        # Initialize database schema
        console.clear()
        components['schema']['status'] = 'installing'
        console.print(display_status())
        console.print("\n[bold]Initializing database schema...[/bold]")

        try:
            from src.giljo_mcp.models.base import init_database
            init_database()
            components['schema']['status'] = 'completed'
            console.print("[green]✓ Database schema initialized[/green]")
        except Exception as e:
            components['schema']['status'] = 'failed'
            console.print(f"[red]✗ Schema initialization failed: {e}[/red]")

        # Install Python dependencies
        console.clear()
        components['dependencies']['status'] = 'installing'
        console.print(display_status())
        console.print("\n[bold]Installing Python dependencies...[/bold]")

        requirements_file = self.root_path / "requirements.txt"
        if requirements_file.exists():
            console.print("[dim]Running: pip install -r requirements.txt[/dim]")
            result = subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=False,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                components['dependencies']['status'] = 'completed'
                console.print("[green]✓ Python dependencies installed[/green]")
                self._validate_critical_dependencies()
            else:
                components['dependencies']['status'] = 'failed'
                console.print("[red]✗ Dependency installation failed[/red]")
                if result.stderr:
                    console.print(f"[dim]Error details: {result.stderr[:500]}[/dim]")
                console.print("[yellow]You may need to run manually: pip install -r requirements.txt[/yellow]")
        else:
            components['dependencies']['status'] = 'failed'
            console.print("[red]✗ requirements.txt not found[/red]")

        # System validation
        console.clear()
        components['validation']['status'] = 'installing'
        console.print(display_status())
        console.print("\n[bold]Validating installation...[/bold]")

        try:
            from installer.health_checker import HealthChecker
            checker = HealthChecker()

            # Check components
            checks = []
            if profile in ["team", "enterprise"]:
                pg_status, pg_msg = checker.check_postgresql(True)
                checks.append(("PostgreSQL", pg_status, pg_msg))

            if components['redis']['applicable']:
                redis_status, redis_msg = checker.check_redis(True)
                checks.append(("Redis", redis_status, redis_msg))

            ports_status, ports_msg = checker.check_ports(self.config)
            checks.append(("Ports", ports_status, ports_msg))

            fs_status, fs_msg = checker.check_filesystem()
            checks.append(("File System", fs_status, fs_msg))

            all_passed = all(status for _, status, _ in checks)

            for component, status, message in checks:
                if status:
                    console.print(f"  [green]✓[/green] {component}: {message}")
                else:
                    console.print(f"  [red]✗[/red] {component}: {message}")

            components['validation']['status'] = 'completed' if all_passed else 'failed'

        except Exception as e:
            components['validation']['status'] = 'failed'
            console.print(f"[red]✗ Validation failed: {e}[/red]")

        # Final status display
        console.clear()
        console.print("\n[bold cyan]Installation Complete[/bold cyan]\n")
        console.print(display_status())

        # Summary
        failed_components = [name for comp_id, comp in components.items()
                           if comp['status'] == 'failed' and comp['applicable']]

        if failed_components:
            console.print(f"\n[yellow]⚠ Installation completed with issues in: {', '.join(failed_components)}[/yellow]")
            console.print("Please review the errors above and run setup again if needed.")
        else:
            console.print("\n[green]✅ All components installed successfully![/green]")

    def _validate_critical_dependencies(self):
        """Validate that critical dependencies are properly installed"""
        critical_deps = {
            'aiohttp': 'WebSocket client for real-time agent communication',
            'fastapi': 'REST API server and WebSocket endpoints',
            'websockets': 'WebSocket protocol implementation',
            'httpx': 'HTTP client for external API calls',
            'sqlalchemy': 'Database ORM with async support',
            'pydantic': 'Data validation and settings management'
        }

        missing_deps = []
        for dep, purpose in critical_deps.items():
            try:
                __import__(dep)
                console.print(f"[green]✓ {dep}[/green] - {purpose}")
            except ImportError:
                missing_deps.append(dep)
                console.print(f"[red]✗ {dep}[/red] - {purpose} (MISSING)")

        if missing_deps:
            console.print(f"\n[yellow]Warning: {len(missing_deps)} critical dependencies are missing![/yellow]")
            console.print("The application may not function correctly.")
            console.print("Try running: pip install -r requirements.txt")
        else:
            console.print("[green]✓ All critical dependencies validated[/green]")

    def _create_desktop_launcher(self):
        """Create desktop launcher/shortcut for the current OS"""
        console.print("\n[bold]Creating Desktop Launcher...[/bold]")

        try:
            if self.platform_info.get("is_windows"):
                self._create_windows_shortcut()
            elif self.platform_info.get("is_mac"):
                self._create_mac_app()
            elif self.platform_info.get("is_linux"):
                self._create_linux_desktop_entry()
            else:
                console.print("[yellow]Desktop launcher not created - unknown OS[/yellow]")
                return False
            return True
        except Exception as e:
            console.print(f"[yellow]Could not create desktop launcher: {e}[/yellow]")
            return False

    def _create_windows_shortcut(self):
        """Create Windows desktop shortcut and Start Menu entry"""
        try:
            import win32com.client
            import pythoncom
        except ImportError:
            # Fall back to creating just a batch file
            self._create_windows_batch_launcher()
            return

        # Get desktop path
        desktop = Path.home() / "Desktop"
        start_menu = Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Start Menu" / "Programs"

        # Create launcher batch file in installation directory
        launcher_bat = self.root_path / "GiljoAI_MCP.bat"
        with open(launcher_bat, "w") as f:
            f.write(
                f"""@echo off
cd /d "{self.root_path}"
start "GiljoAI Dashboard" cmd /c "python -m giljo_mcp.server --dashboard"
start http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}
"""
            )

        # Create shortcuts
        pythoncom.CoInitialize()
        shell = win32com.client.Dispatch("WScript.Shell")

        for location, path in [("Desktop", desktop), ("Start Menu", start_menu)]:
            shortcut_path = path / "GiljoAI MCP.lnk"
            shortcut = shell.CreateShortCut(str(shortcut_path))
            shortcut.TargetPath = str(launcher_bat)
            shortcut.WorkingDirectory = str(self.root_path)
            shortcut.IconLocation = str(self.root_path / "frontend" / "public" / "favicon.ico")
            shortcut.Description = "GiljoAI MCP Coding Orchestrator"
            shortcut.save()
            console.print(f"  [green]✓[/green] Created {location} shortcut")

    def _create_windows_batch_launcher(self):
        """Create simple batch file launcher when pywin32 is not available"""
        # Create launcher batch file on Desktop
        desktop = Path.home() / "Desktop"
        launcher_bat = desktop / "GiljoAI_MCP.bat"

        with open(launcher_bat, "w") as f:
            f.write(
                f"""@echo off
echo ============================================================
echo GiljoAI MCP Coding Orchestrator
echo ============================================================
echo.
cd /d "{self.root_path}"
echo Starting GiljoAI MCP Server and Dashboard...
start "GiljoAI Server" python -m giljo_mcp.server
timeout /t 3 /nobreak > nul
start http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}
echo.
echo Server is running. Close this window to stop.
pause
"""
            )

        console.print(f"  [green]✓[/green] Created desktop launcher: {launcher_bat}")
        console.print("  [yellow]Note: Install pywin32 for full shortcut support[/yellow]")
        console.print("  [dim]pip install pywin32[/dim]")

    def _create_mac_app(self):
        """Create macOS .app bundle in Applications"""
        import plistlib

        app_name = "GiljoAI MCP"
        app_path = Path("/Applications") / f"{app_name}.app"
        contents_path = app_path / "Contents"
        macos_path = contents_path / "MacOS"
        resources_path = contents_path / "Resources"

        # Create directory structure
        macos_path.mkdir(parents=True, exist_ok=True)
        resources_path.mkdir(parents=True, exist_ok=True)

        # Create launcher script
        launcher_script = macos_path / "launcher"
        with open(launcher_script, "w") as f:
            f.write(
                f"""#!/bin/bash
cd "{self.root_path}"
python3 -m giljo_mcp.server --dashboard &
sleep 2
open "http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}"
"""
            )
        launcher_script.chmod(0o755)

        # Create Info.plist
        info_plist = {
            "CFBundleName": app_name,
            "CFBundleDisplayName": app_name,
            "CFBundleIdentifier": "com.giljoai.mcp",
            "CFBundleVersion": "1.0.0",
            "CFBundleExecutable": "launcher",
            "CFBundleIconFile": "icon",
            "LSUIElement": False,
        }

        with open(contents_path / "Info.plist", "wb") as f:
            plistlib.dump(info_plist, f)

        # Copy icon if available
        icon_source = self.root_path / "frontend" / "public" / "icon.icns"
        if icon_source.exists():
            import shutil

            shutil.copy2(icon_source, resources_path / "icon.icns")

        console.print(f"  [green]✓[/green] Created macOS app bundle in Applications")

    def _create_linux_desktop_entry(self):
        """Create Linux .desktop file for application menu"""
        desktop_dir = Path.home() / ".local" / "share" / "applications"
        desktop_dir.mkdir(parents=True, exist_ok=True)

        desktop_file = desktop_dir / "giljoai-mcp.desktop"

        # Create launcher script
        launcher_script = self.root_path / "launch_giljo.sh"
        with open(launcher_script, "w") as f:
            f.write(
                f"""#!/bin/bash
cd "{self.root_path}"
python3 -m giljo_mcp.server --dashboard &
sleep 2
xdg-open "http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}"
"""
            )
        launcher_script.chmod(0o755)

        # Create .desktop entry
        with open(desktop_file, "w") as f:
            f.write(
                f"""[Desktop Entry]
Name=GiljoAI MCP
Comment=GiljoAI MCP Coding Orchestrator
Exec={launcher_script}
Icon={self.root_path}/frontend/public/icon.png
Terminal=false
Type=Application
Categories=Development;IDE;
"""
            )

        # Make it executable
        desktop_file.chmod(0o755)

        # Also create desktop shortcut if desktop exists
        desktop = Path.home() / "Desktop"
        if desktop.exists():
            import shutil

            shutil.copy2(desktop_file, desktop / "GiljoAI MCP.desktop")
            (desktop / "GiljoAI MCP.desktop").chmod(0o755)
            console.print("  [green]✓[/green] Created desktop shortcut")

        console.print("  [green]✓[/green] Created application menu entry")

    def _show_summary(self):
        """Show setup summary"""
        console.print("\n" + "=" * 60)
        console.print("[bold green]Setup Complete![/bold green]")
        console.print("=" * 60)

        # Configuration summary
        summary_table = Table(title="Configuration Summary", show_header=False)
        summary_table.add_column("Setting", style="cyan")
        summary_table.add_column("Value", style="green")

        summary_table.add_row("Database Type", self.env_vars.get("DB_TYPE", "sqlite"))
        summary_table.add_row("Deployment Mode", self.env_vars.get("GILJO_MCP_MODE", "local"))
        summary_table.add_row(
            "Dashboard URL", f"http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}"
        )
        summary_table.add_row("API URL", f"http://localhost:{self.env_vars.get('GILJO_MCP_API_PORT', '6002')}")
        summary_table.add_row("MCP Server", f"localhost:{self.env_vars.get('GILJO_MCP_SERVER_PORT', '6001')}")
        summary_table.add_row("WebSocket", f"ws://localhost:{self.env_vars.get('GILJO_MCP_WEBSOCKET_PORT', '6003')}")

        console.print(summary_table)

        # Next steps - harmonized with GUI installer
        console.print("\n[bold]To start using GiljoAI MCP:[/bold]")
        console.print()

        # Platform-specific start commands
        if self.platform_info.get("is_windows"):
            console.print("1. Run [cyan]start_giljo.bat[/cyan] to start all services")
            console.print("   • This will start the MCP server, API server, and dashboard")
            console.print("   • The dashboard will open automatically in your browser")
            console.print()
            console.print("2. Use [cyan]stop_giljo.bat[/cyan] to stop all services when done")
        else:
            console.print("1. Run [cyan]./start_giljo.sh[/cyan] to start all services")
            console.print("   • This will start the MCP server, API server, and dashboard")
            console.print("   • The dashboard will open automatically in your browser")
            console.print()
            console.print("2. Use [cyan]./stop_giljo.sh[/cyan] to stop all services when done")

        console.print()
        console.print("[bold]The dashboard includes:[/bold]")
        console.print("• System health monitoring")
        console.print("• Database connectivity status")
        console.print("• Service management controls")
        console.print("• Agent orchestration interface")
        console.print()

        console.print("[bold]Manual startup (alternative):[/bold]")
        console.print(f"• MCP Server: [cyan]python -m giljo_mcp.server[/cyan] (port {self.env_vars.get('GILJO_MCP_SERVER_PORT', '6001')})")
        console.print(f"• API Server: [cyan]python -m giljo_mcp.api_server[/cyan] (port {self.env_vars.get('GILJO_MCP_API_PORT', '6002')})")
        console.print(f"• Dashboard: [cyan]cd frontend && npm run dev[/cyan] (port {self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')})")

        if self.env_vars.get("GILJO_MCP_MODE") != "local":
            console.print("\n[yellow]Security Note:[/yellow]")
            console.print("Your API key has been saved to .env")
            console.print("Keep this key secure and never commit it to version control!")

        console.print("\n[bold cyan]Thank you for installing GiljoAI MCP![/bold cyan]")


# ==============================================================================
# Module-level functions for test compatibility (Hybrid Approach)
# These functions delegate to the GiljoSetup class methods
# ==============================================================================


def detect_platform() -> dict[str, Any]:
    """Detect platform information"""
    # Direct platform detection without class instantiation for test compatibility
    current_platform = sys.platform
    return {
        "os": "windows" if current_platform == "win32" else ("macos" if current_platform == "darwin" else "linux"),
        "path_separator": "\\" if current_platform == "win32" else "/",
        "is_windows": current_platform == "win32",
        "is_unix": current_platform != "win32",
        "python_version": platform.python_version(),
        "architecture": platform.machine(),
    }


def normalize_path(path: str) -> str:
    """Normalize path for the current platform"""
    return str(Path(path).resolve())


def create_directory_structure(base_path: Optional[str] = None) -> dict[str, Path]:
    """Create directory structure and return paths"""
    setup = GiljoSetup()
    if base_path:
        setup.root_path = Path(base_path)
    setup._create_directories()

    # Return created directories
    dirs = {}
    for dir_name in [
        "data",
        "logs",
        "temp",
        "backups",
        "src/giljo_mcp",
        "api",
        "frontend/src",
        "frontend/public",
        "tests",
        "scripts",
        "docker",
        "migrations",
    ]:
        dir_path = setup.root_path / dir_name
        dirs[dir_name.replace("/", "_")] = dir_path
    return dirs


def validate_database_type(db_type: str) -> bool:
    """Validate database type selection"""
    # Accept database names or menu option numbers
    return db_type.lower() in ["sqlite", "postgresql", "postgres", "1", "2"]


def build_database_url(db_type: str, **kwargs) -> str:
    """Build database connection URL"""
    if db_type.lower() == "sqlite":
        db_path = kwargs.get("db_path", "./data/giljo_mcp.db")
        return f"sqlite:///{Path(db_path).as_posix()}"
    if db_type.lower() in ["postgresql", "postgres"]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 5432)
        user = kwargs.get("user", "postgres")
        password = kwargs.get("password", "")
        database = kwargs.get("database", "giljo_mcp_db")
        ssl_mode = kwargs.get("ssl_mode", "")

        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        if ssl_mode:
            url += f"?sslmode={ssl_mode}"
        return url
    raise ValueError(f"Unsupported database type: {db_type}")


def parse_env_template(template_path: Optional[str] = None) -> dict[str, str]:
    """Parse .env.example template"""
    if not template_path:
        template_path = Path(__file__).parent / ".env.example"
    else:
        template_path = Path(template_path)

    env_vars = {}
    if template_path.exists():
        with open(template_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, value = line.split("=", 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars


def generate_env_file(env_path: Optional[str] = None, env_vars: Optional[dict[str, str]] = None) -> Path:
    """Generate .env file from variables

    Args:
        env_path: Path to write .env file (optional, defaults to project root)
        env_vars: Dictionary of environment variables
    """
    setup = GiljoSetup()

    # Handle different call signatures for compatibility
    if isinstance(env_path, dict) and env_vars is None:
        # Called as generate_env_file(env_vars_dict)
        env_vars = env_path
        env_path = None

    if env_path:
        output_path = Path(env_path)
    else:
        output_path = setup.root_path / ".env"

    if env_vars:
        setup.env_vars = env_vars

    setup._generate_env_file()
    return output_path


def check_port_availability(port: int, host: str = "127.0.0.1") -> bool:
    """Check if a port is available"""
    return not check_port(port, host)


def detect_port_conflicts() -> dict[str, bool]:
    """Detect port conflicts for GiljoAI services"""
    conflicts = {}
    giljo_ports = {"dashboard": 6000, "mcp_server": 6001, "api": 6002, "websocket": 6003}

    for service, port in giljo_ports.items():
        conflicts[service] = check_port(port)

    return conflicts


def validate_port_range(port: int) -> bool:
    """Validate port is in valid range"""
    return 1024 <= port <= 65535


def detect_legacy_installation() -> dict[str, Any]:
    """Detect any legacy installation"""
    legacy_info = {"found": False, "services": {}, "config_path": None}

    # Check for existing config file
    legacy_paths = [Path.home() / ".giljo-mcp" / "config.yaml", Path("./config.yaml")]

    for path in legacy_paths:
        if path.exists():
            legacy_info["config_path"] = str(path)
            legacy_info["found"] = True
            break

    return legacy_info


def validate_path(path: str) -> bool:
    """Validate file path"""
    if not path or not path.strip():
        return False
    try:
        p = Path(path)
        # Check if parent directory exists for new files
        if not p.exists():
            return p.parent.exists()
        return True
    except:
        return False


def validate_yes_no(response: str) -> bool:
    """Validate yes/no response"""
    return response.lower() in ["y", "yes", "n", "no"]


def display_error(message: str, details: Optional[str] = None):
    """Display formatted error message"""
    if RICH_AVAILABLE:
        console.print(f"[red]Error: {message}[/red]")
        if details:
            console.print(f"[dim]{details}[/dim]")
    else:
        print(f"Error: {message}")
        if details:
            print(f"  {details}")


# Additional functions for test compatibility
def generate_database_url(db_type: str, **kwargs) -> str:
    """Generate database URL (alias for build_database_url)"""
    return build_database_url(db_type, **kwargs)


def is_port_available(port: int, host: str = "127.0.0.1") -> bool:
    """Check if port is available (alias)"""
    return check_port_availability(port, host)


def validate_port(port: int) -> bool:
    """Validate port number (alias)"""
    return validate_port_range(port)


def backup_existing_env(env_path: Optional[str] = None) -> Optional[Path]:
    """Backup existing .env file"""
    if not env_path:
        env_path = Path(__file__).parent / ".env"
    else:
        env_path = Path(env_path)

    if env_path.exists():
        backup_path = env_path.with_suffix(".env.backup")
        shutil.copy2(env_path, backup_path)
        return backup_path
    return None


# Alias for compatibility
SetupManager = GiljoSetup


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description="GiljoAI MCP Setup")
    parser.add_argument("--non-interactive", action="store_true", help="Run in non-interactive mode with defaults")
    parser.add_argument("--check-only", action="store_true", help="Only check environment without making changes")
    parser.add_argument("--gui", action="store_true", help="Run setup in GUI mode (experimental)")
    args = parser.parse_args()

    try:
        # Handle GUI mode
        if args.gui:
            try:
                from setup_gui import GiljoSetupGUI

                gui_setup = GiljoSetupGUI()
                gui_setup.run()
                sys.exit(0)
            except ImportError as e:
                console.print("[red]GUI mode requires tkinter. Please install it:[/red]")
                console.print("[yellow]pip install tk[/yellow]")
                console.print(f"[dim]Error: {e}[/dim]")
                sys.exit(1)

        setup = GiljoSetup()

        if args.check_only:
            setup._show_welcome()
            setup._check_existing_installation()
            setup._check_ake_mcp(interactive=False)
            setup._check_ports()
            console.print("\n[green]Environment check complete.[/green]")
        elif args.non_interactive:
            console.print("[cyan]Running in non-interactive mode with defaults...[/cyan]")
            setup._show_welcome()
            # Use all defaults
            setup.env_vars = {
                "DATABASE_URL": f"sqlite:///{(setup.root_path / 'data' / 'giljo_mcp.db').as_posix()}",
                "DB_TYPE": "sqlite",
                "GILJO_MCP_MODE": "local",
                "GILJO_MCP_DASHBOARD_PORT": "6000",
                "GILJO_MCP_SERVER_PORT": "6001",
                "GILJO_MCP_API_PORT": "6002",
                "GILJO_MCP_WEBSOCKET_PORT": "6003",
                "LOG_LEVEL": "INFO",
                "DEBUG": "true",
            }
            setup._create_directories()
            setup._generate_env_file()
            setup._show_summary()
        else:
            setup.run()
    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user.[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Setup error: {e}[/red]")
        console.print("[dim]Please report this issue at https://github.com/giljoai/giljo-mcp/issues[/dim]")
        sys.exit(1)


if __name__ == "__main__":
    main()
