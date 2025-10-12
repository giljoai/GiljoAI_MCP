# Phase 1: Localhost CLI Installation

## Phase Overview

Deliver a zero post-install localhost setup via CLI that consistently succeeds. The installer creates the PostgreSQL database/schema during installation using direct connection or guided fallback scripts.

## Critical Requirements

### Must Complete During Installation
1. **Database Creation** - giljo_mcp database with roles
2. **Schema Initialization** - All tables via migrations
3. **Configuration Files** - .env and config.yaml generated
4. **Dependencies** - Local venv with all packages
5. **Launchers** - Platform-specific start scripts
6. **Validation** - Verify everything works

### No Deferred Operations
- Database MUST exist before installer exits
- start_giljo works immediately
- Zero additional configuration needed

## CLI Implementation

### Main Entry Point
```python
# installer/cli/install.py
import click
from pathlib import Path
from installer.core import LocalhostInstaller, ServerInstaller

@click.command()
@click.option('--mode', type=click.Choice(['localhost', 'server']), 
              default='localhost', help='Installation mode')
@click.option('--batch', is_flag=True, help='Non-interactive mode')
@click.option('--pg-host', default='localhost', help='PostgreSQL host')
@click.option('--pg-port', default=5432, help='PostgreSQL port')
@click.option('--pg-password', help='PostgreSQL admin password')
@click.option('--config', type=click.Path(exists=True), help='Config file')
def install(mode, batch, pg_host, pg_port, pg_password, config):
    """GiljoAI MCP CLI Installer"""
    
    if config:
        # Load from config file
        settings = load_config(config)
    elif batch:
        # Batch mode - all params required
        if not pg_password:
            click.echo("Error: --pg-password required in batch mode")
            raise click.Abort()
        settings = {
            'mode': mode,
            'pg_host': pg_host,
            'pg_port': pg_port,
            'pg_password': pg_password
        }
    else:
        # Interactive mode
        settings = interactive_setup(mode)
    
    # Run installation
    installer = LocalhostInstaller() if mode == 'localhost' else ServerInstaller()
    installer.install(settings)
```

### Interactive Flow
```python
def interactive_setup(mode):
    """Interactive prompts for configuration"""
    
    click.echo("=" * 60)
    click.echo("   GiljoAI MCP Installation - CLI")
    click.echo("=" * 60)
    click.echo()
    
    # PostgreSQL configuration
    click.echo("PostgreSQL Configuration:")
    pg_host = click.prompt("  Host", default="localhost")
    pg_port = click.prompt("  Port", default=5432, type=int)
    
    # Check if PostgreSQL is accessible
    if not check_postgresql(pg_host, pg_port):
        click.echo("\n⚠️  PostgreSQL not found!")
        click.echo("Please install PostgreSQL 18 from:")
        click.echo("  https://www.postgresql.org/download/")
        if click.confirm("Have you installed PostgreSQL?"):
            return interactive_setup(mode)  # Retry
        raise click.Abort()
    
    # Admin credentials
    pg_password = click.prompt("  Admin password", hide_input=True)
    
    # Service ports
    click.echo("\nService Ports:")
    api_port = click.prompt("  API", default=8000, type=int)
    ws_port = click.prompt("  WebSocket", default=8001, type=int)
    dashboard_port = click.prompt("  Dashboard", default=3000, type=int)
    
    # Confirm settings
    click.echo("\n" + "=" * 40)
    click.echo("Installation Settings:")
    click.echo(f"  Mode: {mode}")
    click.echo(f"  PostgreSQL: {pg_host}:{pg_port}")
    click.echo(f"  API Port: {api_port}")
    click.echo(f"  WebSocket Port: {ws_port}")
    click.echo(f"  Dashboard Port: {dashboard_port}")
    click.echo("=" * 40)
    
    if not click.confirm("\nProceed with installation?"):
        raise click.Abort()
    
    return {
        'mode': mode,
        'pg_host': pg_host,
        'pg_port': pg_port,
        'pg_password': pg_password,
        'api_port': api_port,
        'ws_port': ws_port,
        'dashboard_port': dashboard_port
    }
```

