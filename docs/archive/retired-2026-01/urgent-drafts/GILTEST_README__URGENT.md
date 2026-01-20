# GiljoAI MCP - Release Simulation Testing

## Purpose

`giltest.bat` and `giltest.py` simulate the **"download from GitHub and extract"** user experience. This lets you test the installer with only the files a real user would get (not your development environment).

## What It Does

```
Development Folder          Release Simulation
(~1,600 files)    ──────>  (~400 files)
    │                           │
    ├─ tests/                   ├─ src/
    ├─ sessions/                ├─ api/
    ├─ devlog/                  ├─ frontend/
    ├─ *.log                    ├─ installer/
    ├─ __pycache__/             ├─ docs/ (user-facing only)
    ├─ .vscode/                 ├─ quickstart.bat
    ├─ .git/                    ├─ bootstrap.py
    └─ ... (dev files)          └─ README.md
```

## Usage

### Quick Start

```bash
# Run the simulation
giltest.bat

# Choose option:
# 1. Clean install (delete everything)
# 2. Preserve data (upgrade test)
```

### Target Directory

Files are copied to:
```
C:\install_test\Giljo_MCP\
```

This simulates extracting `GiljoAI_MCP_v2.0.zip` to that location.

## What Gets Excluded

The script mirrors `.gitattributes` `export-ignore` rules:

### Development Files Excluded:
- ❌ Test files (`tests/`, `test_*.py`, `*_test.py`)
- ❌ Session memories (`sessions/`, `docs/Sessions/`)
- ❌ Development logs (`devlog/`, `docs/devlog/`)
- ❌ Coverage reports (`coverage*.json`, `htmlcov/`)
- ❌ Development scripts (`giltest.py`, `fix_*.py`, `debug*.py`)
- ❌ Build artifacts (`__pycache__/`, `.mypy_cache/`, `.ruff_cache/`)
- ❌ Virtual environments (`venv/`, `env/`)
- ❌ IDE configs (`.vscode/`, `.idea/`, `.claude/`)
- ❌ Git metadata (`.git/`, `.gitignore`, `.gitattributes`)
- ❌ Logs and databases (`logs/`, `*.log`, `*.db`)
- ❌ Internal docs (`TODO.md`, `ROADMAP.md`, `PLANNING.md`)
- ❌ Agent files (`PHASE*.md`, `*_agent_*.json`)

### Release Files Included:
- ✅ Source code (`src/`, `api/`, `frontend/`)
- ✅ Installation scripts (`bootstrap.py`, `quickstart.bat`, `setup*.py`)
- ✅ Registration scripts (`register_*.py`, `register_*.bat`)
- ✅ Configuration templates (`config.yaml.example`, `requirements.txt`)
- ✅ User documentation (`README.md`, `INSTALLATION.md`, `docs/AI_TOOL_INTEGRATION.md`)
- ✅ License and contributing (`LICENSE`, `CONTRIBUTING.md`)
- ✅ Docker files (`docker-compose*.yml`, `Dockerfile`)
- ✅ Utilities (`start_giljo.bat`, `stop_giljo.bat`, `uninstall.py`)

## Why This Matters

### Problem Without It:
Your development environment has ~1,600 files including:
- Test databases with sample data
- Session logs from Claude conversations
- Cached build artifacts
- Git history

If you test the installer in your dev folder, it might work there but fail for real users who download a clean release.

### Solution With It:
Test with exactly what users get:
- ✅ Clean file set (no dev artifacts)
- ✅ No pre-existing configs
- ✅ No cached data
- ✅ No test databases
- ✅ Matches GitHub release archives

## Test Scenarios

### 1. Fresh Install Test
```bash
giltest.bat
# Choose: 2 (Clean install)

cd C:\install_test\Giljo_MCP
quickstart.bat
# Test: Does installer work with release files?
```

### 2. Upgrade Test (Preserve Data)
```bash
# First: Do a fresh install and configure
cd C:\install_test\Giljo_MCP
quickstart.bat
# ... complete installation ...

# Then: Simulate upgrade
cd C:\Projects\GiljoAI_MCP
giltest.bat
# Choose: 1 (Preserve data)

cd C:\install_test\Giljo_MCP
quickstart.bat
# Test: Does upgrade preserve database and config?
```

