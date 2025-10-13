# Installation Flow & Process

**Document Version**: 10_13_2025
**Status**: Single Source of Truth
**Last Updated**: October 13, 2025

---

## Overview

GiljoAI MCP v3.0 uses a **unified installer** (`install.py`) that handles the complete installation workflow across Windows, Linux, and macOS. The installer replaces the deprecated `installer/cli/` system with a single Python script that manages dependencies, database setup, configuration generation, and service launching.

### Installation Methods

**Primary Method** (Recommended):
```bash
python install.py
```

**Platform-Specific Alternatives**:
```bash
# Windows
python install.py

# Linux  
python Linux_Installer/linux_install.py

# Cross-platform headless (CI/CD)
python install.py --headless
```

---

## Installation Architecture

### Unified Installation Process

**Code Reference**: `install.py:1-50` - Installation workflow overview

The installer follows an 8-step process:

1. **Welcome Screen** - Yellow branding and version display
2. **Python Version Check** - Requires Python 3.10+
3. **PostgreSQL Discovery** - Cross-platform detection  
4. **Dependency Installation** - Virtual environment + requirements
5. **Configuration Generation** - .env + config.yaml (v3.0 format)
6. **Database Setup** - Database creation, roles, tables
7. **Service Launch** - API + Frontend startup
8. **Browser Launch** - Opens http://localhost:7274

### Cross-Platform Compatibility

**Supported Platforms**:
- **Windows 10/11** - Primary development platform
- **Linux** (Ubuntu 20.04+, RHEL 8+, Debian 11+)
- **macOS** (10.15+)

**Code Reference**: `install.py:60-90` - UnifiedInstaller class initialization

---

## Installation Requirements

### System Prerequisites

**Python Requirements**:
- **Python 3.10+** (minimum) - Python 3.11+ recommended
- **pip** - Package installer for Python
- **venv** - Virtual environment support (usually bundled)

**Database Requirements**:
- **PostgreSQL 14+** (minimum)  
- **PostgreSQL 18** (recommended and tested)
- **psql** command-line client (for database setup)

**Network Requirements**:
- **Port 7272** available (API server)
- **Port 7274** available (Frontend server)  
- **Port 5432** available (PostgreSQL, if not already configured)

### Software Dependencies

**Python Packages** (from requirements.txt):
```python
# Core framework
fastapi>=0.104.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.7
uvicorn>=0.24.0

# Authentication & Security  
bcrypt>=4.0.0
python-jose[cryptography]>=3.3.0
python-multipart>=0.0.6

# Database management
alembic>=1.12.0

# Utilities
click>=8.1.0
colorama>=0.4.6
pyyaml>=6.0
python-dotenv>=1.0.0
```

**Frontend Dependencies** (from frontend/package.json):
```json
{
  "dependencies": {
    "vue": "^3.3.8",
    "vuetify": "^3.4.4", 
    "@vue/router": "^4.2.5",
    "pinia": "^2.1.7",
    "axios": "^1.6.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-vue": "^4.4.0"
  }
}
```

---

## Installation Workflow

### Step 1: Welcome & System Check

**Welcome Screen Display**:
```
╔══════════════════════════════════════════════════════════════════════╗
║                        GiljoAI MCP v3.0                             ║
║                    Unified Installation System                        ║  
║                                                                      ║
║  Multi-Agent Orchestration Platform for AI Development Teams        ║
╚══════════════════════════════════════════════════════════════════════╝
```

**System Validation**:
```python
# Python version check
def check_python_version():
    current_version = sys.version_info[:2]
    if current_version < MIN_PYTHON_VERSION:
        raise SystemError(
            f"Python {MIN_PYTHON_VERSION[0]}.{MIN_PYTHON_VERSION[1]}+ required. "
            f"Current: {current_version[0]}.{current_version[1]}"
        )
```

**Platform Detection**:
```python
# Cross-platform compatibility check
platform_name = platform.system()  # 'Windows', 'Linux', 'Darwin'
architecture = platform.machine()  # 'x86_64', 'arm64', etc.
```

### Step 2: PostgreSQL Discovery

**Cross-Platform PostgreSQL Detection**:

