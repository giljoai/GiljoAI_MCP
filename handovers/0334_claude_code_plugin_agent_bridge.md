# Handover 0334: Claude Code Plugin - Agent Template Bridge

**Date:** 2025-12-07
**From Agent:** Orchestrator (Handover 0333 Session)
**To Agent:** TDD Implementor + System Architect
**Priority:** High
**Estimated Complexity:** 3-5 days
**Status:** Ready for Implementation

---

## Executive Summary

Create a Claude Code Plugin that connects directly to GiljoAI's agent template database, eliminating the need for local `.md` template files. The plugin is installed ONCE via user profile setup, and each staging prompt includes environment verification and conflict detection.

**Expected Outcome:** Orchestrators in CLI mode can invoke agents by name (e.g., `@implementer`) and the plugin fetches the current template definition from the GiljoAI database in real-time.

---

## Context and Background

### How We Got Here

1. **Handover 0333** simplified the staging prompt from 150+ lines to ~35 lines
2. During testing, we discovered the `agent_type` enforcement problem - orchestrators must match exact template names
3. User insight: Claude Code has a plugin system that can fetch agents dynamically
4. Key realization: We can use the plugin as a bridge to our database, making it the "marketplace"

### Current Pain Points
1. **Template File Management**: Users must export templates to `~/.claude/agents/*.md`
2. **Sync Issues**: Database changes don't reflect until re-export
3. **agent_type Enforcement**: Orchestrator must match exact template names
4. **No Centralized Control**: Each user manages their own files

### The Solution
A Claude Code plugin that:
- Installs ONCE per user (via Profile → Setup page)
- Uses tenant_key for multi-tenant isolation
- Fetches agent templates from GiljoAI MCP server on-demand
- Makes agents available via `/agents` and `@agent_name` syntax

### Critical Discovery: Local File Conflicts

Claude Code has a priority hierarchy:
```
1. Project agents     (.claude/agents/)     ← HIGHEST - will override plugin!
2. User agents        (~/.claude/agents/)   ← Will override plugin!
3. Plugin agents      (from our plugin)     ← Lowest priority
```

**This means existing local `.md` files WILL interfere with plugin agents!**

The staging prompt MUST check for and warn about local file conflicts.

---

## Architecture Decision: Tenant Key

**Using tenant_key** (not API key) because:
- Already embedded in every staging prompt
- Identifies user's data partition
- Simpler flow (no extra key generation)
- Less sensitive than authentication credentials

---

## Two-Phase Architecture

### Phase A: One-Time Plugin Setup (User Profile)

```
User Profile → Integrations → Claude Code CLI Setup
                                    ↓
                    Shows install command with tenant_key
                                    ↓
                    User copies and runs ONCE in Claude Code
                                    ↓
                    Plugin installed permanently for that user
```

**UI Location:** My Settings → Integrations → Claude Code CLI

**UI Elements:**
- Section header: "Claude Code Plugin Setup"
- Description text explaining the plugin
- Copy button for install command
- Connection test button
- Status indicator (Not Verified / Verified)

### Phase B: Per-Project Staging (Environment Check)

```
Stage Project (CLI Mode) → Staging Prompt
                                ↓
                    1. Check for local .md file conflicts
                    2. Verify plugin is installed
                    3. List available agents from /agents
                                ↓
                    Orchestrator proceeds with clean environment
```

---

## Technical Specification

### Plugin Structure

```
giljoai-agents-plugin/
├── package.json              # Plugin metadata
├── .claude-plugin/
│   └── plugin.json           # Claude Code plugin manifest
├── src/
│   └── agent-provider.js     # Dynamic agent fetching logic
└── README.md                 # Installation instructions
```

### Plugin Manifest (plugin.json)

```json
{
  "name": "giljoai-agents",
  "version": "1.0.0",
  "description": "Dynamic agent templates from GiljoAI MCP Server",
  "agents": {
    "source": "dynamic",
    "provider": "./src/agent-provider.js"
  },
  "configuration": {
    "server_url": {
      "type": "string",
      "required": true,
      "description": "GiljoAI MCP server URL"
    },
    "tenant_key": {
      "type": "string",
      "required": true,
      "description": "User's tenant key for isolation"
    }
  }
}
```