### 3. Release Verification
```bash
giltest.bat
# Check output:
# • File count: ~400 (not ~1,600)
# • Reduction: ~75% (dev files excluded)
# • Verify no test files, logs, or dev docs
```

## File Count Verification

After running `giltest.bat`, you should see:

```
📊 File Statistics:
   • Development (source): 1,600+ files
   • Release (copied):     ~400 files
   • Excluded (dev only):  ~1,200 files
   • Reduction:            ~75%
```

If you see significantly different numbers:
- More than 500 files → Some dev files leaked through
- Less than 300 files → Too aggressive, missing release files

## Directory Structure (After Simulation)

```
C:\install_test\Giljo_MCP\
├── api/                    # REST & WebSocket APIs
├── src/                    # Core application code
│   └── giljo_mcp/
├── frontend/               # Vue.js dashboard
├── installer/              # Installation modules
├── docs/                   # User documentation only
│   ├── AI_TOOL_INTEGRATION.md
│   └── (no Sessions/ or devlog/)
├── bootstrap.py            # Main installer entry
├── quickstart.bat          # Quick start script
├── setup.py               # Setup module
├── register_ai_tools.py   # AI tool integration
├── register_claude.bat    # Claude Code integration
├── register_codex.py      # Codex CLI integration
├── register_gemini.py     # Gemini CLI integration
├── register_grok.py       # Grok CLI integration
├── requirements.txt       # Python dependencies
├── README.md             # Main documentation
├── INSTALLATION.md       # Install guide
└── LICENSE               # License file
```

## Configuration

### Change Target Directory

Edit `giltest.py`:
```python
TEST_DIR = Path("C:/your/custom/path")
```

### Add/Remove Exclusions

Edit the `EXCLUDE_DIRS` and `EXCLUDE_FILES` lists in `giltest.py`.

These mirror `.gitattributes` but use robocopy patterns (no `**/` support).

## Troubleshooting

### "No files copied"
**Cause:** Robocopy failed or source directory issue
**Solution:** Check source path, run as administrator

### "Too many files copied"
**Cause:** Exclusion patterns not matching
**Solution:** Check `EXCLUDE_DIRS` and `EXCLUDE_FILES` in script

### "Key files missing"
**Cause:** Over-aggressive exclusions
**Solution:** Verify exclusions don't match release files

### "Antivirus blocking"
**Cause:** Security software blocking robocopy
**Solution:** Add exception for test directory

## Best Practices

### Before Each Test:
1. ✅ Commit your dev work (clean git state)
2. ✅ Run `giltest.bat` (fresh release simulation)
3. ✅ Test in `C:\install_test\Giljo_MCP`
4. ✅ Verify with clean slate (no dev environment)

### After Testing:
1. ✅ Document any installer issues found
2. ✅ Update exclusions if files leaked through
3. ✅ Verify file count stays around ~400

### Regular Checks:
- Compare file count to GitHub releases
- Verify no `.log` or `.db` files
- Check no `test_*.py` files present
- Ensure no `__pycache__/` directories

## Advanced Usage

### Dry Run (See What Would Copy)
Edit `giltest.py` and add to robocopy command:
```python
cmd.extend(["/L"])  # List only, don't copy
```

### Verbose Output
The script already shows robocopy progress. For more details, check robocopy logs.

### Multiple Test Environments
Create multiple target directories:
```python
TEST_DIR_STABLE = Path("C:/install_test/Giljo_MCP_stable")
TEST_DIR_BETA = Path("C:/install_test/Giljo_MCP_beta")
```

## Integration with CI/CD

Could be used in automated testing:
```yaml
# Example GitHub Actions workflow
- name: Simulate Release
  run: python giltest.py

- name: Test Installer
  working-directory: C:/install_test/Giljo_MCP
  run: python bootstrap.py --non-interactive
```

## Related Files

- `.gitattributes` - Defines `export-ignore` rules (source of truth)
- `.gitignore.release` - Additional release exclusions
- `create_distribution.sh/ps1` - Actual release creation scripts
- `MANIFEST.txt` - Release manifest (generated)

## Support

If `giltest.bat` isn't working:
1. Check Python 3.10+ is installed
2. Run from project root directory
3. Verify robocopy is available (Windows built-in)
4. Check write permissions on `C:\install_test\`

---

**Remember:** This simulates what users get from GitHub releases. Always test installers against this clean copy, not your development environment!