**Windows Detection**:
```python
def discover_postgresql_windows():
    # Check common installation paths
    paths = [
        "C:/Program Files/PostgreSQL/*/bin/psql.exe",
        "C:/PostgreSQL/*/bin/psql.exe", 
        "C:/Program Files (x86)/PostgreSQL/*/bin/psql.exe"
    ]
    
    # Check Windows services
    try:
        result = subprocess.run(['sc', 'query', 'postgresql*'], 
                              capture_output=True, text=True)
        # Parse service information
    except FileNotFoundError:
        pass
    
    return psql_path, version
```

**Linux/macOS Detection**:
```python
def discover_postgresql_unix():
    # Check package manager installations
    commands = [
        'which psql',           # Standard PATH lookup
        'dpkg -l postgresql*',  # Debian/Ubuntu  
        'rpm -qa postgresql*',  # RHEL/CentOS
        'brew list postgresql'  # macOS Homebrew
    ]
    
    for cmd in commands:
        try:
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            if result.returncode == 0:
                # Parse version and path
                return psql_path, version
        except:
            continue
    
    return None, None
```

**Version Validation**:
```python
def validate_postgresql_version(psql_path):
    try:
        result = subprocess.run([psql_path, '--version'], 
                              capture_output=True, text=True)
        # Parse: "psql (PostgreSQL) 18.0"
        version_str = result.stdout.split()[-1]
        major_version = int(version_str.split('.')[0])
        
        if major_version < MIN_POSTGRESQL_VERSION:
            print(f"⚠️  PostgreSQL {major_version} found. Minimum: {MIN_POSTGRESQL_VERSION}")
            print(f"📥 Download PostgreSQL 18: {POSTGRESQL_DOWNLOAD_URL}")
            return False
            
        return True
    except Exception as e:
        print(f"❌ Could not validate PostgreSQL version: {e}")
        return False
```

### Step 3: Virtual Environment Setup

**Virtual Environment Creation**:
```python
def setup_virtual_environment(install_dir: Path):
    venv_dir = install_dir / 'venv'
    
    print("🐍 Creating Python virtual environment...")
    
    # Create virtual environment
    subprocess.run([sys.executable, '-m', 'venv', str(venv_dir)], check=True)
    
    # Determine activation script path (cross-platform)
    if platform.system() == 'Windows':
        python_path = venv_dir / 'Scripts' / 'python.exe'
        pip_path = venv_dir / 'Scripts' / 'pip.exe'
    else:
        python_path = venv_dir / 'bin' / 'python'
        pip_path = venv_dir / 'bin' / 'pip'
    
    return python_path, pip_path
```

**Dependency Installation**:
```python
def install_dependencies(pip_path: Path, requirements_file: Path):
    print("📦 Installing Python dependencies...")
    
    # Upgrade pip first
    subprocess.run([str(pip_path), 'install', '--upgrade', 'pip'], check=True)
    
    # Install requirements
    subprocess.run([str(pip_path), 'install', '-r', str(requirements_file)], check=True)
    
    # Install additional development tools (optional)
    dev_packages = ['black', 'ruff', 'mypy', 'pytest']
    for package in dev_packages:
        try:
            subprocess.run([str(pip_path), 'install', package], 
                          check=True, capture_output=True)
        except subprocess.CalledProcessError:
            print(f"⚠️  Optional package {package} installation failed")
```

### Step 4: Configuration Generation

**Database Connection Setup**:
```python
def setup_database_connection():
    print("🔧 Setting up database connection...")
    
    # Prompt for PostgreSQL password
    while True:
        pg_password = click.prompt(
            "PostgreSQL password for 'postgres' user", 
            type=str, 
            hide_input=True
        )
        
        # Test connection
        if test_postgresql_connection('localhost', 5432, 'postgres', pg_password):
            break
        else:
            print("❌ Connection failed. Please try again.")
    
    return {
        'host': 'localhost',
        'port': 5432,
        'username': 'postgres', 
        'password': pg_password
    }
```

