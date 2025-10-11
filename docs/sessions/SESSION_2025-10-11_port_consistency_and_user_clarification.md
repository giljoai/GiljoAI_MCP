# Session: Port Consistency Fix and Database User Architecture Clarification

**Date**: 2025-10-11
**Context**: Continuation of installation workflow improvements started 2025-10-10

## Session Overview

This session addressed two important aspects of the installation system:
1. Port consistency between installer and control panel service launching
2. Clarification of the dual user/role architecture in database setup

## Previous Session Context

**2025-10-10 Work**: Fixed localhost redirect bug where axios interceptor was redirecting to `/login` even for localhost clients. Modified `frontend/src/services/api.js` to detect localhost and skip redirect.

**Relationship to Current Session**: Both sessions focus on improving the installation and service startup experience, ensuring consistent behavior and clear understanding of system architecture.

## Part 1: Port Consistency Fix

### Problem Identified

The `installer/cli/install.py` script was not using explicit port flags when launching services, while `dev_tools/control_panel.py` was using explicit port flags. This inconsistency could lead to:

- Services binding to different ports than configured
- Port conflicts not being detected early
- Confusion about which ports are actually in use
- Fallback to default ports instead of configured ports

### Implementation Details

**File Modified**: `installer/cli/install.py` (lines 789-865, `launch_services()` method)

**Changes Made**:

#### 1. Port Retrieval at Method Start

```python
# Get ports from settings for explicit binding
api_port = self.settings.get('api_port', DEFAULT_API_PORT)
frontend_port = self.settings.get('dashboard_port', DEFAULT_FRONTEND_PORT)
```

This ensures we have the configured ports available throughout the method.

#### 2. Backend API Launch (Verbose Mode)

**Before**:
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script)],
    stdout=None,
    stderr=None,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
)
```

**After**:
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script), "--port", str(api_port)],
    stdout=None,
    stderr=None,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NEW_CONSOLE if os.name == 'nt' else 0
)
```

#### 3. Backend API Launch (Non-Verbose Mode)

**Before**:
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script)],
    stdout=backend_log,
    stderr=subprocess.STDOUT,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
)
```

**After**:
```python
backend_process = subprocess.Popen(
    [str(python_executable), str(api_script), "--port", str(api_port)],
    stdout=backend_log,
    stderr=subprocess.STDOUT,
    cwd=str(api_dir),
    creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
)
```

#### 4. Frontend Launch

**Before**:
```python
npm_cmd = ['npm', 'run', 'dev']

frontend_process = subprocess.Popen(
    npm_cmd,
    # ... rest of process creation
)
```

**After**:
```python
npm_cmd = ['npm', 'run', 'dev', '--', '--port', str(frontend_port), '--strictPort']

frontend_process = subprocess.Popen(
    npm_cmd,
    # ... rest of process creation
)
```

**Note**: The `--strictPort` flag ensures Vite fails fast if the port is unavailable rather than trying alternative ports.

### Pattern Alignment

This change aligns `install.py` with the pattern already used in `dev_tools/control_panel.py`:

```python
# control_panel.py pattern (now matched by install.py)
subprocess.Popen([
    sys.executable,
    api_script,
    "--port", str(api_port)  # Explicit port specification
])

subprocess.Popen([
    npm_cmd,
    'run', 'dev',
    '--', '--port', str(frontend_port), '--strictPort'  # Explicit port + strict mode
])
```

### Benefits

1. **Consistency**: Both installer and control panel use identical service launch patterns
2. **Predictability**: Services always bind to configured ports, no silent fallbacks
3. **Early Detection**: Port conflicts surface immediately with clear error messages
4. **Configuration Respect**: System honors user's port selections from setup wizard
5. **Debugging**: Easier to troubleshoot port-related issues when behavior is consistent

### Testing Verification

To verify the fix works correctly:

```bash
# 1. Run installer
python installer/cli/install.py

# 2. Check that services bind to configured ports
# API should be on port from config.yaml (default 7272)
curl http://localhost:7272/health

# 3. Frontend should be on port from config.yaml (default 7274)
# Check browser opens to correct URL

