# DevLog: Port Scheme Standardization to 727x Range

**Date**: 2025-10-02
**Component**: Infrastructure, Configuration
**Type**: Enhancement
**Status**: Completed

## Summary

Standardized all service ports to a unified 727x range to eliminate conflicts with common developer tools and establish a professional, memorable port allocation scheme.

## Problem

The application was using mixed ports that could conflict with standard developer tools:
- Frontend on 3000 (conflicts with React, Create React App)
- WebSocket on 8001 (conflicts with Django dev server, Tornado)
- Various hardcoded ports across different config files

This created friction for developers running multiple applications simultaneously.

## Solution

Implemented a unified 727x port allocation scheme:
- **7272**: Backend API (HTTP + WebSocket + MCP)
- **7273**: Reserved for WebSocket service (currently unified)
- **7274**: Frontend/Dashboard

## Changes

### Configuration Updates

1. **installer/cli/install.py** (main + test)
   ```python
   @click.option('--ws-port', default=7273)        # was 8001
   @click.option('--dashboard-port', default=7274)  # was 3000
   ```

2. **frontend/vite.config.js** (main + test)
   ```javascript
   const FRONTEND_PORT = parseInt(
     process.env.VITE_FRONTEND_PORT ||
     process.env.GILJO_FRONTEND_PORT ||
     '7274',  // was '6000'
     10
   )
   ```

3. **start_giljo.py** (main + test)
   ```python
   SERVICES = {
     "backend": {"port": 7272},      # unchanged
     "dashboard": {"port": 7274}     # was 3000
   }
   ```

4. **.env** (test installation)
   ```bash
   GILJO_FRONTEND_PORT=7274
   VITE_FRONTEND_PORT=7274
   ```

### Testing

Verified successful launch in test installation:
- Backend health check passed on 7272
- Frontend started correctly on 7274
- No port conflicts detected
- Service communication functional

## Benefits

1. **Professional**: Unique port range specific to GiljoAI
2. **Zero Conflicts**: Avoids all common developer tool ports
3. **Memorable**: Sequential 727x pattern easy to remember
4. **Scalable**: Room for future services (7275-7279)
5. **Consistent**: All ports follow same pattern

## Migration Impact

**Existing Installations**:
- Require re-running installer OR manual .env update
- No breaking changes to API contracts
- Services auto-detect new ports from environment

**New Installations**:
- Automatically use new port scheme
- No additional configuration needed

## Technical Notes

- Frontend config prioritizes environment variables over defaults
- Launcher reads ports from config.yaml or .env files
- Backward compatible with explicit port configuration
- All port references updated across entire codebase

## Related Work

- Fixed Windows npm.cmd issue in launcher
- Updated frontend service manager for npm run dev support
- Synchronized configs between main repo and test installation

## Verification

```bash
# Test installation successful launch
cd C:/install_test/Giljo_MCP
python start_giljo.py

# Verified:
# ✅ Backend on 7272 (health check passed)
# ✅ Frontend on 7274 (npm run dev)
# ✅ No conflicts
# ✅ Clean startup logs
```

## Next Steps

- Monitor for any edge cases in production deployments
- Update user documentation with new default ports
- Consider documenting port scheme in README

## Files Modified

- `installer/cli/install.py`
- `frontend/vite.config.js`
- `start_giljo.py`
- `C:/install_test/Giljo_MCP/.env`
- `docs/session/2025-10-02_port_scheme_update.md` (new)
- `docs/devlog/2025-10-02_port_scheme_standardization.md` (this file)
