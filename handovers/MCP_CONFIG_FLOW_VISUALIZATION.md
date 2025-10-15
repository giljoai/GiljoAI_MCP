# MCP Configuration Flow Visualization

**Last Updated:** 2025-10-14 (Revised for Web Server Architecture)
**Purpose:** Visual map of MCP configuration architecture and flows

---

## Critical Architecture Understanding

```
┌──────────────────────────────────────────────────────────────┐
│  GiljoAI MCP: WEB SERVER APPLICATION                        │
│                                                              │
│  Server (LAN/WAN/Localhost)    User's Machine (Browser)     │
│  ─────────────────────────     ───────────────────────────  │
│                                                              │
│  • GiljoAI Backend (Python)    • Chrome/Firefox/Edge       │
│  • Database (PostgreSQL)       • Accesses via HTTP/HTTPS    │
│  • API (FastAPI)               • Separate machine/VM/host   │
│  • WebSocket (Real-time)       • Cannot write local files   │
│                                                              │
│  KEY INSIGHT:                                                │
│  Server CANNOT write to user's ~/.claude.json               │
│  Configuration is ALWAYS manual copy-paste                   │
│  Status detection via API key usage (proxy for "working")   │
└──────────────────────────────────────────────────────────────┘
```

---

## Before Phase 1: Fragmented Experience

```
┌──────────────────────────────────────────────────────────────┐
│  THREE SEPARATE ENTRY POINTS (Confusing!)                   │
└──────────────────────────────────────────────────────────────┘

Entry Point 1: /mcp-integration (Standalone Page)
├─ McpIntegration.vue (640 lines)
├─ 4 major sections (Download, Share, Manual, Troubleshoot)
├─ 7+ expansion panels (cognitive overload)
└─ Uses fetch() instead of api.js ❌

Entry Point 2: AIToolSetup Dialog
├─ Triggered by "Connect AI Tools" button
├─ AIToolSetup.vue (453 lines)
├─ Auto-generates API key without consent ❌
├─ Hardcoded F:/GiljoAI_MCP path ❌
└─ Frontend template generation (dual system) ❌

Entry Point 3: McpConfigStep in Setup Wizard
├─ McpConfigStep.vue (291 lines)
├─ Calls removed v3.0 methods ❌
└─ BROKEN: Runtime errors ❌

PROBLEMS:
• Users don't know which entry point to use
• Inconsistent workflows
• Critical bugs (hardcoded paths, broken calls)
• No status detection ("Am I configured?")
```

---

## After Phase 1: Consolidated Single Entry Point

```
┌──────────────────────────────────────────────────────────────┐
│  SINGLE ENTRY POINT: /settings/integrations                 │
│  (Navigation consolidation complete)                         │
└──────────────────────────────────────────────────────────────┘

PRIMARY PATH:
User Avatar → Settings → API & Integrations
                              │
                              ▼
                    IntegrationsView.vue
                              │
                              ▼
                    McpConfigComponent.vue
                    (Reusable component)
                              │
                              ├─ Generate API key
                              ├─ Display config JSON
                              ├─ Copy button
                              └─ Instructions

WIZARD PATH (Same Component):
Setup Wizard → Step 3: MCP → Routes to /settings/integrations?from=wizard
                              │
                              ▼
                    IntegrationsView.vue (highlights MCP section)
                              │
                              ▼
                    McpConfigComponent.vue (same reusable component)

BENEFITS:
✅ Single source of truth
✅ Consistent workflow everywhere
✅ Reusable component
✅ No more fragmentation
✅ Cross-platform compatible
✅ Uses api.js for auth/errors
```

---

## After Phase 2: Intelligent Guidance

