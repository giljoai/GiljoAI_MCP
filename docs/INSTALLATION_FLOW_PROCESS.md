# Installation Flow & Process

**Document Version**: 10_21_2025
**Status**: Single Source of Truth
**Last Updated**: 2025-01-05 (Harmonized)
**Harmonization Status**: ✅ Aligned with codebase

---

## Quick Links to Harmonized Documents

- **[Simple_Vision.md](../handovers/Simple_Vision.md)** - User journey including installation workflow
- **[start_to_finish_agent_FLOW.md](../handovers/start_to_finish_agent_FLOW.md)** - Technical verification (Phase 1: Installation & Setup)

**Installation Key Points** (verified):
1. PostgreSQL database setup and table creation
2. **Single baseline migration** applied (Handover 0601) - Creates all 32 tables in <1 second
3. **First user creation** triggers automatic seeding of 6 default agent templates per tenant
4. API server configuration and launch

**Installation Sequence** (post-nuclear reset):
- Database created → Baseline migration applied (32 tables) → First user created → Templates seeded → API started
- **Fresh install time**: <1 second (vs 5+ minutes with old migration chain)
- See Migration Strategy (docs/architecture/migration-strategy.md) for complete details

**Agent Template Seeding**:
- Triggered by first user creation (auth.py:910)
- Seeds 6 default templates: orchestrator, implementer, tester, analyzer, reviewer, documenter
- Source: `template_seeder.py::_get_default_templates_v103()`

---

## Overview

GiljoAI MCP v3.0 uses a **unified cross-platform installer** (`install.py`) that handles the complete installation workflow across Windows, Linux, and macOS. Implemented in Handover 0035, this installer achieves 25.6% code reduction through intelligent platform abstraction while ensuring consistent behavior across all platforms.

### Installation Methods

**Unified Cross-Platform Installer** (v3.1.0+):
```bash
python install.py
```

**Single command works on all platforms:**
- Windows 10/11
- Linux (Ubuntu 22.04+, Fedora 40+, Debian 12+)
- macOS (13+, Intel and ARM)

**Platform auto-detection**: Automatically detects your OS and uses appropriate platform handlers from the Strategy pattern architecture.

**Headless Mode** (CI/CD):
```bash
python install.py --headless
```

### Key Features (Handovers 0034, 0035)

**Security Enhancements**:
- No default admin/admin credentials (Handover 0034)
- First admin account created during /welcome setup wizard
- Recovery PIN system for password reset (Handover 0023)
- Default password "GiljoMCP" only used for admin-initiated user resets

**Cross-Platform Excellence**:
- Single unified codebase with platform handlers
- Automatic pg_trgm extension installation on ALL platforms
- 25.6% code reduction vs. previous dual-installer approach
- Strategy pattern for extensible platform support

---

## Installation Architecture

### Unified Installation Process (Handover 0035)

**Architecture**: Strategy Pattern with Platform Handlers

The installer uses a unified orchestrator (`install.py`) with platform-specific handlers:

```
F:\GiljoAI_MCP/
├── install.py                     # Unified orchestrator (400 lines)
└── installer/
    ├── core/                      # Platform-agnostic modules
    │   ├── database.py           # Unified DB installer
    │   └── config.py             # Unified config generator
    ├── platforms/                 # Platform-specific handlers
    │   ├── __init__.py           # Auto-detection logic
    │   ├── base.py               # Abstract interface
    │   ├── windows.py            # Windows handler
    │   ├── linux.py              # Linux handler
    │   └── macos.py              # macOS handler
    └── shared/                    # Shared utilities
        ├── postgres.py           # PostgreSQL discovery
        └── network.py            # Network utilities
```

**Code Reduction**: 3,350 total lines (25.6% reduction from previous 4,500+ lines across dual installers)

The installer follows a 9-step process:

