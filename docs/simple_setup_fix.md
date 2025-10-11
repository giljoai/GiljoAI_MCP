# Simple Setup Fix - Agent Prompt

## Objective
Simplify the GiljoAI MCP setup flow by removing unnecessary complexity while preserving user choices and control.

## Current Problems
1. Setup wizard makes unnecessary API calls (products) during fresh install
2. Auth/me endpoint returns fake localhost user during setup mode
3. Database table creation happens in web UI instead of install.py (where it used to be)
4. MCP integration and Serena toggle already exist but aren't properly integrated into flow
5. Too many steps for what should be a simple process

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

### 3. Move Database Table Creation Back to install.py
**Location**: `installer/cli/install.py`
- Database tables (via Alembic migrations) should be created during install.py execution
- This used to work and was removed - bring it back
- Add after database creation step (around line where database is configured)
- Use existing `DatabaseManager` and `alembic upgrade head` command
- Keep user choice toggle for this step (don't force it)

### 4. Integrate Existing MCP Script
**Location**: Already exists at `scripts/integrate_mcp.py`
- This script already detects Claude, Codex, Gemini CLI tools
- Add option in install.py to run MCP integration
- Keep as optional user choice
- Script modifies installers to add UniversalMCPInstaller support

### 5. Integrate Existing Serena Toggle
**Location**: Already exists at `api/endpoints/serena.py`
- POST `/api/serena/toggle` - enables/disables Serena in config.yaml
- GET `/api/serena/status` - returns current Serena status
- Add option in install.py to enable Serena
- Keep as optional user choice

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
  - MCP setup (already in install.py via integrate_mcp.py)

## Implementation Notes

### Preserve User Choices
- **DO NOT** remove user choice toggles from install.py
- **DO NOT** force any automatic actions
- Each step should remain optional with clear prompts
- "Start services" toggle already exists - keep it
- Add new toggles for:
  - Create database tables (via Alembic)
  - Integrate MCP tools
  - Enable Serena

### install.py Flow (Enhanced)
```python
# Existing flow with additions:
1. Check prerequisites
2. Configure database (existing)
3. Create database tables (RESTORE THIS - used to exist)
   - Run: alembic upgrade head
   - Keep as optional choice
4. Configure ports (existing)
5. Start services (existing - keep toggle)
6. Integrate MCP tools (NEW - use scripts/integrate_mcp.py)
   - Optional choice
   - Run existing integration script
7. Enable Serena (NEW - use api/endpoints/serena.py)
   - Optional choice
   - Call toggle endpoint or modify config.yaml directly

# Each step has user confirmation/choice
```

### Simplified Architecture
```
install.py (CLI)          →  Setup complete, services running
    ↓
Web UI (if needed)        →  Only for admin account creation
    ↓
Ready to use
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
   - Can access web UI
   - Can create admin account
   - MCP tools available (if chosen)
   - Serena enabled (if chosen)

## Benefits
- Faster setup for new users
- Less confusion about what's happening
- All configuration in one place (install.py)
- Web UI only for admin account (simple and clear)
- Preserves user control and choices
- Uses existing code that was already built

## Remember
- The code for MCP integration already exists: `scripts/integrate_mcp.py`
- The code for Serena toggle already exists: `api/endpoints/serena.py`
- Database table creation used to be in install.py - restore it
- Don't remove user choices - enhance them
- Keep the flow simple and linear