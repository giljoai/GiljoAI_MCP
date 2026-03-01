# NPM/Vite Recurring Corruption Report

**Date**: 2026-03-01
**Branch**: 0750-cleanup-sprint
**Status**: Investigation complete, fixes pending

## Problem

`vite` repeatedly becomes unrecognized after previously working:
```
> giljo-mcp-frontend@3.0.0 dev
> vite --port 7274 --strictPort

'vite' is not recognized as an internal or external command
```

This has happened multiple times. The user must manually reinstall each time.

---

## Root Cause: Hollow Skeleton node_modules

`frontend/node_modules` is in a corrupted "skeleton" state — directories exist but all metadata, binaries, and the completion marker are missing:

| Check | Expected | Actual |
|---|---|---|
| `node_modules/.bin/` entries | ~50+ binaries | **0 (EMPTY)** |
| `node_modules/.package-lock.json` | present | **MISSING** |
| `package.json` files (any depth) | ~476 | **ZERO** |
| `node_modules/vite/` contents | package.json + bin + dist | **only `dist/` + nested `node_modules/`** |
| `node_modules/axios/` contents | package.json + lib + dist | **only `lib/`** |
| `node_modules/vue/` | full package | **ENTIRELY MISSING** |
| Total size | ~200MB+ healthy | **86MB (partial)** |

The skeleton is created by an **interrupted `npm install` or `npm ci`** — npm starts extracting packages, gets killed/interrupted, and leaves partially-extracted directories without metadata.

## Why It Persists (The Bug)

Two files check for node_modules using a flawed existence check that treats the skeleton as valid:

### `startup.py:618-622`
```python
# Check if node_modules exists
node_modules = frontend_dir / "node_modules"
if not node_modules.exists():        # <-- BUG: skeleton passes this check
    subprocess.run([npm_executable, "install"], cwd=str(frontend_dir), check=True)
```

### `dev_tools/control_panel.py:1191-1192`
```python
if not (frontend_dir / "node_modules").exists():   # <-- SAME BUG
    # prompt to install
```

Since the skeleton directory exists (86MB), both skip the reinstall. Vite stays broken indefinitely.

### Existing Proper Check (Not Used at Startup)

`install.py:1480-1516` already has `_verify_npm_dependencies()` that checks for critical packages (vue, vuetify, vue-router, pinia, axios, lodash-es). This is only used during initial installation, not during startup.

---

## Full Investigation Results

### Cleared Suspects

| Suspect | Evidence |
|---|---|
| Git hooks (`.git/hooks/pre-commit`) | Standard pre-commit framework hook — no npm commands |
| Pre-commit config (`.pre-commit-config.yaml`) | ESLint/Prettier hooks DISABLED (commented out). Active hooks exclude `node_modules` |
| `.gitattributes` filters | No smudge/clean/filter configs |
| Python test fixtures (`conftest.py`) | No references to node_modules or npm |
| PowerShell/bash profiles | None exist |
| Root `package.json` workspace conflict | No root package.json |
| Claude Code hooks | Empty hooks config `{}` |
| Disk space | 488GB free on F: |
| Git LFS interference | No LFS tracking patterns |
| npm config | Standard: `ignore-scripts=false`, `package-lock=true` |
| Backend Python scripts | Only `startup.py`, `install.py`, `control_panel.py` reference npm — none delete packages |
| Claude Code project settings | Only allows `Bash(git checkout:*)` — no npm hooks |

### Contributing Factor: Windows Defender

- Real-time monitoring: **ON**
- Current exclusion: only `F:\GiljoAI_MCP\frontend\node_modules`
- **Missing exclusions**: `node.exe` process, npm cache (`C:\Users\giljo\AppData\Local\npm-cache`), Node.js install (`C:\Program Files\nodejs`)

Defender scanning during npm install can cause file locking conflicts on Windows, leading to incomplete extractions.

---

## Fixes Required

### Fix 1: Immediate Recovery
```bash
cd frontend
rmdir /s /q node_modules
npm install
```

### Fix 2: Patch startup.py Health Check
Replace the directory existence check with a completion check:

**File**: `startup.py` (around line 618)

Change from:
```python
if not node_modules.exists():
```

To one of:
```python
# Option A: Check npm's completion marker
if not (node_modules / ".package-lock.json").exists():

# Option B: Check for the specific binary needed
if not (node_modules / ".bin" / "vite").exists() and not (node_modules / ".bin" / "vite.cmd").exists():

# Option C: Reuse install.py's verification (best but requires refactoring)
if not _verify_npm_dependencies(frontend_dir):
```

### Fix 3: Patch control_panel.py Health Check
Same change as Fix 2 in `dev_tools/control_panel.py` (around line 1191).

### Fix 4: Add Windows Defender Exclusions (PowerShell Admin)
```powershell
Add-MpPreference -ExclusionProcess "node.exe"
Add-MpPreference -ExclusionPath "C:\Users\giljo\AppData\Local\npm-cache"
Add-MpPreference -ExclusionPath "C:\Program Files\nodejs"
```

---

## Files Involved

| File | Role | Action Needed |
|---|---|---|
| `startup.py:618-622` | Startup frontend launch | Fix health check |
| `dev_tools/control_panel.py:1191-1192` | GUI frontend launch | Fix health check |
| `install.py:1480-1516` | Initial install verification | Reference implementation (already correct) |
| `frontend/package-lock.json` | Lock file | Healthy (lockfileVersion 3, 476 packages, vite 7.3.1) |
| `frontend/node_modules/` | Dependencies | Delete and reinstall |
