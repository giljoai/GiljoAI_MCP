# Phase 3: Launch Validation & Polish

## Phase Overview

Ensure zero-configuration launch after installation. Polish the entire CLI experience, add comprehensive error handling, and validate that `start_giljo` works immediately without any additional setup.

## Critical Requirements

### Zero Post-Install Configuration
1. **Immediate Launch** - start_giljo works instantly
2. **Service Dependencies** - Correct startup order
3. **Error Recovery** - Graceful handling of issues
4. **Clean Shutdown** - Proper termination
5. **Performance** - Fast startup

## Launch Validator Implementation

```python
# installer/core/validator.py

class LaunchValidator:
    """Validates installation completeness before launch"""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        
    def validate_all(self):
        """Complete validation suite"""
        checks = [
            self.check_config_files,
            self.check_database_connection,
            self.check_schema_complete,
            self.check_dependencies,
            self.check_ports_available,
            self.check_permissions
        ]
        
        click.echo("\n🔍 Validating installation...")
        
        for check in checks:
            name = check.__name__.replace('check_', '').replace('_', ' ').title()
            click.echo(f"  Checking {name}...", nl=False)
            
            if check():
                click.echo(" ✅")
            else:
                click.echo(" ❌")
                return False
        
        return True
    
    def check_config_files(self):
        """Verify config files exist and are valid"""
        required_files = ['.env', 'config.yaml']
        
        for file in required_files:
            if not Path(file).exists():
                self.errors.append(f"Missing {file}")
                return False
            
            # Verify .env has required vars
            if file == '.env':
                with open(file) as f:
                    env_content = f.read()
                required_vars = ['POSTGRES_PASSWORD', 'API_PORT']
                for var in required_vars:
                    if var not in env_content:
                        self.errors.append(f"Missing {var} in .env")
                        return False
        
        return True
    
    def check_database_connection(self):
        """Verify database is accessible"""
        try:
            # Load credentials from .env
            from dotenv import load_dotenv
            load_dotenv()
            
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', 5432),
                database='giljo_mcp',
                user='giljo_user',
                password=os.getenv('POSTGRES_PASSWORD')
            )
            conn.close()
            return True
        except Exception as e:
            self.errors.append(f"Database not accessible: {e}")
            return False
    
    def check_schema_complete(self):
        """Verify all required tables exist"""
        required_tables = [
            'agents', 'messages', 'templates', 
            'configurations', 'products', 'tenants'
        ]
        
        try:
            conn = self.get_db_connection()
            cur = conn.cursor()
            
            cur.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            existing_tables = [row[0] for row in cur.fetchall()]
            
            for table in required_tables:
                if table not in existing_tables:
                    self.errors.append(f"Missing table: {table}")
                    return False
            
            conn.close()
            return True
            
        except Exception as e:
            self.errors.append(f"Schema check failed: {e}")
            return False
    
    def check_ports_available(self):
        """Check if required ports are free"""
        import yaml
        import socket
        
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        ports_to_check = [
            ('API', config['services']['api_port']),
            ('WebSocket', config['services']['websocket_port']),
            ('Dashboard', config['services']['dashboard_port'])
        ]
        
        for name, port in ports_to_check:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                self.errors.append(f"Port {port} ({name}) already in use")
                return False
        
        return True
```

## Service Manager

