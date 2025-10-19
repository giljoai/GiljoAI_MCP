# Linux Installer (DEPRECATED)

**Deprecated Date**: 2025-10-19
**Replaced By**: Unified cross-platform installer (install.py)
**Handover**: 0035

---

## Why Deprecated

The separate Linux installer (`linux_installer/linux_install.py`) was deprecated and replaced with a unified cross-platform installer that works on Windows, Linux, and macOS.

### Critical Bugs in Old Linux Installer

1. **Missing pg_trgm Extension**: Full-text search functionality would fail due to missing PostgreSQL extension
   - Impact: MCPContextIndex table could not use searchable_vector column
   - Severity: CRITICAL - Core feature broken
   - Fixed in: Unified installer (v3.1.0+)

2. **Misleading Success Messages**: Displayed admin/admin credentials that didn't exist
   - Impact: Users confused about login credentials
   - Severity: HIGH - User experience issue
   - Context: Handover 0034 eliminated default credentials but Linux installer wasn't updated
   - Fixed in: Unified installer (v3.1.0+)

3. **Import Path Inconsistency**: Used `Linux_Installer` package name vs `installer` on Windows
   - Impact: Code couldn't be shared between platforms
   - Severity: MEDIUM - Development friction
   - Fixed in: Unified installer (v3.1.0+)

### Code Duplication

**Before Unification**:
- Windows installer: `install.py` (1,344 lines) + `installer/core/` (1,829 lines)
- Linux installer: `linux_installer/linux_install.py` (1,361 lines) + `linux_installer/core/` (1,606 lines)
- Total: 6,140 lines with 85% duplication

**After Unification**:
- Unified installer: `install.py` (1,220 lines) + `installer/` (3,350 total lines)
- Total: 4,570 lines
- Reduction: 25.6% code reduction

---

## Migration

### Old Command

```bash
python linux_installer/linux_install.py
```

### New Command

```bash
python install.py  # Works on all platforms
```

### What Changed

**Platform Auto-Detection**:
- Old: Separate installer per platform
- New: Single installer detects OS automatically

**PostgreSQL Extensions**:
- Old: Linux installer missing pg_trgm extension
- New: All platforms create pg_trgm extension

**Success Messages**:
- Old: Incorrectly referenced admin/admin credentials
- New: Correct message directing to /welcome for first admin creation

**Desktop Integration**:
- Old: Linux .desktop file creation
- New: Same functionality, but in platform handler (`installer/platforms/linux.py`)

---

## Old File Locations (Archived)

**Main Installer**:
- `linux_installer/linux_install.py` → Removed
- Functionality merged into: `install.py` (unified orchestrator)

**Core Modules**:
- `linux_installer/core/database.py` → Merged into `installer/core/database.py`
- `linux_installer/core/config.py` → Merged into `installer/core/config.py`

**Platform-Specific Code**:
- Linux-specific code extracted to: `installer/platforms/linux.py`

---

## Technical Details

### PostgreSQL Extension Issue

**Old Code** (linux_installer/core/database.py):
```python
# MISSING: No pg_trgm extension creation
# Would cause MCPContextIndex queries to fail
```

**New Code** (installer/core/database.py):
```python
# FIXED: pg_trgm extension now created on all platforms
self.logger.info("Creating PostgreSQL extensions (Handover 0017)...")
cur.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
self.logger.info("Extension pg_trgm created successfully")
```

### Success Message Issue

**Old Message** (linux_installer/linux_install.py):
```
====================================
Default Admin Credentials:
  Username: admin
  Password: admin

⚠️ IMPORTANT: Change this password on first login!
====================================
```

**Problem**: These credentials don't exist (Handover 0034 removed default admin)

**New Message** (install.py):
```
Next Steps:
1. Start the server:
   python startup.py

2. Open your browser to:
   http://localhost:7274

3. Create your administrator account:
   You'll be redirected to /welcome to create your first admin account
   (Strong password required: 12+ chars with uppercase, lowercase, digit, special char)
```

---

## For Developers

### If You Need Old Installer Code

**Archive Location**: `docs/archive/LINUX_INSTALLER_DEPRECATED_20251019.md` (this file)

**Git History**:
```bash
# View last version before deprecation
git log --follow -- linux_installer/linux_install.py

# Checkout old version if needed (not recommended)
git checkout <commit-hash> -- linux_installer/
```

### Migrating Custom Modifications

If you had custom modifications to the Linux installer:

1. **Identify platform-specific code**: Should go in `installer/platforms/linux.py`
2. **Identify platform-agnostic code**: Should go in `installer/core/` or `installer/shared/`
3. **Test on all platforms**: Ensure changes work on Windows, Linux, macOS
4. **Update tests**: Add tests to `tests/installer/`

---

## Related Documentation

**New Installer Documentation**:
- [Installation Flow & Process](../INSTALLATION_FLOW_PROCESS.md) - Complete installation guide
- [Platform Handlers](../installer/PLATFORM_HANDLERS.md) - Platform handler architecture
- [Handover 0035](../../handovers/0035_HANDOVER_20251019_UNIFIED_CROSS_PLATFORM_INSTALLER.md) - Technical specification

**Handover References**:
- [Handover 0017](../../handovers/completed/0017_HANDOVER_20251014_DATABASE_SCHEMA_ENHANCEMENT-C.md) - pg_trgm requirement
- [Handover 0034](../../handovers/completed/0034_HANDOVER_20251018_ELIMINATE_ADMIN_ADMIN_IMPLEMENT_CLEAN_FIRST_USER_CREATION-C.md) - Admin credentials removal

---

## Deprecation Timeline

**Phase 1** (2025-10-19): Unified installer released
- Old installers remain available
- Documentation updated to recommend unified installer
- Deprecation warnings added

**Phase 2** (2025-10-26): Old installers marked deprecated
- README updated with deprecation notice
- Users encouraged to migrate
- Support continues for old installers

**Phase 3** (2025-11-02): Old installers archived
- `linux_installer/` directory removed from main branch
- Code archived to `docs/archive/`
- Support discontinued

---

See Handover 0035 for complete migration details and technical specifications.
