# MCP Configuration Flow Visualization

**Last Updated:** 2025-10-14
**Purpose:** Visual map of how MCP configuration works today (before Phase 2 redesign)

---

## Current State: 3 Separate Entry Points

```
USER ACTIONS
═══════════════════════════════════════════════════════════════════════

Entry Point 1: Navigate to /mcp-integration page
Entry Point 2: Click "Connect AI Tools" button (Settings/Dashboard)
Entry Point 3: Go through Setup Wizard (first-time only)

Each leads to DIFFERENT component with DIFFERENT workflow!
```

---

## Flow 1: McpIntegration.vue (Main Page)

```
┌─────────────────────────────────────────────────────────────────┐
│  USER NAVIGATES: /mcp-integration                               │
└──────────────────────────┬──────────────────────────────────────┘
                           │
                           ▼
     ┌─────────────────────────────────────────────────┐
     │   McpIntegration.vue (640 lines)                │
     │   File: frontend/src/views/McpIntegration.vue   │
     └──────────────┬──────────────────────────────────┘
                    │
          ┌─────────┴─────────┬───────────┬───────────┐
          │                   │           │           │
          ▼                   ▼           ▼           ▼
  ┌───────────────┐   ┌─────────────┐   ┌────────┐  ┌──────────────┐
  │ Download      │   │ Share       │   │ Manual │  │ Trouble-     │
  │ Installer     │   │ Links       │   │ Config │  │ shooting     │
  │ Scripts       │   │ (Team)      │   │        │  │ (4 panels)   │
  └───────┬───────┘   └──────┬──────┘   └───┬────┘  └──────────────┘
          │                  │               │
          │                  │               │
  ┌───────▼────────┐  ┌──────▼─────────┐   │
  │ Windows or     │  │ Generate       │   │
  │ Unix Download  │  │ Share Link     │   │
  └───────┬────────┘  └───────┬────────┘   │
          │                   │             │
          ▼                   ▼             ▼
  ┌────────────────────────────────────────────────────────┐
  │  BACKEND: api/endpoints/mcp_installer.py               │
  │                                                        │
  │  Routes:                                               │
  │  • GET  /api/mcp-installer/windows                    │
  │  • GET  /api/mcp-installer/unix                       │
  │  • POST /api/mcp-installer/share-link                 │
  │                                                        │
  │  Functions:                                            │
  │  • download_windows_installer()                       │
  │  • download_unix_installer()                          │
  │  • create_share_link()                                │
  │                                                        │
  │  Templates:                                            │
  │  • Uses Jinja2 to render .bat/.sh with:              │
  │    - User's API key (from APIKey table)              │
  │    - Server URL                                       │
  │    - Embedded config JSON                             │
  └────────────────────────┬───────────────────────────────┘
                           │
                           ▼
              ┌────────────────────────────┐
              │  USER RECEIVES FILE:       │
              │  • giljo-mcp-setup.bat  OR │
              │  • giljo-mcp-setup.sh      │
              │                            │
              │  File contains:            │
              │  1. Detect Claude CLI     │
              │  2. Modify ~/.claude.json  │
              │  3. Insert giljo-mcp config│
              └────────────┬───────────────┘
                           │
                           ▼
                 USER RUNS SCRIPT LOCALLY
                           │
                           ▼
          ┌────────────────────────────────────┐
          │  Script edits:                     │
          │  ~/.claude.json                    │
          │                                    │
          │  Adds section:                     │
          │  {                                 │
          │    "mcpServers": {                 │
          │      "giljo-mcp": {                │
          │        "command": "python",        │
          │        "args": ["-m","giljo_mcp"], │
          │        "env": {                    │
          │          "GILJO_SERVER_URL":"...", │
          │          "GILJO_API_KEY": "..."    │
          │        }                           │
          │      }                             │
          │    }                               │
          │  }                                 │
          └────────────────────────────────────┘
```

---

