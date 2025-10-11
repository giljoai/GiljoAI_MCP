# Installation Port Consistency Fix - Completion Report

**Date**: 2025-10-11
**Agent**: Documentation Manager
**Status**: Complete

## Objective

Ensure consistent port handling across all service launch entry points by aligning `installer/cli/install.py` with the explicit port specification pattern already used in `dev_tools/control_panel.py`. This prevents port fallback behavior and ensures services always bind to configured ports.

## Background

### Problem Statement

The GiljoAI MCP system has multiple entry points for launching services:
- `installer/cli/install.py` - Used during initial installation
- `dev_tools/control_panel.py` - Used for service management
- `startup.py` - Used for routine startup

Investigation revealed that `install.py` was NOT using explicit port flags when launching services, while `control_panel.py` WAS. This inconsistency could lead to:

1. **Silent Port Fallbacks**: Services binding to different ports than configured
2. **Configuration Mismatch**: Config says port 7272, service actually on port 7273
3. **Debugging Confusion**: "It works in control panel but not from installer"
4. **Port Conflicts**: Issues not detected until services start

### Context

This work completes the installation workflow improvements started in session 2025-10-10, where we fixed the localhost redirect bug in the axios interceptor. Both sessions focus on creating a smooth, predictable installation and startup experience.

## Implementation

### Files Modified

**Primary File**: `installer/cli/install.py`
- **Location**: Lines 789-865
- **Method**: `launch_services()`
- **Changes**: Added explicit port flags to both backend and frontend service launch commands

### Code Changes

#### 1. Port Variable Setup

Added port retrieval at the start of `launch_services()`:

```python
def launch_services(self, verbose: bool = False) -> Tuple[Optional[subprocess.Popen], Optional[subprocess.Popen]]:
    """Launch API and frontend services."""

    # Get ports from settings for explicit binding
    api_port = self.settings.get('api_port', DEFAULT_API_PORT)
    frontend_port = self.settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)

    # ... rest of method
```

#### 2. Backend API Launch - Verbose Mode

**Before** (lines 799-805):
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script)],  # ← No port flag
    stdout=None,
    stderr=None,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
)
```

**After**:
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script), "--port", str(api_port)],  # ← Added port
    stdout=None,
    stderr=None,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
)
```

#### 3. Backend API Launch - Non-Verbose Mode

**Before** (lines 813-819):
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script)],  # ← No port flag
    stdout=backend_log,
    stderr=subprocess.STDOUT,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
)
```

**After**:
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script), "--port", str(api_port)],  # ← Added port
    stdout=backend_log,
    stderr=subprocess.STDOUT,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
)
```

#### 4. Frontend Launch

**Before** (lines 834-835):
```python
npm_cmd = ['npm', 'run', 'dev']  # ← No port flags
```

**After**:
```python
npm_cmd = ['npm', 'run', 'dev', '--', '--port', str(frontend_port), '--strictPort']  # ← Added port + strict mode
```

**Key Addition**: The `--strictPort` flag tells Vite to fail fast if the port is unavailable rather than trying alternative ports (5174, 5175, etc.).

### Pattern Alignment

This brings `install.py` in line with the existing `control_panel.py` pattern:

```python
# dev_tools/control_panel.py (reference implementation)
def start_backend(self):
    subprocess.Popen([
        sys.executable,
        str(api_script),
        "--port", str(api_port)  # ← Explicit port
    ])

def start_frontend(self):
    subprocess.Popen([
        npm_cmd, 'run', 'dev',
        '--', '--port', str(frontend_port), '--strictPort'  # ← Explicit port + strict
    ])
```

Now both entry points use identical service launch patterns.

## Technical Details

### API Server Port Handling

The API server (`api/run_api.py`) accepts ports via:
1. Command-line flag: `--port 7272` (highest priority)
2. Environment variable: `GILJO_PORT` or `GILJO_API_PORT`
3. Config file: `config.yaml` → `services.api.port`
4. Default: 7272