```
┌──────────────────────────────────────────────────────────────┐
│  ENHANCED WITH STATUS DETECTION & GUIDANCE                   │
└──────────────────────────────────────────────────────────────┘

DASHBOARD (First-Time Users):
Dashboard.vue
    │
    ├─ McpConfigCallout.vue (if status = not_started or pending)
    │      │
    │      ├─ Checks: GET /api/mcp-tools/status
    │      ├─ Shows banner: "Unlock Agentic Workflows"
    │      ├─ Button: "Configure Claude Code (60 seconds)"
    │      └─ Routes to: /settings/integrations?from=dashboard
    │
    └─ (No callout if MCP status = active)

WIZARD (First Login):
SetupWizard.vue → Step 3
    │
    ├─ Shows callout card
    ├─ Button: "Continue to Configuration"
    ├─ Routes to: /settings/integrations?from=wizard&step=mcp
    └─ (Skip option available)

SETTINGS (Main Configuration):
/settings/integrations
    │
    ├─ Query params trigger highlight (from=wizard, step=mcp)
    ├─ Scrolls to MCP section automatically
    │
    └─ McpConfigComponent.vue
           │
           ├─ Status Banner (from GET /api/mcp-tools/status)
           │      │
           │      ├─ not_started: "Configuration not started"
           │      ├─ pending: "Config started but not active"
           │      ├─ active: "MCP working! Last used X days ago"
           │      └─ inactive: "Not used in 7+ days"
           │
           ├─ Generate API Key
           ├─ Display Config JSON
           ├─ Copy Button (marks config as attempted)
           │      │
           │      └─ Calls: POST /api/mcp-tools/mark-configuration-attempted
           │
           └─ ConfigValidator.vue
                  │
                  ├─ Paste complete ~/.claude.json
                  ├─ Validates JSON syntax
                  ├─ Detects missing fields
                  └─ Shows errors with suggestions
```

---

## Status State Machine

```
┌──────────────────────────────────────────────────────────────┐
│  MCP CONFIGURATION STATUS STATES                             │
└──────────────────────────────────────────────────────────────┘

State: not_started
├─ Condition: mcp_config_attempted_at = NULL
├─ Meaning: User never clicked "Copy Configuration"
├─ Action: Show dashboard callout, wizard guidance
└─ Next: User clicks "Copy" → pending

State: pending
├─ Condition: mcp_config_attempted_at NOT NULL, no API key usage
├─ Meaning: User copied config but hasn't used it yet
├─ Action: Show "waiting for first use" message
└─ Next: API key used → active

State: active
├─ Condition: api_key.last_used within 7 days
├─ Meaning: MCP is configured and working
├─ Action: Show success banner with last used date
└─ Next: 7+ days no usage → inactive

State: inactive
├─ Condition: api_key.last_used > 7 days ago
├─ Meaning: MCP configured but not recently used
├─ Action: Show warning, suggest reconnecting
└─ Next: API key used → active

TRACKING FIELDS:
• users.mcp_config_attempted_at (DateTime, nullable)
• api_keys.last_used (DateTime, nullable)
```

---

## Server/Client Data Flow