## Flow 2: AIToolSetup.vue (Dialog)

```
┌──────────────────────────────────────────────────────────────┐
│  USER CLICKS: "Connect AI Tools" button                     │
│  Location: UserSettings.vue or SettingsView.vue             │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
     ┌───────────────────────────────────────────────────┐
     │   AIToolSetup.vue (Dialog Component)              │
     │   File: frontend/src/components/AIToolSetup.vue   │
     │   Size: 453 lines                                 │
     └────────────────────┬──────────────────────────────┘
                          │
                          ▼
          ┌───────────────────────────────┐
          │ User Selects Tool:            │
          │ • Claude Code                 │
          │ • Codex CLI                   │
          │ • Generic/Other               │
          └───────────────┬───────────────┘
                          │
                          ▼
      ┌─────────────────────────────────────────────┐
      │  AUTOMATIC API KEY GENERATION (NO CONSENT)  │
      │                                             │
      │  Backend Call:                              │
      │  POST /api/auth/api-keys                   │
      │  Body: { "name": "Claude Code - 10/14/25" }│
      │                                             │
      │  Response: { "key": "gai_..." }            │
      └────────────────┬────────────────────────────┘
                       │
                       ▼
  ┌──────────────────────────────────────────────────────┐
  │  FRONTEND TEMPLATE GENERATION                        │
  │  (NOT backend!)                                      │
  │                                                      │
  │  File: frontend/src/utils/configTemplates.js        │
  │                                                      │
  │  function generateClaudeCodeConfig(apiKey, url) {   │
  │    return JSON.stringify({                          │
  │      'giljo-mcp': {                                 │
  │        command: 'python',                           │
  │        args: ['-m', 'giljo_mcp'],                   │
  │        env: {                                       │
  │          GILJO_MCP_HOME: 'F:/GiljoAI_MCP', ❌      │
  │          GILJO_SERVER_URL: url,                     │
  │          GILJO_API_KEY: apiKey                      │
  │        }                                            │
  │      }                                              │
  │    }, null, 2)                                      │
  │  }                                                  │
  │                                                      │
  │  ⚠️  PROBLEM: Hardcoded Windows path!               │
  └─────────────────────┬────────────────────────────────┘
                        │
                        ▼
        ┌───────────────────────────────────┐
        │  Dialog Shows:                    │
        │  • API Key Warning (one-time)     │
        │  • Config JSON (copyable)         │
        │  • Instructions                   │
        │  • Download Guide button          │
        └───────────────┬───────────────────┘
                        │
                        ▼
          USER MANUALLY COPIES JSON
                        │
                        ▼
       USER MANUALLY PASTES INTO ~/.claude.json
                        │
                        ▼
            USER MANUALLY RESTARTS CLAUDE CLI
```

---

## Flow 3: McpConfigStep.vue (Setup Wizard)

```
┌─────────────────────────────────────────────────────────┐
│  USER IN: First-time Setup Wizard                      │
│  File: frontend/src/views/SetupWizard.vue              │
│  Step: 3 of 3 (MCP Configuration)                      │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
    ┌──────────────────────────────────────────────────┐
    │   McpConfigStep.vue (Wizard Step Component)     │
    │   File: frontend/src/components/setup/          │
    │         McpConfigStep.vue                        │
    │   Size: 291 lines                                │
    │   Status: ⚠️  BROKEN (calls removed methods)     │
    └────────────────┬─────────────────────────────────┘
                     │
                     ▼
     ┌───────────────────────────────────────────┐
     │  User Clicks "Generate Configuration"     │
     └───────────────┬───────────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────────────────┐
  │  ❌ BROKEN CALL (v3.0 removed this method)          │
  │                                                    │
  │  setupService.generateMcpConfig()                 │
  │                                                    │
  │  Location: frontend/src/services/setupService.js  │
  │  Status: Method removed in lines 105-107          │
  │                                                    │
  │  Comment says:                                    │
  │  "// generateMcpConfig() and registerMcp()       │
  │  //  removed as part of v3.0 unified auth"       │
  │                                                    │
  │  Result: RUNTIME ERROR when called                │
  └────────────────────────────────────────────────────┘
```

