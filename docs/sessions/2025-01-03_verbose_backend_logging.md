# Session: Backend Verbose Logging Implementation
**Date**: 2025-01-03
**Purpose**: Add comprehensive verbose logging to backend API for debugging and monitoring

## Context
- Working with symlinked setup between dev repo (C:\Projects\GiljoAI_MCP) and test installation (C:\install_test\Giljo_MCP)
- Database: PostgreSQL 18 with password 4010
- Standard ports: 7272, 7273, 7274
- Need visibility into backend operations and errors during testing

## Implementation Summary

### Files Modified
1. `api/run_api.py` - Enhanced startup logging and configuration
2. `api/app.py` - Added comprehensive initialization and error logging

### Key Changes

#### 1. Enhanced Logging Format
- Added file names and line numbers to all log messages
- Format: `%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s`
- Provides exact location context for every log entry

#### 2. Debug Level by Default
- Changed default log level from `info` to `debug`
- Added `--verbose` flag for convenience
- Ensures all uvicorn and FastAPI loggers use same level

#### 3. Early Initialization Logging
- Added logging before any imports to catch early errors
- Wrapped all imports with try/catch blocks
- Shows exactly which modules load successfully or fail

#### 4. Step-by-Step Initialization
Every initialization step now logs:
- Configuration loading
- Database connection and URL construction
- Table creation
- Tenant manager initialization
- Tool accessor setup
- Authentication manager configuration
- WebSocket manager startup
- Heartbeat task creation

#### 5. Enhanced Error Handling
- Full stack traces with `exc_info=True`
- Request path logging on errors
- Detailed exception types and messages
- Always shows error details (removed debug mode check)

## Logging Output Examples

### Successful Startup
```
2025-01-03 12:00:00 - api.app - INFO - [app.py:20] - Loading FastAPI application...
2025-01-03 12:00:00 - api.app - INFO - [app.py:29] - FastAPI and core dependencies loaded successfully
2025-01-03 12:00:00 - api.app - INFO - [app.py:69] - ======================================================================
2025-01-03 12:00:00 - api.app - INFO - [app.py:70] - Starting GiljoAI MCP API...
2025-01-03 12:00:00 - api.app - INFO - [app.py:71] - ======================================================================
2025-01-03 12:00:00 - api.app - INFO - [app.py:74] - Initializing configuration...
2025-01-03 12:00:00 - api.app - INFO - [app.py:76] - Configuration loaded successfully
2025-01-03 12:00:00 - api.app - INFO - [app.py:84] - Initializing database connection...
2025-01-03 12:00:00 - api.app - INFO - [app.py:103] - Connecting to database: localhost:5432/giljo_mcp
2025-01-03 12:00:00 - api.app - INFO - [app.py:175] - ======================================================================
2025-01-03 12:00:00 - api.app - INFO - [app.py:176] - API startup complete - All systems initialized
2025-01-03 12:00:00 - api.app - INFO - [app.py:177] - ======================================================================
```

### Error with Full Context
```
2025-01-03 12:00:00 - api.app - ERROR - [app.py:113] - Database initialization failed: connection refused
Traceback (most recent call last):
  File "/api/app.py", line 106, in lifespan
    state.db_manager = DatabaseManager(db_url, is_async=True)
  ...
psycopg2.OperationalError: could not connect to server: Connection refused
```

## Benefits
1. **Immediate Error Identification** - Know exactly where failures occur
2. **Module Loading Visibility** - See which imports succeed/fail
3. **Configuration Debugging** - View actual values being used
4. **Performance Monitoring** - Track initialization times
5. **Production Ready** - Can adjust log level for production deployment

## Usage
```bash
# Run with verbose logging (default)
python api/run_api.py

# Run with specific log level
python api/run_api.py --log-level info

# Force verbose mode
python api/run_api.py --verbose
```

## Testing Workflow
1. Make changes in dev repo (C:\Projects\GiljoAI_MCP)
2. Changes immediately reflected via symlinks
3. Restart server in test folder (C:\install_test\Giljo_MCP)
4. Monitor verbose console output for any issues
5. Debug using file:line references in logs

## Next Steps
- Monitor logs during test installation startup
- Identify and fix any initialization errors
- Consider adding performance metrics logging
- May want to add log rotation for production use