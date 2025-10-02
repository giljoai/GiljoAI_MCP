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

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from installer.core.installer import LocalhostInstaller, ServerInstaller
from installer.core.validator import PreInstallValidator
from installer.core.config import ConfigManager


@click.command()
@click.option('--mode',
              type=click.Choice(['localhost', 'server']),
              default='localhost',
              help='Installation mode: localhost for development, server for team deployment')
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
              default=8001,
              type=int,
              help='WebSocket service port')
@click.option('--dashboard-port',
              default=3000,
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

            settings = {
                'mode': mode,
                'pg_host': pg_host,
                'pg_port': pg_port,
                'pg_password': pg_password,
                'api_port': api_port,
                'ws_port': ws_port,
                'dashboard_port': dashboard_port,
                'install_dir': install_dir or str(Path.cwd()),
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
        click.echo("\n" + "="*60)
        click.echo("Pre-Installation Validation")
        click.echo("="*60)

        validator = PreInstallValidator(settings)
        validation_result = validator.validate()

        if not validation_result['valid']:
            click.echo("\nValidation failed:", err=True)
            for error in validation_result['errors']:
                click.echo(f"  - {error}", err=True)

            if not batch and click.confirm("\nAttempt to fix issues and continue?"):
                # Attempt automatic fixes
                for fix in validation_result.get('fixes', []):
                    click.echo(f"Applying fix: {fix}")
                # Retry validation
                validation_result = validator.validate()
                if not validation_result['valid']:
                    click.echo("Cannot proceed with installation.", err=True)
                    sys.exit(1)
            else:
                sys.exit(1)

        click.echo("Validation successful!")

        # Select installer based on mode
        if settings['mode'] == 'localhost':
            installer = LocalhostInstaller(settings)
        else:
            installer = ServerInstaller(settings)

        # Run installation
        click.echo("\n" + "="*60)
        click.echo(f"Starting {settings['mode'].capitalize()} Installation")
        click.echo("="*60)

        result = installer.install()

        if result['success']:
            display_success(settings, result)
        else:
            display_failure(result)
            sys.exit(1)

    except KeyboardInterrupt:
        click.echo("\n\nInstallation cancelled by user.", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"\n\nUnexpected error: {e}", err=True)
        if not batch:
            click.echo("\nPlease report this issue to support.", err=True)
        sys.exit(1)


def display_header(mode: str):
    """Display installation header"""
    click.echo("\n" + "="*60)
    click.echo("   GiljoAI MCP Installation System v2.0")
    click.echo("   Professional CLI Installer")
    click.echo("="*60)
    click.echo(f"\nMode: {mode.upper()}")
    click.echo(f"Platform: {platform.system()} {platform.machine()}")
    click.echo(f"Python: {sys.version.split()[0]}")
    click.echo()
    click.echo("IMPORTANT NOTICE:")
    click.echo("  Currently supports Claude Code only")
    click.echo("  Support for Codex and Gemini coming in 2026")
    click.echo("  See CLAUDE_CODE_EXCLUSIVITY_INVESTIGATION.md for details")
    click.echo()


def interactive_setup(mode: str, pg_host: str, pg_port: int,
                      api_port: int, ws_port: int, dashboard_port: int, install_dir: str) -> Dict[str, Any]:
    """Interactive configuration collection"""

    click.echo("\n" + "="*60)
    click.echo("Installation Location")
    click.echo("="*60)

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

    click.echo("\n" + "="*60)
    click.echo("PostgreSQL Configuration")
    click.echo("="*60)

    # PostgreSQL settings
    pg_host = click.prompt("  Host", default=pg_host)
    pg_port = click.prompt("  Port", default=pg_port, type=int)

    # Check PostgreSQL accessibility
    from installer.core.database import check_postgresql_connection

    click.echo(f"\nChecking PostgreSQL at {pg_host}:{pg_port}...")

    if not check_postgresql_connection(pg_host, pg_port):
        click.echo("\nWarning: Cannot connect to PostgreSQL", err=True)
        click.echo("Please ensure PostgreSQL 18 is installed and running.")
        click.echo("Download from: https://www.postgresql.org/download/")

        if not click.confirm("\nDo you want to continue anyway?"):
            sys.exit(1)
    else:
        click.echo("PostgreSQL connection successful!")

    # Admin credentials
    pg_password = click.prompt("  Admin password (postgres user)",
                              hide_input=True,
                              confirmation_prompt=True)

    # Service configuration
    click.echo("\nService Configuration")
    click.echo("-" * 30)

    api_port = click.prompt("  API Port", default=api_port, type=int)
    ws_port = click.prompt("  WebSocket Port", default=ws_port, type=int)
    dashboard_port = click.prompt("  Dashboard Port", default=dashboard_port, type=int)

    # Server mode configuration
    server_config = {}
    if mode == 'server':
        server_config = interactive_server_setup()

    # Additional options
    click.echo("\n" + "="*60)
    click.echo("Additional Options")
    click.echo("="*60)

    auto_start = click.confirm("  Auto-start services after installation?", default=True)
    open_browser = click.confirm("  Open dashboard in browser after start?", default=True)

    # Summary
    click.echo("\n" + "="*60)
    click.echo("Installation Summary")
    click.echo("="*60)
    click.echo(f"  Mode: {mode}")
    click.echo(f"  PostgreSQL: {pg_host}:{pg_port}")
    click.echo(f"  API Port: {api_port}")
    click.echo(f"  WebSocket Port: {ws_port}")
    click.echo(f"  Dashboard Port: {dashboard_port}")
    click.echo(f"  Auto-start: {'Yes' if auto_start else 'No'}")
    click.echo(f"  Open browser: {'Yes' if open_browser else 'No'}")
    click.echo("="*60)

    if not click.confirm("\nProceed with installation?"):
        click.echo("Installation cancelled.")
        sys.exit(0)

    settings = {
        'mode': mode,
        'pg_host': pg_host,
        'pg_port': pg_port,
        'pg_password': pg_password,
        'api_port': api_port,
        'ws_port': ws_port,
        'dashboard_port': dashboard_port,
        'install_dir': install_dir,
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

    click.echo("\n" + "="*60)
    click.echo("SERVER MODE CONFIGURATION")
    click.echo("="*60)

    # Network binding
    click.echo("\nNetwork Configuration:")
    bind = click.prompt("  Bind address (0.0.0.0 for all interfaces)", default="0.0.0.0")

    # Security warning for network exposure
    if bind != "127.0.0.1":
        click.echo("\n" + "!"*60)
        click.echo("  WARNING: Server will be accessible over network!")
        click.echo("  Security recommendations:")
        click.echo("  - Enable SSL/TLS for encrypted connections")
        click.echo("  - Configure firewall rules")
        click.echo("  - Use strong admin passwords")
        click.echo("  - Enable API key authentication")
        click.echo("!"*60)

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
    click.echo("\nAdmin User Configuration:")
    admin_username = click.prompt("  Username", default="admin")
    admin_password = click.prompt("  Password",
                                  hide_input=True,
                                  confirmation_prompt=True)

    # API key generation
    generate_api_key = click.confirm("\nGenerate API key for programmatic access?", default=True)
    api_key_info = None

    if generate_api_key:
        import secrets
        api_key = f"gai_{secrets.token_urlsafe(32)}"
        api_key_info = api_key
        click.echo(f"\n  Generated API key: {api_key}")
        click.echo("  IMPORTANT: Save this key - it won't be shown again!")

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
        'mode': 'localhost',
        'pg_host': 'localhost',
        'pg_port': 5432,
        'pg_password': 'your_postgres_password',
        'api_port': 7272,
        'ws_port': 8001,
        'dashboard_port': 3000,
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
ws_port: 8001
dashboard_port: 3000

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

    click.echo("\n" + "="*60)
    click.echo("   Installation Completed Successfully!")
    click.echo("="*60)
    click.echo()
    click.echo("Installation Details:")
    click.echo(f"  Mode: {settings['mode']}")
    click.echo(f"  Database: giljo_mcp")
    click.echo(f"  Configuration: config.yaml")
    click.echo(f"  Environment: .env")
    click.echo()

    if result.get('credentials_file'):
        click.echo("Important: Database credentials saved to:")
        click.echo(f"  {result['credentials_file']}")
        click.echo("  Keep this file secure!")
        click.echo()

    if result.get('mcp_registered'):
        click.echo("MCP Registration:")
        click.echo("  Successfully registered with Claude Code")
        click.echo()

    click.echo("Services:")
    click.echo(f"  API: http://localhost:{settings.get('api_port', 7272)}")
    click.echo(f"  WebSocket: ws://localhost:{settings.get('api_port', 7272)}")
    click.echo(f"  Dashboard: http://localhost:{settings.get('dashboard_port', 6000)}")
    click.echo()

    click.echo("IMPORTANT NOTICE:")
    click.echo("  This installation currently supports Claude Code only")
    click.echo("  Support for Codex and Gemini coming in 2026")
    click.echo()

    click.echo("To start GiljoAI MCP:")
    if platform.system() == "Windows":
        click.echo("  .\\start_giljo.bat")
    else:
        click.echo("  ./start_giljo.sh")

    click.echo("\nOr use the Python launcher:")
    click.echo("  python start_giljo.py")
    click.echo()

    # Ask about desktop shortcuts
    create_shortcuts = click.confirm("Create desktop shortcuts?", default=True)
    if create_shortcuts:
        click.echo("\nCreating desktop shortcuts...")
        from installer.core.shortcuts import create_desktop_shortcuts
        shortcut_result = create_desktop_shortcuts(settings)

        if shortcut_result['success']:
            for shortcut in shortcut_result['created']:
                click.echo(f"  ✓ Created: {shortcut}")

        if shortcut_result['errors']:
            click.echo("\nWarnings:", err=True)
            for error in shortcut_result['errors']:
                click.echo(f"  - {error}", err=True)

    click.echo()

    if settings.get('auto_start'):
        click.echo("Starting services...")
        # Import and run launcher from root
        from start_giljo import start_services
        start_services(settings)


def display_failure(result: Dict[str, Any]):
    """Display installation failure message"""

    click.echo("\n" + "="*60, err=True)
    click.echo("   Installation Failed", err=True)
    click.echo("="*60, err=True)
    click.echo(err=True)

    if result.get('error'):
        click.echo(f"Error: {result['error']}", err=True)

    if result.get('details'):
        click.echo("\nDetails:", err=True)
        for detail in result['details']:
            click.echo(f"  - {detail}", err=True)

    if result.get('log_file'):
        click.echo(f"\nFull log available at: {result['log_file']}", err=True)

    click.echo("\nTroubleshooting:", err=True)
    click.echo("  1. Check PostgreSQL is installed and running", err=True)
    click.echo("  2. Verify admin credentials are correct", err=True)
    click.echo("  3. Ensure ports are not in use", err=True)
    click.echo("  4. Review the installation log", err=True)


if __name__ == "__main__":
    install()
