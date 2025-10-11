# GiljoAI MCP v3.0 - Fresh Install Fix Project

**Context**: Fresh installation broken - backend fails, setup wizard has obsolete flow, verbose mode not working
**Reference**: `docs/VERIFICATION_OCT9.md` - Complete architecture and issue analysis
**Priority**: CRITICAL - Blocks all new users from installing
**Agent Type**: TDD Implementor + System Architect

---

## Executive Summary

GiljoAI MCP v3.0 underwent a major refactoring (Oct 8, commit `9375722`) to **eliminate deployment modes** and adopt a **single unified architecture**. However, three critical issues prevent fresh installations from working:

1. **Backend fails to start** - root cause unknown
2. **Verbose mode broken** - console windows don't open
3. **Setup wizard obsolete** - still references deleted deployment modes, admin account conditional instead of required

**Your Mission**: Fix all three issues so fresh installations work perfectly.

---

## Critical Context: v3.0 Architecture

### What Changed (v2.x → v3.0)

**DELETED** in v3.0:
- ❌ Deployment modes (LOCAL/LAN/WAN) - **completely removed**
- ❌ `DeploymentMode` enum - **ImportError if referenced**
- ❌ Mode-based configuration - **no conditional binding**
- ❌ Optional admin account - **now ALWAYS required**

**NEW** in v3.0:
- ✅ Always bind to `0.0.0.0` (all interfaces)
- ✅ OS firewall controls access (defense in depth)
- ✅ Authentication always enabled (no bypass)
- ✅ Auto-login for localhost clients (127.0.0.1, ::1)
- ✅ Database always on localhost (security)
- ✅ Single codebase for all deployment contexts

### Configuration Example (v3.0)

```yaml
services:
  api:
    host: 0.0.0.0  # ALWAYS (not conditional on mode)

database:
  host: localhost  # ALWAYS (never exposed to network)

features:
  authentication: true  # ALWAYS enabled
  auto_login_localhost: true  # Auto-grant for localhost
```

**Read**: `docs/VERIFICATION_OCT9.md` for complete architecture details.

---

## Issue #1: Backend Fails to Start ⚠️ CRITICAL

### Symptom
User tried to manually start backend after fresh install - **FAILED**
Error message: Unknown (needs investigation)

### Investigation Steps

1. **Get actual error**:
   ```bash
   # Ask user to run and provide full error output
   F:\GiljoAI_MCP\venv\Scripts\python.exe api\run_api.py
   ```

2. **Test venv integrity**:
   ```bash
   # Test Python executable
   venv\Scripts\python.exe -c "import sys; print(sys.executable)"

   # Test critical imports
   venv\Scripts\python.exe -c "import fastapi, uvicorn, sqlalchemy; print('OK')"
   ```

3. **Test database connection**:
   ```bash
   # Verify database exists
   psql -U postgres -l | grep giljo_mcp

   # Test connection
   psql -U postgres -d giljo_mcp -c "\dt"
   ```

4. **Check config.yaml**:
   - Verify `services.api.host: 0.0.0.0` (not 127.0.0.1)
   - Verify `database.host: localhost`
   - Verify no syntax errors

5. **Check .env**:
   - Verify `DATABASE_URL` is correct
   - Verify PostgreSQL password matches

### Likely Root Causes
- Corrupted venv (missing packages)
- Database connection failure (wrong credentials)
- Config.yaml parsing error
- Port 7272 already in use
- Import errors (missing dependencies)

### Fix Strategy
Once root cause identified:
- Fix venv if corrupted: `deactivate && rm -rf venv && python -m venv venv && pip install -r requirements.txt`
- Fix database if connection fails: Update credentials in .env
- Fix config if parsing fails: Regenerate config.yaml
- Fix port if conflict: Kill process on 7272 or change port

---

## Issue #2: Verbose Mode Not Working ⚠️ HIGH

### Symptom
Running `python startup.py --verbose` does NOT open console windows
Expected: API and frontend servers open in NEW visible console windows
Actual: Processes start but no console windows visible

### Current Implementation

**File**: `startup.py:327-380`

```python
def start_api_server(verbose: bool = False) -> Optional[subprocess.Popen]:
    popen_kwargs = {"cwd": str(Path.cwd())}

    if verbose and platform.system() == "Windows":
        # CREATE_NEW_CONSOLE flag = 0x00000010
        popen_kwargs["creationflags"] = 0x00000010
        print_success("API server will open in new console window")
    else:
        popen_kwargs["stdout"] = subprocess.PIPE
        popen_kwargs["stderr"] = subprocess.PIPE

    process = subprocess.Popen(
        [python_executable, str(api_script)],
        **popen_kwargs
    )
    return process
```

### Diagnosis Steps

1. **Verify flag parsing**:
   - Add debug print: `print(f"Verbose mode: {verbose}, creationflags: {popen_kwargs.get('creationflags')}")`
   - Run `python startup.py --verbose` and check output