1. **Welcome Screen** - Yellow branding and version display
2. **Python Version Check** - Requires Python 3.10+
3. **PostgreSQL Discovery** - Cross-platform detection with version validation
4. **Dependency Installation** - Virtual environment + requirements
5. **Configuration Generation** - .env + config.yaml (v3.0 format)
6. **Database Setup** - Database creation, roles, tables, pg_trgm extension
7. **Migration Execution** - Alembic migrations for constraints and backfills (v3.0+)
8. **Service Launch** - API + Frontend startup
9. **Browser Launch** - Opens http://localhost:7274/welcome for first admin setup

### Cross-Platform Compatibility

**Fully Supported Platforms** (v3.1.0+):
- **Windows 10/11** - Fully tested, desktop shortcuts (.lnk)
- **Linux** (Ubuntu 22.04+, Fedora 40+, Debian 12+) - Fully tested, desktop launchers (.desktop)
- **macOS** (13+, Intel and ARM) - Fully tested, Homebrew support

**Platform Handler Architecture** (Strategy Pattern):
- `installer/platforms/base.py` - Abstract `PlatformHandler` interface
- `installer/platforms/windows.py` - Windows-specific operations
- `installer/platforms/linux.py` - Linux-specific operations
- `installer/platforms/macos.py` - macOS-specific operations
- `installer/platforms/__init__.py` - Auto-detection via `platform.system()`

**Benefits of Unified Architecture**:
- Bug fixes apply to ALL platforms automatically
- Feature implementations stay synchronized across platforms
- 25.6% less code to maintain
- Extensible for future platforms (Docker, WSL, etc.)

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
- **pg_trgm extension** (automatically installed by unified installer)

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

**PostgreSQL Extension Creation** (CRITICAL - Handover 0035):
```python
def create_postgresql_extensions():
    """
    Create required PostgreSQL extensions
    CRITICAL: pg_trgm extension required for full-text search

    Handover 0035: Unified installer ensures pg_trgm is created on ALL platforms
    Previous Issue: Linux installer was missing this critical extension
    """
    print("🔧 Creating PostgreSQL extensions...")

    # Create pg_trgm extension for full-text search (Handover 0017)
    cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    print("✅ Extension pg_trgm created successfully")
```

**Why pg_trgm is Critical**:
- Enables full-text search capabilities
- Required for MCPContextIndex searchable_vector column
- Must be created with superuser privileges
- Automatically created on ALL platforms (Windows, Linux, macOS) via unified installer
- Previous bug: Missing in old Linux installer (fixed in Handover 0035)

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

**Alembic Migration Execution** (v3.1+ Nuclear Reset - Handover 0601):
```python
def run_database_migrations():
    """
    Run Alembic baseline migration on fresh install

    Post-Nuclear Reset (Handover 0601):
    - ONE pristine baseline migration (f504ea46e988)
    - Creates ALL 32 tables in single transaction (<1 second)
    - Generated from SQLAlchemy models (not manual)
    - Includes pg_trgm extension
    - Zero chicken-and-egg conflicts
    """
    print("🔄 Running database migrations (alembic upgrade head)...")

    # Execute Alembic migrations
    import subprocess
    import sys

    proc = subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        capture_output=True,
        text=True,
        timeout=120  # 2 minute timeout
    )

    if proc.returncode == 0:
        print("✅ Database migrations completed successfully")
        print("ℹ️  Baseline migration creates 32 tables in <1 second")
    else:
        print(f"❌ Database migration failed: {proc.stderr}")
        raise RuntimeError("Migration failed")
```

**Migration Execution Flow** (Post-Nuclear Reset):
1. **Create database and roles** - Database creation, user creation, privileges
2. **Run baseline migration** - `alembic upgrade head` creates ALL 32 tables (f504ea46e988)
3. **Seed templates** - Insert default agent templates (post-migration)

**Baseline Migration** (f504ea46e988):
- **Tables Created**: 32 (31 data tables + alembic_version)
- **Duration**: <1 second (vs 5+ minutes with old 44-migration chain)
- **pg_trgm Extension**: Automatically installed
- **Source**: Generated from current SQLAlchemy models
- **Status**: Production-ready, zero conflicts

