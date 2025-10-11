# Simple Setup Fix - Agent Prompt

## Objective
Simplify the GiljoAI MCP setup flow by removing unnecessary complexity while preserving user choices and control.

## Current Problems
1. Setup wizard makes unnecessary API calls (products) during fresh install
2. Auth/me endpoint returns fake localhost user during setup mode
3. Products endpoint fails with tenant validation errors during setup mode
4. Too many steps for what should be a simple process

## Required Fixes

### 1. Remove Unnecessary Products API Call
**Location**: `frontend/src/views/SetupWizard.vue`
- Remove the products API call during initial setup (lines checking `/api/v1/products/`)
- Products are not needed for fresh installation
- This causes unnecessary errors and complexity

### 2. Fix Auth/Me Endpoint
**Location**: `api/endpoints/auth.py`
- Remove the fake localhost user return during setup mode
- Should return proper setup mode status instead of pretending to be a user
- Current fake user confuses the authentication state

### 3. Fix Tenant Dependency for Setup Mode
**Location**: `api/dependencies.py`
- The `get_tenant_key()` function should check for setup mode first
- In setup mode, return "default" without validation
- Only validate tenant when database is available
- This prevents "Invalid tenant key" errors during setup

### 4. Keep MCP Configuration in Web UI
**Location**: Already exists in the web UI as modal/page
- MCP configuration has been in the UI for a week now
- DO NOT add to install.py CLI
- Users configure MCP through the web interface after setup
- Has clickable links for downloading scripts

### 5. Keep Serena Toggle in Web UI
**Location**: Already exists in the web UI as modal/page
- Serena toggle has been in the UI for a week now
- DO NOT add to install.py CLI
- Users enable/disable Serena through the web interface after setup
- POST `/api/serena/toggle` endpoint already exists

### 6. Simplify Setup Wizard
**Location**: `frontend/src/views/SetupWizard.vue`
- Reduce from 7 steps to essential steps only:
  1. Welcome/Overview (keep)
  2. Admin Account Creation (keep)
  3. Complete (keep)
- Remove:
  - Products step (not needed for fresh install)
  - Database configuration (already in install.py)
  - Database test (already in install.py)

## Implementation Notes

### Preserve User Choices
- **DO NOT** remove user choice toggles from install.py
- **DO NOT** force any automatic actions
- Each step should remain optional with clear prompts
- "Start services" toggle already exists - keep it
- Database table creation already exists in install.py - keep it
- MCP configuration stays in web UI - NOT in CLI
- Serena toggle stays in web UI - NOT in CLI

### install.py Flow (Keep As Is)
```python
# Current flow is already correct:
1. Check prerequisites
2. Configure database (existing)
3. Create database tables (already there)
   - Run: alembic upgrade head
   - Optional choice toggle
4. Configure ports (existing)
5. Start services (existing - keep toggle)

# MCP and Serena are configured through web UI after setup
```

### Simplified Architecture
```
install.py (CLI)          →  Database/services configured
    ↓
Web UI                    →  Admin account creation
    ↓
Dashboard                 →  Configure MCP and Serena (UI modals)
```

Instead of:
```
install.py → Web Setup Wizard (7 steps) → Multiple API calls → Confusion → Ready
```

## Testing the Fix

1. Drop database: `psql -U postgres -c "DROP DATABASE IF EXISTS giljo_mcp;"`
2. Delete config.yaml
3. Run: `python installer/cli/install.py`
4. Verify:
   - Database and tables created
   - Services start
   - Can access web UI without errors
   - Can create admin account
   - MCP configuration available in dashboard
   - Serena toggle available in dashboard

## Benefits
- Faster setup for new users
- Less confusion about what's happening
- Database setup in install.py (where it belongs)
- Web UI for admin account creation
- MCP and Serena in dashboard UI (where users expect them)
- No duplicate functionality between CLI and UI

## Remember
- MCP configuration modal already exists in the web UI (for a week)
- Serena toggle already exists in the web UI (for a week)
- Database table creation already exists in install.py
- Don't add UI features to CLI
- Keep the flow simple and linear