---

## Template Generation: Dual Systems Problem

```
┌────────────────────────────────────────────────────────────┐
│  TWO SOURCES OF TRUTH FOR MCP CONFIG TEMPLATES            │
│  (This causes drift and maintenance issues)                │
└────────────────────────────────────────────────────────────┘

   SYSTEM 1                        SYSTEM 2
   --------                        --------
   FRONTEND                        BACKEND
   --------                        -------

Frontend:                       Backend:
┌─────────────────────┐        ┌──────────────────────┐
│ configTemplates.js  │        │ mcp_installer.py     │
│                     │        │                      │
│ • Python Code       │        │ • Jinja2 templates   │
│ • Hardcoded paths   │  VS    │ • Dynamic rendering  │
│ • Used by           │        │ • Used by            │
│   AIToolSetup       │        │   McpIntegration     │
└─────────────────────┘        └──────────────────────┘

        ▼                               ▼
   JSON string                  .bat/.sh files
   returned to                  downloaded by
   user in dialog               user from page

        ▼                               ▼
   USER COPIES                   USER RUNS
   MANUALLY                      AUTOMATICALLY


⚠️  PROBLEM: If templates diverge, different users get
    different configs depending on which flow they used!
```

---

## API Client Inconsistency

```
┌──────────────────────────────────────────────────────────┐
│  TWO WAYS TO CALL BACKEND APIs                          │
│  (Inconsistent auth handling)                            │
└──────────────────────────────────────────────────────────┘

   METHOD 1                       METHOD 2
   --------                       --------
   NATIVE fetch()                 api.js Client
   --------------                 -------------

McpIntegration.vue uses:      Rest of app uses:
┌────────────────────────┐    ┌─────────────────────────┐
│ fetch(url, {           │    │ api.get(url)            │
│   headers: {           │    │                         │
│     'Authorization':   │    │ (auto-adds auth token)  │
│       Bearer ${token}, │    │ (auto-adds tenant key)  │
│     'X-Tenant-Key':    │    │ (auto-retries on 401)   │
│       hardcoded        │    │ (centralized errors)    │
│   }                    │    │                         │
│ })                     │    │                         │
└────────────────────────┘    └─────────────────────────┘

        ▼                              ▼
   Manual auth                   Automatic auth
   management                    via interceptors

        ▼                              ▼
   localStorage                  axios instance
   direct access                 with interceptors

⚠️  PROBLEM: McpIntegration bypasses api.js benefits:
    - No automatic token refresh on 401
    - No centralized error handling
    - Manual tenant key injection
    - Harder to test (can't mock api.js)
```

---

## Backend API Endpoints (Current)

```
┌───────────────────────────────────────────────────────────────┐
│  API ROUTES FOR MCP CONFIGURATION                             │
│  File: api/endpoints/mcp_installer.py                         │
└───────────────────────────────────────────────────────────────┘

GET /api/mcp-installer/windows
├─ Handler: download_windows_installer()
├─ Returns: .bat file (application/octet-stream)
├─ Contains: Embedded API key, server URL, config JSON
├─ Auth: Required (checks request.state.user)
└─ Uses: Jinja2 template rendering

GET /api/mcp-installer/unix
├─ Handler: download_unix_installer()
├─ Returns: .sh file (application/octet-stream)
├─ Contains: Same as Windows but different script format
├─ Auth: Required
└─ Uses: Jinja2 template rendering

POST /api/mcp-installer/share-link
├─ Handler: create_share_link()
├─ Returns: { windows_url, unix_url, expires_at }
├─ Contains: JWT tokens embedded in URLs
├─ Auth: Required
├─ Secret: Hardcoded SECRET_KEY ⚠️  (should be env var)
└─ Expiry: 7 days (hardcoded)

POST /api/auth/api-keys
├─ Handler: create_api_key() (in auth.py)
├─ Returns: { key, key_id, name, created_at }
├─ Contains: New API key (shown once)
├─ Auth: Required
└─ Called by: AIToolSetup.vue automatically
```

