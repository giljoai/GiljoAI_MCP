# Agent Prompt: Complete File Renaming for Option C (Installer Standardization)

## Mission Objective
Complete the naming standardization for GiljoAI MCP installer files to align with Option C (Hybrid Approach). This involves renaming core installer files and updating all references throughout the codebase to ensure consistency and clarity.

## Context
The installer architecture has been updated with smart dependency detection. However, naming standardization is only partially complete. Legacy file names (`quickstart.bat`, `setup_interactive.py`) need to be renamed to more intuitive names (`install.bat`, `setup_cli.py`) while ensuring no functionality breaks.

## Required Changes

### Phase 1: File Renaming Operations

#### 1.1 Rename quickstart.bat → install.bat
**Action:** Rename the file
```
OLD: quickstart.bat
NEW: install.bat
```

**Verification:**
- File exists at new location
- All content preserved
- File permissions maintained

#### 1.2 Rename setup_interactive.py → setup_cli.py
**Action:** Rename the file
```
OLD: setup_interactive.py
NEW: setup_cli.py
```

**Verification:**
- File exists at new location
- All content preserved
- Python syntax still valid

### Phase 2: Update File References

#### 2.1 Update references to quickstart.bat
**Files to check and update:**
- `README.md` (if exists)
- `INSTALL.md` (if exists)
- `docs/` directory (all .md files)
- `bootstrap.py` (any mentions in comments/strings)
- `*.bat` files (any references)
- `*.sh` files (any references)
- `setup_gui.bat` (line ~32: mentions quickstart.bat)
- `setup_cli.bat` (line ~19: mentions quickstart.bat)
- `INSTALLER_ARCHITECTURE.md` (multiple references)
- `giltest.bat` (if it references quickstart)

**Search patterns:**
```bash
grep -r "quickstart.bat" --include="*.md" --include="*.py" --include="*.bat" --include="*.sh"
```

**Replacement:**
- Change `quickstart.bat` → `install.bat`
- Update documentation prose to reflect new name
- Add backward compatibility notes where appropriate

#### 2.2 Update references to setup_interactive.py
**Files to check and update:**
- `bootstrap.py` (line ~471-478: imports and calls setup_interactive.py)
- `setup_cli.bat` (line ~50: checks for setup_interactive.py, line ~90: runs it)
- `README.md` (if exists)
- `docs/` directory (all .md files)
- `INSTALLER_ARCHITECTURE.md` (references to setup_interactive.py)

**Search patterns:**
```bash
grep -r "setup_interactive" --include="*.md" --include="*.py" --include="*.bat" --include="*.sh"
```

**Critical files requiring code changes:**

**File: `bootstrap.py`**
- Line ~471: `if not Path("setup_interactive.py").exists():`
  - Change to: `if not Path("setup_cli.py").exists():`
- Line ~478: `subprocess.run([sys.executable, "setup_interactive.py"], ...)`
  - Change to: `subprocess.run([sys.executable, "setup_cli.py"], ...)`
- Comments mentioning setup_interactive.py

**File: `setup_cli.bat`**
- Line ~50: `if not exist "setup_interactive.py"`
  - Change to: `if not exist "setup_cli.py"`
- Line ~90: `python setup_interactive.py`
  - Change to: `python setup_cli.py`

### Phase 3: Update Documentation

#### 3.1 Update INSTALLER_ARCHITECTURE.md
**Required changes:**
- Replace all `quickstart.bat` → `install.bat`
- Replace all `setup_interactive.py` → `setup_cli.py`
- Update file structure diagram
- Update installation paths examples
- Add migration note about file renaming

#### 3.2 Update README.md (if exists)
**Search for:**
- Installation instructions mentioning quickstart.bat
- References to setup_interactive.py
- Getting started sections

**Update to:**
- Use `install.bat` as primary installation method
- Reference `setup_cli.py` for CLI mode
- Add note: "Previously called quickstart.bat"

#### 3.3 Update CLAUDE.md (project instructions)
**Check for:**
- Installation command examples
- Development setup instructions
- Any hardcoded file references

### Phase 4: Create Backward Compatibility Documentation

#### 4.1 Create MIGRATION_NOTES.md
Create a new file documenting the changes:

```markdown
# File Renaming Migration (v2.1)

## What Changed

The following files have been renamed for clarity:

| Old Name | New Name | Purpose |
|----------|----------|---------|
| `quickstart.bat` | `install.bat` | Main installation entry point |
| `setup_interactive.py` | `setup_cli.py` | CLI installation wizard |

## Migration Guide

### For Users
- **Old command:** `quickstart.bat`
- **New command:** `install.bat`

Both commands do the same thing. The new name is more intuitive.

### For Developers
If you have scripts or documentation referencing the old names:
1. Update `quickstart.bat` → `install.bat`
2. Update `setup_interactive.py` → `setup_cli.py`

### For CI/CD Pipelines
Update your build scripts to use:
```bash
# Old
python setup_interactive.py --non-interactive