## Core Installation Logic

### Database Creation Flow
```python
class DatabaseInstaller:
    def __init__(self, config):
        self.config = config
        self.fallback_needed = False
        
    def setup(self):
        """Main database setup flow"""
        try:
            # Try direct creation
            self.create_database_direct()
        except PermissionError:
            # Need elevation - use fallback
            self.create_fallback_scripts()
            self.guide_user_elevation()
            self.wait_for_verification()
        
        # Run migrations
        self.run_migrations()
        
    def create_database_direct(self):
        """Create database with admin credentials"""
        # Connect as postgres
        conn = psycopg2.connect(
            host=self.config['pg_host'],
            port=self.config['pg_port'],
            user='postgres',
            password=self.config['pg_password']
        )
        
        # Create roles and database
        with conn.cursor() as cur:
            # Create owner role
            owner_pass = generate_password()
            cur.execute(sql.SQL("""
                CREATE ROLE IF NOT EXISTS giljo_owner 
                LOGIN PASSWORD %s
            """), [owner_pass])
            
            # Create app user
            user_pass = generate_password()
            cur.execute(sql.SQL("""
                CREATE ROLE IF NOT EXISTS giljo_user
                LOGIN PASSWORD %s
            """), [user_pass])
            
            # Create database
            cur.execute(sql.SQL("""
                CREATE DATABASE IF NOT EXISTS giljo_mcp
                OWNER giljo_owner
            """))
            
        # Store passwords for .env
        self.config['owner_password'] = owner_pass
        self.config['user_password'] = user_pass
```

### Fallback Script Generation
```python
def create_fallback_scripts(self):
    """Generate elevation scripts when direct creation fails"""
    
    # Windows PowerShell script
    ps1_content = f"""
# GiljoAI MCP Database Creation Script
# Generated: {datetime.now()}

$ErrorActionPreference = "Stop"

# Parameters (pre-filled)
$PgHost = "{self.config['pg_host']}"
$PgPort = {self.config['pg_port']}
$DbName = "giljo_mcp"
$OwnerPassword = "{generate_password()}"
$UserPassword = "{generate_password()}"

Write-Host "Creating GiljoAI MCP database..." -ForegroundColor Green

# Create roles
psql -h $PgHost -p $PgPort -U postgres -c @"
CREATE ROLE giljo_owner LOGIN PASSWORD '$OwnerPassword';
CREATE ROLE giljo_user LOGIN PASSWORD '$UserPassword';
"@

# Create database
psql -h $PgHost -p $PgPort -U postgres -c @"
CREATE DATABASE giljo_mcp OWNER giljo_owner;
"@

# Grant permissions
psql -h $PgHost -p $PgPort -U postgres -d giljo_mcp -c @"
GRANT CONNECT ON DATABASE giljo_mcp TO giljo_user;
GRANT USAGE ON SCHEMA public TO giljo_user;
"@

Write-Host "Database created successfully!" -ForegroundColor Green
Write-Host "Passwords saved to: credentials.txt"

# Save credentials
@"
OWNER_PASSWORD=$OwnerPassword
USER_PASSWORD=$UserPassword
"@ | Out-File -FilePath credentials.txt
"""
    
    # Write script
    script_path = Path("installer/scripts/create_db.ps1")
    script_path.write_text(ps1_content)
    
    # Similar for Linux/macOS (.sh version)
    # ...
    
def guide_user_elevation(self):
    """Show clear instructions for running elevation script"""
    
    click.echo("\n" + "=" * 60)
    click.echo("🔐 Elevated Privileges Required")
    click.echo("=" * 60)
    click.echo()
    click.echo("We need elevated privileges to create the database.")
    click.echo("A script has been generated with your settings.")
    click.echo()
    
    if platform.system() == "Windows":
        click.echo("Please run in Administrator PowerShell:")
        click.echo("  .\\installer\\scripts\\create_db.ps1")
    else:
        click.echo("Please run with sudo:")
        click.echo("  sudo bash installer/scripts/create_db.sh")
    
    click.echo()
    click.echo("After running the script, press Enter to continue...")
    click.pause()
```