**Benefits of Nuclear Reset**:
- **Simple**: Single atomic operation (no migration chain complexity)
- **Fast**: Fresh installs complete in <1 second
- **Reliable**: Zero chicken-and-egg dependency conflicts
- **Clean**: Pristine foundation for future incremental migrations

**Template Seeding** (Handover 0041):
```python
async def seed_default_templates():
    """
    Seed default agent templates for tenant during installation

    Handover 0041: Database-backed template management
    6 default templates seeded per tenant (orchestrator, analyzer, implementer, tester, reviewer, documenter)
    """
    print("🎯 Seeding default agent templates...")

    from src.giljo_mcp.template_seeder import seed_tenant_templates
    from src.giljo_mcp.database import DatabaseManager

    db_manager = DatabaseManager(database_url, is_async=True)
    async with db_manager.get_session_async() as session:
        template_count = await seed_tenant_templates(session, tenant_key='default')
        if template_count > 0:
            print(f"✅ Seeded {template_count} default agent templates")
        else:
            print("ℹ️  Templates already seeded for this tenant")
```

**Templates Seeded**:
- **orchestrator** - Project coordination and delegation
- **analyzer** - Requirements analysis and architecture design
- **implementer** - Code implementation and feature development
- **tester** - Test creation and quality assurance
- **reviewer** - Code review and security validation
- **documenter** - Documentation creation and maintenance

**Key Features**:
- Idempotent seeding (safe to run multiple times)
- Non-blocking (installation continues if seeding fails)
- Multi-tenant isolation (templates scoped to tenant_key)
- Complete metadata (behavioral rules, success criteria, variables)
- Performance: <2 seconds to seed 6 templates

**Fresh Install Detection** (Handover 0034):
```python
async def initialize_setup_state():
    """
    Initialize SetupState for fresh installation

    Handover 0034: NO default credentials created
    Fresh install detection: User count = 0
    First admin account created via /welcome → /first-login flow
    """
    print("📋 Initializing setup state...")

    from src.giljo_mcp.database import DatabaseManager
    from src.giljo_mcp.models import SetupState
    from datetime import datetime
    import os

    database_url = os.getenv('DATABASE_URL')
    db_manager = DatabaseManager(database_url, is_async=True)

    async with db_manager.get_session_async() as session:
        # Create setup state for fresh installation
        setup_state = SetupState(
            tenant_key='default',
            database_initialized=True,
            database_initialized_at=datetime.utcnow(),
            first_admin_created=False,          # ← Detected via user count = 0
            setup_completed=False,
            setup_version='3.0.0'
        )
        session.add(setup_state)
        await session.commit()

    print("✅ Setup state initialized")
    print("ℹ️  Fresh install will be detected by router (user count = 0)")
```

**Fresh Install Flow** (Current Architecture):
1. **install.py** completes → User count = 0
2. **Browser opens** → `http://localhost:7274`
3. **Router guard checks** → User count via `/api/auth/user-count`
4. **Redirect to** → `/welcome` (if count = 0)
5. **User creates admin** → `/first-login` endpoint
6. **System updates** → User count > 0, router allows dashboard access

**Security Features**:
- No default credentials (admin/admin eliminated in Handover 0034)
- Fresh install detection via user count (not config flags)
- `/api/auth/create-first-admin` endpoint with race condition protection
- Two-layer security gate (frontend router + backend validation)
- Automatic endpoint disablement after first user creation

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
        '--host', bind_address,  # From install config: 127.0.0.1 (localhost) or 0.0.0.0 (LAN/WAN)
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

**Browser Launch** (to Dashboard Root):
```python
def launch_browser():
    """
    Launch browser to root URL for fresh install detection

    Fresh install flow:
    1. Browser opens to http://localhost:7274/
    2. Router checks user count via /api/auth/user-count
    3. If count = 0: Auto-redirect to /welcome
    4. User clicks through to /first-login
    5. Creates admin account with username, password, recovery PIN
    """
    print("🌐 Opening web browser...")

    url = f"http://localhost:{DEFAULT_FRONTEND_PORT}"

    try:
        import webbrowser
        webbrowser.open(url)
        print(f"✅ Browser opened: {url}")
        print("ℹ️  Fresh install will redirect to /welcome → /first-login")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print(f"📋 Manual access: {url}")
```

