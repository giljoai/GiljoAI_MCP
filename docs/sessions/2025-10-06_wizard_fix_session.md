# Session: Setup Wizard Critical Fixes

**Date**: October 6, 2025
**Time**: ~1:00 PM - 1:15 PM (afternoon session)
**Context**: Emergency fix session - setup wizard broken after morning implementation

## Session Overview

The setup wizard, which was added around 2:00 AM, was completely non-functional by 9:50 AM. This session focused on identifying and fixing seven distinct critical issues that prevented the wizard from functioning. The problems ranged from build-time SASS compilation errors to runtime API communication failures.

## Initial State

- **Backend**: Running on localhost:7272, responding to health checks
- **Frontend**: Build failing with SASS errors, wizard inaccessible
- **Setup Status**: Database configured, but wizard broken
- **User Impact**: Complete inability to complete initial setup or reconfigure

## Issues Identified and Fixed

### 1. SASS Compilation Error (commit 989e1da)

**Root Cause**: Over-engineered vite.config.js from wizard implementation created conflicting SASS @use rules.

**Error Message**:
```
@use rules must be written before any other rules
```

**Technical Details**:
- The wizard commit added multiple custom CSS plugins to vite.config.js
- These plugins injected SASS @use statements in the wrong order
- SASS spec requires @use/@forward rules appear before any other CSS rules
- Files added: css-import-plugin.js, vite-vuetify-css-resolver.js, css-transformer.js, vitest-loader.js

**Solution**:
- Reverted vite.config.js to minimal, known-working configuration
- Removed all custom CSS plugin files (5 files deleted)
- Deleted orphaned settings.scss that was causing conflicts
- Let Vite and Vuetify handle CSS imports naturally

**Files Modified**:
- `frontend/vite.config.js` - Simplified to basic Vuetify setup
- `frontend/src/styles/settings.scss` - Deleted
- `frontend/vite-plugins/*.js` - All 5 plugin files deleted

**Lesson**: Vite and Vuetify 3 have built-in CSS handling. Custom plugins are rarely needed and often cause more problems than they solve.

---

### 2. Vue Stepper Slot Syntax Error (commit 7a43efa)

**Root Cause**: Using non-existent `v-stepper-window-item` component instead of proper Vuetify 3 slot syntax.

**Error Message**:
```
[Vue warn]: Slot "default" invoked outside of the render function
```

**Visual Impact**: Completely blank wizard screens, no stepper content visible

**Technical Details**:
- Vuetify 2 used `v-stepper-content` components
- Vuetify 3 uses `v-stepper-window` with `template v-slot` syntax
- The implementation used a non-existent hybrid approach
- Vue couldn't render the stepper items, causing blank screens

**Incorrect Code**:
```vue
<v-stepper-window-item :value="1">
  <!-- Content -->
</v-stepper-window-item>
```

**Correct Code**:
```vue
<v-stepper-window>
  <template v-slot:item.1>
    <!-- Content -->
  </template>
  <template v-slot:item.2>
    <!-- Content -->
  </template>
  <template v-slot:item.3>
    <!-- Content -->
  </template>
</v-stepper-window>
```

**Files Modified**:
- `frontend/src/views/SetupWizard.vue` - Complete stepper structure rewrite

**Lesson**: Always verify component API changes between major versions. Vuetify 3 has significant breaking changes from Vuetify 2.

---

### 3. Router Blocking Wizard Access (commit 3385d4e)

**Root Cause**: Router guard redirecting `/setup` to `/` when setup was already completed.

**Error Impact**: "Re-run Setup Wizard" button did nothing - users couldn't access wizard after initial setup.

**Technical Details**:
- Router beforeEach guard checked `setup.completed` status
- If completed, forced redirect to dashboard
- Made wizard inaccessible for reconfiguration or troubleshooting
- No way to modify network settings or MCP configuration post-setup

**Solution**:
- Removed the redirect logic from router guard
- Allow `/setup` route access regardless of completion status
- Let SetupWizard component handle its own state logic
- Users can now re-run wizard as needed

**Files Modified**:
- `frontend/src/router/index.js` - Removed redirect guard

**Lesson**: Don't enforce business logic in routing guards. Let components manage their own accessibility.

---