---

## Data Flow: Where API Keys Come From

```
┌──────────────────────────────────────────────────────────┐
│  API KEY SOURCES (Inconsistent!)                         │
└──────────────────────────────────────────────────────────┘

Flow 1: McpIntegration Download
═══════════════════════════════
User clicks download
         │
         ▼
Backend: mcp_installer.py:241
         │
         ▼
   Try to get API key:
   api_key = getattr(user, 'api_key', None)
         │
         ├─ If user.api_key exists → Use it
         │
         └─ If None → Use fallback:
            f"temp_key_{user.id}"
         │
         ▼
   Embed in .bat/.sh file

⚠️  PROBLEM: Fallback key is not real!
    MCP server will reject it.


Flow 2: AIToolSetup Dialog
═══════════════════════════
User selects tool
         │
         ▼
   AUTO-GENERATE NEW KEY
   (no user consent)
         │
         ▼
   POST /api/auth/api-keys
   Body: { name: "Claude Code - date" }
         │
         ▼
   Returns: { key: "gai_..." }
         │
         ▼
   Store in database: APIKey table
   • key_id (UUID)
   • key (hashed)
   • name
   • user_id
   • created_at
         │
         ▼
   Show in dialog (ONE TIME ONLY)
         │
         ▼
   User must copy now or lose access

⚠️  PROBLEM: Creates keys without asking!
    User may not realize they're creating credentials.
```

---

## Database Schema (Relevant Tables)

```
┌──────────────────────────────────────────────────────────┐
│  DATABASE: giljo_mcp (PostgreSQL)                        │
│  File: src/giljo_mcp/models.py                           │
└──────────────────────────────────────────────────────────┘

TABLE: users
├─ id (UUID, PK)
├─ email (String, unique)
├─ password_hash (String)
├─ tenant_key (String, FK → tenants.tenant_key)
└─ created_at (DateTime)

TABLE: api_keys (Created by AIToolSetup)
├─ key_id (UUID, PK)
├─ key_hash (String) ← Bcrypt hash of "gai_..." key
├─ name (String) ← e.g., "Claude Code - 10/14/25"
├─ user_id (UUID, FK → users.id)
├─ created_at (DateTime)
└─ last_used (DateTime, nullable)

⚠️  NOTE: User table has no api_key column anymore!
    Old code (mcp_installer.py:241) tries getattr(user, 'api_key')
    which returns None → uses fallback temp key → breaks auth
```

---

## Cross-Platform Compatibility Issues

```
┌────────────────────────────────────────────────────────────┐
│  HARDCODED PATHS (Breaks Linux/macOS)                     │
└────────────────────────────────────────────────────────────┘

Location 1: configTemplates.js:27
────────────────────────────────
env: {
  GILJO_MCP_HOME: 'F:/GiljoAI_MCP',  ❌ Windows-only!
  GILJO_SERVER_URL: serverUrl,
  GILJO_API_KEY: apiKey
}

Problem: F:/ drive doesn't exist on Linux/macOS
Impact: MCP server can't start
Used by: AIToolSetup.vue
Fix: Remove GILJO_MCP_HOME (not needed)


Location 2: AIToolSetup.vue:280
──────────────────────────────
const projectPath = 'F:/GiljoAI_MCP'  ❌ Hardcoded!
const pythonPath = getPythonPath(projectPath, detectOS())

Problem: Hardcoded Windows path passed to path builder
Impact: Config contains invalid paths on other platforms
Fix: Use projectPath = null or detect dynamically


Location 3: pathDetection.js (Not actually used wrong)
────────────────────────────────────────────────────
export function getPythonPath(projectPath, os) {
  if (os === 'windows') {
    return `${projectPath}\\venv\\Scripts\\python.exe`
  }
  return `${projectPath}/venv/bin/python`
}

Status: ✅ Logic is fine, but receives bad projectPath input
```

