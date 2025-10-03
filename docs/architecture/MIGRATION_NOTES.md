# Installer File Migration Notes

**Date:** 2025-09-30
**Version:** Effective immediately

## What Changed

### File Renames
| Old Name | New Name | Purpose |
|----------|----------|---------|
| `quickstart.bat` | `install.bat` | Windows installation entry point |

### File Removals
| Removed File | Replacement | Reason |
|--------------|-------------|--------|
| `setup_interactive.py` | `setup_cli.py` | Obsolete after PostgreSQL migration (Sep 29) |

## Background

`setup_cli.py` was created on September 29, 2025 during the PostgreSQL migration
as the new streamlined, PostgreSQL-focused CLI installer (663 lines vs 1,887 lines).
`setup_interactive.py` is the legacy comprehensive installer that is no longer needed.

The rename from `quickstart.bat` to `install.bat` provides a more intuitive name
that clearly indicates the script's purpose.

## Migration Steps

### For End Users
**No action required** - all installers updated automatically.

Use the new commands:
```batch
# Windows
install.bat

# Mac/Linux (unchanged)
./quickstart.sh

# Universal
python bootstrap.py
```

### For Custom Integrations
Update file references:
- `setup_interactive.py` → `setup_cli.py`
- `quickstart.bat` → `install.bat`

### For Documentation
All documentation has been updated:
- CLAUDE.md
- README.md
- INSTALL.md
- INSTALLATION.md
- INSTALLER_ARCHITECTURE.md

## Backwards Compatibility

**Not backwards compatible:**
- `quickstart.bat` no longer exists (use `install.bat`)
- `setup_interactive.py` no longer exists (use `setup_cli.py`)

This is intentional to enforce the new naming standard and remove legacy code.

## Timeline

- **Sep 29, 2025:** `setup_cli.py` created during PostgreSQL migration
- **Sep 30, 2025:** `setup_interactive.py` removed, `quickstart.bat` renamed to `install.bat`

## Commits

This migration was completed in 3 commits:

1. **Commit 1**: Rename quickstart.bat → install.bat
   - File rename operation

2. **Commit 2**: Delete setup_interactive.py
   - Remove 1,887 lines of obsolete code
   - `setup_cli.py` is now the authoritative CLI installer

3. **Commit 3**: Update all references
   - bootstrap.py: subprocess calls
   - setup_cli.bat: file checks and execution
   - Documentation: all .md files updated

## Validation

All changes have been validated:
- ✓ `setup_interactive.py` removed
- ✓ `setup_cli.py` exists (663 lines, PostgreSQL-focused)
- ✓ `quickstart.bat` removed
- ✓ `install.bat` exists
- ✓ Zero old references in codebase
- ✓ Python syntax validation passed
- ✓ Pre-commit hooks passed

## Support

If you encounter issues related to this migration, please:
1. Ensure you're using the latest version from the repository
2. Use `install.bat` (Windows) or `quickstart.sh` (Mac/Linux)
3. Report any issues on GitHub

## Notes

- The Mac/Linux installer (`quickstart.sh`) was not renamed to maintain consistency
  with existing documentation and user expectations
- Future consideration: Rename `quickstart.sh` → `install.sh` for full platform consistency