### 4. CORS Middleware Order Bug (commit 40c8cc4)

**Root Cause**: CORS middleware executing LAST instead of FIRST due to FastAPI middleware order reversal.

**Error Message**:
```
Access to fetch at 'http://localhost:7272/api/setup/status' from origin 'http://localhost:7274'
has been blocked by CORS policy: No 'Access-Control-Allow-Origin' header is present on the
requested resource.
```

**Technical Details**:
- FastAPI applies middleware in REVERSE order of addition
- Middleware added first executes LAST in the request chain
- Middleware added last executes FIRST in the request chain
- CORS was added first, so it executed last (after other middleware)
- By the time CORS middleware ran, response was already sent

**Original Code (WRONG)**:
```python
# CORS added first = executes LAST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7274"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auth added second = executes SECOND
app.add_middleware(AuthenticationMiddleware)

# Tenant added third = executes FIRST
app.add_middleware(TenantMiddleware)
```

**Fixed Code (CORRECT)**:
```python
# Tenant added first = executes LAST
app.add_middleware(TenantMiddleware)

# Auth added second = executes SECOND
app.add_middleware(AuthenticationMiddleware)

# CORS added last = executes FIRST
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:7274"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

**Request Flow After Fix**:
1. Request arrives → CORS middleware (first to execute)
2. CORS adds headers → Auth middleware
3. Auth validates → Tenant middleware
4. Tenant sets context → Endpoint handler
5. Response with CORS headers returns to browser

**Files Modified**:
- `api/app.py` - Reversed middleware order

**Lesson**: FastAPI middleware order is counterintuitive. Always add CORS middleware LAST in code so it executes FIRST in the request chain.

---

### 5. DashboardView API Error (commit 81410d5)

**Root Cause**: Calling `api.get()` directly when `api` is a structured object, not an Axios instance.

**Error Message**:
```javascript
TypeError: api.get is not a function
```

**Technical Details**:
- Frontend has structured API services: `setupService`, `agentService`, etc.
- The `api` import is an object containing these services
- DashboardView tried to call `api.get('/api/setup/status')`
- Should have called `setupService.checkStatus()`

**Incorrect Code**:
```javascript
import api from '@/services/api';

const response = await api.get('/api/setup/status');
```

**Correct Code**:
```javascript
import { setupService } from '@/services/api';

const response = await setupService.checkStatus();
```

**Files Modified**:
- `frontend/src/views/DashboardView.vue` - Fixed API service import

**Lesson**: Use structured service methods, not raw API calls. It provides type safety and consistent error handling.

---

### 6. Wizard Redirect Loop (commit 69c6658)

**Root Cause**: SetupWizard's `onMounted` hook checking setup status and redirecting immediately.

**Visual Impact**: Wizard flashed on screen for split second, then redirected back to dashboard.

**Technical Details**:
- SetupWizard component checked `setup.completed` in `onMounted()`
- If true, immediately called `router.push('/')`
- Created redirect loop: Dashboard → Wizard → Dashboard
- Users couldn't modify configuration or troubleshoot

**Solution**:
- Removed `onMounted` redirect logic
- Allow wizard to load regardless of completion status
- Display current configuration if already completed
- Users can modify settings and re-save

**Files Modified**:
- `frontend/src/views/SetupWizard.vue` - Removed onMounted redirect

**Lesson**: Don't duplicate routing logic in components. If a route is accessible, the component should render.

---

### 7. Missing MCP Configuration Endpoints (commit c406fa8)

**Root Cause**: Frontend wizard called non-existent `/api/setup/generate-mcp-config` endpoint.

**Error Message**:
```
404 Not Found: /api/setup/generate-mcp-config
```

**Technical Details**:
- Step 1 "Attach Tools" needed to generate MCP configuration
- Required endpoints:
  - `POST /api/setup/generate-mcp-config` - Generate .claude.json config
  - `POST /api/setup/register-mcp` - Write config to user's home directory
- Neither endpoint existed in backend

**Implementation**:
- Added `McpConfigRequest` and `McpConfigResponse` Pydantic models
- Added `RegisterMcpRequest` and `RegisterMcpResponse` models
- Implemented endpoint to auto-detect venv Python path
- Implemented endpoint to write to `~/.claude.json` with backup
- Added error handling for file write failures

**Generated Config Example**:
```json
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "F:\\GiljoAI_MCP\\venv\\Scripts\\python.exe",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_MCP_HOME": "F:/GiljoAI_MCP",
        "GILJO_SERVER_URL": "http://localhost:7272"
      }
    }
  }
}
```

**Files Modified**:
- `api/endpoints/setup.py` - Added two new endpoints with full implementation

**Features Added**:
- Auto-detection of virtual environment Python interpreter
- Safe file writing with backup creation
- Cross-platform path handling (Windows/Linux/macOS)
- Error handling for permission issues
- JSON config merging with existing .claude.json

**Lesson**: Always implement backend endpoints before building frontend UI that depends on them.

---

## Final System State

### Working Features
- Setup wizard accessible at `http://localhost:7274/setup`
- All 3 wizard steps functional:
  1. **Attach Tools**: Generates and registers MCP configuration
  2. **Network Configuration**: Configure CORS and API settings
  3. **Complete Setup**: Finalizes configuration