By passing `--port` explicitly, we ensure the configured port is always used, bypassing environment variable confusion.

### Frontend Port Handling

Vite (frontend dev server) accepts ports via:
1. Command-line flag: `--port 7274` (highest priority)
2. Config file: `vite.config.js` → `server.port`
3. Default: 5173

**Without `--strictPort`**:
```bash
# If port 7274 is busy, Vite tries:
Port 7274 is in use, trying 7275...
Port 7275 is in use, trying 7276...
# Eventually binds to whatever is available
```

**With `--strictPort`**:
```bash
# If port 7274 is busy, Vite fails immediately:
Error: Port 7274 is already in use
# Forces user to resolve conflict
```

The strict mode prevents silent fallbacks that cause configuration mismatches.

### Cross-Platform Compatibility

All changes work across platforms:
- **Windows**: `subprocess.CREATE_NEW_CONSOLE` / `CREATE_NO_WINDOW` flags respected
- **Linux/macOS**: Standard subprocess behavior, flags ignored gracefully
- **Port Flags**: Universal across all platforms (uvicorn for API, Vite for frontend)

## Challenges

### Challenge 1: Maintaining Two Code Paths

The `launch_services()` method has two distinct code paths:
- Verbose mode: Services run in visible console windows
- Non-verbose mode: Services run hidden with output redirected to logs

**Solution**: Applied the port flag change to BOTH paths identically, ensuring consistent behavior regardless of verbosity setting.

### Challenge 2: Frontend Port Syntax

Initial attempt:
```python
npm_cmd = ['npm', 'run', 'dev', '--port', str(frontend_port)]  # ← WRONG
```

This passes `--port` to npm instead of Vite. The correct syntax requires `--` separator:

```python
npm_cmd = ['npm', 'run', 'dev', '--', '--port', str(frontend_port)]  # ← CORRECT
```

Everything after `--` gets passed to the underlying Vite command.

### Challenge 3: Preventing Silent Fallbacks

Without `--strictPort`, Vite's helpful behavior of finding alternative ports becomes a bug - users think the service is on port 7274 but it's actually on 7275.

**Solution**: Added `--strictPort` to force immediate failure on port conflicts, making issues visible during installation rather than runtime.

## Testing

### Manual Testing Checklist

✅ **Fresh Installation**:
```bash
python installer/cli/install.py
# Verified services bind to configured ports (7272, 7274)
# Checked no fallback to alternative ports occurred
```

✅ **Port Conflict Detection**:
```bash
# Start service on port 7272 manually
python api/run_api.py --port 7272

# Run installer (should detect conflict)
python installer/cli/install.py
# Verified clear error message about port 7272 being in use
```

✅ **Verbose Mode**:
```bash
python installer/cli/install.py
# Choose verbose launch option
# Verified port flags present in visible console windows
```

✅ **Non-Verbose Mode**:
```bash
python installer/cli/install.py
# Choose standard launch option
# Checked logs/api.log shows correct port binding
```

✅ **Cross-Entry Point Consistency**:
```bash
# Launch via installer
python installer/cli/install.py

# Stop services, launch via control panel
python dev_tools/control_panel.py

# Verified identical port binding behavior
```

### Verification Commands

```bash
# Check API server port
curl http://localhost:7272/health
# Expected: {"status": "healthy"}

# Check frontend port
curl http://localhost:7274
# Expected: Vite dev server response or dashboard HTML

# Verify no alternative ports in use
netstat -an | grep 7273  # Should be empty
netstat -an | grep 7275  # Should be empty
```

## Benefits

### 1. Predictability
Services ALWAYS bind to configured ports. No surprises.

### 2. Early Failure Detection
Port conflicts surface immediately during installation with clear error messages, not mysteriously during runtime.

### 3. Configuration Trust
Users can trust that config.yaml port settings are actually respected by the system.

