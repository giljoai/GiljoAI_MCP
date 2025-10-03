# Port Scheme Update to 727x Range

**Date**: 2025-10-02
**Session**: Port Scheme Standardization

## Overview

Updated the entire application port scheme from mixed ports to a unified 727x range to avoid conflicts with common developer tools.

## Motivation

The previous port allocation used common ports that could conflict with developer tools:
- Port 3000: Conflicts with React dev server, Create React App
- Port 8001: Conflicts with Django dev server, Tornado
- Port 5000: Conflicts with Flask

Using a unique 727x range ensures zero conflicts in typical developer environments.

## Port Allocation

### New Scheme (727x Range)
- **7272**: Backend API (HTTP + WebSocket + MCP) - *unchanged*
- **7273**: WebSocket Service (currently unified with backend)
- **7274**: Frontend/Dashboard

### Previous Scheme
- **7272**: Backend API - *unchanged*
- **8001**: WebSocket Service
- **3000/6000**: Frontend/Dashboard (varied by config)

## Files Modified

### Main Repository (C:/Projects/GiljoAI_MCP)

1. **installer/cli/install.py**
   - Updated `--ws-port` default: 8001 → 7273
   - Updated `--dashboard-port` default: 3000 → 7274

2. **frontend/vite.config.js**
   - Updated default frontend port: 6000 → 7274
   - Uses `VITE_FRONTEND_PORT` or `GILJO_FRONTEND_PORT` env vars

3. **start_giljo.py**
   - Updated dashboard service default port: 3000 → 7274
   - Maintained backend port at 7272

### Test Installation (C:/install_test/Giljo_MCP)

1. **.env**
   - Added `GILJO_FRONTEND_PORT=7274`
   - Added `VITE_FRONTEND_PORT=7274`
   - Updated all port references to use 727x scheme

2. **frontend/vite.config.js**
   - Same updates as main repository

3. **start_giljo.py**
   - Same updates as main repository

## Testing Results

Successfully tested launcher in test installation:
- ✅ Backend started on port 7272 and passed health check
- ✅ Frontend started on port 7274 using npm run dev
- ✅ No port conflicts detected
- ✅ Services communicate correctly

## Benefits

1. **Zero Conflicts**: Unique port range avoids common developer tool ports
2. **Professional**: Consistent 727x scheme easy to remember
3. **Scalable**: Room for future services (7275, 7276, etc.)
4. **Memorable**: Sequential numbering from project identifier

## Migration Notes

For existing installations:
1. Run installer again to update configuration
2. Or manually update `.env` file with new ports:
   - `GILJO_FRONTEND_PORT=7274`
   - `VITE_FRONTEND_PORT=7274`
3. Restart services with `start_giljo.py`

## Related Changes

- Frontend service manager updated to support npm run dev
- Windows-specific npm.cmd fix included
- All environment variable references updated