- Frontend-backend communication working
- CORS properly configured
- API responding on localhost:7272
- Frontend serving on localhost:7274
- PostgreSQL database connected

### Configuration
- **Mode**: localhost
- **API**: http://localhost:7272
- **Frontend**: http://localhost:7274
- **Database**: PostgreSQL 18 on localhost:5432
- **Setup Status**: completed=true
- **MCP Tools**: Registered in ~/.claude.json

### Files Modified (Total: 7 commits)
1. `frontend/vite.config.js`
2. `frontend/src/views/SetupWizard.vue`
3. `frontend/src/router/index.js`
4. `api/app.py`
5. `frontend/src/views/DashboardView.vue`
6. `api/endpoints/setup.py`
7. Deleted 5 CSS plugin files + settings.scss

## Key Technical Insights

### FastAPI Middleware Order
The most subtle bug was CORS middleware order. FastAPI's middleware stack is counterintuitive:

```
Code Order (add_middleware calls):
1. Middleware A (added first)
2. Middleware B (added second)
3. Middleware C (added third)

Execution Order (request flow):
1. Middleware C (executes first) ← Added last!
2. Middleware B (executes second)
3. Middleware A (executes last) ← Added first!
```

**Rule**: Add CORS middleware LAST so it executes FIRST.

### Vuetify 3 Stepper API
Major breaking change from Vuetify 2:

**Vuetify 2**:
```vue
<v-stepper-content step="1">
  <!-- Content -->
</v-stepper-content>
```

**Vuetify 3**:
```vue
<v-stepper-window>
  <template v-slot:item.1>
    <!-- Content -->
  </template>
</v-stepper-window>
```

### SASS @use Rule Ordering
SASS is strict about import order:

```scss
// ✅ CORRECT
@use 'vuetify/settings';
.my-class { }

// ❌ WRONG - Build error
.my-class { }
@use 'vuetify/settings'; // Error: @use must come first
```

## Lessons Learned

1. **Keep Build Config Simple**: Vite and Vuetify have excellent defaults. Custom plugins often cause more problems than they solve.

2. **Understand Framework Quirks**: FastAPI's reversed middleware order is counterintuitive but documented. Always check framework docs for gotchas.

3. **Component API Compatibility**: Major version upgrades (Vuetify 2→3) have breaking changes. Don't assume syntax compatibility.

4. **Backend-First Development**: Implement API endpoints before building UI that depends on them. Prevents 404 errors and rework.

5. **Let Components Manage State**: Don't duplicate business logic in router guards. Components should control their own accessibility.

6. **Use Structured Services**: Prefer `setupService.checkStatus()` over `api.get('/path')`. Better type safety and consistency.

7. **Test After Every Commit**: Each commit introduced a new problem. More frequent testing would have caught issues earlier.

## Related Documentation

- [Technical Architecture](../TECHNICAL_ARCHITECTURE.md) - System design
- [MCP Tools Manual](../manuals/MCP_TOOLS_MANUAL.md) - MCP configuration details
- [Quick Start Guide](../manuals/QUICK_START.md) - Setup wizard usage
- [Devlog: Wizard Complete Fix](../devlog/2025-10-06_wizard_complete_fix.md) - Completion report
