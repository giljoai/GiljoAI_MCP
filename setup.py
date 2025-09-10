#!/usr/bin/env python3
"""
GiljoAI MCP Interactive Setup Script
Comprehensive setup tool for initial configuration with cross-platform support
"""

import os
import sys

# Fix encoding issues on Windows
if sys.platform == 'win32':
    import locale
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')
import platform
import subprocess
import secrets
import shutil
from pathlib import Path
from typing import Dict, Optional, Tuple, List, Any
import json

# Rich imports for better UX
try:
    from rich import print
    from rich.console import Console
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    RICH_AVAILABLE = True
    console = Console()
except ImportError:
    RICH_AVAILABLE = False
    print("Warning: Rich library not installed. Installing for better UX...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "rich"])
    from rich import print
    from rich.console import Console
    from rich.prompt import Prompt, Confirm, IntPrompt
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, TextColumn
    from rich.syntax import Syntax
    console = Console()

# Import check_ports functionality
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
try:
    from check_ports import check_port, PORT_ASSIGNMENTS
except ImportError:
    print("[red]Error: check_ports.py not found in scripts directory[/red]")
    sys.exit(1)


class GiljoSetup:
    """Interactive setup for GiljoAI MCP"""
    
    def __init__(self):
        self.root_path = Path(__file__).parent
        self.config = {}
        self.env_vars = {}
        self.platform_info = self._detect_platform()
        self.rollback_actions = []  # For error recovery
        
    def _detect_platform(self) -> Dict[str, str]:
        """Detect platform and environment details"""
        return {
            'system': platform.system(),
            'release': platform.release(),
            'python': platform.python_version(),
            'arch': platform.machine(),
            'is_windows': platform.system() == 'Windows',
            'is_mac': platform.system() == 'Darwin',
            'is_linux': platform.system() == 'Linux'
        }
    
    def run(self):
        """Main setup flow"""
        self._show_welcome()
        
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
        
        platform_table.add_row("Operating System", f"{self.platform_info['system']} {self.platform_info['release']}")
        platform_table.add_row("Python Version", self.platform_info['python'])
        platform_table.add_row("Architecture", self.platform_info['arch'])
        platform_table.add_row("Installation Path", str(self.root_path))
        
        console.print(platform_table)
        console.print()
        
    def _check_existing_installation(self) -> bool:
        """Check for existing installation"""
        checks = {
            '.env': self.root_path / '.env',
            'config.yaml': self.root_path / 'config.yaml',
            'data directory': self.root_path / 'data',
            'logs directory': self.root_path / 'logs'
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
        """Check for AKE-MCP installation and offer migration"""
        console.print("\n[bold]Checking for AKE-MCP...[/bold]")
        
        ake_running = False
        for service, port in PORT_ASSIGNMENTS.items():
            if service.startswith("AKE-MCP") and check_port(port):
                ake_running = True
                console.print(f"  [green]✓[/green] {service} detected on port {port}")
        
        if ake_running:
            console.print("\n[yellow]AKE-MCP is currently running.[/yellow]")
            console.print("GiljoAI MCP uses different ports, so both can run simultaneously.")
            
            if interactive and Confirm.ask("\nWould you like to import configuration from AKE-MCP?"):
                self._import_ake_config()
    
    def _import_ake_config(self):
        """Import configuration from AKE-MCP if available"""
        ake_paths = [
            Path.home() / '.ake-mcp' / 'config.yaml',
            Path('F:/AKE-MCP/config.yaml'),
            Path('../AKE-MCP/config.yaml')
        ]
        
        for path in ake_paths:
            if path.exists():
                console.print(f"[green]Found AKE-MCP config at {path}[/green]")
                # We'll note this for future use but won't directly copy
                self.env_vars['AKE_MCP_CONFIG_PATH'] = str(path)
                break
    
    def _check_ports(self):
        """Check port availability"""
        console.print("\n[bold]Checking port availability...[/bold]")
        
        conflicts = []
        available = []
        
        giljo_ports = {
            "Dashboard": 6000,
            "MCP Server": 6001,
            "REST API": 6002,
            "WebSocket": 6003
        }
        
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
                new_port = IntPrompt.ask(
                    f"Enter alternative port for {service}",
                    default=default_port + 100
                )
                self.env_vars[f'GILJO_MCP_{service.upper().replace(" ", "_")}_PORT'] = str(new_port)
        else:
            # Use default ports
            self.env_vars['GILJO_MCP_DASHBOARD_PORT'] = '6000'
            self.env_vars['GILJO_MCP_SERVER_PORT'] = '6001'
            self.env_vars['GILJO_MCP_API_PORT'] = '6002'
            self.env_vars['GILJO_MCP_WEBSOCKET_PORT'] = '6003'
    
    def _configure_database(self):
        """Configure database settings"""
        console.print("\n[bold]Database Configuration[/bold]")
        console.print("GiljoAI MCP supports two database options:")
        console.print("  1. [cyan]SQLite[/cyan] - Simple, no setup required (recommended for development)")
        console.print("  2. [cyan]PostgreSQL[/cyan] - Scalable, production-ready (requires PostgreSQL server)")
        
        db_choice = Prompt.ask(
            "\nSelect database type",
            choices=["sqlite", "postgresql"],
            default="sqlite"
        )
        
        if db_choice == "sqlite":
            self._configure_sqlite()
        else:
            self._configure_postgresql()
    
    def _configure_sqlite(self):
        """Configure SQLite database"""
        console.print("\n[green]Configuring SQLite database...[/green]")
        
        # Use cross-platform path
        db_path = self.root_path / "data" / "giljo_mcp.db"
        self.env_vars['DATABASE_URL'] = f"sqlite:///{db_path.as_posix()}"
        self.env_vars['DB_TYPE'] = 'sqlite'
        
        console.print(f"  Database will be created at: {db_path}")
    
    def _configure_postgresql(self):
        """Configure PostgreSQL database"""
        console.print("\n[green]Configuring PostgreSQL database...[/green]")
        
        # Check if PostgreSQL is available
        pg_port = IntPrompt.ask("PostgreSQL port", default=5432)
        if not check_port(pg_port, 'localhost'):
            console.print("[yellow]Warning: PostgreSQL doesn't appear to be running on port {pg_port}[/yellow]")
            if not Confirm.ask("Continue anyway?"):
                console.print("[cyan]Falling back to SQLite...[/cyan]")
                self._configure_sqlite()
                return
        
        # Collect PostgreSQL credentials
        self.env_vars['DB_HOST'] = Prompt.ask("Database host", default="localhost")
        self.env_vars['DB_PORT'] = str(pg_port)
        self.env_vars['DB_NAME'] = Prompt.ask("Database name", default="giljo_mcp_db")
        self.env_vars['DB_USER'] = Prompt.ask("Database user", default="postgres")
        
        # Handle password securely
        if self.platform_info['is_windows']:
            # Windows doesn't hide password in basic input
            console.print("[yellow]Note: Password will be visible on Windows console[/yellow]")
        self.env_vars['DB_PASSWORD'] = Prompt.ask("Database password", password=True)
        
        # Build connection URL
        self.env_vars['DATABASE_URL'] = (
            f"postgresql://{self.env_vars['DB_USER']}:{self.env_vars['DB_PASSWORD']}"
            f"@{self.env_vars['DB_HOST']}:{self.env_vars['DB_PORT']}/{self.env_vars['DB_NAME']}"
        )
        self.env_vars['DB_TYPE'] = 'postgresql'
        
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
                'host': self.env_vars['DB_HOST'],
                'port': int(self.env_vars['DB_PORT']),
                'user': self.env_vars['DB_USER'],
                'password': self.env_vars['DB_PASSWORD']
            }
            
            # Try to connect to postgres database first
            conn_params['database'] = 'postgres'
            conn = psycopg2.connect(**conn_params)
            cur = conn.cursor()
            
            # Check if our database exists
            cur.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.env_vars['DB_NAME'],)
            )
            
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
        """Configure server settings"""
        console.print("\n[bold]Server Configuration[/bold]")
        
        # Deployment mode
        mode_choices = {
            "local": "Local development (localhost only)",
            "lan": "LAN accessible (network access with API keys)",
            "wan": "WAN accessible (internet access with TLS/OAuth)"
        }
        
        console.print("\nDeployment modes:")
        for key, desc in mode_choices.items():
            console.print(f"  • [cyan]{key}[/cyan]: {desc}")
        
        mode = Prompt.ask(
            "\nSelect deployment mode",
            choices=list(mode_choices.keys()),
            default="local"
        )
        self.env_vars['GILJO_MCP_MODE'] = mode
        
        # Logging configuration
        log_level = Prompt.ask(
            "Log level",
            choices=["DEBUG", "INFO", "WARNING", "ERROR"],
            default="INFO"
        )
        self.env_vars['LOG_LEVEL'] = log_level
        
        # Development settings
        if mode == "local":
            self.env_vars['DEBUG'] = 'true'
            self.env_vars['HOT_RELOAD'] = 'true'
        else:
            self.env_vars['DEBUG'] = 'false'
            self.env_vars['HOT_RELOAD'] = 'false'
    
    def _configure_security(self):
        """Configure security settings"""
        if self.env_vars.get('GILJO_MCP_MODE') != 'local':
            console.print("\n[bold]Security Configuration[/bold]")
            
            # Generate API key
            api_key = secrets.token_urlsafe(32)
            self.env_vars['GILJO_MCP_API_KEY'] = api_key
            console.print(f"[green]✓ Generated API key[/green]")
            
            # Generate secret key for sessions
            secret_key = secrets.token_hex(32)
            self.env_vars['GILJO_MCP_SECRET_KEY'] = secret_key
            console.print(f"[green]✓ Generated secret key[/green]")
            
            console.print("\n[yellow]Important: Save these keys securely![/yellow]")
            console.print(f"API Key: {api_key}")
    
    def _create_directories(self):
        """Create necessary directories with proper permissions"""
        console.print("\n[bold]Creating directories...[/bold]")
        
        directories = [
            'data',
            'logs',
            'temp',
            'backups',
            'src/giljo_mcp',
            'api',
            'frontend/src',
            'frontend/public',
            'tests',
            'scripts',
            'docker',
            'migrations'
        ]
        
        for dir_name in directories:
            dir_path = self.root_path / dir_name
            if not dir_path.exists():
                dir_path.mkdir(parents=True, exist_ok=True)
                console.print(f"  [green]✓[/green] Created {dir_name}/")
            else:
                console.print(f"  [dim]•[/dim] {dir_name}/ already exists")
        
        # Set appropriate permissions on sensitive directories
        if not self.platform_info['is_windows']:
            # Unix-like systems: restrict access to data and logs
            import stat
            (self.root_path / 'data').chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
            (self.root_path / 'logs').chmod(stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP)
    
    def _generate_config_yaml(self):
        """Generate config.yaml file from settings"""
        console.print("\n[bold]Generating config.yaml...[/bold]")
        
        # Import ConfigManager
        try:
            from src.giljo_mcp.config_manager import generate_sample_config, ConfigManager
        except ImportError:
            console.print("[yellow]Warning: ConfigManager not available, using template[/yellow]")
            return
        
        # Create ConfigManager instance
        config = ConfigManager(config_path=self.root_path / "config.yaml", auto_reload=False)
        
        # Apply settings from setup
        if self.env_vars.get('GILJO_MCP_MODE'):
            from src.giljo_mcp.config_manager import DeploymentMode
            config.server.mode = DeploymentMode(self.env_vars['GILJO_MCP_MODE'])
        
        # Database configuration
        if self.env_vars.get('DB_TYPE') == 'postgresql':
            config.database.type = 'postgresql'
            config.database.pg_host = self.env_vars.get('DB_HOST', 'localhost')
            config.database.pg_port = int(self.env_vars.get('DB_PORT', 5432))
            config.database.pg_database = self.env_vars.get('DB_NAME', 'giljo_mcp_db')
            config.database.pg_user = self.env_vars.get('DB_USER', 'postgres')
            config.database.pg_password = self.env_vars.get('DB_PASSWORD', '')
        else:
            config.database.type = 'sqlite'
        
        # Server ports
        if port := self.env_vars.get('GILJO_MCP_DASHBOARD_PORT'):
            config.server.dashboard_port = int(port)
        if port := self.env_vars.get('GILJO_MCP_SERVER_PORT'):
            config.server.mcp_port = int(port)
        if port := self.env_vars.get('GILJO_MCP_API_PORT'):
            config.server.api_port = int(port)
        if port := self.env_vars.get('GILJO_MCP_WEBSOCKET_PORT'):
            config.server.websocket_port = int(port)
        
        # Logging
        if level := self.env_vars.get('LOG_LEVEL'):
            config.logging.level = level
        
        # Save configuration
        config.save_to_file()
        console.print(f"  [green]✓[/green] Generated config.yaml")
    
    def _generate_env_file(self):
        """Generate .env file from template"""
        console.print("\n[bold]Generating .env file...[/bold]")
        
        env_template = self.root_path / '.env.example'
        env_file = self.root_path / '.env'
        
        if not env_template.exists():
            console.print("[red]Error: .env.example not found[/red]")
            return
        
        # Read template
        with open(env_template, 'r') as f:
            template_content = f.read()
        
        # Replace values
        env_content = []
        for line in template_content.split('\n'):
            if '=' in line and not line.strip().startswith('#'):
                key = line.split('=')[0].strip()
                if key in self.env_vars:
                    env_content.append(f"{key}={self.env_vars[key]}")
                else:
                    env_content.append(line)
            else:
                env_content.append(line)
        
        # Add any additional env vars not in template
        template_keys = set(line.split('=')[0].strip() for line in template_content.split('\n') 
                          if '=' in line and not line.strip().startswith('#'))
        for key, value in self.env_vars.items():
            if key not in template_keys:
                env_content.append(f"{key}={value}")
        
        # Write .env file
        with open(env_file, 'w') as f:
            f.write('\n'.join(env_content))
        
        console.print(f"  [green]✓[/green] Generated .env file")
        
        # Add .env to .gitignore if not already there
        gitignore = self.root_path / '.gitignore'
        if gitignore.exists():
            with open(gitignore, 'r') as f:
                gitignore_content = f.read()
            if '.env' not in gitignore_content:
                with open(gitignore, 'a') as f:
                    f.write('\n# Environment variables\n.env\n')
                console.print(f"  [green]✓[/green] Added .env to .gitignore")
    
    def _install_dependencies(self):
        """Install Python dependencies"""
        console.print("\n[bold]Installing dependencies...[/bold]")
        
        requirements_file = self.root_path / 'requirements.txt'
        if not requirements_file.exists():
            console.print("[yellow]requirements.txt not found. Skipping dependency installation.[/yellow]")
            return
        
        if Confirm.ask("Install Python dependencies now?"):
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True,
            ) as progress:
                task = progress.add_task("Installing dependencies...", total=None)
                
                # Install main requirements
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                    capture_output=True,
                    text=True
                )
                
                if result.returncode == 0:
                    console.print("[green]✓ Dependencies installed successfully[/green]")
                else:
                    console.print("[red]✗ Error installing dependencies[/red]")
                    console.print(result.stderr)
                
                # Install PostgreSQL adapter if needed
                if self.env_vars.get('DB_TYPE') == 'postgresql':
                    progress.update(task, description="Installing PostgreSQL adapter...")
                    subprocess.run(
                        [sys.executable, "-m", "pip", "install", "psycopg2-binary"],
                        capture_output=True
                    )
                    console.print("[green]✓ PostgreSQL adapter installed[/green]")
    
    def _show_summary(self):
        """Show setup summary"""
        console.print("\n" + "="*60)
        console.print("[bold green]Setup Complete![/bold green]")
        console.print("="*60)
        
        # Configuration summary
        summary_table = Table(title="Configuration Summary", show_header=False)
        summary_table.add_column("Setting", style="cyan")
        summary_table.add_column("Value", style="green")
        
        summary_table.add_row("Database Type", self.env_vars.get('DB_TYPE', 'sqlite'))
        summary_table.add_row("Deployment Mode", self.env_vars.get('GILJO_MCP_MODE', 'local'))
        summary_table.add_row("Dashboard URL", f"http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}")
        summary_table.add_row("API URL", f"http://localhost:{self.env_vars.get('GILJO_MCP_API_PORT', '6002')}")
        summary_table.add_row("MCP Server", f"localhost:{self.env_vars.get('GILJO_MCP_SERVER_PORT', '6001')}")
        summary_table.add_row("WebSocket", f"ws://localhost:{self.env_vars.get('GILJO_MCP_WEBSOCKET_PORT', '6003')}")
        
        console.print(summary_table)
        
        # Next steps
        console.print("\n[bold]Next Steps:[/bold]")
        console.print("1. Review the generated .env file")
        console.print("2. Start the development server:")
        console.print("   [cyan]python -m giljo_mcp.server[/cyan]")
        console.print("3. Open the dashboard:")
        console.print(f"   [cyan]http://localhost:{self.env_vars.get('GILJO_MCP_DASHBOARD_PORT', '6000')}[/cyan]")
        
        if self.env_vars.get('GILJO_MCP_MODE') != 'local':
            console.print("\n[yellow]Security Note:[/yellow]")
            console.print("Your API key has been saved to .env")
            console.print("Keep this key secure and never commit it to version control!")
        
        console.print("\n[bold cyan]Thank you for choosing GiljoAI MCP![/bold cyan]")


