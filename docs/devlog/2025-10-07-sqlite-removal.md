# SQLite Complete Removal - PostgreSQL-Only Enforcement

**Date:** 2025-10-07
**Status:** ✅ COMPLETE
**Priority:** HIGH
**Type:** Bug Fix + Architecture Cleanup

---

## Executive Summary

Completed removal of all legacy SQLite code from the GiljoAI MCP codebase. The project standardized on PostgreSQL-only 8 days ago, but SQLite fallback code remained in Alembic migrations and installer configuration, causing fresh installations to potentially use unsupported SQLite database instead of required PostgreSQL.

**Impact:** Fresh installations will now exclusively use PostgreSQL 14-18 with clear error messages if not configured correctly.

---

## Problem Statement

### Issue Discovered

User attempted fresh installation and encountered error:
```
NotImplementedError: No support for ALTER of constraints in SQLite dialect
```

**Root Cause Investigation Revealed:**

1. **Alembic Using SQLite:** `migrations/env.py` had SQLite fallback from legacy code
2. **Installer Had SQLite Templates:** Configuration manager defaulted to SQLite if PostgreSQL not detected
3. **No Clear Errors:** Silent fallback to unsupported database instead of failing with clear message

### Why This Matters

- **Data Integrity:** SQLite doesn't support all PostgreSQL features used in migrations
- **Production Readiness:** PostgreSQL required for multi-tenant isolation, JSONB queries, advanced indexing
- **Developer Experience:** Confusing errors when migrations fail on SQLite
- **Architecture Compliance:** Violates project decision made 8 days ago

---

## Solution Overview

### Three-Part Fix

1. **Alembic Migration Environment** - PostgreSQL-only with explicit .env loading
2. **Installer Configuration** - Removed SQLite fallback, added validation
3. **Documentation Cleanup** - Fixed CLAUDE.md confusion, created install guide

---

## Technical Implementation

### Part 1: Alembic PostgreSQL-Only

**File:** `migrations/env.py`

**Problem:**
- SQLite fallback on lines 24-27
- `.env` file not loaded (DATABASE_URL not seen)
- No validation of database type

**Solution:**
```python
# Load environment variables explicitly
from dotenv import load_dotenv
load_dotenv()

# Try DATABASE_URL first
db_url = os.getenv("DATABASE_URL")
if not db_url:
    # Construct from individual PostgreSQL vars
    db_host = os.getenv("POSTGRES_HOST", "localhost")
    db_port = os.getenv("POSTGRES_PORT", "5432")
    db_name = os.getenv("POSTGRES_DB", "giljo_mcp")
    db_user = os.getenv("POSTGRES_USER", "giljo_user")
    db_pass = os.getenv("POSTGRES_PASSWORD")

    if db_pass:
        db_url = f"postgresql://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}"
    else:
        raise ValueError(
            "PostgreSQL database URL not configured!\n"
            "Set DATABASE_URL or POSTGRES_PASSWORD in .env file.\n"
            "SQLite is NOT supported - PostgreSQL 14-18 is required."
        )

config.set_main_option("sqlalchemy.url", db_url)
```

**Benefits:**
- ✅ Loads `.env` explicitly with `python-dotenv`
- ✅ Clear error if PostgreSQL not configured
- ✅ Never falls back to SQLite
- ✅ Works with both `DATABASE_URL` and individual `POSTGRES_*` vars

**Git Commit:** `51b1317`

### Part 2: Installer PostgreSQL-Only

**Files Modified:**
1. `installer/core/profile.py`
2. `installer/config/config_manager.py`
3. `installer/config/templates/.env.developer` (DELETED)

#### Change 2.1: Profile Defaults

**File:** `installer/core/profile.py` (line 140-142)

**Before:**
```python
description="Ideal for individual developers working on local machines. Uses SQLite for simplicity and requires minimal configuration.",
configuration=ProfileConfiguration(
    database_type="sqlite",
```

**After:**
```python
description="Ideal for individual developers working on local machines. Uses PostgreSQL 14-18 for development.",
configuration=ProfileConfiguration(
    database_type="postgresql",
```

#### Change 2.2: Configuration Manager Database Setup

**File:** `installer/config/config_manager.py` (lines 222-236)

**Before:**
```python
# Database Configuration
db_type = profile_defaults.get("database", "sqlite")
if db_type == "postgresql" and "postgresql" in connection_strings:
    config.add_value("DATABASE_URL", connection_strings["postgresql"], ...)
else:
    # SQLite fallback
    db_path = user_inputs.get("db_path", "data/giljo_mcp.db")
    config.add_value("DATABASE_URL", f"sqlite:///{db_path}", ...)
```