---

## What Happens When User Configures MCP (Success Path)

```
┌──────────────────────────────────────────────────────────────┐
│  FULL SUCCESS FLOW (Assuming no errors)                     │
└──────────────────────────────────────────────────────────────┘

1. User visits /mcp-integration
   │
   ▼
2. Clicks "Download for Windows"
   │
   ▼
3. Frontend: fetch(/api/mcp-installer/windows)
   │
   ▼
4. Backend: Generates .bat with:
   │  • User's API key (or fallback)
   │  • Server URL (from config)
   │  • Embedded config JSON
   │
   ▼
5. User receives: giljo-mcp-setup.bat
   │
   ▼
6. User double-clicks .bat file
   │
   ▼
7. Script runs locally on user's machine:
   │  • Detects Python installation
   │  • Finds ~/.claude.json location
   │  • Reads existing config (if any)
   │  • Parses JSON
   │  • Adds/updates "mcpServers.giljo-mcp" section
   │  • Writes back to ~/.claude.json
   │  • Shows success message
   │
   ▼
8. User restarts Claude Code CLI:
   │  $ claude quit
   │  $ claude
   │
   ▼
9. Claude Code loads ~/.claude.json
   │
   ▼
10. Claude Code spawns MCP server process:
    │  Command: python -m giljo_mcp
    │  Env vars:
    │    GILJO_SERVER_URL=http://localhost:7272
    │    GILJO_API_KEY=gai_...
    │
    ▼
11. GiljoAI MCP server starts (server.py)
    │  • Reads env vars
    │  • Connects to GiljoAI backend
    │  • Authenticates with API key
    │  • Registers available tools
    │
    ▼
12. User types in Claude Code:
    │  "Show my projects"
    │
    ▼
13. Claude Code recognizes MCP tool
    │  • Calls: get_projects_list()
    │  • Via: stdio communication
    │
    ▼
14. MCP server handles request:
    │  • Calls GiljoAI API: GET /api/projects
    │  • Returns results to Claude Code
    │
    ▼
15. Claude Code shows results to user
    │
    ▼
16. ✅ SUCCESS: MCP integration working!
```

---

## Component Import/Usage Map

```
┌──────────────────────────────────────────────────────────┐
│  WHERE COMPONENTS ARE USED                               │
└──────────────────────────────────────────────────────────┘

McpIntegration.vue
├─ Route: /mcp-integration
├─ Imported by: frontend/src/router/index.js
└─ Direct navigation from: Dashboard, Settings, Setup Wizard

AIToolSetup.vue (Dialog)
├─ Imported by:
│  ├─ frontend/src/views/UserSettings.vue
│  ├─ frontend/src/views/SettingsView.vue
│  └─ frontend/src/views/Dashboard.vue (maybe)
│
└─ Triggered by: "Connect AI Tools" button clicks

McpConfigStep.vue
├─ Imported by: frontend/src/views/SetupWizard.vue:88
├─ Used in: Setup wizard (step 3 of 3)
└─ Status: ⚠️  BROKEN (should be removed or rewritten)
```

---

## File Dependency Graph

