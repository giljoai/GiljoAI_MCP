# Project Cleanup Handoff - Remove Old GUI Installer Artifacts

## Date: October 2, 2025
## Mission: Clean project folder of OLD installation process remnants
## Priority: HIGH - Project folder is cluttered with obsolete code

---

## PROJECT CONTEXT

We successfully refactored from GUI-based installer to CLI-only installer (Phases 1-4 complete).
However, the old GUI installer files, tests, and documentation still exist in the project, creating confusion.

**Current Status:**
- NEW CLI installer: WORKING (installer/cli/, installer/core/)
- OLD GUI installer: DEPRECATED but still present (needs identification and removal)
- Project folder: CLUTTERED with mixed old/new files

---

## CLEANUP OBJECTIVES

### 1. Identify Old Installation Files
- GUI installer components (likely React/Vue based)
- Old installer Python files (pre-refactor)
- Obsolete test files for GUI installer
- Outdated documentation
- Old configuration templates
- Deprecated launcher scripts

### 2. Create Backup Report
- Generate comprehensive list of files to be removed
- Document what each old file did
- Create comparison table: OLD vs NEW approach
- Save backup archive of old files before deletion

### 3. Clean Project Structure
- Remove all old installer files
- Clean up test directories
- Remove obsolete documentation
- Delete unused dependencies
- Update .gitignore if needed

---

## KNOWN OLD INSTALLER PATTERNS TO FIND

### Likely Old GUI Files:
```
- install_gui.py or gui_installer.py
- installer/gui/* (entire folder if exists)
- installer/frontend/* (if separate from main app)
- static/installer/*
- templates/installer/*
- Any .ui or .qml files (Qt)
- Any installer-specific React/Vue components
```

### Old Test Files:
```
- tests/test_gui_installer.py
- tests/installer_gui/*
- tests/old_installer/*
- Any test files dated before September 2025
```

### Old Documentation:
```
- docs/gui_installer_guide.md
- docs/old_installation.md
- README sections about GUI installer
- Any installation screenshots (*.png in docs/)
```

### Old Configuration:
```
- install_config_gui.yaml
- installer_settings.ini
- gui_preferences.json
```

---

## SEARCH STRATEGY FOR AGENTS

### Phase 1: Discovery
```python
# Search patterns to identify old files:
1. Find all files with "gui" in name related to installer
2. Find files modified before refactor date (check git history)
3. Look for imports of GUI libraries (tkinter, PyQt, Kivy, etc.)
4. Find references to old installation process in comments
5. Identify orphaned test files (tests that no longer have matching source)
```

### Phase 2: Analysis
```python
# For each suspected old file:
1. Check if it's imported anywhere in current code
2. Verify it's not needed by NEW installer
3. Document its original purpose
4. Map to NEW equivalent (if exists)
```

### Phase 3: Backup
```python
# Create backup structure:
backup/
├── old_installer_backup_20251002/
│   ├── sources/          # Old source files
│   ├── tests/            # Old test files
│   ├── docs/             # Old documentation
│   ├── configs/          # Old configurations
│   └── INVENTORY.md      # Complete list with descriptions
```

---

## SPECIFIC FILES TO INVESTIGATE

Check these files specifically (from project root):
```
1. C:/Projects/GiljoAI_MCP/giltest.py - Might be old
2. C:/Projects/GiljoAI_MCP/devuninstall.py - Check if outdated
3. C:/Projects/GiljoAI_MCP/uninstall.py - Verify if old version
4. C:/Projects/GiljoAI_MCP/install.py - If exists at root, likely old
5. C:/Projects/GiljoAI_MCP/setup.py - Check if installer-related
6. Any .spec files (PyInstaller)
7. Any .iss files (Inno Setup)
```

---

## DELEGATION TO AGENTS

### For documentation-architect:
```
Task: Create comprehensive inventory of old installer artifacts
- Search entire project for GUI installer remnants
- Document each file's original purpose
- Create OLD vs NEW comparison table
- Generate INVENTORY.md report
```