**Environment Configuration (.env)**:
```python
def generate_env_file(install_dir: Path, db_credentials: dict):
    env_file = install_dir / '.env'
    
    env_content = f"""# GiljoAI MCP v3.0 Environment Variables
# Generated on {time.strftime('%Y-%m-%d %H:%M:%S')}

# Database Configuration (PostgreSQL 18)
DATABASE_URL=postgresql://{db_credentials['username']}:{db_credentials['password']}@{db_credentials['host']}:{db_credentials['port']}/giljo_mcp

# Database Connection Details
DB_HOST={db_credentials['host']}
DB_PORT={db_credentials['port']}
DB_NAME=giljo_mcp
DB_USER=giljo_user
DB_PASSWORD={db_credentials['password']}

# JWT Secret (generated randomly)
JWT_SECRET={generate_jwt_secret()}

# Service Configuration
API_PORT={DEFAULT_API_PORT}
FRONTEND_PORT={DEFAULT_FRONTEND_PORT}

# CORS Origins (updated by installer based on network config)
CORS_ORIGINS=["http://127.0.0.1:{DEFAULT_FRONTEND_PORT}","http://localhost:{DEFAULT_FRONTEND_PORT}"]

# Installation Metadata
INSTALLATION_DATE={time.strftime('%Y-%m-%d')}
INSTALLATION_PLATFORM={platform.system()}
PYTHON_VERSION={sys.version_info.major}.{sys.version_info.minor}
"""
    
    with open(env_file, 'w') as f:
        f.write(env_content)
    
    print(f"✅ Environment configuration saved: {env_file}")
```

**YAML Configuration (config.yaml)**:
```python
def generate_config_yaml(install_dir: Path, settings: dict):
    config_file = install_dir / 'config.yaml'
    
    config_data = {
        'version': '3.0.0',
        'deployment_context': 'localhost',  # Informational only
        
        'installation': {
            'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S'),
            'platform': platform.system(),
            'install_dir': str(install_dir.absolute()),
            'version': '3.0.0'
        },
        
        'database': {
            'type': 'postgresql',
            'host': 'localhost',      # ALWAYS localhost in v3.0
            'port': 5432,
            'name': 'giljo_mcp',
            'user': 'giljo_user'
        },
        
        'services': {
            'api': {
                'host': '0.0.0.0',    # ALWAYS 0.0.0.0 in v3.0
                'port': settings.get('api_port', DEFAULT_API_PORT),
                'external_host': settings.get('external_host', 'localhost')
            },
            'frontend': {
                'port': settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)
            }
        },
        
        'features': {
            'authentication': True,         # ALWAYS enabled in v3.0
            'firewall_configured': False,   # Update after firewall setup
            'api_keys_enabled': False,      # Enable for network access
            'multi_user': False            # Enable for multi-user deployments
        },
        
        'security': {
            'cors': {
                'allowed_origins': [
                    f"http://127.0.0.1:{settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)}",
                    f"http://localhost:{settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)}"
                ]
            },
            'rate_limiting': {
                'enabled': True,
                'requests_per_minute': 60
            }
        }
    }
    
    import yaml
    with open(config_file, 'w') as f:
        yaml.dump(config_data, f, default_flow_style=False, sort_keys=False)
    
    print(f"✅ YAML configuration saved: {config_file}")
```

### Step 5: Database Initialization

**Database Creation**:
```python
def create_database(db_credentials: dict):
    print("🗄️  Creating GiljoAI MCP database...")
    
    # Create database using psql
    create_db_sql = """
    -- Create database
    CREATE DATABASE giljo_mcp 
        WITH ENCODING='UTF8' 
        LC_COLLATE='en_US.UTF-8' 
        LC_CTYPE='en_US.UTF-8'
        TEMPLATE=template0;
    
    -- Create application user
    CREATE USER giljo_user WITH ENCRYPTED PASSWORD '{}';
    
    -- Grant privileges
    GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_user;
    """.format(db_credentials['password'])
    
    # Execute SQL commands
    psql_cmd = [
        'psql', 
        f"postgresql://postgres:{db_credentials['password']}@localhost:5432/postgres",
        '-c', create_db_sql
    ]
    
    try:
        subprocess.run(psql_cmd, check=True, capture_output=True, text=True)
        print("✅ Database 'giljo_mcp' created successfully")
    except subprocess.CalledProcessError as e:
        if "already exists" in e.stderr:
            print("ℹ️  Database 'giljo_mcp' already exists")
        else:
            raise
```

**Table Creation via DatabaseManager**:
```python
async def create_database_tables():
    print("📋 Creating database tables...")
    
    # Import after environment is set up
    import os
    from src.giljo_mcp.database import DatabaseManager
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise ValueError("DATABASE_URL not found in environment")
    
    # Create database manager and tables
    db_manager = DatabaseManager(database_url, is_async=True)
    
    # Create all tables using Base.metadata.create_all()
    await db_manager.create_tables_async()
    
    print("✅ Database tables created successfully")
```