```python
# installer/core/service_manager.py

class ServiceManager:
    """Manages service startup with dependencies"""
    
    SERVICE_ORDER = [
        'database',
        'api',
        'websocket',
        'dashboard'
    ]
    
    def __init__(self):
        self.processes = {}
        self.config = self.load_config()
        
    def start_all(self):
        """Start all services in order"""
        
        for service in self.SERVICE_ORDER:
            click.echo(f"  Starting {service}...", nl=False)
            
            if self.start_service(service):
                click.echo(" ✅")
                time.sleep(2)  # Wait for startup
            else:
                click.echo(" ❌")
                self.stop_all()
                return False
        
        return True
    
    def start_service(self, service):
        """Start individual service"""
        
        if service == 'database':
            return self.ensure_database_running()
        
        elif service == 'api':
            proc = subprocess.Popen([
                sys.executable, '-m', 'uvicorn',
                'giljo_mcp.api:app',
                '--host', self.config['services']['bind'],
                '--port', str(self.config['services']['api_port'])
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes['api'] = proc
            
        elif service == 'websocket':
            proc = subprocess.Popen([
                sys.executable, '-m', 'giljo_mcp.websocket'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes['websocket'] = proc
            
        elif service == 'dashboard':
            proc = subprocess.Popen([
                sys.executable, '-m', 'giljo_mcp.dashboard'
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.processes['dashboard'] = proc
        
        # Wait and check if process started successfully
        if service != 'database':
            time.sleep(1)
            if self.processes[service].poll() is not None:
                # Process died immediately
                stderr = self.processes[service].stderr.read()
                click.echo(f"\nError starting {service}: {stderr}")
                return False
        
        return True
    
    def ensure_database_running(self):
        """Ensure PostgreSQL is running"""
        
        # Check with pg_isready
        result = subprocess.run(
            ['pg_isready', '-h', 'localhost', '-p', '5432'],
            capture_output=True
        )
        
        if result.returncode == 0:
            return True
        
        # Try to start PostgreSQL
        click.echo("\n  PostgreSQL not running, attempting to start...")
        
        if platform.system() == "Windows":
            subprocess.run(['net', 'start', 'postgresql-x64-18'])
        elif platform.system() == "Darwin":
            subprocess.run(['brew', 'services', 'start', 'postgresql@18'])
        else:
            subprocess.run(['sudo', 'systemctl', 'start', 'postgresql-18'])
        
        time.sleep(5)
        
        # Check again
        result = subprocess.run(
            ['pg_isready', '-h', 'localhost', '-p', '5432'],
            capture_output=True
        )
        
        return result.returncode == 0
```

## Enhanced Universal Launcher