## Configuration Generation

### Environment File (.env)
```python
def generate_env_file(config):
    """Create .env with secure defaults"""
    
    env_content = f"""
# GiljoAI MCP Environment Configuration
# Generated: {datetime.now()}

# Database
POSTGRES_HOST={config['pg_host']}
POSTGRES_PORT={config['pg_port']}
POSTGRES_DB=giljo_mcp
POSTGRES_USER=giljo_user
POSTGRES_PASSWORD={config['user_password']}

# Owner credentials (for migrations only)
POSTGRES_OWNER_PASSWORD={config['owner_password']}

# Environment
ENVIRONMENT=development
DEBUG=False

# Service Ports  
API_PORT={config.get('api_port', 8000)}
WEBSOCKET_PORT={config.get('ws_port', 8001)}
DASHBOARD_PORT={config.get('dashboard_port', 3000)}
"""
    
    env_path = Path(".env")
    env_path.write_text(env_content)
    
    # Set permissions (important!)
    if platform.system() != "Windows":
        os.chmod(env_path, 0o600)
    
    click.echo(f"✅ Created .env (secured)")
```

### Configuration File (config.yaml)
```python
def generate_config_file(config):
    """Create config.yaml"""
    
    yaml_config = {
        'installation': {
            'version': '1.0.0',
            'mode': 'localhost',
            'timestamp': datetime.now().isoformat(),
            'installer_version': '2.0.0'
        },
        'database': {
            'type': 'postgresql',
            'host': config['pg_host'],
            'port': config['pg_port'],
            'name': 'giljo_mcp',
            'user': 'giljo_user',
            'version': '18'
        },
        'services': {
            'bind': '127.0.0.1',
            'api_port': config.get('api_port', 8000),
            'websocket_port': config.get('ws_port', 8001),
            'dashboard_port': config.get('dashboard_port', 3000)
        },
        'features': {
            'auto_start_browser': True,
            'ssl_enabled': False,
            'api_keys': False
        },
        'status': {
            'installation_complete': True,
            'database_created': True,
            'ready_to_launch': True
        }
    }
    
    with open('config.yaml', 'w') as f:
        yaml.dump(yaml_config, f, default_flow_style=False)
    
    click.echo("✅ Created config.yaml")
```

## Launcher Creation

### Universal Python Launcher
```python
def create_launcher():
    """Create start_giljo.py"""
    
    launcher_code = '''#!/usr/bin/env python
"""Universal launcher for GiljoAI MCP"""

import sys
import os
import time
import subprocess
from pathlib import Path

def validate_installation():
    """Verify installation is complete"""
    required_files = ['.env', 'config.yaml']
    for file in required_files:
        if not Path(file).exists():
            print(f"❌ Missing {file} - please run installer")
            return False
    return True

def check_port(port):
    """Check if port is available"""
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result != 0

def start_services():
    """Start all services in order"""
    print("🚀 Starting GiljoAI MCP services...")
    
    # Load config
    import yaml
    with open('config.yaml') as f:
        config = yaml.safe_load(f)
    
    # Check ports
    for service, port in config['services'].items():
        if 'port' in service and not check_port(port):
            print(f"❌ Port {port} already in use")
            return False
    
    # Start services
    processes = []
    
    # API server
    api_proc = subprocess.Popen([
        sys.executable, '-m', 'giljo_mcp.api'
    ])
    processes.append(api_proc)
    
    # WebSocket server  
    ws_proc = subprocess.Popen([
        sys.executable, '-m', 'giljo_mcp.websocket'
    ])
    processes.append(ws_proc)
    
    # Dashboard
    dash_proc = subprocess.Popen([
        sys.executable, '-m', 'giljo_mcp.dashboard'
    ])
    processes.append(dash_proc)
    
    print("✅ All services started!")
    print(f"   Dashboard: http://localhost:{config['services']['dashboard_port']}")
    print(f"   API: http://localhost:{config['services']['api_port']}/docs")
    print("   Press Ctrl+C to stop")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\\n🛑 Stopping services...")
        for proc in processes:
            proc.terminate()
        print("✅ Services stopped")

if __name__ == "__main__":
    if not validate_installation():
        sys.exit(1)
    start_services()
'''
    
    Path('launchers/start_giljo.py').write_text(launcher_code)
    
    # Platform-specific wrappers
    if platform.system() == "Windows":
        create_windows_launcher()
    else:
        create_unix_launcher()
```

