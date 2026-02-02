# Fresh Install Requirements Analysis

**Document Purpose**: Comprehensive analysis of what `install.py` expects for a pristine/fresh installation.

**Date**: 2026-02-02
**Analyzer**: Installation Flow Agent
**Source**: `F:\GiljoAI_MCP\install.py` v3.2+

---

## Table of Contents

1. [Fresh Install Detection Logic](#fresh-install-detection-logic)
2. [Pre-Flight Checks](#pre-flight-checks)
3. [Files and Directories Created](#files-and-directories-created)
4. [Database Operations](#database-operations)
5. [Pristine State Requirements](#pristine-state-requirements)
6. [Hidden State Detection](#hidden-state-detection)
7. [Nuclear Reset Checklist](#nuclear-reset-checklist)

---

## Fresh Install Detection Logic

### Primary Detection Mechanism

**Location**: `install.py:296`

```python
is_fresh_install = not (self.install_dir / ".env").exists()
```

**Determination**:
- ✅ **Fresh Install**: `.env` file does NOT exist
- ⚠️ **Upgrade/Existing**: `.env` file EXISTS

**Secondary Indicators**:

1. **Alembic Version Table** (`install.py:1871-1874`):
   - Fresh install: `alembic_version` table does NOT exist
   - Existing: `alembic_version` table exists with version stamp

2. **Database Existence** (`installer/core/database.py:210-212`):
   - Checks: `SELECT 1 FROM pg_database WHERE datname = 'giljo_mcp'`
   - Fresh install: Database does NOT exist
   - Existing: Database exists (triggers warning but continues)

3. **PostgreSQL Roles** (`installer/core/database.py:214-219`):
   - Checks: `SELECT 1 FROM pg_roles WHERE rolname = 'giljo_owner'`
   - Checks: `SELECT 1 FROM pg_roles WHERE rolname = 'giljo_user'`
   - Fresh install: Roles do NOT exist
   - Existing: Roles exist (passwords updated)

---

## Pre-Flight Checks

### 1. Python Version Check (`install.py:523`)

```python
def check_python_version(self) -> bool:
    """Check if Python 3.10+ is available"""
```

**Requirements**:
- ✅ Python 3.10 or higher
- ❌ Python 3.9 or lower → Installation FAILS

### 2. PostgreSQL Discovery (`install.py:542-678`)

**Discovery Methods** (in order):
1. **PATH detection**: `shutil.which("psql")`
2. **Common paths**: Platform-specific searches
   - Windows: `C:\Program Files\PostgreSQL\{14-18}\bin\psql.exe`
   - Linux/macOS: `/usr/bin/psql`, `/usr/local/bin/psql`
3. **Custom path**: User-provided path via `--pg-bin` flag

**Version Requirements** (`installer/core/database.py:41-43`):
- Minimum: PostgreSQL 14
- Maximum: PostgreSQL 18 (tested)
- Recommended: PostgreSQL 18

**Connection Check** (`installer/core/database.py:1147-1156`):
- Socket connection to `localhost:5432`
- 5-second timeout
- DOES NOT validate credentials (connection test only)

### 3. NPM Pre-Flight Checks (`install.py:1257-1306`)

**Checks Performed**:
1. **npm registry access**: `npm ping --registry https://registry.npmjs.org`
2. **Disk space**: Minimum 500MB free
3. **package-lock.json**: Exists and valid JSON
4. **node_modules**: Check if previous install corrupted

**Warning Conditions** (non-blocking):
- Registry unreachable (offline install possible)
- Disk space between 500MB-1GB (low)

**Failure Conditions** (blocking):
- Disk space < 500MB
- package-lock.json invalid JSON

---

## Files and Directories Created

### Configuration Files

| File | Created By | Purpose | Gitignored |
|------|-----------|---------|-----------|
| `config.yaml` | `ConfigManager.generate_config_yaml()` | System configuration (ports, features, firewall) | ✅ YES |
| `.env` | `ConfigManager.generate_env_file()` | Secrets (DB passwords, JWT secret) | ✅ YES |
| `installer/credentials/db_credentials.txt` | `DatabaseInstaller.save_credentials()` | Database credentials backup | ✅ YES |

### Directory Structure Created

```
F:\GiljoAI_MCP/
├── venv/                          # Created by install_dependencies()
├── logs/                          # Created by ConfigManager
├── installer/                     # Pre-existing
│   ├── credentials/               # Created by DatabaseInstaller
│   └── scripts/                   # Created by fallback_setup() (if needed)
├── frontend/node_modules/         # Created by npm install
└── migrations/                    # Pre-existing (contains baseline migration)
```

### Files NOT Created (Must Pre-Exist)

- `alembic.ini` - **MUST EXIST** (`install.py:1832`)
- `migrations/` directory - **MUST EXIST** (`install.py:1839`)
- `migrations/versions/baseline_v32_unified.py` - **MUST EXIST**
- `requirements.txt` - **MUST EXIST** (`install.py:781`)
- `frontend/package.json` - **MUST EXIST**
- `frontend/package-lock.json` - **MUST EXIST**

---

## Database Operations

### 1. Database Creation (`installer/core/database.py:173-369`)

**Sequence**:

```sql
-- 1. Create roles (if not exist)
CREATE ROLE giljo_owner LOGIN PASSWORD '<generated_20_char>';
CREATE ROLE giljo_user LOGIN PASSWORD '<generated_20_char>';

-- 2. Create database (if not exist)
CREATE DATABASE giljo_mcp OWNER giljo_owner;

-- 3. Grant permissions
GRANT CONNECT ON DATABASE giljo_mcp TO giljo_user;
GRANT CREATE ON DATABASE giljo_mcp TO giljo_owner;

-- 4. Create extensions (Handover 0017)
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- 5. Schema permissions
GRANT USAGE, CREATE ON SCHEMA public TO giljo_owner;
GRANT ALL ON SCHEMA public TO giljo_user;

-- 6. Default privileges
ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO giljo_user;

ALTER DEFAULT PRIVILEGES FOR ROLE giljo_owner IN SCHEMA public
    GRANT USAGE, SELECT ON SEQUENCES TO giljo_user;
```

**Password Generation**:
- Length: 20 characters
- Character set: `[a-zA-Z0-9]` (no special characters)
- Method: `secrets.choice()` (cryptographically secure)

### 2. Table Creation (`install.py:1809-2016`)

**Method**: Alembic Migrations (NOT `create_all()`)

**Process**:
1. Load `.env` to get `DATABASE_URL`
2. Check if `alembic_version` table exists
3. If NOT exists → Fresh install → Run `alembic upgrade head`
4. If exists → Check version stamp → Run pending migrations only
5. Verify essential tables created:
   - `setup_state` (CRITICAL)
   - `users` (CRITICAL)
   - `products` (CRITICAL)
   - `product_memory_entries`
   - `agent_templates`

**Single Baseline Migration** (Handover 0601):
- File: `migrations/versions/baseline_v32_unified.py`
- Creates: 32 tables from pristine SQLAlchemy models
- Runtime: <1 second for fresh install
- Idempotent: Safe to run multiple times

### 3. Initial Data Seeding (`install.py:940-1007`)

**Setup State Record** (`install.py:960-987`):

```python
setup_state = SetupState(
    id=str(uuid4()),
    tenant_key=default_tenant_key,  # Generated per installation
    completed=False,                # Wizard not completed
    setup_version="3.2.0",
    created_at=datetime.now(timezone.utc),
    updated_at=datetime.now(timezone.utc),
)
```

**NO Admin User Created** (Handover 0034):
- Removed: Default `admin/admin` account
- First user: Created via `/welcome` → `/first-login` in web UI
- Authentication: ALWAYS enabled (no localhost auto-login)

---

## Pristine State Requirements

### Files That MUST NOT Exist for Fresh Install

| File/Directory | Detection Method | Impact if Exists |
|---------------|------------------|------------------|
| `.env` | `(install_dir / ".env").exists()` | Treated as upgrade, skips config generation |
| `config.yaml` | Checked in `ConfigManager` | Overwritten if exists |
| `venv/` | `self.venv_dir.exists()` | Reused if exists, not recreated |
| `frontend/node_modules/` | `node_modules.exists()` | Reused if exists, not reinstalled |
| `installer/credentials/db_credentials.txt` | Overwritten | Previous credentials lost |

### Database Objects That MUST NOT Exist

| Object | Type | Detection Method | Impact if Exists |
|--------|------|------------------|------------------|
| `giljo_mcp` | Database | `pg_database` query | Warning shown, database reused |
| `giljo_owner` | Role | `pg_roles` query | Password updated, role reused |
| `giljo_user` | Role | `pg_roles` query | Password updated, role reused |
| `alembic_version` | Table | `information_schema.tables` | Treated as upgrade, only pending migrations run |

### Directories That MUST Exist

| Directory | Purpose | Failure if Missing |
|-----------|---------|-------------------|
| `migrations/` | Alembic migrations | ✅ CRITICAL - Install FAILS |
| `migrations/versions/` | Migration scripts | ✅ CRITICAL - Install FAILS |
| `frontend/` | Vue dashboard | ✅ CRITICAL - npm install FAILS |
| `src/giljo_mcp/` | Core Python code | ✅ CRITICAL - Python imports FAIL |
| `api/` | FastAPI server | ⚠️ Non-critical - Service start FAILS |

---

## Hidden State Detection

### 1. Alembic Migration State

**Location**: PostgreSQL database `giljo_mcp.alembic_version`

**Detection** (`install.py:1860-1887`):
```python
# Check if alembic_version table exists
SELECT EXISTS (
    SELECT FROM information_schema.tables
    WHERE table_name = 'alembic_version'
)

# If exists, check version stamp
SELECT version_num FROM alembic_version LIMIT 1;
```

**States**:
- ✅ **Fresh**: Table does NOT exist
- ⚠️ **Incomplete**: Table exists, no version stamp
- 🔄 **Existing**: Table exists with version stamp (e.g., `baseline_v32_unified`)

### 2. PostgreSQL Roles and Permissions

**Hidden State**: Role ownership and default privileges

**Impact**: If roles exist with different permissions:
- New permissions granted via `ALTER DEFAULT PRIVILEGES`
- Existing table permissions NOT retroactively changed
- May require manual `GRANT` for existing tables

### 3. Virtual Environment Site-Packages

**Location**: `venv/Lib/site-packages/` (Windows) or `venv/lib/python3.x/site-packages/` (Linux/macOS)

**Impact**:
- If venv exists with old dependencies → `pip install` upgrades
- If venv corrupted → Installation may fail with import errors
- **Solution**: Delete `venv/` for true pristine state

### 4. npm Cache and Lock Files

**Locations**:
- `frontend/node_modules/`
- `frontend/package-lock.json`
- System npm cache (`~/.npm/`)

**Impact**:
- Cached packages may mask registry issues
- Corrupted `node_modules` → npm install fails
- **Solution**: `rm -rf frontend/node_modules/ && npm install`

### 5. Service Lock Files (Potential)

**Expected Locations** (not currently implemented):
- `api/server.pid` - API server PID
- `frontend/dev-server.pid` - Frontend dev server PID
- `logs/api.lock` - Log file lock

**Current Status**: ❌ NOT IMPLEMENTED in v3.2
- No PID files created by `install.py`
- No lock files checked during startup
- Services started via `subprocess.Popen()` (no PID tracking)

---

## Nuclear Reset Checklist

### Purpose
Complete system reset to pristine state for fresh installation.

### ⚠️ CRITICAL WARNINGS

1. **DATA LOSS**: This process DELETES ALL DATA permanently
2. **NO ROLLBACK**: Cannot undo database drop operations
3. **BACKUP FIRST**: Export any data you want to keep

### Step-by-Step Reset Procedure

#### Phase 1: Filesystem Cleanup

```powershell
# Navigate to installation directory
cd F:\GiljoAI_MCP

# 1. Remove configuration files
Remove-Item .env -Force -ErrorAction SilentlyContinue
Remove-Item config.yaml -Force -ErrorAction SilentlyContinue

# 2. Remove credentials
Remove-Item -Recurse installer\credentials\ -Force -ErrorAction SilentlyContinue

# 3. Remove Python virtual environment
Remove-Item -Recurse venv\ -Force -ErrorAction SilentlyContinue

# 4. Remove node_modules
Remove-Item -Recurse frontend\node_modules\ -Force -ErrorAction SilentlyContinue

# 5. Remove logs
Remove-Item -Recurse logs\ -Force -ErrorAction SilentlyContinue

# 6. Remove any flag files
Remove-Item database_created.flag -Force -ErrorAction SilentlyContinue
Remove-Item installer\scripts\*.ps1 -Force -ErrorAction SilentlyContinue
Remove-Item installer\scripts\*.sh -Force -ErrorAction SilentlyContinue
```

#### Phase 2: Database Cleanup

**Option A: Drop and Recreate (Recommended)**

```sql
-- Connect to PostgreSQL as admin
psql -U postgres

-- Drop database (CASCADE removes all connections)
DROP DATABASE IF EXISTS giljo_mcp WITH (FORCE);

-- Drop roles
DROP ROLE IF EXISTS giljo_user;
DROP ROLE IF EXISTS giljo_owner;

-- Verify cleanup
\l                           -- List databases (giljo_mcp should NOT appear)
\du                          -- List roles (giljo_* should NOT appear)

-- Exit
\q
```

**Option B: Truncate All Tables (Preserves Structure)**

```sql
-- Connect to giljo_mcp database
psql -U postgres -d giljo_mcp

-- Truncate all tables (preserves schema)
TRUNCATE TABLE alembic_version CASCADE;
TRUNCATE TABLE setup_state CASCADE;
TRUNCATE TABLE users CASCADE;
TRUNCATE TABLE products CASCADE;
TRUNCATE TABLE projects CASCADE;
TRUNCATE TABLE agent_templates CASCADE;
TRUNCATE TABLE agent_executions CASCADE;
TRUNCATE TABLE mcp_agent_jobs CASCADE;
TRUNCATE TABLE product_memory_entries CASCADE;
-- ... (all other tables)

-- Exit
\q
```

**Option C: Drop Only Alembic State (Keeps Data)**

```sql
-- Connect to giljo_mcp database
psql -U postgres -d giljo_mcp

-- Drop alembic version table (forces fresh migration)
DROP TABLE IF EXISTS alembic_version;

-- Verify
\dt                          -- List tables (alembic_version should NOT appear)

-- Exit
\q
```

#### Phase 3: Cache Cleanup

```powershell
# 1. Clear npm cache
npm cache clean --force

# 2. Clear pip cache (optional)
pip cache purge

# 3. Clear Python bytecode
Get-ChildItem -Recurse -Filter "*.pyc" | Remove-Item -Force
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force
```

#### Phase 4: Verification

**Check Filesystem**:
```powershell
# These should ALL return "File/Directory not found"
Test-Path .env                              # Should be False
Test-Path config.yaml                       # Should be False
Test-Path venv                              # Should be False
Test-Path frontend\node_modules             # Should be False
Test-Path installer\credentials             # Should be False
```

**Check Database**:
```sql
-- Connect to PostgreSQL
psql -U postgres

-- Verify database does NOT exist
\l                                          -- giljo_mcp should NOT appear

-- Verify roles do NOT exist
\du                                         -- giljo_owner, giljo_user should NOT appear

-- Exit
\q
```

#### Phase 5: Fresh Install

```powershell
# Run installer
python install.py

# Expected output:
# - "Fresh install detected - will run all migrations from scratch"
# - "Creating database and roles..."
# - "Generating .env with real database credentials..."
# - "Running database migrations (alembic upgrade head)..."
# - "Setup state initialized"
```

---

## Common Issues and Solutions

### Issue 1: "alembic_version table exists but empty"

**Symptom**:
```
Empty alembic_version table - will stamp and run migrations
ERROR: Multiple head revisions found
```

**Cause**: Previous migration failed mid-run

**Solution**:
```sql
-- Drop alembic_version and retry
DROP TABLE alembic_version;
```

### Issue 2: "Database already exists" warning but install fails

**Symptom**:
```
Database 'giljo_mcp' already exists, using existing database
ERROR: Migration failed: Table 'users' already exists
```

**Cause**: Database exists with partial schema (not managed by Alembic)

**Solution**:
```sql
-- Drop database completely
DROP DATABASE giljo_mcp WITH (FORCE);
```

### Issue 3: `.env` exists but DATABASE_URL invalid

**Symptom**:
```
ERROR: DATABASE_URL not found in .env after regeneration
```

**Cause**: `.env` file corrupted or incomplete

**Solution**:
```powershell
# Delete .env and retry
Remove-Item .env -Force
python install.py
```

### Issue 4: PostgreSQL role password mismatch

**Symptom**:
```
psycopg2.OperationalError: password authentication failed for user "giljo_user"
```

**Cause**: `.env` password doesn't match PostgreSQL role password

**Solution**:
```sql
-- Option A: Reset role passwords to match .env
ALTER ROLE giljo_owner WITH PASSWORD 'password_from_env';
ALTER ROLE giljo_user WITH PASSWORD 'password_from_env';

-- Option B: Drop roles and reinstall
DROP ROLE giljo_user;
DROP ROLE giljo_owner;
-- Then rerun install.py
```

### Issue 5: npm install fails with "ENOSPC" error

**Symptom**:
```
ERROR: npm install failed with exit code 1
ENOSPC: no space left on device
```

**Cause**: Disk space < 500MB

**Solution**:
```powershell
# Check disk space
Get-PSDrive F | Select-Object Used,Free

# Free up space or install to different drive
python install.py --install-dir D:\GiljoAI_MCP
```

---

## Summary: What Must Be Deleted for Pristine State

### 🔴 CRITICAL (Must Delete)

| Item | Type | Reason |
|------|------|--------|
| `.env` | File | Primary fresh install detector |
| `giljo_mcp` database | PostgreSQL DB | Contains all application data and schema |
| `giljo_owner` role | PostgreSQL Role | Owns database objects |
| `giljo_user` role | PostgreSQL Role | Application runtime user |
| `alembic_version` table | PostgreSQL Table | Migration state tracking |

### 🟡 RECOMMENDED (Should Delete)

| Item | Type | Reason |
|------|------|--------|
| `config.yaml` | File | Will be regenerated, prevents stale config |
| `venv/` | Directory | Ensures clean dependency installation |
| `frontend/node_modules/` | Directory | Prevents cached package issues |
| `installer/credentials/` | Directory | Removes old database passwords |
| `logs/` | Directory | Clears old log files |

### 🟢 OPTIONAL (Nice to Have)

| Item | Type | Reason |
|------|------|--------|
| npm cache | System Cache | Prevents cached package issues |
| pip cache | System Cache | Forces fresh package downloads |
| `__pycache__/` | Directories | Clears compiled Python bytecode |
| `*.pyc` files | Files | Clears compiled Python bytecode |

### ⚪ DO NOT DELETE

| Item | Type | Reason |
|------|------|--------|
| `alembic.ini` | File | Required for migrations |
| `migrations/` | Directory | Required for schema creation |
| `src/` | Directory | Core application code |
| `frontend/src/` | Directory | Frontend source code |
| `.git/` | Directory | Version control history |

---

## Appendix: Install.py Architecture

### Installation Flow

```
1. Welcome Screen
   └─ Display banner, version, license

2. Python Version Check (3.10+)
   └─ FAIL → Exit with error

3. PostgreSQL Discovery
   ├─ PATH search
   ├─ Common paths search
   └─ Custom path prompt (if not found)

4. Dependency Installation
   ├─ Create venv (if not exists)
   ├─ Install requirements.txt
   └─ Verify imports

5. Config Generation (BEFORE database setup!)
   ├─ Generate config.yaml (ports, features)
   └─ (Skip .env generation - happens after DB setup)

6. Database Setup
   ├─ Create database and roles (DatabaseInstaller)
   ├─ Generate .env with REAL credentials
   ├─ Reload environment variables
   ├─ Run Alembic migrations (create schema)
   └─ Seed initial data (SetupState only)

7. Database Migrations
   ├─ Check alembic_version table
   ├─ Run alembic upgrade head
   └─ Verify essential tables created

8. NPM Installation
   ├─ Pre-flight checks (registry, disk, lockfile)
   ├─ npm install (uses npm ci if lockfile valid)
   └─ Verify dependencies installed

9. Service Startup
   ├─ Start API server (python api/app.py)
   ├─ Start Frontend (npm run dev)
   └─ Open browser (http://localhost:7274)

10. Welcome Screen
    ├─ First user registration
    ├─ Setup wizard (MCP config, Serena activation)
    └─ Dashboard redirect
```

### Key Design Decisions

1. **Single Baseline Migration** (Handover 0601):
   - NO incremental migrations for v3.2
   - Single `baseline_v32_unified.py` creates all 32 tables
   - <1 second execution time
   - Idempotent (safe to run multiple times)

2. **Config Generation Order** (Handover 0034):
   - `config.yaml` generated BEFORE database setup
   - `.env` generated AFTER database setup (uses real credentials)
   - Fixes password synchronization bug

3. **No Default Admin** (Handover 0034):
   - Removed `admin/admin` default account
   - First user created via web UI `/first-login`
   - Setup state tracks `default_password_active: false`

4. **Cross-Platform Compatibility**:
   - All paths use `pathlib.Path()`
   - Platform-specific PostgreSQL discovery
   - Windows/Linux/macOS installation scripts

---

## Document Metadata

**Version**: 1.0
**Last Updated**: 2026-02-02
**Agent**: Installation Flow Agent
**Handover References**: 0034, 0601, 0017
**Related Docs**:
- `docs/INSTALLATION_FLOW_PROCESS.md`
- `docs/architecture/migration-strategy.md`
- `handovers/completed/0601_nuclear_migration_reset.md`