**Default Admin User Creation**:
```python
async def create_default_admin():
    print("👤 Creating default admin user...")
    
    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.models import User, SetupState
    from src.giljo_mcp.auth.password import hash_password
    import uuid
    import os
    
    database_url = os.getenv('DATABASE_URL')
    db_manager = DatabaseManager(database_url, is_async=True)
    
    async with db_manager.get_session_async() as session:
        # Create default admin user
        admin_user = User(
            id=str(uuid.uuid4()),
            tenant_key='default',
            username='admin',
            password_hash=hash_password('admin'),  # Default password
            role='admin',
            is_active=True,
            is_system_user=False
        )
        session.add(admin_user)
        
        # Create setup state with default password active
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            database_initialized_at=datetime.utcnow(),
            default_password_active=True,  # Forces password change
            setup_completed=False,
            setup_version='3.0.0'
        )
        session.add(setup_state)
        
        await session.commit()
    
    print("✅ Default admin user created (admin/admin)")
    print("⚠️  Password change required on first login")
```

### Step 6: Service Launch

**API Server Startup**:
```python
def start_api_server(install_dir: Path, venv_python: Path):
    print("🚀 Starting API server...")
    
    api_script = install_dir / 'api' / 'run_api.py'
    
    # Start API server in background
    api_cmd = [
        str(venv_python),
        str(api_script),
        '--host', '0.0.0.0',  # Always bind to all interfaces
        '--port', str(DEFAULT_API_PORT)
    ]
    
    api_process = subprocess.Popen(
        api_cmd,
        cwd=str(install_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for API to start
    print("⏳ Waiting for API server to start...")
    time.sleep(5)
    
    # Verify API is running
    if check_port_availability('localhost', DEFAULT_API_PORT):
        print(f"❌ API server failed to start on port {DEFAULT_API_PORT}")
        return None
    
    print(f"✅ API server started: http://localhost:{DEFAULT_API_PORT}")
    return api_process
```

**Frontend Server Startup**:
```python
def start_frontend_server(install_dir: Path):
    print("🎨 Starting frontend server...")
    
    frontend_dir = install_dir / 'frontend'
    
    # Install npm dependencies if needed
    package_json = frontend_dir / 'package.json'
    node_modules = frontend_dir / 'node_modules'
    
    if not node_modules.exists():
        print("📦 Installing frontend dependencies...")
        subprocess.run(['npm', 'install'], 
                      cwd=str(frontend_dir), check=True)
    
    # Start development server
    frontend_cmd = ['npm', 'run', 'dev', '--', '--port', str(DEFAULT_FRONTEND_PORT)]
    
    frontend_process = subprocess.Popen(
        frontend_cmd,
        cwd=str(frontend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Wait for frontend to start
    print("⏳ Waiting for frontend server to start...")
    time.sleep(8)
    
    # Verify frontend is running
    if check_port_availability('localhost', DEFAULT_FRONTEND_PORT):
        print(f"❌ Frontend server failed to start on port {DEFAULT_FRONTEND_PORT}")
        return None
        
    print(f"✅ Frontend server started: http://localhost:{DEFAULT_FRONTEND_PORT}")
    return frontend_process
```

### Step 7: Launch Validation

**System Health Check**:
```python
def validate_installation():
    print("🔍 Validating installation...")
    
    checks = []
    
    # API Health Check
    try:
        import requests
        response = requests.get(f'http://localhost:{DEFAULT_API_PORT}/health', timeout=5)
        if response.status_code == 200:
            checks.append(("API Server", "✅ Healthy"))
        else:
            checks.append(("API Server", f"⚠️  Status {response.status_code}"))
    except Exception as e:
        checks.append(("API Server", f"❌ {str(e)[:50]}"))
    
    # Database Connection Check
    try:
        import psycopg2
        database_url = os.getenv('DATABASE_URL')
        conn = psycopg2.connect(database_url)
        conn.close()
        checks.append(("Database", "✅ Connected"))
    except Exception as e:
        checks.append(("Database", f"❌ {str(e)[:50]}"))
    
    # Frontend Accessibility Check
    try:
        response = requests.get(f'http://localhost:{DEFAULT_FRONTEND_PORT}', timeout=5)
        if response.status_code == 200:
            checks.append(("Frontend", "✅ Accessible"))
        else:
            checks.append(("Frontend", f"⚠️  Status {response.status_code}"))
    except Exception as e:
        checks.append(("Frontend", f"❌ {str(e)[:50]}"))
    
    # Print validation results
    print("\n📊 Installation Validation:")
    print("=" * 40)
    for component, status in checks:
        print(f"{component:15} {status}")
    print("=" * 40)
    
    return all("✅" in status for _, status in checks)
```

