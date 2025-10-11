# Phase 2: Server Mode CLI Installation

## Phase Overview

Extend localhost installation to support LAN/WAN deployment without breaking existing functionality. Add network configuration, basic security, and cross-platform support while maintaining simplicity.

## Critical Requirements

### Maintain Phase 1
- Localhost mode continues working perfectly
- No regression in features
- Same simple CLI experience

### New for Server Mode
1. **Network Configuration** - Bind to network interfaces
2. **Basic Security** - API keys, admin user, SSL optional
3. **Remote Database Access** - PostgreSQL network configuration
4. **Firewall Helpers** - Generated rules (manual apply)
5. **Multi-User Support** - Basic user management

## CLI Enhancements

### Server Mode Options
```python
@click.command()
@click.option('--mode', type=click.Choice(['localhost', 'server']), 
              default='localhost', help='Installation mode')
@click.option('--bind', default='0.0.0.0', help='Bind address (server mode)')
@click.option('--admin-username', help='Admin username (server mode)')
@click.option('--admin-password', help='Admin password (server mode)')
@click.option('--enable-ssl', is_flag=True, help='Enable SSL/TLS')
@click.option('--ssl-cert', type=click.Path(exists=True), help='SSL certificate')
@click.option('--ssl-key', type=click.Path(exists=True), help='SSL private key')
def install(mode, bind, admin_username, admin_password, enable_ssl, ssl_cert, ssl_key):
    """GiljoAI MCP CLI Installer with Server Mode"""
```

### Interactive Server Setup
```python
def interactive_server_setup():
    """Additional prompts for server mode"""
    
    click.echo("\n" + "=" * 60)
    click.echo("SERVER MODE CONFIGURATION")
    click.echo("=" * 60)
    
    # Network binding
    click.echo("\n🌐 Network Configuration:")
    bind = click.prompt("  Bind address", default="0.0.0.0")
    
    # Security warning
    if bind != "127.0.0.1":
        click.echo("\n⚠️  WARNING: Server will be accessible over network!")
        click.echo("   Consider enabling SSL for production use.")
        if not click.confirm("   Continue with network exposure?"):
            raise click.Abort()
    
    # SSL Configuration
    enable_ssl = click.confirm("\n🔐 Enable SSL/TLS?", default=False)
    ssl_config = {}
    
    if enable_ssl:
        ssl_choice = click.prompt(
            "  SSL certificate",
            type=click.Choice(['self-signed', 'existing']),
            default='self-signed'
        )
        
        if ssl_choice == 'self-signed':
            ssl_config['type'] = 'self-signed'
            click.echo("  ℹ️  Will generate self-signed certificate")
        else:
            ssl_config['type'] = 'existing'
            ssl_config['cert'] = click.prompt("  Certificate path")
            ssl_config['key'] = click.prompt("  Private key path")
    else:
        click.echo("\n⚠️  SSL disabled - NOT recommended for production!")
    
    # Admin user setup
    click.echo("\n👤 Admin User Configuration:")
    admin_username = click.prompt("  Username", default="admin")
    admin_password = click.prompt("  Password", hide_input=True, 
                                confirmation_prompt=True)
    
    # API key generation
    if click.confirm("\n🔑 Generate API key for programmatic access?", default=True):
        api_key = generate_api_key()
        click.echo(f"  Generated API key: {api_key}")
        click.echo("  ⚠️  Save this key - it won't be shown again!")
    
    return {
        'bind': bind,
        'ssl': ssl_config,
        'admin_username': admin_username,
        'admin_password': admin_password,
        'api_key': api_key if 'api_key' in locals() else None
    }
```

## Network Configuration

### Database Remote Access
```python
class DatabaseNetworkConfig:
    def configure_for_server(self):
        """Configure PostgreSQL for network access"""
        
        click.echo("\n📝 Configuring PostgreSQL for network access...")
        
        # Find PostgreSQL config directory
        pg_config_dir = self.find_pg_config_dir()
        
        # Backup existing configs
        self.backup_configs(pg_config_dir)
        
        # Update postgresql.conf
        postgresql_conf = pg_config_dir / 'postgresql.conf'
        with open(postgresql_conf, 'a') as f:
            f.write("\n# GiljoAI MCP Server Configuration\n")
            f.write(f"listen_addresses = '{self.config['bind']}'\n")
            f.write("max_connections = 50\n")
        
        # Update pg_hba.conf for LAN access
        pg_hba = pg_config_dir / 'pg_hba.conf'
        with open(pg_hba, 'a') as f:
            f.write("\n# GiljoAI MCP Network Access\n")
            f.write("# Allow LAN connections (adjust subnet as needed)\n")
            f.write("host    giljo_mcp    giljo_user    192.168.0.0/16    md5\n")
            f.write("host    giljo_mcp    giljo_user    10.0.0.0/8        md5\n")
            
            if self.config.get('ssl', {}).get('type'):
                f.write("# SSL connections\n")
                f.write("hostssl giljo_mcp    giljo_user    0.0.0.0/0         md5\n")
        
        # Restart PostgreSQL
        if click.confirm("Restart PostgreSQL to apply changes?"):
            self.restart_postgresql()
        else:
            click.echo("⚠️  Remember to restart PostgreSQL manually!")
```

