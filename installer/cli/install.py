#!/usr/bin/env python3
"""
GiljoAI MCP CLI Installer
Main entry point for the installation system
"""

import click
import sys
import os
import yaml
import platform
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

# Enable ANSI color support on Windows
if platform.system() == 'Windows':
    import ctypes
    kernel32 = ctypes.windll.kernel32
    kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer.core.installer import LocalhostInstaller, ServerInstaller
from installer.core.validator import PreInstallValidator
from installer.core.config import ConfigManager


# Color constants using standard ANSI escape codes (compatible with all terminals)
GOLD = '\033[93m'       # Bright yellow - GiljoAI, headers, URLs
GREEN = '\033[92m'      # Bright green - Success
RED = '\033[91m'        # Bright red - Errors
PURPLE = '\033[95m'     # Bright magenta - Info
WHITE = '\033[97m'      # Bright white - Regular text
CYAN = '\033[96m'       # Bright cyan - Claude Code (closest to orange in standard ANSI)
GRAY = '\033[90m'       # Dark gray - Codex
MAGENTA = '\033[95m'    # Bright magenta/pink - Gemini
BOLD = '\033[1m'
BG_BLUE = '\033[44m'    # Blue background
RESET = '\033[0m'

def c_gold(text):
    """Colorize text in gold (brand color)"""
    return f"{GOLD}{text}{RESET}"

def c_green(text):
    """Colorize text in green (success)"""
    return f"{GREEN}{text}{RESET}"

def c_red(text):
    """Colorize text in red (error)"""
    return f"{RED}{text}{RESET}"

def c_purple(text):
    """Colorize text in purple (info)"""
    return f"{PURPLE}{text}{RESET}"

def c_white(text):
    """Colorize text in white (regular)"""
    return f"{WHITE}{text}{RESET}"

def c_orange(text):
    """Colorize text in cyan (Claude Code - closest to orange in ANSI)"""
    return f"{CYAN}{text}{RESET}"

def c_gray(text):
    """Colorize text in gray (Codex)"""
    return f"{GRAY}{text}{RESET}"

def c_pink(text):
    """Colorize text in magenta/pink (Gemini)"""
    return f"{MAGENTA}{text}{RESET}"

def c_bold_gold(text):
    """Colorize text in bold gold"""
    return f"{BOLD}{GOLD}{text}{RESET}"


@click.command()
@click.option('--mode',
              type=click.Choice(['local', 'server']),
              default='local',
              help='Installation mode: local for development, server for team deployment')
@click.option('--batch',
              is_flag=True,
              help='Non-interactive batch mode')
@click.option('--pg-host',
              default='localhost',
              help='PostgreSQL host address')
@click.option('--pg-port',
              default=5432,
              type=int,
              help='PostgreSQL port number')
@click.option('--pg-password',
              help='PostgreSQL admin password (required for batch mode)')
@click.option('--config',
              type=click.Path(exists=True),
              help='Configuration file path for automated installation')
@click.option('--generate-config',
              is_flag=True,
              help='Generate a configuration template and exit')
@click.option('--api-port',
              default=7272,
              type=int,
              help='API service port')
@click.option('--ws-port',
              default=7273,
              type=int,
              help='WebSocket service port')
@click.option('--dashboard-port',
              default=7274,
              type=int,
              help='Dashboard service port')
@click.option('--install-dir',
              type=click.Path(),
              default=None,
              help='Installation directory (defaults to current directory)')
@click.option('--bind',
              default='127.0.0.1',
              help='Bind address for server mode (0.0.0.0 for network access)')
@click.option('--enable-ssl',
              is_flag=True,
              help='Enable SSL/TLS for server mode')
@click.option('--ssl-cert',
              type=click.Path(exists=True),
              help='Path to existing SSL certificate')
@click.option('--ssl-key',
              type=click.Path(exists=True),
              help='Path to existing SSL private key')
@click.option('--admin-username',
              help='Admin username for server mode')
@click.option('--admin-password',
              help='Admin password for server mode')
@click.option('--generate-api-key',
              is_flag=True,
              help='Generate API key for programmatic access')