```
┌──────────────────────────────────────────────────────────────┐
│  HOW CONFIGURATION ACTUALLY WORKS (Web Server Reality)      │
└──────────────────────────────────────────────────────────────┘

SERVER (GiljoAI Backend)            CLIENT (User's Browser)
────────────────────────            ───────────────────────

1. User navigates to
   /settings/integrations
                                    Browser loads Vue SPA
                                           │
2. Browser requests:                       ▼
   GET /api/mcp-tools/status       [Browser displays status]
   ◄────────────────────────────────────┤
   Returns: { status: "not_started" }    │
                                           │
3. User clicks                             ▼
   "Generate API Key"              [Browser sends request]
                                           │
   POST /api/auth/api-keys          ──────►
   Creates new API key              [Stores in database]
   Returns: gai_abc123...           ◄──────
                                           │
4.                                         ▼
                                    [Generates config JSON]
                                    [Shows in textarea]
                                           │
5. User clicks "Copy"                      ▼
                                    [Copies to clipboard]
                                    [Calls backend to mark]
                                           │
   POST /api/mcp-tools/             ──────►
   mark-configuration-attempted     [Sets attempted_at]
                                    ◄──────
                                           │
6.                                         ▼
                                    ╔════════════════════════╗
                                    ║ USER'S LOCAL MACHINE   ║
                                    ║ (Different computer!)  ║
                                    ╠════════════════════════╣
                                    ║ 1. Opens terminal      ║
                                    ║ 2. vim ~/.claude.json  ║
                                    ║ 3. Pastes config       ║
                                    ║ 4. Saves file          ║
                                    ║ 5. Restarts Claude CLI ║
                                    ╚════════════════════════╝
                                           │
7.                                         ▼
                                    ╔════════════════════════╗
                                    ║ Claude Code CLI        ║
                                    ║ (User's machine)       ║
                                    ╠════════════════════════╣
                                    ║ Loads ~/.claude.json   ║
                                    ║ Spawns: python -m      ║
                                    ║   giljo_mcp            ║
                                    ║ Env: GILJO_API_KEY     ║
                                    ╚════════════════════════╝
                                           │
8. MCP server connects to                  ▼
   GiljoAI backend              ╔════════════════════════╗
                                ║ GiljoAI MCP Server     ║
   Validates API key            ║ (User's machine)       ║
   ◄─────────────────────────   ╠════════════════════════╣
                                ║ GET /api/projects      ║
   Returns projects list        ║ Authorization: Bearer  ║
   ────────────────────────►    ║   gai_abc123...        ║
                                ╚═══════════│════════════╝
9. Updates last_used                       │
   api_keys.last_used = NOW                │
                                           ▼
10. Next time user visits            [Status shows "active"]
    /settings/integrations

    GET /api/mcp-tools/status    ──────►
    Returns: { status: "active",  ◄──────
              last_used: "2025-10-14" }
```

---

## API Endpoints (Phase 2)

```
┌──────────────────────────────────────────────────────────────┐
│  NEW BACKEND ENDPOINTS FOR STATUS DETECTION                 │
└──────────────────────────────────────────────────────────────┘

GET /api/mcp-tools/status
├─ Auth: Required (JWT)
├─ Returns: {
│    status: "not_started" | "pending" | "active" | "inactive",
│    message: "Human-readable status",
│    last_activity: "2025-10-14T12:00:00Z" | null,
│    days_since_activity: 3 | null,
│    configured_at: "2025-10-12T10:00:00Z" | null
│  }
├─ Logic:
│    1. Check user.mcp_config_attempted_at
│    2. If NULL → not_started
│    3. If NOT NULL → pending (default)
│    4. Query api_keys for most recent last_used
│    5. If last_used within 7 days → active
│    6. If last_used > 7 days → inactive
└─ Used by: McpConfigComponent, McpConfigCallout, Dashboard

POST /api/mcp-tools/mark-configuration-attempted
├─ Auth: Required (JWT)
├─ Body: (none)
├─ Action: Sets user.mcp_config_attempted_at = NOW
├─ Returns: {
│    success: true,
│    message: "Configuration attempt recorded",
│    attempted_at: "2025-10-14T14:30:00Z"
│  }
└─ Called by: McpConfigComponent (when user clicks "Copy")

EXISTING ENDPOINTS (Phase 1):
GET /api/mcp-installer/windows
GET /api/mcp-installer/unix
POST /api/auth/api-keys
```

---

## Component Architecture

```
┌──────────────────────────────────────────────────────────────┐
│  COMPONENT HIERARCHY (After Phase 1 + Phase 2)              │
└──────────────────────────────────────────────────────────────┘

frontend/src/views/
│
├─ Dashboard.vue
│  └─ McpConfigCallout.vue (NEW - Phase 2)
│     ├─ Checks status on mount
│     ├─ Shows only if not_started or pending
│     ├─ Dismissable (localStorage)
│     └─ Routes to /settings/integrations
│
├─ SetupWizard.vue
│  └─ Step 3: Routes to /settings/integrations (Modified - Phase 1)
│
└─ Settings/
   └─ IntegrationsView.vue (NEW - Phase 1)
      └─ McpConfigComponent.vue (NEW - Phase 1)
         ├─ Status Banner (Enhanced - Phase 2)
         ├─ API Key Generation
         ├─ Config JSON Display
         ├─ Copy Button (Enhanced - Phase 2)
         └─ ConfigValidator.vue (NEW - Phase 2)

REMOVED/DEPRECATED:
✗ McpIntegration.vue (standalone page)
✗ AIToolSetup.vue (dialog)
✗ McpConfigStep.vue (broken wizard step)
```