### Step 8: Browser Launch & Completion

**Browser Launch**:
```python
def launch_browser():
    print("🌐 Opening web browser...")
    
    url = f"http://localhost:{DEFAULT_FRONTEND_PORT}"
    
    try:
        import webbrowser
        webbrowser.open(url)
        print(f"✅ Browser opened: {url}")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"📋 Manual access: {url}")
```

**Installation Summary**:
```python
def display_installation_summary(db_credentials: dict):
    print("\n" + "=" * 70)
    print("🎉 GiljoAI MCP v3.0 Installation Complete!")
    print("=" * 70)
    
    print(f"""
📍 Installation Directory: {Path.cwd()}
🗄️  Database: PostgreSQL (giljo_mcp)
🔐 Default Credentials: admin / admin

🌐 Access URLs:
   Dashboard: http://localhost:{DEFAULT_FRONTEND_PORT}
   API Docs:  http://localhost:{DEFAULT_API_PORT}/docs
   Health:    http://localhost:{DEFAULT_API_PORT}/health

⚠️  IMPORTANT FIRST STEPS:
   1. Change default password (admin/admin) - REQUIRED
   2. Complete setup wizard (MCP integration, Serena)
   3. Configure firewall if needed for network access
   
📚 Documentation:
   - docs/README_FIRST.md - Start here
   - docs/FIRST_LAUNCH_EXPERIENCE_10_13_2025.md - Next steps
   
🛠️  Service Management:
   Start: python startup.py
   Stop:  Ctrl+C in terminal
   
Happy orchestrating! 🤖✨
""")
    
    print("=" * 70)
```

---

## Command Line Options

### Interactive Installation (Default)

```bash
python install.py
```

**Interactive Prompts**:
- PostgreSQL password input
- Network configuration (localhost/LAN IP)
- Optional MCP integration setup
- Service startup confirmation

### Headless Installation (CI/CD)

```bash
python install.py --headless --pg-password "mypassword"
```

**Additional Headless Options**:
```bash
python install.py \
    --headless \
    --pg-password "secure_password" \
    --api-port 8000 \
    --frontend-port 8080 \
    --external-host "192.168.1.100"
```

### Advanced Installation Options

**Custom Installation Directory**:
```bash
python install.py --install-dir "/opt/giljoai-mcp"
```

**Skip Service Startup** (configuration only):
```bash
python install.py --no-start-services
```

**Development Mode** (additional tools):
```bash
python install.py --dev-tools
```

---

## Platform-Specific Considerations

### Windows Installation

**Prerequisites**:
- **PowerShell 5.1+** or **PowerShell 7+**
- **Visual Studio Build Tools** (for psycopg2 compilation)
- **PostgreSQL 18** from https://www.postgresql.org/download/windows/

**Firewall Configuration**:
```powershell
# Allow GiljoAI MCP through Windows Firewall (optional)
New-NetFirewallRule -DisplayName "GiljoAI MCP API" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7272

New-NetFirewallRule -DisplayName "GiljoAI MCP Frontend" `
    -Direction Inbound -Action Allow -Protocol TCP -LocalPort 7274
```

**Service Management**:
```batch
REM Start services
python startup.py

REM Alternative batch files
start_giljo.bat     REM Start all services
stop_giljo.bat      REM Stop all services  
```

### Linux Installation

**Prerequisites** (Ubuntu/Debian):
```bash
# Update package list
sudo apt update

# Install Python and PostgreSQL
sudo apt install python3.11 python3.11-venv python3-pip postgresql-18

# Install Node.js
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt install -y nodejs

# Install build tools (for psycopg2)
sudo apt install build-essential python3-dev libpq-dev
```

**Prerequisites** (RHEL/CentOS):
```bash
# Install Python and PostgreSQL
sudo dnf install python3.11 python3-pip postgresql18-server nodejs npm

# Install development tools
sudo dnf groupinstall "Development Tools"
sudo dnf install python3-devel postgresql-devel
```

**PostgreSQL Configuration**:
```bash
# Initialize PostgreSQL (if not already done)
sudo postgresql-setup --initdb

# Start and enable PostgreSQL
sudo systemctl start postgresql
sudo systemctl enable postgresql