@click.version_option(version='2.0.0')
def install(mode, batch, pg_host, pg_port, pg_password, config, generate_config,
            api_port, ws_port, dashboard_port, install_dir, bind, enable_ssl, ssl_cert, ssl_key,
            admin_username, admin_password, generate_api_key):
    """
    GiljoAI MCP CLI Installer

    Professional installation system for localhost and server deployments.
    Supports both interactive and batch modes with zero post-install configuration.
    """

    try:
        # Generate config template if requested
        if generate_config:
            generate_config_template()
            return

        # Display header
        if not batch:
            display_header(mode)

        # Load or collect configuration
        if config:
            click.echo(f"Loading configuration from: {config}")
            settings = load_config_file(config)
        elif batch:
            # Validate batch mode requirements
            if not pg_password:
                click.echo("Error: --pg-password is required in batch mode", err=True)
                sys.exit(1)

            # Ensure install_dir is an absolute path
            install_dir_resolved = str(Path(install_dir or Path.cwd()).resolve())

            settings = {
                'mode': mode,
                'pg_host': pg_host,
                'pg_port': pg_port,
                'pg_password': pg_password,
                'api_port': api_port,
                'ws_port': ws_port,
                'dashboard_port': dashboard_port,
                'install_dir': install_dir_resolved,
                'bind': bind if mode == 'server' else '127.0.0.1',
                'enable_ssl': enable_ssl,
                'ssl_cert': ssl_cert,
                'ssl_key': ssl_key,
                'admin_username': admin_username,
                'admin_password': admin_password,
                'generate_api_key': generate_api_key,
                'batch': True
            }
        else:
            # Interactive mode
            settings = interactive_setup(mode, pg_host, pg_port,
                                       api_port, ws_port, dashboard_port, install_dir)

        # Pre-installation validation
        click.echo("\n" + c_gold("="*60))
        click.echo(c_bold_gold("Pre-Installation Validation"))
        click.echo(c_gold("="*60))

        validator = PreInstallValidator(settings)
        validation_result = validator.validate()

        if not validation_result['valid']:
            click.echo(c_red("\n✗ Validation failed:"), err=True)
            for error in validation_result['errors']:
                click.echo(c_red(f"  - {error}"), err=True)

            if not batch and click.confirm("\nAttempt to fix issues and continue?"):
                # Attempt automatic fixes
                for fix in validation_result.get('fixes', []):
                    click.echo(c_purple(f"Applying fix: {fix}"))
                # Retry validation
                validation_result = validator.validate()
                if not validation_result['valid']:
                    click.echo(c_red("Cannot proceed with installation."), err=True)
                    sys.exit(1)
            else:
                sys.exit(1)

        click.echo(c_green("✓ Validation successful!"))

        # Select installer based on mode
        if settings['mode'] == 'localhost':
            installer = LocalhostInstaller(settings)
        else:
            installer = ServerInstaller(settings)

        # Run installation
        click.echo("\n" + c_gold("="*60))
        click.echo(c_bold_gold(f"Starting {settings['mode'].capitalize()} Installation"))
        click.echo(c_gold("="*60))

        result = installer.install()

        if result['success']:
            display_success(settings, result)
        else:
            display_failure(result)
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo(c_red("\n\n✗ Installation cancelled by user."), err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(c_red(f"\n\n✗ Unexpected error: {e}"), err=True)
        if not batch:
            click.echo(c_white("\nPlease report this issue to support."), err=True)
        sys.exit(1)


def display_header(mode: str):
    """Display installation header"""
    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("   GiljoAI MCP Installation System v2.0"))
    click.echo(c_gold("   Professional CLI Installer"))
    click.echo(c_gold("="*60))
    click.echo(c_white(f"\nMode: {c_gold(mode.upper())}"))
    click.echo(c_white(f"Platform: {platform.system()} {platform.machine()}"))
    click.echo(c_white(f"Python: {sys.version.split()[0]}"))
    click.echo()
    click.echo(c_purple("IMPORTANT NOTICE:"))
    click.echo(c_white("  Currently supports ") + c_white("Claude Code") + c_white(" only"))
    click.echo(c_white("  Support for ") + c_white("Codex") + c_white(" and ") + c_white("Gemini") + c_white(" coming in 2026"))
    click.echo()