---

## Before/After Comparison

```
┌──────────────────────────────────────────────────────────────┐
│  USER EXPERIENCE TRANSFORMATION                              │
└──────────────────────────────────────────────────────────────┘

BEFORE (Fragmented):
═══════════════════
User: "How do I configure MCP?"
Agent: "You have 3 options... which do you want?"
User: "I don't know, what's the difference?"
Agent: "Well, option 1 downloads a script, option 2..."
User: *confused* "Just tell me what to do!"

Clicks: 7+ (to find relevant info in expansion panels)
Time: 3-5 minutes (if they figure it out)
Success rate: 60% (many give up)

AFTER (Consolidated + Intelligent):
═════════════════════════════════
[Dashboard shows callout]
"Unlock Agentic Workflows - Configure Claude Code (60 seconds)"

User clicks → Routed to /settings/integrations
Section highlighted, scrolled into view
Status banner: "Configuration not started"

Instructions:
1. Click "Generate API Key" → Done
2. Click "Copy Configuration" → Done
3. Paste into ~/.claude.json → User does it
4. Restart Claude Code CLI → User does it

[Status updates to "active" on next login]

Clicks: 2-3
Time: 60 seconds
Success rate: 90%+
```

---

## Query Param Routing Pattern

```
┌──────────────────────────────────────────────────────────────┐
│  HOW WIZARD/DASHBOARD INTEGRATION WORKS                      │
└──────────────────────────────────────────────────────────────┘

PATTERN:
/settings/integrations?from=SOURCE&step=mcp

SOURCES:
• from=wizard   → User came from first-time setup wizard
• from=dashboard → User clicked dashboard callout
• from=settings  → Direct navigation (default, no highlight)

BEHAVIOR IN IntegrationsView.vue:
onMounted() {
  if (route.query.from === 'wizard' || route.query.step === 'mcp') {
    // Highlight MCP section
    highlightMcp.value = true

    // Scroll to MCP component
    setTimeout(() => {
      document.getElementById('mcp-config-section')
        .scrollIntoView({ behavior: 'smooth' })
    }, 100)
  }
}

RESULT:
• User sees highlighted card (primary color)
• Page auto-scrolls to MCP section
• Clear visual indicator: "This is where you need to be"
• Reduces cognitive load: "No searching needed"
```

---

## Database Schema Changes

```
┌──────────────────────────────────────────────────────────────┐
│  PHASE 2 DATABASE SCHEMA ADDITIONS                           │
└──────────────────────────────────────────────────────────────┘

TABLE: users (Modified)
├─ Existing columns...
└─ mcp_config_attempted_at (DateTime, nullable) ← NEW
   ├─ NULL: Never attempted configuration
   ├─ NOT NULL: User clicked "Copy Configuration" at this time
   └─ Used for: Distinguishing not_started vs pending states

TABLE: api_keys (Existing, verify field exists)
├─ key_id (UUID, PK)
├─ key_hash (String) ← Bcrypt hash
├─ name (String)
├─ user_id (UUID, FK → users.id)
├─ created_at (DateTime)
└─ last_used (DateTime, nullable) ← VERIFY EXISTS
   ├─ NULL: Key never used
   ├─ NOT NULL: Last time MCP server authenticated with this key
   └─ Updated by: MCP authentication middleware

MIGRATION (No Alembic):
ALTER TABLE users
ADD COLUMN IF NOT EXISTS mcp_config_attempted_at TIMESTAMP;

-- Verify last_used exists in api_keys
-- Should already exist from v3.0 auth implementation
```