**Installation Summary** (Handover 0034, 0035):
```python
def display_installation_summary():
    print("\n" + "=" * 70)
    print("🎉 GiljoAI MCP v3.0 Installation Complete!")
    print("=" * 70)

    print(f"""
📍 Installation Directory: {Path.cwd()}
🗄️  Database: PostgreSQL 18 (giljo_mcp) with pg_trgm extension
🔐 Fresh Install: Will auto-redirect to /welcome (user count = 0)

⚠️  IMPORTANT NEXT STEPS:
   1. Browser redirects to /welcome → /first-login
   2. Create first admin account (username, password, recovery PIN)
   3. Login and access dashboard
   4. Configure AI coding agents via Avatar → My Settings → API & Integrations
   5. Configure firewall if needed for network access

🔒 Security Features:
   - No default credentials (admin/admin eliminated)
   - Fresh install detection via user count (not config flags)
   - Recovery PIN system for password reset (Handover 0023)
   - Two-layer security gate (router + backend validation)

📚 Documentation:
   - docs/README_FIRST.md - Start here
   - docs/FIRST_LAUNCH_EXPERIENCE.md - Complete onboarding guide

🛠️  Service Management:
   Start: python startup.py
   Stop:  Ctrl+C in terminal

Happy orchestrating! 🤖
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

### Platform Handler System (Handover 0035)

GiljoAI MCP v3.1.0+ uses a **unified installer with platform handlers** - a single codebase that intelligently adapts to your operating system.

**Architecture**:
- `installer/platforms/base.py` - Abstract `PlatformHandler` interface
- `installer/platforms/__init__.py` - Auto-detects OS and returns appropriate handler
- Platform-specific code isolated in handler classes

**Platform Detection**:
```python
import platform
os_name = platform.system()  # 'Windows', 'Linux', 'Darwin'

# Auto-select handler
if os_name == 'Windows':
    handler = WindowsPlatformHandler()
elif os_name == 'Linux':
    handler = LinuxPlatformHandler()
elif os_name == 'Darwin':
    handler = MacOSPlatformHandler()
