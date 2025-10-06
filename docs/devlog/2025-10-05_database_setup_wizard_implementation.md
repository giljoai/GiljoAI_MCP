# Database Setup Wizard Implementation

**Date**: 2025-10-05
**Agent**: Database Expert Agent
**Status**: Backend Complete - Frontend Pending

## Overview

Implemented comprehensive PostgreSQL database setup functionality for the GiljoAI MCP setup wizard. The system now allows users to configure their database through the frontend wizard instead of requiring manual database setup.

## Components Implemented

### 1. Backend API Endpoints (`api/endpoints/database_setup.py`)

Created new module with two main endpoints:

#### `/api/setup/database/test-connection` (POST)
- **Purpose**: Test PostgreSQL connection without making changes
- **Accepts**: Host, port, admin username, admin password, database name
- **Returns**: Connection status, PostgreSQL version, whether database already exists
- **Error Handling**: Distinguishes between auth failures, connection refused, and other errors

#### `/api/setup/database/setup` (POST)
- **Purpose**: Complete database setup with migrations
- **Process**:
  1. Tests connection to PostgreSQL with admin credentials
  2. Creates `giljo_mcp` database if it doesn't exist
  3. Creates database roles (`giljo_owner`, `giljo_user`)
  4. Runs Alembic migrations to create schema
  5. Updates config.yaml with validated credentials
  6. Removes `setup_mode` flag to allow backend to start normally
  7. Creates backup of config.yaml before updating

- **Returns**: Success status, credentials file location, migration status, warnings
- **Security**: Stores credentials in separate file, uses app user (`giljo_user`) not admin

### 2. ConfigManager Updates (`src/giljo_mcp/config_manager.py`)

Added `setup_mode` flag support:

- **Flag Purpose**: Allows placeholder password (`"SETUP_REQUIRED"`) during initial setup
- **Implementation**:
  - Added `self.setup_mode = False` to `__init__`
  - Loads from config.yaml in `_load_from_file()`
  - Modified password validation to skip check if `setup_mode` is `True`
  - Prevents backend startup failures during wizard phase

### 3. API Router Registration (`api/app.py`)

- Imported `database_setup` module
- Registered router at `/api/setup/database` prefix
- Tagged as `database-setup` for API documentation

### 4. Database Installer Integration

Leveraged existing `DatabaseInstaller` class (`installer/core/database.py`):
- Uses production-grade database creation logic
- Generates secure passwords
- Handles role creation and permissions
- Runs Alembic migrations
- Creates credentials file for reference

## Key Features

### Multi-Step Setup Process

1. **Connection Test**: Validates credentials before proceeding
2. **Database Creation**: Creates database if it doesn't exist
3. **Role Setup**: Creates owner and application user roles
4. **Schema Migration**: Runs Alembic to create tables
5. **Config Update**: Writes validated credentials to config.yaml
6. **Cleanup**: Removes setup_mode flag

### Error Handling

- Specific error messages for common failures
- Auth failures distinguished from connection issues
- Graceful handling of existing databases
- Rollback capability (migrations run both directions)

### Security

- Admin credentials only used for setup, not stored permanently
- Application runs with limited `giljo_user` role
- Credentials backed up before updates
- Passwords generated securely using `secrets` module

## Configuration Flow

### Before Setup

```yaml
database:
  type: postgresql
  postgresql:
    host: localhost
    port: 5432
    database: giljo_mcp
    user: postgres
    password: "SETUP_REQUIRED"  # Placeholder
setup_mode: true  # Allows backend to start
```

### After Setup

```yaml
database:
  type: postgresql
  postgresql:
    host: localhost
    port: 5432
    database: giljo_mcp
    user: giljo_user  # Application user
    password: "**  # Generated secure password
# setup_mode removed - normal validation enabled
```

## Frontend Integration (Pending)

The `DatabaseStep.vue` component needs to be updated to:

1. Show input fields for PostgreSQL credentials
2. Pre-fill with sensible defaults (localhost, 5432, postgres)
3. Add "Test Connection" button
4. Add "Create Database & Run Migrations" button
5. Show progress indicators during setup
6. Display helpful error messages
7. Handle success and navigate to next step

## Testing Requirements

### Integration Tests Needed

1. Test connection endpoint with valid/invalid credentials
2. Test database setup with clean PostgreSQL instance
3. Test setup with existing database
4. Test config.yaml updates
5. Test setup_mode flag behavior
6. Test migration execution
7. Test error scenarios (connection refused, auth failed, etc.)

### Manual Testing Steps

1. Fresh install: Run minimal installer
2. Verify backend starts with `setup_mode: true`
3. Open setup wizard
4. Enter PostgreSQL admin credentials
5. Test connection
6. Create database
7. Verify backend restarts successfully
8. Check database schema is correct

## Files Modified

- `api/endpoints/database_setup.py` (NEW)
- `api/app.py` (Updated imports and router registration)
- `src/giljo_mcp/config_manager.py` (Added setup_mode flag support)

## Files Referenced

- `installer/core/database.py` (Existing DatabaseInstaller class)
- `alembic.ini` (Migration configuration)
- `frontend/src/components/setup/DatabaseStep.vue` (Needs update)

## Next Steps

1. Update `DatabaseStep.vue` with full setup UI
2. Create integration tests
3. Test end-to-end workflow
4. Update minimal installer to set `setup_mode: true` in generated config
5. Update setup wizard documentation

## Notes

- Database setup requires PostgreSQL 14-18 (18 recommended)
- Uses existing production-grade installer logic
- All database interactions use psycopg2 with proper error handling
- Alembic migrations ensure consistent schema
- Multi-tenant isolation enforced through `tenant_key` filtering

## Related Documentation

- `docs/IMPLEMENTATION_PLAN.md` - Setup wizard architecture
- `installer/core/DATABASE_IMPLEMENTATION.md` - Database installer details
- `docs/manuals/INSTALLATION.md` - Installation guide