```
┌────────────────────────────────────────────────────────────┐
│  FILE DEPENDENCIES                                         │
└────────────────────────────────────────────────────────────┘

McpIntegration.vue
  │
  ├─→ @/config/api (API_CONFIG.REST_API.baseURL)
  ├─→ date-fns (format function)
  └─→ native fetch() ⚠️  (should use api.js)

AIToolSetup.vue
  │
  ├─→ @/config/api (API_CONFIG.REST_API.baseURL)
  ├─→ @/utils/configTemplates (generateClaudeCodeConfig, etc.)
  ├─→ @/utils/pathDetection (getPythonPath, detectOS)
  └─→ native fetch() ⚠️  (for API key generation)

McpConfigStep.vue
  │
  ├─→ @/services/setupService ⚠️  BROKEN
  │   │
  │   └─→ setupService.generateMcpConfig() ← REMOVED IN v3.0
  │       setupService.registerMcp() ← REMOVED IN v3.0
  │       setupService.checkMcpConfigured() ← REMOVED IN v3.0
  │
  └─→ @/components/ui/AppAlert.vue

configTemplates.js
  │
  └─→ No dependencies (pure functions)

pathDetection.js
  │
  └─→ No dependencies (pure functions)

setupService.js
  │
  ├─→ @/config/api
  └─→ Methods removed: generateMcpConfig, registerMcp, checkMcpConfigured
      (Comments on lines 105-107 explain removal)
```

---

## Key Problems Summary (From Audit)

```
┌────────────────────────────────────────────────────────────┐
│  CRITICAL ISSUES (MUST FIX IN PHASE 1)                    │
└────────────────────────────────────────────────────────────┘

❌ 1. Hardcoded F:/GiljoAI_MCP breaks Linux/macOS
      Location: configTemplates.js:27
      Impact: CRITICAL - Cross-platform incompatibility

❌ 2. McpConfigStep.vue calls removed methods
      Location: McpConfigStep.vue:193, 220, 226
      Impact: CRITICAL - Runtime crashes in setup wizard

❌ 3. Dual template systems (frontend + backend)
      Location: configTemplates.js vs mcp_installer.py
      Impact: HIGH - Maintenance burden, drift risk

❌ 4. fetch() bypassing api.js interceptors
      Location: McpIntegration.vue:446-492
      Impact: MODERATE - Missing auth refresh, error handling

❌ 5. API key auto-generation without consent
      Location: AIToolSetup.vue:258-276
      Impact: MODERATE - Security UX concern

┌────────────────────────────────────────────────────────────┐
│  UX ISSUES (FIX IN PHASE 2)                               │
└────────────────────────────────────────────────────────────┘

⚠️ 6. Fragmented user journey (3 entry points)
      Impact: HIGH - Cognitive overload, confusion

⚠️ 7. No clear primary action
      Impact: HIGH - Users don't know what to do

⚠️ 8. Expansion panel overload (7+ panels)
      Impact: MODERATE - Critical info buried

⚠️ 9. Inconsistent success feedback
      Impact: MINOR - Copy buttons use different patterns

⚠️ 10. No progress persistence
       Impact: MINOR - Can't tell if already configured
```

---

## Recommended Two-Phase Fix

```
┌────────────────────────────────────────────────────────────┐
│  PHASE 1: STABILIZATION (0016-A) - 2-3 hours             │
│  Fix critical bugs, enable cross-platform compatibility   │
└────────────────────────────────────────────────────────────┘

✅ Remove hardcoded F:/GiljoAI_MCP paths
✅ Fix or remove broken McpConfigStep.vue
✅ Replace fetch() with api.js client
✅ Move SECRET_KEY to environment variable
✅ Replace alert() with Vuetify components

Result: Stable foundation, works on all platforms

┌────────────────────────────────────────────────────────────┐
│  PHASE 2: UX ENHANCEMENT (0016-B) - 4-5 hours            │
│  Consolidate fragmented experience, add validation        │
└────────────────────────────────────────────────────────────┘

✅ Redesign McpIntegration with tabs (Quick Setup vs Advanced)
✅ Create ConfigValidator component
✅ Create TroubleshootingFAQ component
✅ Add API key consent flow to AIToolSetup
✅ Add status detection ("Already configured")

Result: Unified, guided experience with validation
```

---

**This visualization shows the CURRENT state (before Phase 1 & 2 fixes).**

**Next steps: Execute Handover 0016-A, then 0016-B.**