### SSL Configuration
```python
def setup_ssl(config):
    """Configure SSL/TLS for server mode"""
    
    ssl_dir = Path("certs")
    ssl_dir.mkdir(exist_ok=True)
    
    if config['ssl']['type'] == 'self-signed':
        click.echo("\n🔐 Generating self-signed certificate...")
        
        # Generate using OpenSSL or Python cryptography
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        
        # Generate key
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # Generate certificate
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "GiljoAI MCP"),
            x509.NameAttribute(NameOID.COMMON_NAME, config.get('hostname', 'localhost')),
        ])
        
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)
        ).sign(key, hashes.SHA256())
        
        # Save files
        cert_path = ssl_dir / "server.crt"
        key_path = ssl_dir / "server.key"
        
        with open(cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(key_path, "wb") as f:
            f.write(key.private_key_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.TraditionalOpenSSL,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        click.echo(f"  ✅ Certificate: {cert_path}")
        click.echo(f"  ✅ Private key: {key_path}")
        
        return str(cert_path), str(key_path)
    
    else:
        # Use existing certificates
        return config['ssl']['cert'], config['ssl']['key']
```

### Firewall Helper Scripts
```python
def generate_firewall_rules(config):
    """Generate firewall rules for manual application"""
    
    ports = {
        'API': config['api_port'],
        'WebSocket': config['ws_port'],
        'Dashboard': config['dashboard_port'],
        'PostgreSQL': 5432
    }
    
    click.echo("\n🔥 Firewall Configuration Required")
    click.echo("=" * 60)
    
    if platform.system() == "Windows":
        click.echo("\nWindows Firewall (run as Administrator):")
        for name, port in ports.items():
            click.echo(f"""
netsh advfirewall firewall add rule ^
  name="GiljoAI MCP {name}" ^
  dir=in action=allow ^
  protocol=TCP localport={port}
""")
    
    elif platform.system() == "Linux":
        click.echo("\nLinux (UFW):")
        for name, port in ports.items():
            click.echo(f"sudo ufw allow {port}/tcp comment 'GiljoAI MCP {name}'")
        
        click.echo("\nLinux (iptables alternative):")
        for name, port in ports.items():
            click.echo(f"sudo iptables -A INPUT -p tcp --dport {port} -j ACCEPT")
    
    elif platform.system() == "Darwin":
        click.echo("\nmacOS (pfctl):")
        click.echo("Add to /etc/pf.conf:")
        for name, port in ports.items():
            click.echo(f"pass in proto tcp from any to any port {port}  # GiljoAI MCP {name}")
        click.echo("\nThen reload: sudo pfctl -f /etc/pf.conf")
    
    # Save to file for reference
    rules_file = Path("firewall_rules.txt")
    with open(rules_file, 'w') as f:
        f.write(f"# Firewall rules for GiljoAI MCP\n")
        f.write(f"# Generated: {datetime.now()}\n\n")
        for name, port in ports.items():
            f.write(f"{name}: {port}\n")
    
    click.echo(f"\n📝 Rules saved to: {rules_file}")
```

## Security Implementation

### Admin User Creation
```python
def create_admin_user(config):
    """Create administrative user account"""
    
    from werkzeug.security import generate_password_hash
    
    admin_data = {
        'username': config['admin_username'],
        'password_hash': generate_password_hash(config['admin_password']),
        'role': 'admin',
        'created_at': datetime.now(),
        'api_key': config.get('api_key')
    }
    
    # Store in database
    conn = get_db_connection()
    cur = conn.cursor()
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            username VARCHAR(50) UNIQUE NOT NULL,
            password_hash VARCHAR(255) NOT NULL,
            role VARCHAR(20) NOT NULL,
            api_key VARCHAR(100),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cur.execute("""
        INSERT INTO users (username, password_hash, role, api_key)
        VALUES (%s, %s, %s, %s)
    """, (admin_data['username'], admin_data['password_hash'],
          admin_data['role'], admin_data['api_key']))
    
    conn.commit()
    click.echo(f"✅ Admin user '{config['admin_username']}' created")
```