### 4. Debugging Simplification
When troubleshooting, we can confidently say "service is on port 7272" without checking if it silently fell back to 7273.

### 5. Pattern Consistency
All service launch entry points (installer, control panel, startup.py) now use identical patterns, reducing cognitive load for developers.

## Additional Context: Database User/Role Architecture

During this session, a user question revealed confusion about the dual user architecture. For completeness, this devlog documents the clarification provided:

### PostgreSQL Roles vs Application Users

**GiljoAI MCP creates TWO types of users**:

#### Type 1: PostgreSQL Roles (Database Credentials)
Created in `installer/core/database.py` (lines 202-297):

1. **giljo_owner** - Full database admin privileges
   - Used for: Schema migrations, administrative tasks
   - Password: Randomly generated, stored in `.env`

2. **giljo_user** - Limited application privileges
   - Used for: Day-to-day application operations
   - Password: Randomly generated, stored in `.env`

#### Type 2: Application Users (Users Table)
Created during setup wizard, stored in `users` table:

1. **Admin User** - Application-level authentication
   - Used for: Dashboard login, API access
   - Password: User-provided, hashed and stored in database

### Why This Matters for Deletion Reports

When uninstalling, the report shows:
```
Removed:
- giljo_mcp database
- 1 users                    ← Application users (users table)
- X API keys                 ← API keys table
- giljo_user role            ← PostgreSQL role #1
- giljo_owner role           ← PostgreSQL role #2
```

**Interpretation**: "1 users" refers to application user accounts. The two PostgreSQL roles are listed separately. Total = 2 roles + 1 app user = 3 user-related entities.

This architecture provides security benefits (principle of least privilege) and operational flexibility (separate database and application authentication).

## Next Steps

**Completed in This Session**:
- ✅ Port consistency across installer and control panel
- ✅ Explicit port flags for both backend and frontend
- ✅ Strict port mode to prevent silent fallbacks
- ✅ Architecture clarification documentation

**Future Enhancements** (Not Required, Optional Improvements):
1. Add pre-launch port availability check with user-friendly messaging
2. Provide port conflict resolution options (kill existing process, choose new port)
3. Add port verification step after service launch (confirm binding succeeded)
4. Document the dual user architecture in installer output for clarity

**Related Work**:
- Previous Session (2025-10-10): Axios interceptor localhost redirect fix
- Both sessions complete the installation workflow improvements initiative

## Files Modified

### Primary Changes
- `installer/cli/install.py` (lines 789-865)
  - Added port variable setup
  - Modified verbose mode backend launch (+1 line)
  - Modified non-verbose mode backend launch (+1 line)
  - Modified frontend launch command (+1 flag, +1 option)

### Related Files (Reference Only, Not Modified)
- `dev_tools/control_panel.py` (reference implementation)
- `installer/core/database.py` (lines 202-297, role creation context)
- `api/run_api.py` (accepts --port flag)
- `frontend/vite.config.js` (port configuration)

## Lessons Learned

1. **Consistency is Critical**: Small inconsistencies between entry points cause disproportionate confusion
2. **Explicit > Implicit**: Explicit port flags prevent "it works on my machine" scenarios
3. **Fail Fast**: Strict port mode surfaces issues early when they're easier to fix
4. **Pattern Alignment**: When multiple codepaths exist, ensure they follow identical patterns
5. **Architecture Documentation**: Complex architectures (like dual user systems) need proactive documentation before questions arise

## Conclusion

This change completes the installation workflow improvements by ensuring predictable, consistent port binding behavior across all service launch entry points. Services now always bind to configured ports, conflicts are detected immediately, and users can trust their configuration settings are respected.

The port consistency fix, combined with the previous session's localhost redirect fix, creates a smooth installation experience where services behave predictably and users aren't surprised by unexpected redirects or port changes.

**Status**: ✅ Complete and production-ready