## Testing Requirements

### Unit Tests
```python
# installer/tests/test_localhost_install.py

def test_postgresql_detection():
    """Test PostgreSQL detection logic"""
    
def test_database_creation():
    """Test database and role creation"""
    
def test_fallback_script_generation():
    """Test elevation script generation"""
    
def test_config_generation():
    """Test .env and config.yaml creation"""
```

### Integration Tests
```python
def test_complete_localhost_install():
    """End-to-end localhost installation"""
    
def test_elevation_fallback_flow():
    """Test fallback path when no admin access"""
    
def test_immediate_launch():
    """Verify start_giljo works after install"""
```

## Success Criteria

### Functional
- ✅ CLI installer works (interactive & batch)
- ✅ PostgreSQL detection and setup
- ✅ Database created during install
- ✅ Fallback scripts for elevation
- ✅ Configuration files generated
- ✅ Launchers created and working

### Performance
- ✅ Install < 5 minutes
- ✅ Launch < 30 seconds
- ✅ Minimal dependencies

### User Experience
- ✅ Clear prompts and feedback
- ✅ Helpful error messages
- ✅ No post-install configuration
- ✅ Immediate launch capability

## Implementation Order

1. **CLI Framework** - Click setup with options
2. **PostgreSQL Detection** - Check and guide
3. **Database Creation** - Direct + fallback
4. **Configuration** - .env and config.yaml
5. **Launchers** - Python + platform wrappers
6. **Testing** - Unit and integration

## Deliverables

- `installer/cli/install.py` - Main CLI entry point
- `installer/core/database.py` - Database setup logic
- `installer/scripts/create_db.*` - Fallback scripts
- `launchers/start_giljo.py` - Universal launcher
- Complete test suite
- Clear console output throughout


## Agent Coordination Matrix

| From → To | Handoff | Critical Points |
|-----------|---------|-----------------|
| Orchestrator → Database | PostgreSQL requirements | Version 18, fallback strategy |
| Database → Network | Remote access config | pg_hba.conf, SSL requirements |
| Network → Implementation | Server mode features | SSL paths, API keys |
| Implementation → Testing | Complete installer | Both modes, all platforms |
| Testing → Orchestrator | Test results | Go/no-go decision |

## Communication Protocols

### Task Assignment

task:
  agent: database-specialist
  action: implement-fallback-scripts
  requirements:
    - Windows PowerShell version
    - Linux/macOS bash version
    - Idempotent operations
    - Clear user guidance
  success_criteria:
    - Scripts generated with parameters
    - User can run elevated
    - Installation continues after
Status Reporting
yamlstatus:
  agent: implementation-developer
  phase: localhost-cli
  progress: 75%
  completed:
    - CLI framework
    - Interactive prompts
    - Batch mode
  blocking:
    - None
  next:
    - Configuration generation
    - Launcher creation
Issue Escalation
yamlissue:
  agent: network-engineer
  severity: medium
  description: SSL cert generation failing on Windows
  impact: Server mode without SSL
  recommendation: Use OpenSSL binary or Python cryptography
  decision_needed: true
Quality Standards
All agents must ensure:

No GUI components - CLI only
Two modes only - Localhost and server
PostgreSQL 18 - Single database option
Zero post-install - Must work immediately
Cross-platform - Windows, Linux, macOS
Professional output - Clear, helpful, no emojis
Error recovery - Never fail silently
Security by default - Localhost binding, explicit network consent

Success Metrics
Phase 1 (Localhost)

Database created during install ✓
Fallback scripts work ✓
start_giljo launches immediately ✓

Phase 2 (Server)

Network binding with warnings ✓
SSL optional but recommended ✓
Firewall rules generated ✓

Phase 3 (Polish)

Launch validation complete ✓
Error recovery implemented ✓
Performance targets met ✓