```

### Platform-Specific Details (v3.1.0+)

**Windows:**
- PostgreSQL detection: `C:\Program Files\PostgreSQL\18\bin\psql.exe`
- Virtual environment: `venv\Scripts\python.exe`
- Desktop shortcuts: `.lnk` files created automatically via `win32com.client`
- npm execution: Requires `shell=True` for subprocess calls
- Platform handler: `installer/platforms/windows.py`

**Linux:**
- PostgreSQL detection: `/usr/lib/postgresql/18/bin/psql` or `/usr/bin/psql`
- Virtual environment: `venv/bin/python`
- Desktop shortcuts: `.desktop` files created and marked trusted automatically
- Distribution-specific: Ubuntu, Fedora, Debian detection for installation guides
- Platform handler: `installer/platforms/linux.py`

**macOS:**
- PostgreSQL detection:
  - Homebrew ARM: `/opt/homebrew/opt/postgresql@18/bin/psql`
  - Homebrew Intel: `/usr/local/opt/postgresql@18/bin/psql`
  - Postgres.app: `/Applications/Postgres.app/Contents/Versions/*/bin/psql`
- Virtual environment: `venv/bin/python`
- Desktop shortcuts: Not yet supported (future: .app bundles)
- Platform handler: `installer/platforms/macos.py`

**Benefits of Unified Approach** (vs. Old Dual Installers):
- Bug fixes (like pg_trgm) apply to ALL platforms automatically
- Handover implementations (0034, 0023) synchronized across all platforms
- 25.6% code reduction (3,350 lines vs. 4,500+)
- Extensible for future platforms (Docker, WSL, BSD, etc.)

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

# Verify version
python --version  # Should be 3.10+
```

**Issue: PostgreSQL not found**
```bash
# Check if PostgreSQL is installed
which psql
psql --version

# If not found, install PostgreSQL 18
# Windows: https://www.postgresql.org/download/windows/
# Linux: sudo apt install postgresql-18
# macOS: brew install postgresql@18

# Unified installer will auto-detect PostgreSQL across all platforms
```

**Issue: pg_trgm extension creation fails** (Handover 0035)
```bash
# Symptom: "ERROR: permission denied to create extension pg_trgm"
# Solution: Run installer with PostgreSQL superuser password

# The unified installer automatically creates pg_trgm extension
# Ensure you provide correct postgres user password during installation

# Manual verification after install:
psql -U postgres -d giljo_mcp -c "SELECT * FROM pg_extension WHERE extname = 'pg_trgm';"
```

**Issue: npm install failed / Frontend dependencies missing**
```bash
# Symptom: Vite error "Failed to resolve import 'lodash-es'" or similar
# Cause: npm install failed during installation (network timeout, disk space, firewall)

# The installer now retries npm install 3 times with exponential backoff
# If all retries fail, installation stops with troubleshooting steps

# Manual fix after failed installation:
cd frontend/
rm -rf node_modules package-lock.json
npm cache verify
npm install --verbose

# Common causes:
# 1. Network connectivity - test with:
curl https://registry.npmjs.org/

# 2. Disk space - need ~500MB for node_modules:
df -h  # Linux/macOS
dir    # Windows

# 3. Proxy/firewall blocking npm registry:
npm config get proxy
npm config get https-proxy
# If behind corporate proxy, configure:
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080

# 4. npm cache corruption:
npm cache clean --force
npm install
```

---

## npm Installation Architecture (v3.1)

**Overview**: The installer uses a production-grade npm installation system with intelligent fallback strategy, pre-flight health checks, and comprehensive retry logic.

### Smart Installation Strategy

The installer automatically chooses the optimal npm command:

1. **npm ci** (first attempt) - Reproducible builds using package-lock.json
2. **npm install** (fallback) - If lockfile missing or npm ci fails
3. **Automatic retry** - 3 attempts with exponential backoff (2s, 4s, 8s)
4. **Cache clearing** - On final retry to resolve corruption issues

```bash
# Installation flow
npm ci                    # Attempt 1 (if package-lock.json exists)
  -> fails
npm install               # Attempt 2 (automatic fallback)
  -> fails
npm cache clean --force   # Clear cache
npm install               # Attempt 3 (final attempt)
```

### Pre-Flight Health Checks

Before attempting installation, the system validates:

1. **npm registry accessibility** - Tests connection to registry.npmjs.org
2. **Disk space** - Ensures minimum 500MB available for node_modules
3. **package-lock.json presence** - Warns if missing (affects reproducibility)

```bash
# Pre-flight checks automatically run during installation
# Checks logged to: logs/install_npm.log
```

### Two-Tier Verification

Installation success is verified using two independent checks:

1. **Folder check** - Ensures node_modules directory exists
2. **Dependency check** - Validates critical packages are present (vue, vuetify, lodash-es, etc.)

This prevents false positives from incomplete installations.

### Retry and Recovery Logic

**Retry Strategy**:
- 3 maximum attempts per installation
- Exponential backoff: 2s, 4s, 8s between attempts
- Automatic fallback from npm ci to npm install
- Cache clearing on final retry

**Recovery Actions**:
- Automatic: Switches to npm install if npm ci fails
- Automatic: Clears npm cache before final attempt
- Manual: User intervention required if all retries fail

### Diagnostic Logging

All npm operations are logged to: `logs/install_npm.log`

**Log contents**:
- Timestamp for each attempt
- Command executed (npm ci vs npm install)
- Full stdout and stderr output
- Pre-flight check results
- Verification results

```bash
# View npm installation logs
cat logs/install_npm.log           # Linux/macOS
type logs\install_npm.log          # Windows

# Logs include:
# - Pre-flight health check results
# - Each retry attempt with timestamps
# - Full npm command output
# - Verification status
```

### Troubleshooting npm ci Specific Issues

**npm ci fails with "lockfile mismatch"**:
```bash
# The installer automatically falls back to npm install
# No manual action needed - fallback is automatic

# If you want to fix lockfile manually:
cd frontend/
rm package-lock.json
npm install                  # Regenerates lockfile
```

**npm ci fails with "registry error"**:
```bash
# Pre-flight checks will detect this before attempting npm ci
# Check logs/install_npm.log for detailed error message

# Manual verification:
npm ping                     # Test npm registry connection
curl https://registry.npmjs.org/  # Test network connectivity
```

**All retries fail**:
```bash
# Installer stops with troubleshooting instructions
# Check logs/install_npm.log for detailed diagnostics

# Common issues and fixes:
# 1. Corporate proxy/firewall
npm config set proxy http://proxy.company.com:8080
npm config set https-proxy http://proxy.company.com:8080

# 2. Corrupted npm cache
npm cache clean --force
npm cache verify

# 3. Insufficient disk space
df -h                        # Linux/macOS - check available space
dir                          # Windows - check available space
# Need minimum 500MB for node_modules

# 4. Network connectivity
ping registry.npmjs.org      # Test basic connectivity
npm ping                     # Test npm registry access
```

### Architecture Benefits

**Reliability**:
- Pre-flight checks catch issues before installation
- Automatic retry with exponential backoff
- Smart fallback from npm ci to npm install
- Two-tier verification prevents false positives

**Observability**:
- Comprehensive logging to logs/install_npm.log
- Detailed error messages with troubleshooting steps
- Pre-flight check results visible during installation

**Cross-Platform**:
- Works on Windows, Linux, macOS
- Platform-specific command execution handled automatically
- Consistent behavior across all platforms

**Related Documentation**: See Handover 0082 for implementation details

---

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

**Issue: Can't access /welcome page** (Handover 0034)
```bash
# Symptom: Browser redirects to /login instead of /welcome
# Cause: Database already has users (not a fresh install)

# Check user count:
psql -U postgres -d giljo_mcp -c "SELECT COUNT(*) FROM users;"

# For fresh install (0 users), router should redirect to /welcome
# For existing install (>0 users), router should redirect to /login

# If you need to reset to fresh install:
psql -U postgres -d giljo_mcp -c "DELETE FROM users; UPDATE setup_state SET first_admin_created = false, first_admin_created_at = NULL;"
```

**Issue: Forgot recovery PIN** (Handover 0023)
```bash
# Option 1: Admin password reset (if multi-user)
# Admin can reset your password via Users management
# New password will be "GiljoMCP" (must change on next login)
# Recovery PIN remains unchanged

# Option 2: Database reset (single-user/self-hosting)
psql -U postgres -d giljo_mcp
UPDATE users SET recovery_pin_hash = NULL WHERE username = 'your_username';
# User must set new recovery PIN on next login
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
sc query postgresql-x64-18  # Windows

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

### First Launch Checklist (Handover 0034)

After successful installation, the browser opens to the /welcome page:

1. **Create First Admin Account** (http://localhost:7274/welcome):
   - Enter admin username (your choice)
   - Enter secure password (12+ characters, uppercase, lowercase, digit, special character)
   - Confirm password
   - **Set 4-digit Recovery PIN** (Handover 0023) - Used for password reset
   - Confirm Recovery PIN

2. **Complete Setup Wizard**: 3-step setup (Welcome, MCP Config, Serena)

3. **Configure AI Coding Agent Integration**: Avatar → My Settings → API & Integrations
   - Set up Claude Code, CODEX, or Gemini integration
   - Generate Personal API Key for MCP-over-HTTP access

4. **Verify Installation**: Check all services are running via dashboard

5. **Configure Firewall** (Optional): If network access needed for LAN/WAN

6. **Connect Claude Code** (Optional): Set up MCP-over-HTTP integration

### Recovery PIN System (Handover 0023)

**Purpose**: Self-service password recovery without email infrastructure

**PIN Requirements**:
- **Format**: 4-digit numeric (0000-9999)
- **Storage**: Hashed with bcrypt (same security as passwords)
- **When Set**: During first admin creation, or on first login for admin-created users
- **Use Case**: Forgot password recovery via /forgot-password page

**Password Reset Flow**:
1. User clicks "Forgot Password?" on login page
2. Enter username and 4-digit recovery PIN
3. System validates username + PIN combination
4. User sets new password (meeting complexity requirements)
5. Recovery PIN remains unchanged

**Security Measures**:
- PIN hashing prevents plaintext storage
- Rate limiting: 5 failed attempts trigger 15-minute lockout
- Timing-safe PIN comparison prevents timing attacks
- Generic error messages prevent user enumeration
- Audit logging for all password reset operations

**Admin Password Reset** (Alternative):
- Admin users can reset other users' passwords via Users management
- Reset password becomes default: "GiljoMCP"
- User must change password on next login
- Recovery PIN remains unchanged

### Connecting Claude Code via MCP (Post-Install)

After completing the installation, you can connect Claude Code to GiljoAI MCP for zero-dependency agent orchestration:

**Step 1: Generate API Key**
1. Login to GiljoAI MCP dashboard (http://localhost:7274)
2. Click your avatar → "My Settings"
3. Navigate to "API and Integrations" tab
4. Click "Personal API Keys" → "Generate New API Key"
5. Name your key (e.g., "Claude Code Access")
6. Copy the API key (shown only once)

**Step 2: Configure Claude Code**
```bash
# Add GiljoAI MCP as an HTTP transport server
claude mcp add --transport http giljo-mcp http://localhost:7272/mcp \
  --header "X-API-Key: gk_YOUR_COPIED_API_KEY"

# For network access (replace with your server IP)
claude mcp add --transport http giljo-mcp http://10.1.0.164:7272/mcp \
  --header "X-API-Key: gk_YOUR_COPIED_API_KEY"
```

**Step 3: Verify Connection**
```bash
# Within Claude Code, check MCP status
> /mcp

# Should show "giljo-mcp" with "Connected" status
```

**Step 4: Start Using Tools**
```bash
# In Claude Code, ask for orchestration help
> "List all my projects"
> "Create a new project called 'Website Redesign' with mission 'Modernize company website'"
> "Show me all active agents"
```

**Complete MCP Documentation**: See [MCP-over-HTTP Integration](MCP_OVER_HTTP_INTEGRATION.md) for full details.

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

## Related Documentation

**Core Installation & Setup**:
- [First Launch Experience](FIRST_LAUNCH_EXPERIENCE.md) - Complete first-run walkthrough including /welcome setup
- [README_FIRST.md](README_FIRST.md) - Central navigation hub for all documentation

**Technical Architecture**:
- [Server Architecture & Tech Stack](SERVER_ARCHITECTURE_TECH_STACK.md) - v3.0 unified architecture details
- [User Structures & Tenants](USER_STRUCTURES_TENANTS.md) - Multi-tenant system design
- [GiljoAI MCP Purpose](GILJOAI_MCP_PURPOSE.md) - System overview and capabilities

**Recent Handovers Referenced**:
- **Handover 0035**: Unified Cross-Platform Installer (25.6% code reduction, pg_trgm fix)
- **Handover 0034**: Eliminate admin/admin, Clean First User Creation
- **Handover 0023**: Password Reset via Recovery PIN System

**MCP Integration**:
- [MCP-over-HTTP Integration](MCP_OVER_HTTP_INTEGRATION.md) - Connecting Claude Code via HTTP transport

---

*This document provides comprehensive installation procedures and troubleshooting guidance as the single source of truth. Last updated: October 21, 2025 to reflect Handovers 0023 (Recovery PIN), 0034 (First Admin Creation), and 0035 (Unified Installer).*