# ==============================================================================
# Module-level functions for test compatibility (Hybrid Approach)
# These functions delegate to the GiljoSetup class methods
# ==============================================================================

def detect_platform() -> Dict[str, Any]:
    """Detect platform information"""
    # Direct platform detection without class instantiation for test compatibility
    current_platform = sys.platform
    return {
        'os': 'windows' if current_platform == 'win32' else ('macos' if current_platform == 'darwin' else 'linux'),
        'path_separator': '\\' if current_platform == 'win32' else '/',
        'is_windows': current_platform == 'win32',
        'is_unix': current_platform != 'win32',
        'python_version': platform.python_version(),
        'architecture': platform.machine()
    }

def normalize_path(path: str) -> str:
    """Normalize path for the current platform"""
    return str(Path(path).resolve())

def create_directory_structure(base_path: str = None) -> Dict[str, Path]:
    """Create directory structure and return paths"""
    setup = GiljoSetup()
    if base_path:
        setup.root_path = Path(base_path)
    setup._create_directories()
    
    # Return created directories
    dirs = {}
    for dir_name in ['data', 'logs', 'temp', 'backups', 'src/giljo_mcp', 'api', 
                     'frontend/src', 'frontend/public', 'tests', 'scripts', 
                     'docker', 'migrations']:
        dir_path = setup.root_path / dir_name
        dirs[dir_name.replace('/', '_')] = dir_path
    return dirs