# Set postgres user password
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'your_password';"
```

### macOS Installation

**Prerequisites** (Homebrew):
```bash
# Install Homebrew (if not already installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
brew install python@3.11 postgresql@18 node@18

# Start PostgreSQL
brew services start postgresql@18
```

**Path Configuration**:
```bash
# Add to ~/.zshrc or ~/.bash_profile
export PATH="/opt/homebrew/bin:$PATH"
export PATH="/opt/homebrew/opt/python@3.11/bin:$PATH"
export PATH="/opt/homebrew/opt/postgresql@18/bin:$PATH"
```

---

## Troubleshooting Installation

### Common Issues

**Issue: Python version too old**
```bash
# Solution: Install Python 3.11+
# Windows: Download from python.org
# Linux: sudo apt install python3.11
# macOS: brew install python@3.11
```

**Issue: PostgreSQL not found**
```bash
# Check if PostgreSQL is installed
which psql
psql --version

# If not found, install PostgreSQL
# Windows: https://www.postgresql.org/download/windows/
# Linux: sudo apt install postgresql-18
# macOS: brew install postgresql@18
```

**Issue: Port already in use**
```bash
# Check what's using the port
netstat -tulpn | grep :7272  # Linux
netstat -ano | findstr :7272  # Windows

# Kill process using port (if safe to do so)
# Linux: sudo kill -9 <PID>
# Windows: taskkill /PID <PID> /F

# Or use different ports
python install.py --api-port 8000 --frontend-port 8080
```

**Issue: Permission denied**
```bash
# Ensure proper file permissions
chmod +x install.py

# Or run with explicit python
python3.11 install.py
```

**Issue: Database connection refused**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql  # Linux
brew services list | grep postgresql  # macOS

# Check PostgreSQL is accepting connections
psql -h localhost -p 5432 -U postgres -c "SELECT 1;"
```

### Installation Logs

**Log Locations**:
```bash
# Installation logs (created during install)
./logs/installer.log

# API server logs (created after startup)  
./logs/api.log

# Database setup logs
./logs/database_setup.log
```

**Verbose Installation**:
```bash
# Run with verbose output
python install.py --verbose

# Or enable debug logging
export GILJO_LOG_LEVEL=DEBUG
python install.py
```

### Recovery Procedures

**Clean Installation Reset**:
```bash
# Remove virtual environment
rm -rf venv/

# Remove configuration files
rm -f .env config.yaml

# Drop database (if needed)
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# Re-run installation
python install.py
```

**Partial Installation Recovery**:
```bash
# Skip completed steps
python install.py --skip-venv --skip-database

# Only regenerate configuration
python install.py --config-only

# Only start services
python startup.py
```

---

## Post-Installation Steps

### First Launch Checklist

After successful installation:

1. **Access Application**: Visit http://localhost:7274
2. **Change Default Password**: Login with admin/admin, forced password change
3. **Complete Setup Wizard**: 3-step setup (MCP, Serena, Complete)
4. **Verify Installation**: Check all services are running
5. **Configure Firewall**: If network access needed

### Service Management

**Starting Services**:
```bash
# Recommended method
python startup.py

# Manual service startup
python api/run_api.py &
cd frontend && npm run dev &
```

**Stopping Services**:
```bash
# Ctrl+C in terminal where services are running
# Or kill processes by PID
```

**Service Status Check**:
```bash
# Check API health
curl http://localhost:7272/health

# Check frontend accessibility
curl http://localhost:7274
```

### Development Environment Setup

**IDE Configuration**:
```bash
# Activate virtual environment
source venv/bin/activate  # Linux/macOS
venv\Scripts\activate     # Windows

# Install development tools
pip install black ruff mypy pytest

# Configure IDE to use venv/bin/python (or venv\Scripts\python.exe)
```

**Git Configuration**:
```bash
# Initialize git (if not already done)
git init

# Configure gitignore (already provided)
# .env, config.yaml, venv/, node_modules/ are ignored

# Make initial commit
git add .
git commit -m "feat: Initial GiljoAI MCP v3.0 installation"
```

---

**See Also**:
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE_10_13_2025.md) - Detailed first-run walkthrough
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK_10_13_2025.md) - Technical architecture details
- [User Structures & Tenants](USER_STRUCTURES_TENANTS_10_13_2025.md) - Multi-tenant system understanding
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE_10_13_2025.md) - System overview and capabilities

---

*This document provides comprehensive installation procedures and troubleshooting guidance as the single source of truth for the October 13, 2025 documentation harmonization.*