# Session Memory: Installer Frontend Dependencies & Reset Script Enhancements

**Date:** 2025-10-03
**Agent:** Claude Code
**Project:** GiljoAI MCP
**Tasks:**
1. Fix installer to install frontend npm dependencies
2. Enhance reset.py with backup and sync capabilities

---

## Problem 1: Frontend Dependencies Not Installed

### Issue
After running the installer, the frontend failed to start with error:
```
'vite' is not recognized as an internal or external command
```

The installer was only installing Python dependencies, not frontend npm packages.

### Root Cause
The `installer/core/installer.py` `install()` method only had a step for Python dependencies (`install_dependencies()`), but no step for frontend npm dependencies.

### Solution Implemented

**Added Step 4.5: Install Frontend Dependencies**

Modified `installer/core/installer.py`:

1. **Updated installation workflow** (lines 107-116):
   ```python
   # Step 4.5: Install frontend dependencies
   self.logger.info("Step 4.5: Installing frontend dependencies")
   frontend_result = self.install_frontend_dependencies()

   if not frontend_result['success']:
       # Don't fail installation if frontend deps fail, just warn
       result['warnings'] = result.get('warnings', [])
       result['warnings'].append("Failed to install frontend dependencies - frontend may not work")
       self.logger.warning("Frontend dependency installation failed, but continuing installation")
   ```

2. **Created new method** `install_frontend_dependencies()` (lines 587-652):
   - Checks if frontend directory exists
   - Verifies npm is installed (`npm --version`)
   - Skips if `node_modules` already exists
   - Runs `npm install` in frontend directory
   - Has 5-minute timeout for safety
   - Non-blocking: Warns on failure but doesn't stop installation

**Key Features:**
- Detects npm availability before attempting installation
- Provides clear user feedback with progress messages
- Graceful degradation: Installation continues even if npm fails
- Prevents duplicate installs by checking for existing `node_modules`

---

## Problem 2: Reset Script Lacking Safety Features

### Issue
The `reset.py` script would blindly reset the test environment without:
- Checking for unsaved changes in test folder
- Offering to sync changes back to dev repo
- Creating a backup before destructive operations

This risked losing work done in the test environment.

### Solution Implemented

**Enhanced reset.py with Three Major Features:**

### Feature 1: Compare Test vs Dev Repo

**New Function:** `compare_and_offer_sync()` (lines 570-646)

- Compares all sync-able files and directories
- Uses `filecmp.cmp()` for content comparison
- Checks modification timestamps to determine which is newer
- Lists changed files (shows first 10, counts rest)
- Distinguishes between:
  - Newer files in test folder (can sync to dev)
  - Older files in test folder (dev repo is newer)

**Supporting Function:** `compare_directory()` (lines 649-671)

- Recursively compares directory contents
- Skips environment-specific files (venv, node_modules, etc.)
- Returns list of changed file paths

**Supporting Function:** `sync_to_dev_repo()` (lines 674-708)

- Copies changed files from test to dev repo
- Creates parent directories as needed
- Handles both files and directories
- Shows sync progress for each file

### Feature 2: Create Backup

**New Function:** `create_backup()` (lines 711-759)

- Creates timestamped backup: `C:\install_test\Backup\YYYY-MM-DD_HH-MM-SS_backup`
- Excludes:
  - venv (large, can be recreated)
  - node_modules (large, can be recreated)
  - Environment-specific files (.env, config.yaml, data/, logs/, etc.)
  - Symlinked folders (already backed up in dev repo)
- Uses `shutil.ignore_patterns()` to skip cache files
- Returns backup path for user reference

### Feature 3: Updated Workflow

**Modified:** `main()` function (lines 762-795)

New workflow order:
1. **Step 0:** Compare and offer sync (`compare_and_offer_sync()`)
2. **Step 0.5:** Create backup (`create_backup()`)
3. Show what will be done
4. Display backup location
5. Ask for confirmation
6. Continue with original reset process

---

## Technical Details

### New Constants Added

```python
BACKUP_DIR = Path("C:/install_test/Backup")

SYNC_DIRS = [
    "api", "src", "frontend", "installer", "tests",
    "migrations", "docker", "launchers", "certs"
]

SYNC_FILES = [
    # Python, batch, shell, config, and documentation files
    # (see full list in reset.py lines 54-79)
]
```

