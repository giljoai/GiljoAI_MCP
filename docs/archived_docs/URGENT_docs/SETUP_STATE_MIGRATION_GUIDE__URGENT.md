# Setup State Migration Guide

**For Developers and System Administrators**

**Date:** 2025-10-07
**Version:** 2.0.0
**Target Audience:** Developers, DevOps, System Administrators

---

## Table of Contents

1. [Overview](#overview)
2. [Migration Scenarios](#migration-scenarios)
3. [Existing Installations](#existing-installations)
4. [New Installations](#new-installations)
5. [Version Mismatch Resolution](#version-mismatch-resolution)
6. [Database Schema Changes](#database-schema-changes)
7. [API Endpoint Changes](#api-endpoint-changes)
8. [Frontend Compatibility](#frontend-compatibility)
9. [Testing Migration](#testing-migration)
10. [Rollback Procedures](#rollback-procedures)
11. [Troubleshooting](#troubleshooting)

---

## Overview

This guide explains how to migrate from the legacy file-based setup state system to the new hybrid file/database architecture. The migration is designed to be seamless and automatic in most cases.

### What Changed

| Component | Before (v1.x) | After (v2.0) |
|-----------|---------------|--------------|
| **Setup State Storage** | `config.yaml` (gitignored file) | `setup_state` table (PostgreSQL) + file fallback |
| **Version Tracking** | None | `setup_version`, `database_version`, `schema_version` |
| **State Persistence** | File-only | Database + file fallback |
| **Migration** | Manual | Automatic via Alembic |
| **Multi-tenancy** | Partial | Full support |

### Migration Goals

- ✅ Zero downtime for existing installations
- ✅ Automatic data migration from legacy sources
- ✅ Backward compatible API responses
- ✅ Graceful degradation if database unavailable
- ✅ Clear recovery path for failed migrations

---

## Migration Scenarios

### Scenario 1: Existing Localhost Installation

**System State:**
- GiljoAI MCP installed and running
- Setup wizard completed
- `config.yaml` has `setup.completed = true`
- No `setup_state.json` file exists
- Using localhost mode

**What Happens:**

```
1. Developer runs: git pull
   ↓
2. Alembic migration executes automatically
   ↓
3. Migration script checks for legacy state:
   - Looks for ~/.giljo-mcp/setup_state.json (not found)
   - Reads setup.completed from config.yaml (found: true)
   ↓
4. Creates setup_state database row:
   - tenant_key: "default"
   - completed: true
   - setup_version: "2.0.0"
   - install_mode: "localhost"
   - tools_enabled: (parsed from config.yaml)
   ↓
5. Application starts normally
   - SetupStateManager reads from database
   - Version check passes
   - Setup wizard accessible for re-runs
```

**Developer Action Required:** None (automatic)

### Scenario 2: Existing LAN Installation

**System State:**
- GiljoAI MCP installed and configured for LAN
- Setup wizard completed with API key
- `config.yaml` has network settings
- LAN mode active

**What Happens:**

```
1. Administrator runs: git pull
   ↓
2. Alembic migration executes
   ↓
3. Creates setup_state row with:
   - completed: true
   - install_mode: "lan"
   - features_configured: { network_mode: "lan", lan_config: {...} }
   - config_snapshot: (full config.yaml backup)
   ↓
4. Backend restart triggered (service restart)
   ↓
5. Application starts, version check passes
```

**Administrator Action Required:**
- Restart backend service (if not auto-restarted)
- Verify LAN mode still active
- Test API key authentication

### Scenario 3: Fresh Installation (CLI Installer)

**System State:**
- Running CLI installer for first time
- PostgreSQL not yet installed
- No existing configuration

**What Happens:**

```
1. User runs: python installer/cli/install.py
   ↓
2. Installer detects no database available
   ↓
3. Uses file storage:
   - Creates ~/.giljo-mcp/setup_state.json
   - Stores initial state (completed: false)
   ↓
4. Installer installs PostgreSQL
   ↓
5. Installer runs Alembic migrations
   ↓
6. Migration detects setup_state.json file
   ↓
7. Migrates file data to database
   ↓
8. Backs up file to setup_state.json.backup
   ↓
9. Application starts with database storage
```

**User Action Required:** None (automatic)

### Scenario 4: Incomplete Setup (Wizard Not Completed)

**System State:**
- Setup wizard started but not completed
- `config.yaml` has `setup.completed = false` or missing
- User stopped mid-wizard

**What Happens:**

```
1. Migration runs
   ↓
2. Detects setup not completed
   ↓
3. Creates setup_state row:
   - completed: false
   - setup_version: "2.0.0"
   ↓
4. On application start:
   - Router guard detects setup incomplete
   - Redirects to /setup
   - User can complete wizard
```

**User Action Required:** Complete setup wizard

---

## Existing Installations

### Pre-Migration Checklist

Before updating to v2.0, verify:

- [ ] Backup `config.yaml`: `cp config.yaml config.yaml.backup`
- [ ] Backup database: `pg_dump giljo_mcp > backup.sql`
- [ ] Document current configuration:
  - Network mode (localhost/LAN/WAN)
  - Attached tools (Claude Code, Serena)
  - API key (if LAN/WAN mode)
- [ ] Verify PostgreSQL is running: `psql -U postgres -c "\l"`
- [ ] Check disk space: At least 100MB free

### Migration Steps

#### Step 1: Pull Latest Code

```bash
cd /path/to/GiljoAI_MCP
git pull origin master
```

#### Step 2: Update Dependencies (if needed)

```bash
# Python dependencies
pip install -r requirements.txt

# Frontend dependencies (if changed)
cd frontend/
npm install
cd ..
```

#### Step 3: Run Database Migration

**Automatic (Recommended):**

```bash
# Migration runs automatically on application start
python api/run_api.py
```

**Manual (if needed):**

```bash
# Run Alembic migration explicitly
alembic upgrade head
```

**Verify migration:**

```bash
# Check setup_state table exists
psql -U postgres -d giljo_mcp -c "\d setup_state"

# Check for migrated data
psql -U postgres -d giljo_mcp -c "SELECT tenant_key, completed, setup_version FROM setup_state;"
```

#### Step 4: Verify Application

```bash
# Start backend
python api/run_api.py

# In another terminal, check status
curl http://localhost:7272/api/setup/status

# Expected response:
# {
#   "completed": true,
#   "database_configured": true,
#   "tools_attached": ["claude-code"],
#   "network_mode": "localhost"
# }
```

#### Step 5: Test Setup Wizard

```bash
# Open browser
http://localhost:7274/setup

# Should load wizard (not redirect)
# Can re-run wizard if needed
```

### Post-Migration Verification

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Database table exists | `psql -U postgres -d giljo_mcp -c "\dt setup_state"` | Table listed |
| State row exists | `psql -U postgres -d giljo_mcp -c "SELECT * FROM setup_state;"` | 1 row returned |
| Setup status API | `curl localhost:7272/api/setup/status` | JSON with `completed: true` |
| Frontend loads | Visit `http://localhost:7274` | Dashboard loads (not setup) |
| Wizard accessible | Visit `http://localhost:7274/setup` | Wizard loads |

---

## New Installations

### Installation Flow

```
1. Run CLI installer
   ↓
2. Installer creates ~/.giljo-mcp/setup_state.json
   ↓
3. Installer installs PostgreSQL
   ↓
4. Installer runs migrations (creates setup_state table)
   ↓
5. Migration migrates file → database automatically
   ↓
6. User completes setup wizard
   ↓
7. Wizard calls POST /api/setup/complete
   ↓
8. SetupStateManager saves to database
   ↓
9. Setup complete, redirect to dashboard
```

### Database Initialization

For new installations, the database is created empty:

```sql
-- After migration, setup_state table exists but is empty
SELECT COUNT(*) FROM setup_state;
-- Result: 0

-- First wizard completion creates row
-- POST /api/setup/complete
-- ...wizard completes...

SELECT COUNT(*) FROM setup_state;
-- Result: 1

SELECT tenant_key, completed, setup_version FROM setup_state;
--  tenant_key | completed | setup_version
-- ------------+-----------+---------------
--  default    | true      | 2.0.0
```

### CLI Installer Changes

No changes required for users. The installer:

1. Detects database availability automatically
2. Uses file storage if database not yet available
3. Migrates to database after PostgreSQL installation
4. No user interaction needed

---

## Version Mismatch Resolution

### Detecting Version Mismatches

Version mismatches occur when:

1. Code updated via `git pull` but setup state remains old version
2. Database migrated but application not restarted
3. Setup version incremented but migration not run

### Automatic Detection

On application startup, the system checks versions:

```python
# api/app.py - startup event
@app.on_event("startup")
async def check_setup_state():
    state_manager = SetupStateManager.get_instance("default")
    is_compatible, error_msg = state_manager.check_version_compatibility()

    if not is_compatible:
        logger.warning(f"Version mismatch detected: {error_msg}")
        # Trigger migration or notify user
```

### Resolution Options

#### Option 1: Automatic Migration (Recommended)

```bash
# Call migration endpoint
curl -X POST http://localhost:7272/api/setup/migrate

# Response:
# {
#   "migrated": true,
#   "old_version": "1.0.0",
#   "current_version": "2.0.0",
#   "message": "Migration completed successfully"
# }
```

#### Option 2: Re-run Setup Wizard

```bash
# Navigate to setup wizard
http://localhost:7274/setup

# Complete wizard with current settings
# This updates setup_version to current
```

#### Option 3: Manual Database Update

```sql
-- Update setup version manually (use with caution)
UPDATE setup_state
SET setup_version = '2.0.0'
WHERE tenant_key = 'default';
```

### Version Compatibility Matrix

| Setup Version | Database Version | Schema Version | Compatible? |
|---------------|------------------|----------------|-------------|
| 2.0.0 | 18.x | 1 | ✅ Yes |
| 2.0.0 | 14.x | 1 | ✅ Yes |
| 1.0.0 | 18.x | 1 | ⚠️ Needs migration |
| 2.0.0 | NULL | 1 | ⚠️ Needs DB setup |

---

## Database Schema Changes

### New Table: `setup_state`

**Created by Migration:** `e2639692ae52_add_setup_state_table.py`

```sql
CREATE TABLE setup_state (
    id VARCHAR(36) PRIMARY KEY,
    tenant_key VARCHAR(36) NOT NULL UNIQUE,
    completed BOOLEAN NOT NULL DEFAULT false,
    completed_at TIMESTAMP WITH TIME ZONE,
    setup_version VARCHAR(20),
    database_version VARCHAR(20),
    python_version VARCHAR(20),
    node_version VARCHAR(20),
    features_configured JSONB NOT NULL DEFAULT '{}',
    tools_enabled JSONB NOT NULL DEFAULT '[]',
    config_snapshot JSONB,
    validation_passed BOOLEAN NOT NULL DEFAULT true,
    validation_failures JSONB NOT NULL DEFAULT '[]',
    validation_warnings JSONB NOT NULL DEFAULT '[]',
    last_validation_at TIMESTAMP WITH TIME ZONE,
    installer_version VARCHAR(20),
    install_mode VARCHAR(20),
    install_path TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE,
    meta_data JSONB DEFAULT '{}'
);
```

### Indexes Created

```sql
-- B-tree indexes
CREATE INDEX idx_setup_tenant ON setup_state(tenant_key);
CREATE INDEX idx_setup_completed ON setup_state(completed);
CREATE INDEX idx_setup_mode ON setup_state(install_mode);

-- GIN indexes for JSONB queries
CREATE INDEX idx_setup_features_gin ON setup_state USING gin(features_configured);
CREATE INDEX idx_setup_tools_gin ON setup_state USING gin(tools_enabled);

-- Partial index for incomplete setups
CREATE INDEX idx_setup_incomplete ON setup_state(tenant_key, completed)
WHERE completed = false;
```

### Data Migration

Migration logic handles these sources:

1. **Legacy file:** `~/.giljo-mcp/setup_state.json` (if exists)
2. **Config file:** `config.yaml` → `setup.completed` field
3. **Default values:** For fresh installations

### Rollback Schema Changes

If you need to rollback to pre-v2.0:

```bash
# Revert migration
alembic downgrade -1

# This will:
# - Drop setup_state table
# - Drop indexes
# - Preserve data in backup file

# NOTE: You'll need to manually restore config.yaml settings
# from the backup you created pre-migration
```

---

## API Endpoint Changes

### Modified Endpoints

#### GET /api/setup/status

**Changes:**
- Now reads from `SetupStateManager` instead of `config.yaml`
- Response format unchanged (backward compatible)
- New optional field: `needs_migration`

**Before (v1.x):**
```python
def get_setup_status():
    config = read_yaml("config.yaml")
    return {
        "completed": config.get("setup", {}).get("completed", False),
        "tools_attached": config.get("tools", [])
    }
```

**After (v2.0):**
```python
def get_setup_status():
    state_manager = SetupStateManager.get_instance("default")
    state = state_manager.get_state()
    is_compatible, _ = state_manager.check_version_compatibility()

    return {
        "completed": state.get("completed", False),
        "tools_attached": state.get("tools_enabled", []),
        "needs_migration": not is_compatible  # NEW
    }
```

**Response Compatibility:**

```json
// v1.x response
{
  "completed": true,
  "database_configured": true,
  "tools_attached": ["claude-code"]
}

// v2.0 response (backward compatible)
{
  "completed": true,
  "database_configured": true,
  "tools_attached": ["claude-code"],
  "network_mode": "localhost",
  "needs_migration": false  // NEW (optional)
}
```

#### POST /api/setup/complete

**Changes:**
- Now saves to `SetupStateManager` in addition to `config.yaml`
- Stores configuration snapshot for rollback
- Response format unchanged

**Before (v1.x):**
```python
def complete_setup(config):
    write_yaml("config.yaml", config)
    return {"success": true}
```

**After (v2.0):**
```python
def complete_setup(config):
    # Write to config.yaml (as before)
    write_yaml("config.yaml", updated_config)

    # NEW: Persist to database
    state_manager = SetupStateManager.get_instance("default")
    state_manager.mark_completed(
        features_configured=config.features,
        tools_enabled=config.tools,
        config_snapshot=updated_config  # NEW: snapshot
    )

    return {"success": true}
```

### New Endpoints

#### POST /api/setup/migrate

**Purpose:** Migrate setup state from old version to current

**Request:**
```bash
curl -X POST http://localhost:7272/api/setup/migrate
```

**Response:**
```json
{
  "migrated": true,
  "old_version": "1.0.0",
  "current_version": "2.0.0",
  "message": "Migration completed successfully"
}
```

**Use Cases:**
- Version mismatch detected at startup
- Manual migration trigger
- Testing migration logic

---

## Frontend Compatibility

### Router Guard Changes

**Before (v1.x):**
```javascript
// router/index.js
router.beforeEach(async (to, from, next) => {
  if (to.path !== '/setup') {
    const status = await checkSetupStatus();
    if (!status.completed) {
      return next('/setup');  // Redirect to setup
    }
  }
  next();
});
```

**After (v2.0):**
```javascript
// No changes needed - backend API is backward compatible
router.beforeEach(async (to, from, next) => {
  if (to.path !== '/setup') {
    const status = await checkSetupStatus();  // Same call
    if (!status.completed) {
      return next('/setup');
    }

    // NEW: Check for migration needed (optional)
    if (status.needs_migration) {
      console.warn('Setup state needs migration');
      // Could show banner or notification
    }
  }
  next();
});
```

### Component Changes

**SetupWizard.vue:**
- No changes required
- API calls remain the same
- Response format unchanged

**setupService.js:**
- No changes required
- Endpoints unchanged
- Request/response formats compatible

### Testing Frontend Changes

```bash
# No changes needed to existing tests
cd frontend/
npm run test

# All existing tests should pass
```

---

## Testing Migration

### Test Plan

#### 1. Test Localhost → v2.0 Migration

```bash
# Simulate existing localhost installation
# 1. Setup v1.x system
git checkout v1.x
python api/run_api.py
# Complete setup wizard
# Stop system

# 2. Migrate to v2.0
git checkout master
alembic upgrade head

# 3. Verify migration
psql -U postgres -d giljo_mcp -c "SELECT * FROM setup_state;"
# Should show 1 row with completed=true

# 4. Start system
python api/run_api.py

# 5. Test setup status
curl http://localhost:7272/api/setup/status
# Should return completed=true

# 6. Test wizard access
http://localhost:7274/setup
# Should load wizard (re-run capability)
```

#### 2. Test Fresh Installation

```bash
# Simulate fresh install
# 1. Drop database
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 2. Run installer
python installer/cli/install.py

# 3. Check file storage created
cat ~/.giljo-mcp/setup_state.json

# 4. Complete setup wizard
http://localhost:7274/setup

# 5. Verify database storage
psql -U postgres -d giljo_mcp -c "SELECT * FROM setup_state;"
```

#### 3. Test Version Mismatch Detection

```bash
# Simulate version mismatch
# 1. Update setup_version in database
psql -U postgres -d giljo_mcp -c "UPDATE setup_state SET setup_version = '1.0.0';"

# 2. Start application
python api/run_api.py
# Check logs for mismatch warning

# 3. Check status endpoint
curl http://localhost:7272/api/setup/status
# Should return needs_migration=true

# 4. Run migration
curl -X POST http://localhost:7272/api/setup/migrate

# 5. Verify fixed
curl http://localhost:7272/api/setup/status
# Should return needs_migration=false
```

#### 4. Test LAN Mode Migration

```bash
# Simulate LAN installation
# 1. Setup system in LAN mode (v1.x)
# Complete wizard with LAN configuration

# 2. Migrate to v2.0
git pull
alembic upgrade head

# 3. Verify LAN settings preserved
psql -U postgres -d giljo_mcp -c "SELECT features_configured FROM setup_state;"
# Should show LAN config

# 4. Restart backend
python api/run_api.py

# 5. Verify LAN mode active
curl http://localhost:7272/api/setup/status
# Should show network_mode=lan

# 6. Test API key authentication
curl -H "Authorization: Bearer $API_KEY" http://localhost:7272/api/projects
```

### Automated Migration Tests

```bash
# Run migration tests
pytest tests/integration/test_setup_state_migration.py -v

# Expected output:
# test_migrate_from_file_to_db ..................... PASSED
# test_migrate_from_config_yaml .................... PASSED
# test_migrate_legacy_setup_state .................. PASSED
# test_version_mismatch_detection .................. PASSED
# test_backward_compatible_api ..................... PASSED
```

---

## Rollback Procedures

### When to Rollback

Rollback if:
- Migration fails and cannot be fixed
- Critical bugs discovered in v2.0
- Need to revert to known-good state

**WARNING:** Rollback should be last resort. Try troubleshooting first.

### Rollback Steps

#### Step 1: Stop Application

```bash
# Stop backend
pkill -f "python api/run_api.py"

# Stop frontend (if running)
pkill -f "npm run dev"
```

#### Step 2: Restore Database

```bash
# Revert Alembic migration
alembic downgrade -1

# This drops setup_state table and indexes

# Optional: Restore from backup
# psql -U postgres -d giljo_mcp < backup.sql
```

#### Step 3: Restore Code

```bash
# Checkout previous version
git checkout v1.x

# Or specific commit
git checkout <commit-hash>
```

#### Step 4: Restore Config

```bash
# Restore config.yaml from backup
cp config.yaml.backup config.yaml

# Verify setup.completed field present
grep -A 2 "setup:" config.yaml
```

#### Step 5: Restart Application

```bash
# Start backend
python api/run_api.py

# Start frontend
cd frontend/
npm run dev
```

#### Step 6: Verify Rollback

```bash
# Check status
curl http://localhost:7272/api/setup/status

# Expected: Old API response format
# {
#   "completed": true,
#   "tools_attached": [...]
# }

# Verify dashboard loads
http://localhost:7274
```

### Rollback Checklist

- [ ] Application stopped
- [ ] Database backup created (before rollback)
- [ ] Alembic migration reverted
- [ ] Code reverted to v1.x
- [ ] config.yaml restored from backup
- [ ] Application restarted successfully
- [ ] Dashboard loads without errors
- [ ] Setup status API returns expected data
- [ ] No console errors in browser

### Data Preservation During Rollback

The rollback preserves:

- ✅ Projects and agents (not affected)
- ✅ Messages and tasks (not affected)
- ✅ Configuration in config.yaml (restored from backup)
- ❌ setup_state table (dropped, but data backed up in migration)

**Note:** The migration creates a backup at `~/.giljo-mcp/setup_state.json.backup` before migrating. This can be restored if needed.

---

## Troubleshooting

### Issue 1: Migration Fails with "setup_state already exists"

**Symptom:**
```
alembic.runtime.migration.MigrationError: table "setup_state" already exists
```

**Cause:** Migration was partially run before

**Solution:**
```bash
# Check migration status
alembic current

# If migration applied, mark as complete
alembic stamp head

# Or revert and re-run
alembic downgrade -1
alembic upgrade head
```

### Issue 2: "setup_state table not found" Error

**Symptom:**
```
ERROR: relation "setup_state" does not exist
```

**Cause:** Migration not run or database not initialized

**Solution:**
```bash
# Run migration
alembic upgrade head

# Verify table created
psql -U postgres -d giljo_mcp -c "\dt setup_state"

# If still missing, check Alembic version table
psql -U postgres -d giljo_mcp -c "SELECT * FROM alembic_version;"
```

### Issue 3: Version Mismatch After Migration

**Symptom:**
```
WARNING: Setup version mismatch: stored=1.0.0, current=2.0.0
```

**Cause:** Database migrated but setup_version not updated

**Solution:**
```bash
# Run migration endpoint
curl -X POST http://localhost:7272/api/setup/migrate

# Or update manually
psql -U postgres -d giljo_mcp -c "UPDATE setup_state SET setup_version = '2.0.0';"

# Restart application
```

### Issue 4: Setup Wizard Redirect Loop

**Symptom:** Navigating to dashboard redirects to /setup, then back to dashboard

**Cause:** Setup state out of sync with validation logic

**Solution:**
```bash
# Check database state
psql -U postgres -d giljo_mcp -c "SELECT completed, validation_passed FROM setup_state;"

# If completed=true but validation_passed=false:
psql -U postgres -d giljo_mcp -c "UPDATE setup_state SET validation_passed = true;"

# Re-run setup wizard
http://localhost:7274/setup
```

### Issue 5: API Returns "Setup already completed"

**Symptom:** Trying to re-run wizard, but API rejects with "Setup already completed"

**Cause:** Legacy logic checking config.yaml instead of database

**Solution:**
```bash
# Verify you're running v2.0
git log -1 --oneline

# Check API endpoint code
grep -A 10 "Setup already completed" api/endpoints/setup.py

# If using old logic, update code:
git pull
pip install -r requirements.txt
# Restart API
```

### Issue 6: File Storage Not Migrating to Database

**Symptom:** `~/.giljo-mcp/setup_state.json` still used, database empty

**Cause:** Database session not available or migration failed

**Solution:**
```bash
# Check if database accessible
psql -U postgres -d giljo_mcp -c "SELECT 1;"

# Manually trigger migration
python -c "
from src.giljo_mcp.setup.state_manager import SetupStateManager
from src.giljo_mcp.database import get_session

with get_session() as session:
    manager = SetupStateManager.get_instance('default', db_session=session)
    success = manager.migrate_from_file_to_db()
    print(f'Migration success: {success}')
"

# Verify database populated
psql -U postgres -d giljo_mcp -c "SELECT * FROM setup_state;"
```

### Issue 7: LAN Mode Not Working After Migration

**Symptom:** LAN mode was configured, but after migration API binds to localhost only

**Cause:** `config.yaml` not updated with LAN settings during migration

**Solution:**
```bash
# Check config.yaml
cat config.yaml | grep -A 5 "installation:"

# Should show:
# installation:
#   mode: lan

# If shows localhost, check database
psql -U postgres -d giljo_mcp -c "SELECT features_configured FROM setup_state;"

# Restore from config_snapshot
psql -U postgres -d giljo_mcp -c "SELECT config_snapshot FROM setup_state;"

# Manually update config.yaml with snapshot data
# Or re-run wizard
```

### Issue 8: Frontend Shows "Setup Required" Banner After Completion

**Symptom:** Dashboard shows setup required banner despite setup being complete

**Cause:** Frontend cached status or localStorage out of sync

**Solution:**
```javascript
// In browser console:
localStorage.clear();
location.reload();

// Or specifically:
localStorage.removeItem('giljo_setup_complete');
localStorage.removeItem('giljo_lan_setup_complete');

// Then refresh page
```

### Getting Help

If issues persist:

1. **Check logs:**
   ```bash
   # Backend logs
   tail -f logs/giljo-mcp.log

   # Database logs (PostgreSQL)
   tail -f /var/log/postgresql/postgresql-18-main.log
   ```

2. **Gather diagnostic info:**
   ```bash
   # System info
   python --version
   psql --version
   node --version

   # Database state
   psql -U postgres -d giljo_mcp -c "
     SELECT tenant_key, completed, setup_version, install_mode
     FROM setup_state;
   "

   # Alembic state
   alembic current
   alembic history
   ```

3. **Report issue:**
   - GitHub: [Create issue](https://github.com/GiljoAI/MCP/issues)
   - Include: System info, error logs, steps to reproduce

---

## Summary

### Migration Quick Reference

| Scenario | Action | Expected Result |
|----------|--------|-----------------|
| Existing localhost install | `git pull` + restart | Automatic migration |
| Existing LAN install | `git pull` + restart | Automatic migration, verify API key |
| Fresh install | Run CLI installer | Automatic file→DB migration |
| Version mismatch | `POST /api/setup/migrate` | Version updated |
| Migration failed | Check troubleshooting | Manual intervention |
| Need rollback | `alembic downgrade -1` + restore backup | Reverted to v1.x |

### Key Takeaways

1. **Migration is automatic** in most cases
2. **Backup before migrating** (config.yaml + database)
3. **Test after migration** (status API + wizard access)
4. **Version tracking** prevents future drift issues
5. **Rollback is possible** but should be last resort

### Post-Migration Best Practices

- ✅ Monitor logs for warnings during first few days
- ✅ Test setup wizard re-run capability
- ✅ Verify LAN mode still works (if applicable)
- ✅ Document any custom configuration changes
- ✅ Update team documentation with new architecture

---

**Document Version:** 1.0.0
**Last Updated:** 2025-10-07
**Author:** Documentation Manager Agent
**Status:** Final