2. **Test console creation**:
   ```python
   # Test script to verify CREATE_NEW_CONSOLE works
   import subprocess, sys
   proc = subprocess.Popen(
       [sys.executable, "-c", "print('Test'); input('Press Enter')"],
       creationflags=0x00000010
   )
   # Should open NEW console window
   ```

3. **Check venv Python path**:
   - Verify `python_executable` resolves correctly
   - Ensure it's the venv Python, not system Python

### Fix Strategy

**Add debug logging** to startup.py:
```python
def start_api_server(verbose: bool = False):
    popen_kwargs = {"cwd": str(Path.cwd())}

    if verbose:
        if platform.system() == "Windows":
            popen_kwargs["creationflags"] = 0x00000010
            print_success(f"API server opening in NEW console (flag: {hex(0x00000010)})")
        else:
            print_warning("Verbose mode only supported on Windows currently")
    else:
        popen_kwargs["stdout"] = subprocess.PIPE
        popen_kwargs["stderr"] = subprocess.PIPE

    # Debug output
    print_info(f"Starting API server with: {popen_kwargs}")

    process = subprocess.Popen([python_executable, str(api_script)], **popen_kwargs)
    return process
```

**Apply same fix to** `start_frontend_server()` function.

---

## Issue #3: Setup Wizard Obsolete ⚠️ CRITICAL