### API Key Generation
```python
def generate_api_key():
    """Generate secure API key"""
    import secrets
    return f"gai_{secrets.token_urlsafe(32)}"

def setup_api_authentication(config):
    """Configure API key authentication"""
    
    if config.get('api_key'):
        # Add to environment
        with open('.env', 'a') as f:
            f.write(f"\n# API Authentication\n")
            f.write(f"API_KEY={config['api_key']}\n")
            f.write(f"REQUIRE_API_KEY=true\n")
        
        click.echo("✅ API key authentication configured")
```

## Enhanced Configuration

### Server Mode config.yaml
```python
def generate_server_config(config):
    """Generate config.yaml for server mode"""
    
    yaml_config = {
        'installation': {
            'version': '1.0.0',
            'mode': 'server',
            'timestamp': datetime.now().isoformat()
        },
        'network': {
            'bind': config['bind'],
            'ssl_enabled': bool(config.get('ssl')),
            'ssl_cert': config.get('ssl', {}).get('cert'),
            'ssl_key': config.get('ssl', {}).get('key')
        },
        'security': {
            'admin_user': config['admin_username'],
            'api_key_required': bool(config.get('api_key')),
            'rate_limiting': {
                'enabled': True,
                'requests_per_minute': 60
            }
        },
        'database': {
            'host': config['pg_host'],
            'port': config['pg_port'],
            'name': 'giljo_mcp',
            'remote_access': True,
            'max_connections': 50
        },
        'services': {
            'bind': config['bind'],
            'api_port': config['api_port'],
            'websocket_port': config['ws_port'],
            'dashboard_port': config['dashboard_port']
        }
    }
    
    with open('config.yaml', 'w') as f:
        yaml.dump(yaml_config, f, default_flow_style=False)
```

## Cross-Platform Launchers

### Enhanced Unix Launcher
```bash
#!/bin/bash
# start_giljo.sh - Server mode aware launcher

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Load configuration
source .env

# Determine mode from config
MODE=$(grep "mode:" config.yaml | cut -d' ' -f2)

echo "============================================"
echo "   GiljoAI MCP - $MODE Mode"
echo "============================================"

# Check if already running
if pgrep -f "giljo_mcp" > /dev/null; then
    echo "GiljoAI MCP is already running!"
    exit 1
fi

# Network binding warning
if [ "$MODE" = "server" ]; then
    echo "⚠️  Server mode - accessible over network"
    BIND=$(grep "bind:" config.yaml | head -1 | cut -d' ' -f2)
    echo "   Binding to: $BIND"
    
    if grep -q "ssl_enabled: false" config.yaml; then
        echo "   ⚠️  SSL disabled - not recommended for production!"
    fi
fi

# Start services
echo "Starting services..."

# Use SSL if configured
if grep -q "ssl_enabled: true" config.yaml; then
    SSL_ARGS="--ssl-certfile certs/server.crt --ssl-keyfile certs/server.key"
fi

# Start API with appropriate binding
python -m uvicorn giljo_mcp.api:app \
    --host $BIND \
    --port $API_PORT \
    $SSL_ARGS &

echo "============================================"
echo "   Services running!"
if [ "$MODE" = "server" ]; then
    echo "   Dashboard: https://$BIND:$DASHBOARD_PORT"
    echo "   API: https://$BIND:$API_PORT/docs"
else
    echo "   Dashboard: http://localhost:$DASHBOARD_PORT"
    echo "   API: http://localhost:$API_PORT/docs"
fi
echo "   Press Ctrl+C to stop"
echo "============================================"
```

## Testing Requirements

### Server Mode Tests
```python
def test_network_binding():
    """Test server binds to network interfaces"""
    
def test_ssl_configuration():
    """Test SSL setup and HTTPS connections"""
    
def test_admin_authentication():
    """Test admin user login"""
    
def test_api_key_auth():
    """Test API key authentication"""
    
def test_firewall_rules_generation():
    """Test firewall helper scripts"""
    
def test_remote_database_access():
    """Test PostgreSQL network connectivity"""
```

## Success Criteria

### Functional
- ✅ Localhost mode unaffected
- ✅ Server mode network accessible
- ✅ SSL/TLS optional but encouraged
- ✅ Admin user creation
- ✅ API key authentication
- ✅ Firewall rules generated
- ✅ Remote database access

### Security
- ✅ Explicit consent for network exposure
- ✅ SSL warnings when disabled
- ✅ Secure password storage
- ✅ API key generation
- ✅ Rate limiting ready

### User Experience
- ✅ Clear security warnings
- ✅ Simple SSL setup
- ✅ Helpful firewall guidance
- ✅ Same CLI simplicity

## Deliverables

- Enhanced `install.py` with server options
- `installer/core/network.py` - Network configuration
- `installer/core/security.py` - SSL and auth setup
- Firewall helper script generation
- Cross-platform launcher enhancements
- Server mode test suite

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