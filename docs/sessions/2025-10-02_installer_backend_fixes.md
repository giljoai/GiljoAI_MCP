# Session: Installer Backend Startup Fixes

**Date**: 2025-10-02
**Type**: Bug Fix & Debugging
**Status**: Completed ✅

## Summary

Diagnosed and fixed three critical bugs preventing the GiljoAI MCP backend from starting after installation. The backend was hanging during FastAPI startup due to database permission issues and configuration mismatches.

## Issues Discovered

### 1. Deployment Mode Case Mismatch
**File**: `installer/core/config.py:139`
**Symptom**: `ValueError: 'LOCAL' is not a valid DeploymentMode`
**Root Cause**: Installer generated `.env` with uppercase `GILJO_MCP_MODE=LOCAL`, but `DeploymentMode` enum expected lowercase values (`local`, `lan`, `wan`)
**Fix**: Changed deployment mode generation from `'LOCAL'/'LAN'` to `'local'/'lan'`

### 2. Wrong API Import Path
**File**: `installer/core/service_manager.py:145`
**Symptom**: Backend process started but never completed initialization
**Root Cause**: Service manager attempted to launch `api.main:app`, but the FastAPI application is located at `api.app:app`
**Fix**: Changed uvicorn import path from `'api.main:app'` to `'api.app:app'`

### 3. Missing PostgreSQL Schema Permissions
**File**: `installer/core/database.py:280-287`
**Symptom**: `asyncpg.exceptions.InsufficientPrivilegeError: permission denied for schema public`
**Root Cause**: Database installer only granted `USAGE` on public schema to `giljo_user`, but didn't grant access to existing tables/sequences
**Fix**: Added comprehensive permissions:
```sql
GRANT ALL ON SCHEMA public TO giljo_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO giljo_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO giljo_user;
```

## Debugging Process

1. **Initial Symptom**: Backend hung at "Waiting 10s for backend to start" during launcher execution
2. **Log Analysis**: Launcher logs showed process starting but failing health checks
3. **Direct Execution**: Ran backend directly with full output to capture actual error
4. **Error Identification**: FastAPI lifespan startup failed with PostgreSQL permission error
5. **Manual Fix**: Granted permissions manually to verify solution
6. **Code Fix**: Updated installer database setup to include proper permissions
7. **Verification**: Backend now starts successfully and passes health checks

## Files Modified

### Main Repository (C:/Projects/GiljoAI_MCP)
- `installer/core/config.py` - Fixed deployment mode case
- `installer/core/service_manager.py` - Fixed API import path
- `installer/core/database.py` - Added public schema permissions

### Test Installation (C:/install_test/Giljo_MCP)
- Same files updated for immediate testing
- `.env` file manually corrected for current installation

## Testing Results

**Before Fixes:**
- Backend: ❌ Failed to start (permission error)
- Health Check: ❌ Timeout
- Dashboard: ❌ Could not start (backend dependency)

**After Fixes:**
- Backend: ✅ Started successfully on port 7272
- Health Check: ✅ Passing
- API Endpoints: ✅ Available at `/docs`, `/health`, etc.
- Dashboard: ⚠️ Frontend issue (separate concern)

## Impact

- **Severity**: Critical - prevented any fresh installation from working
- **Scope**: All fresh installs using the localhost deployment mode
- **Resolution**: Complete - backend now starts successfully on fresh installations

## Commands for Manual Permission Fix (if needed)

```bash
# Grant permissions to existing giljo_mcp database
PGPASSWORD=$DB_PASSWORD "/c/Program Files/PostgreSQL/18/bin/psql.exe" -U postgres -d giljo_mcp -c "
  GRANT ALL ON SCHEMA public TO giljo_user;
  GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO giljo_user;
  GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO giljo_user;
"
```

## Lessons Learned

1. **Enum Value Casing**: Always verify case sensitivity when using Python enums with string values
2. **Import Path Verification**: Module structure should match actual file layout (no `api/main.py` existed)
3. **Database Permissions**: PostgreSQL 18 requires explicit schema-level grants; default privileges alone aren't sufficient for existing objects
4. **Testing Procedure**: Fresh installation testing is critical - development environments may mask permission issues

## Next Steps

- [ ] Dashboard frontend startup issue (file not found error)
- [ ] Consider adding automated permission verification to installer
- [ ] Update installer documentation with PostgreSQL 18 permission requirements