# 4. Verify no port fallback occurred
# Check logs/api.log for actual binding port
```

## Part 2: Database User/Role Architecture Clarification

### User Question

"Why does the deletion report show '1 user' when the installer creates 2 users?"

### Architecture Explanation

The GiljoAI MCP system creates **two different types of users** during installation:

#### Type 1: PostgreSQL Roles (Database-Level Credentials)

**Location**: Created in `installer/core/database.py` (lines 202-297)

**Roles Created**:

1. **giljo_owner** - Owner role with full administrative privileges
   ```sql
   CREATE ROLE giljo_owner WITH LOGIN PASSWORD 'random_password_1';
   GRANT ALL PRIVILEGES ON DATABASE giljo_mcp TO giljo_owner;
   ALTER DATABASE giljo_mcp OWNER TO giljo_owner;
   ```

2. **giljo_user** - Standard application user role
   ```sql
   CREATE ROLE giljo_user WITH LOGIN PASSWORD 'random_password_2';
   GRANT CONNECT ON DATABASE giljo_mcp TO giljo_user;
   GRANT USAGE ON SCHEMA public TO giljo_user;
   GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO giljo_user;
   ```

**Purpose**:
- `giljo_owner`: Used for database migrations, schema changes, administrative tasks
- `giljo_user`: Used by running application for day-to-day operations (principle of least privilege)

**Credentials Storage**: Both passwords are randomly generated and stored in `.env`:
```env
# PostgreSQL roles
DB_OWNER_PASSWORD=<random_generated_password_1>
DB_USER_PASSWORD=<random_generated_password_2>
```

#### Type 2: Application Users (Users Table Records)

**Location**: Created during setup wizard, stored in `users` table

**Users Created**:

1. **Admin User** - Created during initial setup
   - Username: Provided by installer user
   - Password: Hashed and stored securely
   - Role: Admin (full application privileges)
   - Stored in database table: `users`

**Purpose**:
- Application-level authentication
- Dashboard login
- API access control
- Multi-user support (future)

### Deletion Report Breakdown

When the installer reports cleanup during uninstall:

```
Removing existing GiljoAI MCP installation...
Removed:
- giljo_mcp database
- 1 users                    ← Application users (users table records)
- X API keys                 ← API keys (api_keys table records)
- giljo_user role            ← PostgreSQL role #1
- giljo_owner role           ← PostgreSQL role #2
```

**Interpretation**:
- "1 users" = 1 application user account (admin user from setup wizard)
- "giljo_user role" = PostgreSQL database role #1
- "giljo_owner role" = PostgreSQL database role #2

**Total**: 2 PostgreSQL roles + 1 application user = 3 total user-related entities

The report IS showing both PostgreSQL roles being deleted (listed as separate line items), while "X users" specifically refers to application user accounts in the `users` table.

### Code References

**PostgreSQL Role Creation** (`installer/core/database.py`):

```python
# Lines 202-297
def create_roles(self, cursor, owner_password: str, user_password: str):
    """Create PostgreSQL roles for GiljoAI MCP."""

    # Create owner role
    cursor.execute(sql.SQL(
        "CREATE ROLE {} WITH LOGIN PASSWORD %s"
    ).format(sql.Identifier(self.owner_role)), [owner_password])

    # Create standard user role
    cursor.execute(sql.SQL(
        "CREATE ROLE {} WITH LOGIN PASSWORD %s"
    ).format(sql.Identifier(self.user_role)), [user_password])

    # Grant privileges...
```

**Application User Creation** (during setup wizard):

```python
# Created via API endpoint or direct database insert
# Stored in users table with hashed password
INSERT INTO users (username, email, password_hash, role)
VALUES ('admin', 'admin@example.com', '<hashed>', 'admin');
```

### Why This Architecture?

**Security Benefits**:
1. **Principle of Least Privilege**: Application runs with limited `giljo_user` role, not full admin
2. **Separation of Concerns**: Database operations separated from application authentication
3. **Migration Safety**: Schema changes use `giljo_owner`, protecting against accidental damage
4. **Audit Trail**: Clear separation between database-level and application-level access

**Operational Benefits**:
1. **Flexibility**: Can grant different database privileges without changing application code
2. **Multi-User Support**: Application users can be added/removed without affecting database roles
3. **Backup/Restore**: Database roles persist across application reinstalls
4. **Security Hardening**: Database credentials never exposed to end users

## Related Files

**Modified This Session**:
- `installer/cli/install.py` (lines 789-865)

**Related Files**:
- `dev_tools/control_panel.py` (reference implementation for port handling)
- `installer/core/database.py` (lines 202-297, role creation)
- `frontend/src/services/api.js` (fixed in previous session 2025-10-10)

## Next Steps

**Installation Workflow** (✅ Complete):
- Port consistency across all service launchers
- Localhost redirect handling
- Clear database architecture

**Potential Future Enhancements**:
1. Add port conflict detection before service launch
2. Provide clearer messaging about dual user architecture in installer output
3. Add option to customize PostgreSQL role names
4. Document role privilege grants in setup wizard output

## Lessons Learned

1. **Consistency Matters**: Even small inconsistencies in service launching can cause confusion and debugging pain
2. **Explicit > Implicit**: Explicit port flags prevent silent fallback behavior
3. **Architecture Clarity**: Complex architectures (like dual user systems) benefit from clear documentation
4. **Pattern Alignment**: When multiple entry points exist (installer, control panel, startup.py), ensure they follow the same patterns

## Related Documentation

- **Previous Session**: `SESSION_2025-10-10_localhost_redirect_fix.md`
- **Architecture**: `docs/TECHNICAL_ARCHITECTURE.md` (database layer)
- **Deployment**: `docs/guides/FIREWALL_CONFIGURATION.md` (port configuration)
- **Installation**: `docs/manuals/INSTALL.md` (setup process)