# New
python setup_cli.py --non-interactive
```

## Rationale

The old names were confusing:
- "quickstart" implied a fast/simple install, but it's a full installer
- "setup_interactive" was unclear about being CLI-focused

New names are clearer:
- "install" - obvious purpose
- "setup_cli" - clear it's the command-line interface

## Timeline
- **v2.0 and earlier:** Old names
- **v2.1 onward:** New names (this release)
```

### Phase 5: Testing & Validation

#### 5.1 Python Syntax Validation
```bash
python -m py_compile bootstrap.py
python -m py_compile setup_cli.py
```

#### 5.2 File Existence Checks
```bash
# Verify old files are gone
test ! -f quickstart.bat && echo "✓ quickstart.bat removed"
test ! -f setup_interactive.py && echo "✓ setup_interactive.py removed"

# Verify new files exist
test -f install.bat && echo "✓ install.bat exists"
test -f setup_cli.py && echo "✓ setup_cli.py exists"
```

#### 5.3 Reference Validation
```bash
# Check for remaining old references
grep -r "quickstart.bat" --include="*.py" --include="*.bat" --include="*.md" && echo "WARNING: Old references found" || echo "✓ No old references"
grep -r "setup_interactive.py" --include="*.py" --include="*.bat" --include="*.md" && echo "WARNING: Old references found" || echo "✓ No old references"
```

#### 5.4 Functional Testing
- Verify `install.bat` launches bootstrap.py
- Verify `setup_cli.bat` finds and launches setup_cli.py
- Verify bootstrap.py correctly calls setup_cli.py
- Test Python imports don't break

## Success Criteria

✅ **Files renamed successfully:**
- `install.bat` exists (was quickstart.bat)
- `setup_cli.py` exists (was setup_interactive.py)

✅ **All references updated:**
- No mentions of `quickstart.bat` in code (except MIGRATION_NOTES.md)
- No mentions of `setup_interactive.py` in code (except MIGRATION_NOTES.md)

✅ **Documentation updated:**
- README.md uses new names
- INSTALLER_ARCHITECTURE.md updated
- MIGRATION_NOTES.md created

✅ **Tests pass:**
- Python syntax validation passes
- File existence checks pass
- No broken references found

✅ **Functional verification:**
- Can run `install.bat` successfully
- Can run `python bootstrap.py` successfully
- Can run `setup_cli.bat` successfully

## Execution Order

Execute in this exact order to avoid breaking dependencies:

1. **Backup first** (optional but recommended)
   - Create git commit or backup copies

2. **Rename files**
   - Rename setup_interactive.py → setup_cli.py (do this first to avoid import errors)
   - Rename quickstart.bat → install.bat

3. **Update code references**
   - Update bootstrap.py
   - Update setup_cli.bat
   - Update setup_gui.bat

4. **Update documentation**
   - Update INSTALLER_ARCHITECTURE.md
   - Update README.md (if exists)
   - Create MIGRATION_NOTES.md

5. **Validate**
   - Run syntax checks
   - Run reference validation
   - Test functionality

6. **Report**
   - List all files changed
   - Confirm success criteria met
   - Note any warnings or issues

## Safety Notes

- **Reversible:** Keep git history to rollback if needed
- **No data loss:** Renaming preserves all file content
- **Test first:** Run in test environment before production
- **Check imports:** Python imports are case-sensitive

## Edge Cases to Handle

1. **If README.md doesn't exist:** Skip section 3.2, note in report
2. **If grep finds no references:** That's success, note in report
3. **If files already renamed:** Skip rename, report as already complete
4. **If syntax errors found:** Report immediately, don't continue
5. **If imports break:** Revert rename, investigate dependencies

## Expected Output

At completion, the agent should report:

```
✅ File Renaming Complete - Option C Standardization

Files Renamed:
- quickstart.bat → install.bat
- setup_interactive.py → setup_cli.py

Code References Updated:
- bootstrap.py (2 changes)
- setup_cli.bat (2 changes)
- setup_gui.bat (1 change)

Documentation Updated:
- INSTALLER_ARCHITECTURE.md (updated)
- MIGRATION_NOTES.md (created)
- README.md (updated - if exists)

Validation Results:
✓ Python syntax check passed
✓ No broken references found
✓ File structure verified
✓ Functional tests passed

Total files modified: [count]
All success criteria met.
```

## Error Handling

If any step fails:
1. **Stop execution** - don't continue to next phase
2. **Report error** with specific file/line number
3. **Suggest fix** if possible
4. **Ask for guidance** on how to proceed

Do NOT:
- Continue after errors
- Make assumptions about fixes
- Delete files without renaming
- Skip validation steps

---

## Agent Instructions Summary

You are tasked with completing the file renaming standardization for GiljoAI MCP installer. Follow the phases above in exact order. Be thorough, validate each step, and report clearly. Safety and accuracy are more important than speed.

**Your primary objective:** Rename files and update all references so the installer uses intuitive names (`install.bat`, `setup_cli.py`) instead of legacy names (`quickstart.bat`, `setup_interactive.py`).

**On completion:** Provide a comprehensive report showing all changes made and validation results.