def interactive_setup(mode: str, pg_host: str, pg_port: int,
                      api_port: int, ws_port: int, dashboard_port: int, install_dir: str) -> Dict[str, Any]:
    """Interactive configuration collection"""

    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("Installation Location"))
    click.echo(c_gold("="*60))

    # Ask for installation directory
    if install_dir is None:
        install_dir = click.prompt("  Installation directory",
                                  default=str(Path.cwd()),
                                  type=click.Path())
    else:
        click.echo(f"  Using installation directory: {install_dir}")

    # Create directory if it doesn't exist
    install_path = Path(install_dir)
    if not install_path.exists():
        if click.confirm(f"  Directory '{install_dir}' doesn't exist. Create it?"):
            install_path.mkdir(parents=True, exist_ok=True)
        else:
            click.echo("Installation cancelled.")
            sys.exit(1)

    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("PostgreSQL Configuration"))
    click.echo(c_gold("="*60))

    # PostgreSQL settings
    pg_host = click.prompt(c_white("  Host"), default=pg_host)
    pg_port = click.prompt(c_white("  Port"), default=pg_port, type=int)

    # Check PostgreSQL accessibility
    from installer.core.database import check_postgresql_connection

    click.echo(c_purple(f"\nChecking PostgreSQL at {pg_host}:{pg_port}..."))

    if not check_postgresql_connection(pg_host, pg_port):
        click.echo(c_red("\n⚠ Warning: Cannot connect to PostgreSQL"), err=True)
        click.echo(c_white("Please ensure ") + c_gold("PostgreSQL 18") + c_white(" is installed and running."))
        click.echo(c_white("Download from: ") + c_gold("https://www.postgresql.org/download/"))

        if not click.confirm("\nDo you want to continue anyway?"):
            sys.exit(1)
    else:
        click.echo(c_green("✓ PostgreSQL connection successful!"))

    # Admin credentials
    pg_password = click.prompt("  Admin password (postgres user)",
                              hide_input=True,
                              confirmation_prompt=True)

    # Service configuration
    click.echo(c_gold("\nService Configuration"))
    click.echo(c_gold("-" * 30))

    api_port = click.prompt(c_white("  API Port"), default=api_port, type=int)
    ws_port = click.prompt(c_white("  WebSocket Port"), default=ws_port, type=int)
    dashboard_port = click.prompt(c_white("  Dashboard Port"), default=dashboard_port, type=int)

    # Server mode configuration
    server_config = {}
    if mode == 'server':
        server_config = interactive_server_setup()

    # Additional options
    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("Additional Options"))
    click.echo(c_gold("="*60))

    auto_start = click.confirm(c_white("  Auto-start services after installation?"), default=True)
    open_browser = click.confirm(c_white("  Open dashboard in browser after start?"), default=True)

    # Summary
    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("Installation Summary"))
    click.echo(c_gold("="*60))
    click.echo(c_white(f"  Mode: {c_gold(mode)}"))
    click.echo(c_white(f"  PostgreSQL: {pg_host}:{pg_port}"))
    click.echo(c_white(f"  API Port: {api_port}"))
    click.echo(c_white(f"  WebSocket Port: {ws_port}"))
    click.echo(c_white(f"  Dashboard Port: {dashboard_port}"))
    click.echo(c_white(f"  Auto-start: {'Yes' if auto_start else 'No'}"))
    click.echo(c_white(f"  Open browser: {'Yes' if open_browser else 'No'}"))
    click.echo(c_gold("="*60))

    if not click.confirm("\nProceed with installation?"):
        click.echo("Installation cancelled.")
        sys.exit(0)

    # Ensure install_dir is an absolute path
    install_dir_resolved = str(Path(install_dir).resolve())

    settings = {
        'mode': mode,
        'pg_host': pg_host,
        'pg_port': pg_port,
        'pg_password': pg_password,
        'api_port': api_port,
        'ws_port': ws_port,
        'dashboard_port': dashboard_port,
        'install_dir': install_dir_resolved,
        'auto_start': auto_start,
        'open_browser': open_browser,
        'batch': False
    }

    # Merge server configuration if present
    if server_config:
        settings.update(server_config)

    return settings