### For implementation-developer:
```
Task: Safely remove old installer code
- Verify no current dependencies on old files
- Create backup archive before deletion
- Update imports and references
- Clean up orphaned test files
```

### For testing-specialist:
```
Task: Verify NEW installer still works after cleanup
- Run full test suite after removal
- Verify no broken imports
- Check all installation modes
- Confirm launcher functionality
```

---

## CRITICAL PRESERVATION LIST

### DO NOT DELETE:
```
installer/cli/install.py          # NEW CLI installer
installer/core/*.py                # NEW core modules
installer/tests/test_phase*.py    # NEW phase tests
installer/tests/test_harmony*.py  # NEW harmony tests
launchers/start_giljo.*           # Current launchers
docs/install_project/*.md         # Project documentation
```

### KEEP BUT REVIEW:
```
giltest_enhanced.py               # Might be NEW
test_scenarios.py                 # Might be NEW
PHASE_*.md files                  # Check if current
```

---

## EXPECTED OUTCOMES

### 1. Backup Archive Created
- Location: `C:/Projects/GiljoAI_MCP/backup/old_installer_backup_[date]/`
- Complete inventory with descriptions
- All old files preserved before deletion

### 2. Clean Project Structure
```
C:/Projects/GiljoAI_MCP/
├── installer/
│   ├── cli/          # NEW CLI interface ✓
│   ├── core/         # NEW core modules ✓
│   ├── tests/        # NEW tests only ✓
│   └── scripts/      # Helper scripts ✓
├── launchers/        # Clean launchers ✓
├── docs/
│   └── install_project/  # Current docs ✓
└── [No old installer files at root]
```

### 3. Comparison Report
Document showing:
- What was removed
- Why it was removed
- NEW equivalent (if any)
- Space saved
- Dependencies cleaned

---

## VERIFICATION CHECKLIST

After cleanup, verify:
- [ ] NEW installer runs successfully
- [ ] All test suites pass
- [ ] No import errors
- [ ] Documentation is current
- [ ] No broken symbolic links
- [ ] Git status is clean
- [ ] Backup is complete and accessible

---

## SAMPLE COMMANDS FOR AGENTS

```bash
# Find potential old GUI files
grep -r "tkinter\|PyQt\|Kivy\|wx\|GUI" --include="*.py"

# Find old test files
find . -name "*test*gui*.py" -o -name "*gui*test*.py"

# Check for old imports
grep -r "from installer.gui" --include="*.py"
grep -r "import installer_gui" --include="*.py"

# Find files not modified recently (before refactor)
find . -name "*.py" -mtime +30 | grep -i install

# Look for orphaned files
# (files not imported anywhere)
```

---

## PRIORITY ORDER

1. **HIGH**: Remove obvious GUI installer files
2. **HIGH**: Clean test directories of old tests
3. **MEDIUM**: Update documentation
4. **MEDIUM**: Remove old config files
5. **LOW**: Clean up comments referencing old system
6. **LOW**: Update README

---

## SUCCESS CRITERIA

- ✅ All old GUI installer code removed
- ✅ Backup created with full inventory
- ✅ NEW installer works perfectly
- ✅ Test suite passes 100%
- ✅ Project folder organized and clean
- ✅ Documentation accurate and current
- ✅ No confusion between old/new systems

---

## WARNING NOTES

1. **Check Dependencies**: Some old files might be imported by application code (not installer)
2. **Preserve History**: Use git to preserve history, don't delete .git
3. **Test Thoroughly**: Run full test suite after each deletion batch
4. **Document Everything**: Keep detailed log of what was removed and why

---

## HANDOFF INSTRUCTIONS

For the next session:
1. Start with: "Execute cleanup from CLEANUP_OLD_INSTALLER_HANDOFF.md"
2. Use installation-orchestrator to coordinate
3. Begin with discovery phase before any deletion
4. Create backup first, delete second
5. Test after each major deletion

This cleanup will make the project much cleaner and prevent future confusion between old and new installation systems.