### Agent Provider Logic

```javascript
// src/agent-provider.js
async function getAgents(config) {
  const { server_url, tenant_key } = config;

  const response = await fetch(
    `${server_url}/api/v1/agent-templates/plugin?tenant_key=${tenant_key}`
  );

  if (!response.ok) {
    console.error('Failed to fetch agents from GiljoAI');
    return [];
  }

  const data = await response.json();

  // Convert to Claude Code agent format
  return data.templates.map(t => ({
    name: t.name,
    description: t.description,
    instructions: t.full_instructions,
    capabilities: t.capabilities || []
  }));
}

module.exports = { getAgents };
```

### New Backend API Endpoint

**Endpoint:** `GET /api/v1/agent-templates/plugin`

**Query Parameters:**
- `tenant_key` (required): User's tenant key

**Response:**
```json
{
  "templates": [
    {
      "name": "implementer",
      "role": "Code Implementation Specialist",
      "description": "Implements features following TDD...",
      "full_instructions": "You are an implementer agent. Your role is to...",
      "capabilities": ["code_generation", "testing"],
      "is_active": true
    }
  ],
  "tenant_key": "tk_xxx",
  "count": 5,
  "cache_ttl": 300
}
```

---

## Staging Prompt Changes (CLI Mode)

**Current CLI Mode Block (from 0333):**
```
CLAUDE CODE CLI MODE:
- You will spawn agents using Claude Code's Task tool
- agent_type parameter = subagent_type (MUST match template name exactly)
- Agents are hidden subprocesses - user sees progress via dashboard
- After spawning, agents call get_agent_mission() to start work
```

**New CLI Mode Block:**
```
CLAUDE CODE CLI MODE:

ENVIRONMENT PRE-FLIGHT:
Before proceeding, verify your agent environment is clean:

1. CHECK FOR LOCAL OVERRIDES (these will interfere with managed agents):
   ls ~/.claude/agents/*.md 2>/dev/null && echo "WARNING: User agents found"
   ls .claude/agents/*.md 2>/dev/null && echo "WARNING: Project agents found"

   If files found: Remove or rename them to use GiljoAI managed agents.

2. VERIFY PLUGIN INSTALLED:
   /plugins list | grep giljoai-agents

   If not found: Visit GiljoAI → My Settings → Integrations → Claude Code Setup

3. LIST AVAILABLE AGENTS:
   /agents

   Should show your GiljoAI templates (implementer, tester, etc.)

PROCEED ONLY when:
- No local .md overrides exist
- Plugin is installed
- /agents shows your templates

SPAWNING AGENTS:
- Use Task tool: subagent_type must match agent name from /agents exactly
- Example: Task(subagent_type="implementer", prompt="Build the auth module")
- Agents receive their full instructions automatically from the plugin
```

---

## Implementation Plan (Sub-Handovers)

### 0334a: Backend API Endpoint
**Effort:** 4-6 hours

Create the plugin-specific endpoint for fetching agent templates.

**Files:**
- `api/endpoints/agent_templates.py` (new)
- `api/app.py` (register router)
- `tests/api/test_agent_templates_plugin.py` (new)

### 0334b: Plugin Package Creation
**Effort:** 6-8 hours

Create the Claude Code plugin package.

**Files:**
- `plugins/giljoai-agents/` (new directory)
- Plugin manifest, provider, and README

### 0334c: User Profile Setup UI
**Effort:** 4-6 hours

Add the plugin setup section to user settings.

**Files:**
- `frontend/src/views/SettingsView.vue` or `MySettingsView.vue`
- `frontend/src/components/settings/ClaudeCodeSetup.vue` (new)

### 0334d: Staging Prompt Integration
**Effort:** 2-3 hours

Update CLI mode staging prompt with environment checks.