def interactive_server_setup() -> Dict[str, Any]:
    """Interactive server mode configuration"""

    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("SERVER MODE CONFIGURATION"))
    click.echo(c_gold("="*60))

    # Network binding
    click.echo(c_gold("\nNetwork Configuration:"))
    bind = click.prompt(c_white("  Bind address (0.0.0.0 for all interfaces)"), default="0.0.0.0")

    # Security warning for network exposure
    if bind != "127.0.0.1":
        click.echo("\n" + c_red("!"*60))
        click.echo(c_red("  ⚠ WARNING: Server will be accessible over network!"))
        click.echo(c_white("  Security recommendations:"))
        click.echo(c_white("  - Enable SSL/TLS for encrypted connections"))
        click.echo(c_white("  - Configure firewall rules"))
        click.echo(c_white("  - Use strong admin passwords"))
        click.echo(c_white("  - Enable API key authentication"))
        click.echo(c_red("!"*60))

        if not click.confirm("\n  Continue with network exposure?"):
            raise click.Abort()

    # SSL Configuration
    enable_ssl = click.confirm("\nEnable SSL/TLS?", default=False)
    ssl_config = {}

    if enable_ssl:
        ssl_choice = click.prompt(
            "  SSL certificate type",
            type=click.Choice(['self-signed', 'existing']),
            default='self-signed'
        )

        if ssl_choice == 'self-signed':
            ssl_config = {
                'type': 'self-signed',
                'hostname': click.prompt("  Server hostname", default=platform.node())
            }
            click.echo("  Will generate self-signed certificate")
        else:
            ssl_config = {
                'type': 'existing',
                'cert_path': click.prompt("  Certificate path"),
                'key_path': click.prompt("  Private key path")
            }
    else:
        if bind != "127.0.0.1":
            click.echo("\n  WARNING: SSL disabled - NOT recommended for production!")

    # Admin user setup
    click.echo(c_gold("\nAdmin User Configuration:"))
    admin_username = click.prompt(c_white("  Username"), default="admin")
    admin_password = click.prompt(c_white("  Password"),
                                  hide_input=True,
                                  confirmation_prompt=True)

    # API key generation
    generate_api_key = click.confirm(c_white("\nGenerate API key for programmatic access?"), default=True)
    api_key_info = None

    if generate_api_key:
        import secrets
        api_key = f"gai_{secrets.token_urlsafe(32)}"
        api_key_info = api_key
        click.echo(c_purple(f"\n  Generated API key: ") + c_gold(api_key))
        click.echo(c_red("  ⚠ IMPORTANT: Save this key - it won't be shown again!"))

    return {
        'bind': bind,
        'enable_ssl': enable_ssl,
        'ssl': ssl_config,
        'admin_username': admin_username,
        'admin_password': admin_password,
        'generate_api_key': generate_api_key,
        'api_key': api_key_info,
        'features': {
            'ssl': enable_ssl,
            'api_keys': generate_api_key,
            'multi_user': True  # Server mode always supports multi-user
        }
    }


def load_config_file(config_path: str) -> Dict[str, Any]:
    """Load configuration from file"""
    path = Path(config_path)

    if not path.exists():
        raise click.ClickException(f"Configuration file not found: {config_path}")

    try:
        with open(path, 'r') as f:
            config = yaml.safe_load(f)

        # Validate required fields
        required = ['mode', 'pg_host', 'pg_port', 'pg_password']
        missing = [field for field in required if field not in config]

        if missing:
            raise click.ClickException(f"Missing required fields in config: {', '.join(missing)}")

        return config

    except yaml.YAMLError as e:
        raise click.ClickException(f"Invalid YAML in configuration file: {e}")


def generate_config_template():
    """Generate a configuration template file"""

    template = {
        'mode': 'local',
        'pg_host': 'localhost',
        'pg_port': 5432,
        'pg_password': 'your_postgres_password',
        'api_port': 7272,
        'ws_port': 7273,
        'dashboard_port': 7274,
        'auto_start': True,
        'open_browser': True,
        'features': {
            'ssl': False,
            'api_keys': False,
            'multi_user': False
        }
    }

    # Server mode additions (commented)
    template_with_comments = """# GiljoAI MCP Installation Configuration Template
# Generated: {}

# Installation mode: 'localhost' or 'server'
mode: localhost

# PostgreSQL Configuration
pg_host: localhost
pg_port: 5432
pg_password: your_postgres_password  # postgres user password

# Service Ports
api_port: 7272
ws_port: 7273
dashboard_port: 7274

# Post-installation Options
auto_start: true
open_browser: true

# Feature Flags
features:
  ssl: false        # Server mode: enable SSL
  api_keys: false   # Server mode: require API keys
  multi_user: false # Server mode: multi-user support

# Server Mode Configuration (uncomment for server deployment)
# server:
#   bind: 0.0.0.0
#   admin_user: admin
#   admin_password: change_this_password
#   allowed_ips: []  # Empty = allow all
#   ssl_cert: /path/to/cert.pem
#   ssl_key: /path/to/key.pem
""".format(datetime.now().isoformat())

    output_path = Path("install_config.yaml")
    output_path.write_text(template_with_comments)

    click.echo(f"Configuration template generated: {output_path.absolute()}")
    click.echo("\nEdit this file with your settings, then run:")
    click.echo(f"  python installer/cli/install.py --config {output_path}")