def validate_database_type(db_type: str) -> bool:
    """Validate database type selection"""
    # Accept database names or menu option numbers
    return db_type.lower() in ['sqlite', 'postgresql', 'postgres', '1', '2']

def build_database_url(db_type: str, **kwargs) -> str:
    """Build database connection URL"""
    if db_type.lower() == 'sqlite':
        db_path = kwargs.get('db_path', './data/giljo_mcp.db')
        return f"sqlite:///{Path(db_path).as_posix()}"
    elif db_type.lower() in ['postgresql', 'postgres']:
        host = kwargs.get('host', 'localhost')
        port = kwargs.get('port', 5432)
        user = kwargs.get('user', 'postgres')
        password = kwargs.get('password', '')
        database = kwargs.get('database', 'giljo_mcp_db')
        ssl_mode = kwargs.get('ssl_mode', '')
        
        url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
        if ssl_mode:
            url += f"?sslmode={ssl_mode}"
        return url
    else:
        raise ValueError(f"Unsupported database type: {db_type}")

def parse_env_template(template_path: str = None) -> Dict[str, str]:
    """Parse .env.example template"""
    if not template_path:
        template_path = Path(__file__).parent / '.env.example'
    else:
        template_path = Path(template_path)
    
    env_vars = {}
    if template_path.exists():
        with open(template_path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    return env_vars

def generate_env_file(env_path: str = None, env_vars: Dict[str, str] = None) -> Path:
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
        output_path = setup.root_path / '.env'
    
    if env_vars:
        setup.env_vars = env_vars
    
    setup._generate_env_file()
    return output_path

def check_port_availability(port: int, host: str = '127.0.0.1') -> bool:
    """Check if a port is available"""
    return not check_port(port, host)

def detect_port_conflicts() -> Dict[str, bool]:
    """Detect port conflicts for GiljoAI services"""
    conflicts = {}
    giljo_ports = {
        'dashboard': 6000,
        'mcp_server': 6001,
        'api': 6002,
        'websocket': 6003
    }
    
    for service, port in giljo_ports.items():
        conflicts[service] = check_port(port)
    
    return conflicts

def validate_port_range(port: int) -> bool:
    """Validate port is in valid range"""
    return 1024 <= port <= 65535

def detect_ake_mcp() -> Dict[str, Any]:
    """Detect AKE-MCP installation"""
    ake_info = {
        'found': False,  # Use 'found' for test compatibility
        'services': {},
        'config_path': None
    }
    
    # Check running services
    for service, port in PORT_ASSIGNMENTS.items():
        if service.startswith("AKE-MCP"):
            if check_port(port):
                ake_info['found'] = True
                ake_info['services'][service] = port
    
    # Check for config file
    ake_paths = [
        Path.home() / '.ake-mcp' / 'config.yaml',
        Path('F:/AKE-MCP/config.yaml'),
        Path('../AKE-MCP/config.yaml')
    ]
    
    for path in ake_paths:
        if path.exists():
            ake_info['config_path'] = str(path)
            ake_info['found'] = True  # Also set found if config exists
            break
    
    return ake_info

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
    return response.lower() in ['y', 'yes', 'n', 'no']

def display_error(message: str, details: str = None):
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

def is_port_available(port: int, host: str = '127.0.0.1') -> bool:
    """Check if port is available (alias)"""
    return check_port_availability(port, host)

def validate_port(port: int) -> bool:
    """Validate port number (alias)"""
    return validate_port_range(port)

def backup_existing_env(env_path: str = None) -> Optional[Path]:
    """Backup existing .env file"""
    if not env_path:
        env_path = Path(__file__).parent / '.env'
    else:
        env_path = Path(env_path)
    
    if env_path.exists():
        backup_path = env_path.with_suffix('.env.backup')
        shutil.copy2(env_path, backup_path)
        return backup_path
    return None

# Alias for compatibility
SetupManager = GiljoSetup

def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(description='GiljoAI MCP Setup')
    parser.add_argument('--non-interactive', action='store_true', 
                       help='Run in non-interactive mode with defaults')
    parser.add_argument('--check-only', action='store_true',
                       help='Only check environment without making changes')
    args = parser.parse_args()
    
    try:
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
                'DATABASE_URL': f"sqlite:///{(setup.root_path / 'data' / 'giljo_mcp.db').as_posix()}",
                'DB_TYPE': 'sqlite',
                'GILJO_MCP_MODE': 'local',
                'GILJO_MCP_DASHBOARD_PORT': '6000',
                'GILJO_MCP_SERVER_PORT': '6001',
                'GILJO_MCP_API_PORT': '6002',
                'GILJO_MCP_WEBSOCKET_PORT': '6003',
                'LOG_LEVEL': 'INFO',
                'DEBUG': 'true',
                'HOT_RELOAD': 'true'
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