**Files:**
- `src/giljo_mcp/thin_prompt_generator.py`

### 0334e: Testing & Documentation
**Effort:** 4-6 hours

End-to-end testing and user documentation.

**Files:**
- Integration tests
- `docs/user_guides/claude_code_plugin_setup.md` (new)

---

## Multi-Tenant Isolation

### How It Works
1. User's `tenant_key` is embedded in plugin config during setup
2. Plugin calls API with tenant_key on every agent fetch
3. Backend filters templates by tenant_key
4. User only sees their own templates

### Security Considerations
- Tenant key is not secret (it's a partition ID)
- API validates tenant_key exists
- No cross-tenant data exposure
- Rate limiting prevents enumeration

---

## Success Criteria

1. Plugin setup page exists in User Settings → Integrations
2. Plugin installs successfully with generated command
3. `/agents` command shows templates from user's database
4. Agents can be invoked with `@agent_name` syntax
5. Template changes in UI reflect on next `/agents` call
6. Multi-tenant isolation verified
7. Conflict detection warns about local .md files
8. Works in CLI mode staging workflow

---

## Testing Requirements

### Unit Tests
- Backend endpoint returns templates for valid tenant_key
- Backend returns empty for invalid tenant_key
- Rate limiting works

### Integration Tests
- Plugin installation flow
- Agent fetching with valid config
- Error handling for network issues
- Conflict detection in staging prompt

### Manual Testing Checklist
1. Go to Settings → Integrations → Claude Code Setup
2. Copy the install command
3. Run in Claude Code terminal
4. Verify `/plugins list` shows giljoai-agents
5. Verify `/agents` shows your templates
6. Create a local `~/.claude/agents/test.md` file
7. Stage a project in CLI mode
8. Verify warning about local file conflict appears
9. Remove the test file
10. Stage again, verify clean environment message
11. Invoke `@implementer` and verify it works

---

## Dependencies

- Claude Code plugin system (verify version requirements)
- GiljoAI MCP server running
- Valid tenant_key
- User Settings page exists

---

## Rollback Plan

If plugin approach fails:
1. Keep existing local template export working
2. CLI mode falls back to manual template management
3. No database changes required for rollback
4. Setup UI can be hidden via feature flag

---

## Related Handovers

- **0333**: Staging Prompt Architecture Correction (COMPLETE)
- **0260**: Claude Code CLI Mode (toggle persistence)
- **0262**: Agent Mission Protocol (atomic get_agent_mission)

---

## Open Questions Resolved

| Question | Decision |
|----------|----------|
| Plugin install per-prompt or one-time? | **One-time** via Profile setup |
| How to handle local file conflicts? | **Warn in staging prompt** with explicit check |
| Tenant key or API key? | **Tenant key** - simpler, already available |
| Cache duration? | **5 minutes** (300s TTL) |

---

## Files Summary

### New Files
- `api/endpoints/agent_templates.py`
- `plugins/giljoai-agents/package.json`
- `plugins/giljoai-agents/.claude-plugin/plugin.json`
- `plugins/giljoai-agents/src/agent-provider.js`
- `plugins/giljoai-agents/README.md`
- `frontend/src/components/settings/ClaudeCodeSetup.vue`
- `tests/api/test_agent_templates_plugin.py`
- `docs/user_guides/claude_code_plugin_setup.md`

### Modified Files
- `api/app.py` (register new router)
- `src/giljo_mcp/thin_prompt_generator.py` (CLI mode block)
- `frontend/src/views/MySettingsView.vue` (add setup section)

---

## Estimated Total Effort

| Phase | Effort | Priority |
|-------|--------|----------|
| 0334a: Backend API | 4-6 hours | High |
| 0334b: Plugin Package | 6-8 hours | High |
| 0334c: Profile Setup UI | 4-6 hours | High |
| 0334d: Staging Prompt | 2-3 hours | High |
| 0334e: Testing & Docs | 4-6 hours | Medium |
| **Total** | **20-29 hours** | - |