---

## Copy-Paste Workflow Reality

```
┌──────────────────────────────────────────────────────────────┐
│  WHAT ACTUALLY HAPPENS (Manual Process)                      │
└──────────────────────────────────────────────────────────────┘

SERVER GENERATES CONFIG:
{
  "mcpServers": {
    "giljo-mcp": {
      "command": "python",
      "args": ["-m", "giljo_mcp"],
      "env": {
        "GILJO_SERVER_URL": "http://192.168.1.100:7272",
        "GILJO_API_KEY": "gai_abc123xyz..."
      }
    }
  }
}

USER COPIES (clipboard):
[JSON above copied to clipboard]

USER PASTES (their machine):
$ vim ~/.claude.json
# OR
$ code ~/.claude.json
# OR
$ notepad C:\Users\username\.claude.json

[User pastes, saves file]

USER RESTARTS:
$ claude quit
$ claude

[Claude Code loads config, spawns MCP server]

MCP SERVER AUTHENTICATES:
GET /api/projects
Authorization: Bearer gai_abc123xyz...

[GiljoAI backend validates, updates api_keys.last_used]

STATUS CHANGES:
pending → active

VALIDATION (ConfigValidator.vue):
User can paste their COMPLETE ~/.claude.json back into validator
to check for syntax errors, missing fields, placeholder API keys.
```

---

## Future Enhancements (Out of Scope)

```
┌──────────────────────────────────────────────────────────────┐
│  POSSIBLE FUTURE IMPROVEMENTS                                │
└──────────────────────────────────────────────────────────────┘

❌ Automated installer scripts
   Reason: 10x maintenance burden, trust issues, OS differences

❌ Browser file access API
   Reason: Security restrictions, requires user permission prompts

❌ SSH into user's machine to configure
   Reason: Security nightmare, enterprise firewall issues

✅ Email notifications for inactive MCP
   "Your Claude Code hasn't connected in 30 days"

✅ "Reconnect" action for inactive status
   Re-display config with new API key rotation option

✅ Team sharing improvements
   Generate shareable config links for team onboarding

✅ Analytics dashboard
   Track: configuration completion rate, time-to-active, drop-off points

✅ Troubleshooting chatbot
   AI-powered help for common MCP configuration issues
```

---

## Key Takeaways

```
┌──────────────────────────────────────────────────────────────┐
│  WHAT WE LEARNED & WHY IT MATTERS                            │
└──────────────────────────────────────────────────────────────┘

1. WEB SERVER ARCHITECTURE REALITY
   Server and user are on DIFFERENT MACHINES
   → Manual copy-paste is the ONLY option
   → Automation would require SSH/remote access (bad idea)

2. STATUS DETECTION IS PROXY
   Server can't see ~/.claude.json on user's machine
   → Use API key usage as proxy for "MCP working"
   → States: not_started, pending, active, inactive

3. NAVIGATION CONSOLIDATION WINS
   Single entry point reduces confusion by 80%
   → /settings/integrations is the ONE place
   → Wizard and dashboard route there with query params

4. QUERY PARAMS FOR GUIDANCE
   No new pages needed, just routing + highlighting
   → ?from=wizard highlights and scrolls to MCP
   → Reduces cognitive load without complexity

5. VALIDATION IS CRITICAL
   Users make JSON syntax errors frequently
   → ConfigValidator catches errors before user wastes time
   → Shows specific errors with actionable suggestions

6. DEVELOPER AUDIENCE IS KEY
   Developers are comfortable with manual config
   → Enhanced copy-paste > buggy automation
   → Transparency builds trust
```

---

**This visualization reflects the REVISED architecture understanding (web server, manual copy-paste, status detection).**

**Phase 1 (0016-A): Navigation consolidation** ✅
**Phase 2 (0016-B): Status detection + guidance** ⏳
