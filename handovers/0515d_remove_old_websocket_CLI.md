# Handover 0515d: Remove Old WebSocket Files [CLI]

**Execution Environment**: CLI (Claude Code CLI - Local)
**Duration**: 2-3 hours
**Dependencies**: MUST complete 0515c first and verify V2 is working
**Branch**: Work directly on master after 0515c is merged

---

## Why CLI?
- File system operations (deleting files)
- Need to verify build still works locally
- Need to test WebSocket still functions
- Quick local validation required

---

## Scope

Delete all old WebSocket implementation files and references after V2 migration is complete and tested.

---

## Files to Delete

### Primary Files to Remove
```bash
frontend/src/websocket.js              # Old WebSocket implementation
frontend/src/flowWebSocket.js          # Flow-specific wrapper
frontend/src/stores/websocket.old.js   # Old store (if exists)
frontend/src/composables/useWebSocket.js # Old composable (if exists)
```

### Check for Additional Files
```bash
# Find all old WebSocket files
find frontend/src -name "*websocket*" -o -name "*WebSocket*" | grep -v V2

# Look for flow-related files
find frontend/src -name "*flow*" | grep -i websocket
```

---

## Pre-Deletion Checklist

### Step 1: Verify V2 is Working
```bash
# Start the application
cd frontend
npm run dev

# In browser:
# 1. Open DevTools > Network > WS tab
# 2. Verify WebSocket connection shows as "websocketV2"
# 3. Create an agent job
# 4. Verify real-time updates work
```

### Step 2: Check for References
```bash
# Ensure no components still import old files
grep -r "from.*websocket\.js" frontend/src/
grep -r "from.*flowWebSocket" frontend/src/
grep -r "import.*websocket\.js" frontend/src/
grep -r "import.*flowWebSocket" frontend/src/

# Check for any remaining old WebSocket usage
grep -r "WebSocket" frontend/src/ | grep -v "V2\|v2"
```

### Step 3: Backup Files (Just in Case)
```bash
# Create backup directory
mkdir -p frontend/src/websocket/backup

# Copy old files to backup
cp frontend/src/websocket.js frontend/src/websocket/backup/
cp frontend/src/flowWebSocket.js frontend/src/websocket/backup/
```

---

## Deletion Process

### Step 1: Delete Primary Files
```bash
# Remove old WebSocket files
rm -f frontend/src/websocket.js
rm -f frontend/src/flowWebSocket.js
rm -f frontend/src/stores/websocket.old.js
rm -f frontend/src/composables/useWebSocket.js
```

### Step 2: Clean Up Any References
If any imports still exist after deletion, update them:

```javascript
// OLD (will cause error after deletion)
import { websocket } from './websocket'

// NEW (should already be updated in 0515c)
import { useWebSocketV2 } from '@/websocket/useWebSocketV2'
```

### Step 3: Remove from Git
```bash
# Stage deletions
git rm frontend/src/websocket.js
git rm frontend/src/flowWebSocket.js

# Check what will be committed
git status
```

---

## Validation Steps

### Step 1: Build Verification
```bash
cd frontend

# Clear cache
rm -rf node_modules/.vite

# Build should succeed with no errors
npm run build

# Check for any import errors
# If errors, fix imports then rebuild
```

### Step 2: Runtime Verification
```bash
# Start dev server
npm run dev

# In browser console, verify:
# - No 404 errors for WebSocket files
# - No console errors about missing imports
# - WebSocket V2 connects successfully
```

### Step 3: Functional Testing
1. Open application in browser
2. Check WebSocket indicator shows "Connected"
3. Create a new agent job
4. Verify real-time status updates work
5. Refresh page
6. Verify WebSocket reconnects

### Step 4: Search for Stragglers
```bash
# Final check for any remaining references
grep -r "websocket\.js\|flowWebSocket" frontend/src/

# Should return nothing. If found, update those files.
```

---

## Common Issues & Fixes

### Issue: Build fails with import error
```
Module not found: Error: Can't resolve './websocket'
```
**Fix**: Find the component with bad import and update to use V2

### Issue: WebSocket not connecting
**Fix**: Verify 0515c was properly implemented and V2 is initialized in main.js

### Issue: Real-time updates stopped working
**Fix**: Check browser console, ensure V2 WebSocket is connecting to correct URL

### Issue: Found more WebSocket files
**Fix**: Determine if they're V2 files (keep) or old files (delete)

---

## Git Commit

After successful deletion and testing:

```bash
git add -A
git commit -m "cleanup: Remove old WebSocket implementation files

- Deleted websocket.js (old implementation)
- Deleted flowWebSocket.js (flow wrapper)
- Cleaned up all references
- WebSocket V2 is now the only implementation
- Verified build and runtime work correctly

Part of 0515d frontend consolidation"
```

---

## Final Verification

### Console Commands to Verify Success
```javascript
// In browser console after deletion
// Should work:
const wsStore = window.$pinia._s.get('websocket')
console.log(wsStore.isConnected) // true
console.log(wsStore.connectionState) // 'connected'

// Should fail:
console.log(window.flowWebSocket) // undefined
console.log(window.websocket) // undefined (unless V2 is named this)
```

### Network Tab Verification
1. Open DevTools > Network > WS
2. Should see single WebSocket connection
3. Connection name should indicate V2
4. Messages should flow for events

---

## Success Criteria

- [ ] Old WebSocket files deleted
- [ ] No references to old files remain
- [ ] Build succeeds with no errors
- [ ] WebSocket V2 connects properly
- [ ] Real-time updates still work
- [ ] No console errors
- [ ] Git commit created
- [ ] Backup files can be deleted after verification

---

## Rollback Plan

If issues arise after deletion:

```bash
# Restore from backup
cp frontend/src/websocket/backup/websocket.js frontend/src/
cp frontend/src/websocket/backup/flowWebSocket.js frontend/src/

# Or restore from git
git checkout HEAD~1 frontend/src/websocket.js
git checkout HEAD~1 frontend/src/flowWebSocket.js
```

---

**End of 0515d Scope**