### Import Additions

```python
from datetime import datetime
import filecmp
```

---

## User Experience Improvements

### Before
1. Run `reset.py`
2. Immediate destruction of test environment
3. No backup, no sync option
4. Lost any work done in test folder

### After
1. Run `reset.py`
2. **See comparison** of test vs dev repo changes
3. **Choose to sync** changes to dev repo (y/N)
4. **Automatic backup** created with timestamp
5. **See backup location** before proceeding
6. **Final confirmation** before reset
7. Reset proceeds with safety net in place

---

## Example Output Flow

```
============================================================
  Comparing Test Folder with Dev Repo
============================================================

[!] Found 3 newer/changed files in test folder:
  1. installer/core/installer.py
  2. reset.py
  3. src/giljo_mcp/config.py

Do you want to copy these changes to the dev repo before reset? (y/N): y

============================================================
  Syncing Changes to Dev Repo
============================================================

[OK] Synced: installer/core/installer.py
[OK] Synced: reset.py
[OK] Synced: src/giljo_mcp/config.py

[OK] Synced 3 items to dev repo

============================================================
  Creating Backup
============================================================

Backing up to: C:\install_test\Backup\2025-10-03_16-30-45_backup
- Skipping symlink: docs
- Skipping symlink: scripts
- Skipping symlink: examples

[OK] Backed up 15 items to C:\install_test\Backup\2025-10-03_16-30-45_backup

Test Directory: C:\install_test\Giljo_MCP
Dev Repository: C:\Projects\GiljoAI_MCP
Backup Location: C:\install_test\Backup

This will:
  - Drop PostgreSQL databases (giljo_mcp, giljo_mcp_test)
  - Drop PostgreSQL users (giljo_user, giljo_owner)
  - Clean %APPDATA% installations
  - Remove venv, .env, config.yaml (NOT reinstalled)
  - Copy fresh code from dev repo
  - Preserve CLAUDE.md, .serena/, and symlinked folders

[!] After reset, manually run:
      install.bat (Windows)
      quickstart.sh (Linux/Mac)

[OK] Backup created at: C:\install_test\Backup\2025-10-03_16-30-45_backup

Proceed with reset? (y/N):
```

---

## Files Modified

1. **`installer/core/installer.py`**
   - Added `install_frontend_dependencies()` method (67 lines)
   - Updated `install()` workflow to include Step 4.5
   - Lines changed: ~80

2. **`reset.py`**
   - Added 3 new functions: `compare_and_offer_sync()`, `compare_directory()`, `sync_to_dev_repo()`, `create_backup()`
   - Updated `main()` workflow
   - Added new constants: `BACKUP_DIR`, `SYNC_DIRS`, `SYNC_FILES`
   - Added imports: `datetime`, `filecmp`
   - Lines changed: ~200+

---

## Testing Performed

### Installer Test
1. Fresh installation in test folder
2. Verified frontend dependencies installed automatically
3. Confirmed `node_modules` directory created
4. Frontend started successfully without errors

### Reset Script Test
1. Modified files in test folder
2. Ran `reset.py`
3. Verified comparison showed changed files
4. Tested sync to dev repo
5. Verified backup created with timestamp
6. Confirmed backup excludes venv and symlinks
7. Reset proceeded normally after confirmation

---

## Benefits

### For Installer
- ✅ Complete one-command installation (no manual npm install)
- ✅ Frontend works immediately after installation
- ✅ Better user experience for non-technical users
- ✅ Consistent with installation expectations

### For Reset Script
- ✅ Never lose work from test folder
- ✅ Easy sync back to dev repo
- ✅ Safety backup before destructive operations
- ✅ Timestamped backups for recovery
- ✅ Clear user feedback at each step
- ✅ Can cancel without consequence

---

## Future Considerations

### Installer
- Consider adding build step for frontend (`npm run build`)
- Add progress indicators for long npm installs
- Support for yarn/pnpm as alternatives to npm

### Reset Script
- Add option to restore from previous backup
- Add cleanup of old backups (keep last N)
- Support for partial reset (database only, config only, etc.)
- Interactive file selection for sync

---

**Status:** ✅ Complete and Tested
**Impact:** High - Significant improvement to developer workflow and data safety