### Symptom
Setup wizard still has v2.x flow:
1. Database Test (WRONG - should be last)
2. **Deployment Mode** (OBSOLETE - doesn't exist in v3.0)
3. **Admin Account** (CONDITIONAL - should be ALWAYS)
4. MCP Configuration
5. Serena Integration
6. Complete

### Correct Flow (v3.0)
1. **Admin Account** (ALWAYS - no condition)
2. MCP Configuration
3. Serena Integration
4. Database Test (courtesy check)
5. Complete

**NO deployment mode step** - it was deleted in v3.0!

### Files to Fix

#### 1. `frontend/src/views/SetupWizard.vue`

**Line 150-182**: Current step configuration (WRONG)

```javascript
// CURRENT (OBSOLETE)
const allSteps = [
  {
    component: DatabaseCheckStep,  // Position 0 - WRONG
    title: 'Database Test',
    name: 'database',
  },
  {
    component: DeploymentModeStep,  // ← DELETE THIS - obsolete!
    title: 'Deployment Mode',
    name: 'deploymentMode',
  },
  {
    component: AdminAccountStep,    // Position 2 - WRONG
    title: 'Admin Setup',
    name: 'adminSetup',
    showIf: (config) => config.deploymentMode === 'lan' || config.deploymentMode === 'wan',
    // ↑ REMOVE CONDITION - admin ALWAYS required in v3.0
  },
  {
    component: AttachToolsStep,     // Position 3
    title: 'MCP Configuration',
    name: 'attachTools',
  },
  {
    component: SerenaAttachStep,    // Position 4
    title: 'Serena Enhancement',
    name: 'serena',
  },
  {
    component: SetupCompleteStep,   // Position 5
    title: 'Complete',
    name: 'complete',
  },
]
```

**CHANGE TO**:

```javascript
// CORRECT (v3.0)
const allSteps = [
  {
    component: AdminAccountStep,    // Position 0 - FIRST
    title: 'Create Admin Account',
    name: 'adminSetup',
    // NO showIf - ALWAYS shown
    description: 'Create your administrator account for GiljoAI MCP'
  },
  {
    component: AttachToolsStep,     // Position 1
    title: 'MCP Tool Configuration',
    name: 'attachTools',
    description: 'Configure MCP tools (Claude Code, Cursor, Windsurf)'
  },
  {
    component: SerenaAttachStep,    // Position 2
    title: 'Serena Integration',
    name: 'serena',
    description: 'Enable Serena MCP enhancement (optional)'
  },
  {
    component: DatabaseCheckStep,   // Position 3 - LAST (courtesy)
    title: 'Database Connectivity',
    name: 'database',
    description: 'Verify PostgreSQL database connection'
  },
  {
    component: SetupCompleteStep,   // Position 4
    title: 'Setup Complete',
    name: 'complete',
  },
]
// DeploymentModeStep COMPLETELY REMOVED
```

**ALSO**:
- **Line 140**: Remove import of `DeploymentModeStep`
- **Line 186**: Remove `deploymentMode` from config reactive state
- **Line 143-148**: Remove `getStepProps` logic for `deploymentMode` case

#### 2. DELETE `frontend/src/components/setup/DeploymentModeStep.vue`

This file is obsolete - deployment modes don't exist in v3.0.

```bash
# Delete the file
rm frontend/src/components/setup/DeploymentModeStep.vue
```

#### 3. Update AdminAccountStep Component

**File**: `frontend/src/components/setup/AdminAccountStep.vue`

**Remove** any references to deployment mode:
- No conditional display logic
- No mode-specific instructions
- Admin account is ALWAYS created, not dependent on mode

---

## Testing Your Fixes

### Test 1: Fresh Install Flow

```bash
# 1. Drop database (simulate fresh install)
psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"

# 2. Run installer
python install.py

# 3. Verify setup wizard opens
# Should show: Admin Account step FIRST (not DB test)
```

**Expected Wizard Flow**:
1. ✅ **Admin Account** - Create username, password, email
2. ✅ **MCP Configuration** - Configure tools (skip if not needed)
3. ✅ **Serena Integration** - Enable checkbox (optional)
4. ✅ **Database Test** - Connection test (should pass)
5. ✅ **Complete** - Setup done, redirect to dashboard

### Test 2: Verbose Mode

```bash
# Start with verbose mode
python startup.py --verbose

# Expected:
# - NEW console window opens for API server (visible)
# - NEW console window opens for frontend server (visible)
# - Both show real-time output
```

### Test 3: Backend Startup

```bash
# Direct backend test
venv\Scripts\python.exe api\run_api.py

# Expected:
# - Server starts successfully
# - Binds to 0.0.0.0:7272
# - No errors in console
# - Health check responds: curl http://localhost:7272/health
```

---

## Success Criteria

**Issue #1: Backend Startup** ✅
- [ ] Root cause identified and documented
- [ ] Backend starts successfully: `python api/run_api.py`
- [ ] No import errors
- [ ] Database connection works
- [ ] Health endpoint responds: `http://localhost:7272/health`

**Issue #2: Verbose Mode** ✅
- [ ] `python startup.py --verbose` opens console windows
- [ ] API server console visible with real-time output
- [ ] Frontend server console visible with real-time output
- [ ] Debug logging shows creationflags being set

**Issue #3: Setup Wizard** ✅
- [ ] DeploymentModeStep deleted
- [ ] Admin Account step is FIRST (position 0)
- [ ] Admin Account ALWAYS shown (no showIf condition)
- [ ] Database Test is LAST (position 3)
- [ ] Fresh install shows correct step order
- [ ] Admin account creation works
- [ ] Setup completes and redirects to dashboard

---

## Important Files Reference

### Configuration
- `config.yaml` - Always has `services.api.host: 0.0.0.0`
- `.env` - Database credentials, ports, secrets
- `requirements.txt` - 19 core dependencies (v3.0)

### Backend
- `api/run_api.py` - Backend startup script
- `api/app.py` - FastAPI application
- `startup.py` - Unified launcher (API + frontend)

### Frontend
- `frontend/src/views/SetupWizard.vue` - Main wizard (FIX THIS)
- `frontend/src/components/setup/` - Step components
- `frontend/src/router/index.js` - Routing logic

### Documentation
- `docs/VERIFICATION_OCT9.md` - **READ THIS FIRST** - Complete architecture
- `docs/RELEASE_NOTES_V3.0.0.md` - v3.0 changes
- `CLAUDE.md` - Project instructions (being updated)

---

## Commands You'll Need

```bash
# Database
psql -U postgres -l                          # List databases
psql -U postgres -c "DROP DATABASE giljo_mcp;"  # Drop database
psql -U postgres -d giljo_mcp -c "\dt"       # List tables

# Python/Venv
venv\Scripts\python.exe -c "import fastapi"  # Test imports
venv\Scripts\python.exe api\run_api.py       # Start API directly
python install.py                            # Run installer
python startup.py --verbose                  # Start with verbose mode

# Process Management
netstat -an | findstr :7272                  # Check port
tasklist | findstr python                    # Find Python processes
taskkill /PID <pid> /F                       # Kill process

# Git
git status                                   # Check changes
git diff frontend/src/views/SetupWizard.vue  # See wizard changes
```

---

## Quick Start for You

1. **Read** `docs/VERIFICATION_OCT9.md` - Full context and architecture
2. **Investigate** Issue #1 (backend startup failure) - Get actual error
3. **Fix** Issue #3 (setup wizard) - Easiest to fix, clear requirements
4. **Fix** Issue #2 (verbose mode) - Add debug logging first
5. **Test** all three fixes with fresh install
6. **Document** what you found in `docs/VERIFICATION_OCT9.md`

---

## Questions? Read These First

- **Why no deployment modes?** - v3.0 unified architecture, firewall controls access
- **Why admin account first?** - v3.0 always requires auth, admin is mandatory
- **Why database test last?** - Courtesy check after setup, not a blocker
- **Why 0.0.0.0 binding?** - Defense in depth, OS firewall layer
- **Why auto-login localhost?** - Developer UX, TCP layer IP detection

**All answered in**: `docs/VERIFICATION_OCT9.md`

---

**Agent Assignment**: TDD Implementor + System Architect
**Priority**: CRITICAL - Blocks all fresh installations
**Timeline**: Fix all 3 issues
**Reference**: `docs/VERIFICATION_OCT9.md` - Complete analysis

**GO FIX IT!** 🚀
