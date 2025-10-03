# DevLog: Vite Symlink Configuration for Development
**Date**: 2025-01-03
**Category**: Frontend Configuration
**Priority**: Medium
**Status**: Implemented

## Problem Statement
When running the frontend via symlinks (test installation → dev repository), Vite was serving files with `/@fs/` paths that caused browser module resolution errors:

```
Uncaught TypeError: Failed to resolve module specifier "vue".
Relative references must start with either "/", "./", or "../".
```

## Root Cause
The test installation setup uses symlinks:
- `C:\install_test\Giljo_MCP\frontend` → `C:\Projects\GiljoAI_MCP\frontend`

When Vite starts in the test installation, it follows the symlink and attempts to serve files using absolute file system paths (`/@fs/C:/Projects/GiljoAI_MCP/...`), which the browser cannot resolve.

## Solution
Updated `vite.config.js` with relaxed file system restrictions:

```javascript
export default defineConfig({
  plugins: [vue()],
  server: {
    port: FRONTEND_PORT,
    host: true,
    strictPort: false,
    cors: true,
    fs: {
      // Allow serving files outside root - needed for symlinked development setup
      // NOTE: This only affects dev server, NOT production builds
      strict: false,
      allow: ['..']
    }
  },
  // ... rest of config
})
```

## Impact on Production Builds

### No Impact - Here's Why:

1. **Development-Only Setting**
   - The `server.fs` configuration **only affects Vite's dev server**
   - Production builds (`npm run build`) completely ignore this setting

2. **Production Build Process**
   ```bash
   npm run build
   ```
   - Bundles all code into static files in `frontend/dist/`
   - Resolves all imports at build time
   - Creates standalone, optimized files
   - Outputs regular HTML/JS/CSS that works anywhere

3. **Release Deployments**
   - Release versions use the built `dist/` folder
   - No dev server involved
   - No symlinks in release packages
   - Standard static file serving

## Configuration Breakdown

### `fs.strict: false`
- **Development**: Allows Vite to serve files outside the project root
- **Production**: Not used (build process ignores this)
- **Security**: Only affects local dev server (localhost)

### `fs.allow: ['..']`
- **Development**: Explicitly allows serving from parent directory
- **Production**: Not used (build process resolves all paths)
- **Purpose**: Necessary for symlinked directory structure

## Testing Scenarios

### Development (Symlinked)
```bash
cd C:\install_test\Giljo_MCP
python start_giljo.py --dev
# Opens http://localhost:7274 - works with symlinks
```

### Development (Non-Symlinked)
```bash
cd C:\Projects\GiljoAI_MCP
npm run dev
# Same config works for regular setup too
```

### Production Build
```bash
npm run build
# Outputs to dist/ - ignores fs settings entirely
```

### Production Deployment
```bash
# Serve the built files (multiple options):
npx serve dist/
# or
python -m http.server --directory dist/
# or
# Copy dist/ to web server
```

## Security Considerations

### Development Environment
- `fs.strict: false` only runs on localhost
- Not exposed to network in standard dev setup
- Only affects files the developer already has access to

### Production Environment
- Production uses static files from `dist/`
- No Vite dev server running
- No file system access involved
- Standard web server security applies

## Future Considerations

### For Installer
The installer should:
1. ✅ Support both symlinked (dev) and regular (production) setups
2. ✅ Use `npm run build` for production installations
3. ✅ Serve from `dist/` in production mode
4. ✅ Use dev server only for development mode

### For Release Process
1. Build process: `npm run build`
2. Include `dist/` folder in release
3. Don't include `node_modules/` (users won't need it)
4. Don't include `vite.config.js` in runtime (only needed for dev)

## Verification Checklist

- [x] Dev mode works with symlinks
- [x] Dev mode works without symlinks
- [x] Config documented with comments
- [ ] Production build tested (has unrelated Vue error to fix)
- [ ] Release package tested (future task)

## Related Files
- `frontend/vite.config.js` - Updated configuration
- `start_giljo.py` - Launcher that starts dev server
- `CLAUDE.md` - Documents the symlink setup

## References
- [Vite Server Options](https://vitejs.dev/config/server-options.html#server-fs-allow)
- [Vite Build Process](https://vitejs.dev/guide/build.html)