def display_success(settings: Dict[str, Any], result: Dict[str, Any]):
    """Display successful installation message"""

    click.echo("\n" + c_gold("="*60))
    click.echo(c_bold_gold("   ✓ Installation Completed Successfully!"))
    click.echo(c_gold("="*60))
    click.echo()
    click.echo(c_gold("Installation Details:"))
    click.echo(c_white(f"  Mode: {c_gold(settings['mode'])}"))
    click.echo(c_white(f"  Database: {c_gold('giljo_mcp')}"))
    click.echo(c_white(f"  Configuration: {c_gold('config.yaml')}"))
    click.echo(c_white(f"  Environment: {c_gold('.env')}"))
    click.echo()

    if result.get('credentials_file'):
        click.echo(c_purple("Important: Database credentials saved to:"))
        click.echo(c_gold(f"  {result['credentials_file']}"))
        click.echo(c_red("  ⚠ Keep this file secure!"))
        click.echo()

    click.echo(c_gold("Services:"))
    click.echo(c_white("  API: ") + c_gold(f"http://localhost:{settings.get('api_port', 7272)}"))
    click.echo(c_white("  WebSocket: ") + c_gold(f"ws://localhost:{settings.get('api_port', 7272)}"))
    click.echo(c_white("  Dashboard: ") + c_gold(f"http://localhost:{settings.get('dashboard_port', 7274)}"))
    click.echo()

    click.echo(c_purple("🎯 Next Step: Complete Setup in the Application"))
    click.echo()
    click.echo(c_white("  Open the dashboard and go to ") + c_gold("Settings → Setup Wizard"))
    click.echo()
    click.echo(c_white("  In the Setup Wizard, you can configure:"))
    click.echo(c_white("    • Claude Code MCP tools (optional)"))
    click.echo(c_white("    • LAN/WAN deployment (if needed)"))
    click.echo(c_white("    • Firewall settings (if needed)"))
    click.echo()

    click.echo(c_gold("To start GiljoAI MCP:"))
    if platform.system() == "Windows":
        click.echo(c_white("  ") + c_gold(".\\start_giljo.bat"))
    else:
        click.echo(c_white("  ") + c_gold("./start_giljo.sh"))

    click.echo(c_white("\nOr use the Python launcher:"))
    click.echo(c_white("  ") + c_gold("python start_giljo.py"))
    click.echo()

    # Ask about desktop shortcuts
    create_shortcuts = click.confirm(c_white("Create desktop shortcuts?"), default=True)
    if create_shortcuts:
        click.echo(c_purple("\nCreating desktop shortcuts..."))
        from installer.core.shortcuts import create_desktop_shortcuts
        shortcut_result = create_desktop_shortcuts(settings)

        if shortcut_result['success']:
            for shortcut in shortcut_result['created']:
                click.echo(c_green(f"  ✓ Created: {shortcut}"))

        if shortcut_result['errors']:
            click.echo(c_red("\n⚠ Warnings:"), err=True)
            for error in shortcut_result['errors']:
                click.echo(c_red(f"  - {error}"), err=True)

    click.echo()

    if settings.get('auto_start'):
        click.echo(c_purple("Starting services..."))
        # Import and run launcher from installation directory
        import sys
        from pathlib import Path
        install_dir = Path(settings.get('install_dir', Path.cwd()))
        sys.path.insert(0, str(install_dir))

        try:
            from start_giljo import start_services
            start_services(settings)
        except Exception as e:
            click.echo(f"\nWarning: Could not auto-start services: {e}", err=True)
            click.echo("You can start services manually using the commands above.", err=True)


def display_failure(result: Dict[str, Any]):
    """Display installation failure message"""

    click.echo("\n" + c_red("="*60), err=True)
    click.echo(c_bold_gold("   ✗ Installation Failed"), err=True)
    click.echo(c_red("="*60), err=True)
    click.echo(err=True)

    if result.get('error'):
        click.echo(c_red(f"Error: {result['error']}"), err=True)

    if result.get('details'):
        click.echo(c_red("\nDetails:"), err=True)
        for detail in result['details']:
            click.echo(c_white(f"  - {detail}"), err=True)

    if result.get('log_file'):
        click.echo(c_white(f"\nFull log available at: ") + c_gold(result['log_file']), err=True)

    click.echo(c_purple("\nTroubleshooting:"), err=True)
    click.echo(c_white("  1. Check ") + c_gold("PostgreSQL") + c_white(" is installed and running"), err=True)
    click.echo(c_white("  2. Verify admin credentials are correct"), err=True)
    click.echo(c_white("  3. Ensure ports are not in use"), err=True)
    click.echo(c_white("  4. Review the installation log"), err=True)


if __name__ == "__main__":
    install()