```python
#!/usr/bin/env python
"""
start_giljo.py - Universal launcher with validation and recovery
"""

import sys
import os
import time
import click
from pathlib import Path
from installer.core.validator import LaunchValidator
from installer.core.service_manager import ServiceManager
from installer.core.recovery import ErrorRecovery

class GiljoLauncher:
    def __init__(self):
        self.validator = LaunchValidator()
        self.manager = ServiceManager()
        self.recovery = ErrorRecovery()
        
    def launch(self):
        """Main launch sequence"""
        
        self.print_banner()
        
        # Step 1: Validate
        if not self.validator.validate_all():
            self.handle_validation_errors()
            return False
        
        click.echo("\n✅ Installation validated")
        
        # Step 2: Start services
        click.echo("\n🚀 Starting services...")
        if not self.manager.start_all():
            self.handle_startup_errors()
            return False
        
        click.echo("\n✅ All services running")
        
        # Step 3: Wait for ready
        click.echo("\n⏳ Waiting for services to be ready...")
        if not self.wait_for_ready():
            click.echo("❌ Services failed to become ready")
            return False
        
        # Step 4: Open browser
        self.open_dashboard()
        
        # Step 5: Monitor
        self.print_status()
        self.monitor_services()
        
    def print_banner(self):
        """Display startup banner"""
        click.echo("""
╔══════════════════════════════════════════╗
║     GiljoAI MCP - Launch System         ║
╚══════════════════════════════════════════╝
""")
    
    def handle_validation_errors(self):
        """Handle validation failures"""
        click.echo("\n❌ Installation validation failed!")
        click.echo("\nErrors found:")
        
        for error in self.validator.errors:
            click.echo(f"  • {error}")
        
        # Attempt recovery
        click.echo("\n🔧 Attempting automatic recovery...")
        
        for error in self.validator.errors:
            if "Port" in error and "in use" in error:
                # Port conflict
                port = int(error.split()[1])
                if self.recovery.recover_port_conflict(port):
                    click.echo(f"  ✅ Resolved port {port} conflict")
                    
            elif "Database not accessible" in error:
                # Database down
                if self.recovery.recover_database():
                    click.echo("  ✅ Database started")
                    
            elif "Missing" in error and ".env" in error:
                # Missing config
                click.echo("  ❌ Missing configuration files")
                click.echo("     Please run the installer first")
                return
        
        # Retry validation
        if self.validator.validate_all():
            click.echo("\n✅ Recovery successful!")
            return True
        
        click.echo("\n❌ Could not recover automatically")
        click.echo("   Please run the installer to fix issues")
        return False
    
    def wait_for_ready(self, timeout=30):
        """Wait for services to be ready"""
        import requests
        import yaml
        
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        services = [
            ('API', f"http://localhost:{config['services']['api_port']}/health"),
            ('Dashboard', f"http://localhost:{config['services']['dashboard_port']}")
        ]
        
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            all_ready = True
            
            for name, url in services:
                try:
                    response = requests.get(url, timeout=1)
                    if response.status_code != 200:
                        all_ready = False
                except:
                    all_ready = False
            
            if all_ready:
                return True
            
            time.sleep(1)
            click.echo(".", nl=False)
        
        return False
    
    def open_dashboard(self):
        """Open dashboard in browser"""
        import webbrowser
        import yaml
        
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        mode = config['installation']['mode']
        
        if mode == 'server' and config.get('network', {}).get('ssl_enabled'):
            url = f"https://{config['network']['bind']}:{config['services']['dashboard_port']}"
        else:
            url = f"http://localhost:{config['services']['dashboard_port']}"
        
        click.echo(f"\n🌐 Opening dashboard: {url}")
        webbrowser.open(url)
    
    def print_status(self):
        """Print running status"""
        import yaml
        
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        mode = config['installation']['mode']
        
        click.echo("\n" + "=" * 50)
        click.echo("   GiljoAI MCP is running!")
        click.echo("=" * 50)
        
        if mode == 'localhost':
            click.echo(f"   Dashboard: http://localhost:{config['services']['dashboard_port']}")
            click.echo(f"   API Docs: http://localhost:{config['services']['api_port']}/docs")
        else:
            bind = config['network']['bind']
            protocol = 'https' if config['network'].get('ssl_enabled') else 'http'
            click.echo(f"   Dashboard: {protocol}://{bind}:{config['services']['dashboard_port']}")
            click.echo(f"   API Docs: {protocol}://{bind}:{config['services']['api_port']}/docs")
        
        click.echo("\n   Press Ctrl+C to stop all services")
        click.echo("=" * 50)
    
    def monitor_services(self):
        """Monitor services and handle shutdown"""
        try:
            while True:
                # Check if services are still running
                for name, proc in self.manager.processes.items():
                    if proc.poll() is not None:
                        click.echo(f"\n⚠️  Service {name} stopped unexpectedly")
                        if click.confirm("Attempt restart?"):
                            self.manager.start_service(name)
                
                time.sleep(5)
                
        except KeyboardInterrupt:
            click.echo("\n\n🛑 Shutting down services...")
            self.manager.stop_all()
            click.echo("✅ All services stopped")
            click.echo("Goodbye!")

if __name__ == "__main__":
    launcher = GiljoLauncher()
    sys.exit(0 if launcher.launch() else 1)
```

## Error Recovery System

```python
# installer/core/recovery.py

class ErrorRecovery:
    """Intelligent error recovery during launch"""
    
    def recover_port_conflict(self, port):
        """Handle port already in use"""
        
        # Check if it's our service
        if self.is_our_service(port):
            click.echo(f"  ℹ️  GiljoAI service already on port {port}")
            return True
        
        # Find alternative
        alt_port = self.find_free_port(port + 1)
        
        if click.confirm(f"  Use port {alt_port} instead?"):
            self.update_config_port(port, alt_port)
            return True
        
        return False
    
    def recover_database(self):
        """Attempt to start PostgreSQL"""
        
        if platform.system() == "Windows":
            result = subprocess.run(
                ['net', 'start', 'postgresql-x64-18'],
                capture_output=True
            )
        else:
            result = subprocess.run(
                ['sudo', 'systemctl', 'start', 'postgresql-18'],
                capture_output=True
            )
        
        time.sleep(5)
        
        # Test connection
        try:
            conn = psycopg2.connect(
                host='localhost',
                database='giljo_mcp',
                user='giljo_user',
                password=os.getenv('POSTGRES_PASSWORD')
            )
            conn.close()
            return True
        except:
            return False
    
    def find_free_port(self, start_port):
        """Find next available port"""
        import socket
        
        for port in range(start_port, start_port + 100):
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result != 0:
                return port
        
        return None
    
    def update_config_port(self, old_port, new_port):
        """Update port in configuration"""
        import yaml
        
        with open('config.yaml') as f:
            config = yaml.safe_load(f)
        
        # Find and update port
        for service, port in config['services'].items():
            if port == old_port:
                config['services'][service] = new_port
                break
        
        with open('config.yaml', 'w') as f:
            yaml.dump(config, f)
        
        # Also update .env
        with open('.env') as f:
            env_lines = f.readlines()
        
        with open('.env', 'w') as f:
            for line in env_lines:
                if f'={old_port}' in line:
                    line = line.replace(f'={old_port}', f'={new_port}')
                f.write(line)
```