**After:**
```python
# Database Configuration - PostgreSQL ONLY
db_type = profile_defaults.get("database", "postgresql")
if "postgresql" in connection_strings:
    config.add_value("DATABASE_URL", connection_strings["postgresql"], ...)
else:
    # PostgreSQL is required - raise error if not configured
    raise ValueError(
        "PostgreSQL database configuration is required. "
        "SQLite is not supported. Please install PostgreSQL 14-18."
    )
```

#### Change 2.3: Developer Profile Defaults

**File:** `installer/config/config_manager.py` (line 346)

**Before:**
```python
"developer": {
    "database": "sqlite",
```

**After:**
```python
"developer": {
    "database": "postgresql",  # PostgreSQL required - SQLite not supported
```

#### Change 2.4: Database URL Validation

**File:** `installer/config/config_manager.py` (lines 586-593)

**Before:**
```python
# Check database URL format
if db_url:
    if not any(db_url.startswith(prefix) for prefix in ["sqlite://", "postgresql://", "mysql://"]):
        errors.append(f"Invalid DATABASE_URL format: {db_url}")
```

**After:**
```python
# Check database URL format - PostgreSQL ONLY
if db_url:
    if not db_url.startswith("postgresql://"):
        errors.append(
            f"Invalid DATABASE_URL: PostgreSQL required. "
            f"Got: {db_url[:20]}... SQLite/MySQL not supported."
        )
```

#### Change 2.5: Template Deletion

**File:** `installer/config/templates/.env.developer` - **DELETED**

**Reason:** Contained SQLite configuration template that would mislead developers.

**Git Commit:** `f5119ab`

### Part 3: Documentation Cleanup

#### CLAUDE.md Cleanup

**Problem:** CLAUDE.md referenced "System 1 - C: Drive" and "System 2 - F: Drive" causing confusion when user only has F: drive.

**Solution:**
1. Removed all multi-system references
2. Simplified to single development environment (F: drive)
3. Removed from git tracking (`git rm --cached CLAUDE.md`)
4. File remains local-only for system-specific documentation

**Git Commits:**
- `648e046` - Remove C: drive references
- `9056c3c` - Remove from git tracking

#### Fresh Install Guide Created

**File:** `FRESH_INSTALL_GUIDE.md`

**Contents:**
- Pre-installation checklist (PostgreSQL running, clean slate)
- Step-by-step installation process
- Verification procedures
- Troubleshooting SQLite errors
- Emergency rollback procedures

**Git Commit:** `c2ad393`

---

## Testing Results

### Test 1: Alembic Migration Environment

**Command:**
```bash
cd F:\GiljoAI_MCP
alembic current
```

**Before Fix:**
```
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
```

**After Fix:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
```

✅ **PASS** - Alembic now uses PostgreSQL

### Test 2: Missing PostgreSQL Error Message

**Scenario:** Run Alembic without PostgreSQL configured

**Expected:** Clear error message about PostgreSQL requirement

**Result:**
```
ValueError: PostgreSQL database URL not configured!
Set DATABASE_URL or POSTGRES_PASSWORD in .env file.
SQLite is NOT supported - PostgreSQL 14-18 is required.
```

✅ **PASS** - Clear, actionable error message

### Test 3: Installer Validation

**Scenario:** Attempt installation with SQLite URL

**Expected:** Validation error rejecting SQLite

**Result:**
```
Invalid DATABASE_URL: PostgreSQL required.
Got: sqlite:///data/gi... SQLite/MySQL not supported.
```

✅ **PASS** - Installer rejects non-PostgreSQL databases

---

## Impact Analysis

### Code Changes

| File | Lines Added | Lines Removed | Net Change |
|------|-------------|---------------|------------|
| migrations/env.py | 23 | 7 | +16 |
| installer/core/profile.py | 1 | 1 | 0 (changed) |
| installer/config/config_manager.py | 13 | 6 | +7 |
| installer/config/templates/.env.developer | 0 | 69 | -69 (deleted) |
| FRESH_INSTALL_GUIDE.md | 294 | 0 | +294 (new) |
| CLAUDE.md | 0 | 575 | -575 (untracked) |
| **TOTAL** | **331** | **658** | **-327** |

### Commits Made

```
51b1317 - fix: Remove SQLite fallback from Alembic migrations - PostgreSQL only
c2ad393 - docs: Add comprehensive fresh install guide for setup state architecture
648e046 - docs: Remove multi-system C: drive references from CLAUDE.md
9056c3c - chore: Remove CLAUDE.md from git tracking
f5119ab - fix: Remove all SQLite references from installer - PostgreSQL only
```

**Total:** 5 commits

### Affected Components

- ✅ **Alembic Migrations** - Now PostgreSQL-only
- ✅ **CLI Installer** - Validates and requires PostgreSQL
- ✅ **Configuration Manager** - No SQLite defaults
- ✅ **Profile System** - All profiles use PostgreSQL
- ✅ **Documentation** - Fresh install guide, session memory

---

## Deployment Instructions

### For Fresh Installation (F: Drive)

```bash
# 1. Ensure PostgreSQL 14-18 is running
# Verify with: psql -U postgres -c "SELECT version();"