## Performance Optimization

```python
class LaunchOptimizer:
    """Optimize launch performance"""
    
    def __init__(self):
        self.cache_dir = Path.home() / '.giljo-mcp' / 'cache'
        self.cache_dir.mkdir(parents=True, exist_ok=True)
    
    def cache_validation(self):
        """Cache validation results for faster launches"""
        
        cache_file = self.cache_dir / 'validation.json'
        
        validation_data = {
            'timestamp': time.time(),
            'config_hash': self.get_config_hash(),
            'python_version': sys.version,
            'tables_verified': True
        }
        
        with open(cache_file, 'w') as f:
            json.dump(validation_data, f)
    
    def use_cache(self):
        """Check if cached validation is still valid"""
        
        cache_file = self.cache_dir / 'validation.json'
        
        if not cache_file.exists():
            return False
        
        with open(cache_file) as f:
            cache = json.load(f)
        
        # Cache valid for 1 hour
        if time.time() - cache['timestamp'] > 3600:
            return False
        
        # Check config hasn't changed
        if cache['config_hash'] != self.get_config_hash():
            return False
        
        return True
```

## Testing Requirements

### Launch Tests
```python
def test_immediate_launch():
    """Verify start_giljo works immediately after install"""
    
def test_validation_complete():
    """Test all validation checks pass"""
    
def test_service_startup_order():
    """Verify services start in correct dependency order"""
    
def test_database_preexists():
    """Confirm database exists before launch"""
```

### Recovery Tests
```python
def test_port_conflict_recovery():
    """Test automatic port conflict resolution"""
    
def test_database_down_recovery():
    """Test PostgreSQL startup recovery"""
    
def test_missing_config_detection():
    """Test detection of missing configuration"""
```

### Performance Tests
```python
def test_launch_time():
    """Verify launch completes in < 30 seconds"""
    
def test_validation_caching():
    """Test validation cache improves performance"""
```

## Success Criteria

### Functional
- ✅ start_giljo works immediately
- ✅ No additional configuration needed
- ✅ Services start in correct order
- ✅ Error recovery works
- ✅ Clean shutdown

### Performance
- ✅ Launch < 30 seconds
- ✅ Validation caching works
- ✅ Minimal resource usage

### User Experience
- ✅ Clear progress indication
- ✅ Helpful error messages
- ✅ Recovery suggestions
- ✅ Professional output

## Final Polish Checklist

### Console Output
- [x] ASCII banner on startup
- [x] Color-coded status (click.style)
- [x] Progress indicators
- [x] Clear error messages
- [x] Professional tone throughout

### Error Handling
- [x] All errors caught gracefully
- [x] Recovery attempted automatically
- [x] Clear guidance when manual intervention needed
- [x] No stack traces shown to user

### Documentation
- [x] README with quick start
- [x] Troubleshooting guide
- [x] Platform-specific notes
- [x] FAQ section

## Deliverables

- `start_giljo.py` - Enhanced universal launcher
- `installer/core/validator.py` - Launch validation
- `installer/core/service_manager.py` - Service orchestration
- `installer/core/recovery.py` - Error recovery
- `installer/core/optimizer.py` - Performance optimization
- Complete test suite
- Professional polish throughout

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