# 2. (Optional) Drop old database for clean slate
PGPASSWORD=$DB_PASSWORD psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 3. Pull latest changes
cd F:\GiljoAI_MCP
git pull

# 4. Install dependencies
pip install -r requirements.txt

# 5. Run installer
python installer/cli/install.py

# What happens:
# - Creates PostgreSQL database
# - Runs ALL migrations (including setup_state table)
# - Copies source code including SetupStateManager
# - Generates config.yaml and .env with PostgreSQL settings
# - NO SQLite fallback - fails with clear error if PostgreSQL not available
```

### Verification Steps

```bash
# 1. Check Alembic uses PostgreSQL
alembic current
# Should show: "Context impl PostgresqlImpl"

# 2. Verify setup_state table exists
PGPASSWORD=$DB_PASSWORD psql -U postgres -d giljo_mcp -c "\d setup_state"
# Should show table structure

# 3. Start API server
python api/run_api.py
# Should start without "SetupStateManager" import errors
```

---

## Known Issues

### 1. Migration Data Migration Warning (Non-Critical)

**Symptom:**
```
WARNI [alembic.runtime.migration] Failed to migrate legacy setup state:
(psycopg2.errors.SyntaxError) syntax error at or near ":"
```

**Cause:** Migration tries to migrate legacy `setup_state.json` data but has SQL syntax issue with JSONB parameter binding.

**Impact:** Low - Only affects migrations with existing legacy data. Fresh installs have no legacy data to migrate.

**Status:** Tracked for future fix, not blocking fresh installations.

### 2. Other Modified Files Detected

**Issue:** `git status` shows modified files unrelated to SQLite removal (pyproject.toml, docker files, scripts).

**Cause:** Likely from code formatter (Black) or unrelated edits during session.

**Action:** Reset to avoid including in SQLite removal commits. Need separate investigation.

**Follow-up:** Create separate commit for those changes after review.

---

## Future Improvements

### 1. Automated SQLite Detection

Add pre-commit hook or CI check to prevent SQLite code from being added:

```bash
# .git/hooks/pre-commit
if git diff --cached | grep -i "sqlite://"; then
    echo "ERROR: SQLite detected in commit. PostgreSQL-only project."
    exit 1
fi
```

### 2. Database Type Enum

Replace string-based database types with enum:

```python
from enum import Enum

class DatabaseType(Enum):
    POSTGRESQL = "postgresql"
    # No SQLite option available
```

### 3. Installer Dry-Run Mode

Add `--dry-run` flag to installer to validate configuration without making changes:

```bash
python installer/cli/install.py --dry-run
# Shows what would be configured without actually doing it
```

---

## Lessons Learned

### 1. Architecture Decisions Need Codebase-Wide Enforcement

When standardizing on PostgreSQL, should have immediately:
- Grepped entire codebase for "sqlite"
- Updated all configuration templates
- Added validation to reject SQLite

**Action:** Document architecture decisions in `ARCHITECTURE_DECISIONS.md` with enforcement checklist.

### 2. Git-Ignored Files Can Still Be Tracked

Adding file to `.gitignore` doesn't remove from tracking if already committed. Need `git rm --cached`.

**Action:** Added to developer onboarding documentation.

### 3. Environment Variable Loading Not Always Automatic

Some Python contexts (like Alembic's env.py) don't auto-load `.env` files. Need explicit `load_dotenv()`.

**Action:** Document in troubleshooting guide.

### 4. Fail Fast with Clear Messages

Better to raise clear error immediately than silently fall back to unsupported configuration.

**Action:** Apply this principle to all configuration validation going forward.

---

## Related Documents

- **Session Memory:** `docs/sessions/2025-10-07-sqlite-removal-and-fresh-install-prep.md`
- **Fresh Install Guide:** `FRESH_INSTALL_GUIDE.md`
- **Setup State Architecture:** `docs/architecture/SETUP_STATE_ARCHITECTURE.md`
- **Migration Guide:** `docs/architecture/SETUP_STATE_MIGRATION_GUIDE.md`

---

## Sign-Off

**Issue:** SQLite fallback code causing fresh installs to use unsupported database
**Resolution:** Complete removal of SQLite from Alembic, installer, and templates
**Status:** ✅ COMPLETE
**Commits:** 5 commits, 327 net lines removed
**Testing:** All validation tests passing
**Documentation:** Session memory, devlog, fresh install guide
**Ready for Deployment:** ✅ YES

**Next Steps:**
1. User performs fresh installation on F: drive
2. Verify installer completes successfully
3. Test setup wizard flow
4. Mark issue as closed

---

**End of Devlog**
