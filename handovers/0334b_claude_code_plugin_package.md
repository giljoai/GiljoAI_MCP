# Handover 0334b: Claude Code Plugin Package Creation

**Date:** 2025-12-07
**From Agent:** Documentation Manager (0334 Session)
**To Agent:** TDD Implementor, System Architect
**Priority:** High
**Estimated Complexity:** 6-8 hours
**Status:** Ready for Implementation
**Parent Handover:** 0334 (Claude Code Plugin - Agent Template Bridge)

---

## Executive Summary

Create a Claude Code plugin package that dynamically fetches agent templates from the GiljoAI MCP server, eliminating the need for local `.md` template files. The plugin connects to the database via the API endpoint created in 0334a, providing real-time agent synchronization and centralized template management.

**Expected Outcome:** A production-ready npm package that can be installed once per user via `claude plugins install` and automatically provides all active agent templates from their GiljoAI tenant.

---

## Context and Background

### How We Got Here

1. **Handover 0333** simplified the staging prompt from 150+ lines to ~35 lines
2. During testing, we discovered the `agent_type` enforcement problem - orchestrators must match exact template names
3. User insight: Claude Code has a plugin system that can fetch agents dynamically
4. Key realization: We can use the plugin as a bridge to our database, making GiljoAI the "marketplace"
5. **Handover 0334a** created the backend API endpoint (`GET /api/v1/agent-templates/plugin`)
6. **This handover (0334b)** creates the plugin package that consumes that endpoint

### The Local File Conflict Problem

**CRITICAL DISCOVERY:** Claude Code has a priority hierarchy for agent resolution:

```
1. Project agents     (.claude/agents/)     ← HIGHEST - will override plugin!
2. User agents        (~/.claude/agents/)   ← Will override plugin!
3. Plugin agents      (from our plugin)     ← Lowest priority
```

**This means:** Any existing local `.md` files WILL interfere with plugin-provided agents. The staging prompt (0334d) must check for and warn about these conflicts.

### Why a Plugin Approach?

**Benefits:**
- **Centralized Management**: Templates managed in GiljoAI UI, not scattered .md files
- **Real-Time Sync**: Database changes reflect immediately (or with short TTL cache)
- **Multi-Tenant Isolation**: Each user sees only their tenant's templates via tenant_key
- **No Manual Export**: Users never manually copy/paste templates to disk
- **Version Control**: Template changes tracked in database, not git-ignored files

**vs. Local File Approach:**
- ❌ Manual export required after every template change
- ❌ Sync issues between database and filesystem
- ❌ No centralized control or audit trail
- ❌ Each user manages their own collection

---

## Research Required Before Implementation

**IMPORTANT:** This handover is based on assumptions about Claude Code's plugin API. Before implementation, research and verify:

### Questions to Answer

1. **Plugin Manifest Format:**
   - What is the exact schema for `.claude-plugin/plugin.json`?
   - Are our assumed fields (`name`, `version`, `description`, `agents`, `configuration`) correct?
   - What additional fields are required or optional?

2. **Dynamic Agent Provider:**
   - What is the exact signature for the `provider` function?
   - Does `agents.source: "dynamic"` actually exist, or is there a different mechanism?
   - What format does `getAgents()` need to return?
   - Are there lifecycle hooks (onLoad, onUnload, etc.)?

3. **Configuration System:**
   - Can plugins accept configuration parameters?
   - How does a user provide `server_url` and `tenant_key` during installation?
   - Is there a config UI, or is it CLI-only?

4. **Installation Flow:**
   - What does `claude plugins install` actually look like?
   - Can we provide a package name (e.g., `@giljoai/claude-code-agents`)?
   - Can we pass config inline: `--config server_url=... --config tenant_key=...`?
   - Or does config happen in a separate step?

5. **Agent Format:**
   - What fields does a Claude Code agent object require?
   - Is our assumed format correct: `{ name, description, instructions, capabilities }`?
   - Are there additional required fields (version, author, etc.)?

6. **Caching Behavior:**
   - Does Claude Code cache plugin agent lists?
   - How often does it re-fetch from the provider?
   - Can we control cache TTL, or is it fixed?

### How to Research

**Documentation Sources:**
- Claude Code official docs (if available)
- GitHub repo for Claude Code (if public)
- Existing plugin examples (if any in the wild)
- Anthropic developer documentation

**Experimental Approach:**
If no docs exist:
1. Create a minimal test plugin with hardcoded agents
2. Test installation and invocation
3. Reverse-engineer the required format
4. Document findings in this handover before proceeding

**Action Item:** Document ALL research findings in a `## Research Findings` section below before writing code.

---

## Technical Specification

### Plugin Directory Structure

```
plugins/giljoai-agents/
├── package.json              # NPM package metadata
├── .claude-plugin/
│   └── plugin.json           # Claude Code plugin manifest
├── src/
│   └── agent-provider.js     # Dynamic agent fetching logic
├── tests/
│   └── agent-provider.test.js # Unit tests
├── README.md                 # Installation and usage guide
└── .gitignore                # Ignore node_modules, etc.
```

### Plugin Manifest (plugin.json)

**ASSUMPTION (verify during research):**

```json
{
  "name": "giljoai-agents",
  "version": "1.0.0",
  "description": "Dynamic agent templates from GiljoAI MCP Server",
  "author": "GiljoAI",
  "homepage": "https://github.com/yourusername/giljoai-mcp",
  "agents": {
    "source": "dynamic",
    "provider": "../src/agent-provider.js"
  },
  "configuration": {
    "server_url": {
      "type": "string",
      "required": true,
      "description": "GiljoAI MCP server URL (e.g., http://localhost:7272)",
      "default": "http://localhost:7272"
    },
    "tenant_key": {
      "type": "string",
      "required": true,
      "description": "User's tenant key for multi-tenant isolation"
    }
  }
}
```

**Key Fields:**
- `agents.source: "dynamic"` - Tells Claude Code to fetch agents at runtime (vs. static)
- `agents.provider` - Path to JavaScript module that exports `getAgents()` function
- `configuration` - User-provided values during installation

**TODO:** Verify this schema during research phase. Update if actual format differs.

### Agent Provider Logic (agent-provider.js)

**ASSUMPTION (verify during research):**

```javascript
/**
 * Dynamic agent provider for GiljoAI MCP Server
 * Fetches agent templates from the database via HTTP API
 */

async function getAgents(config) {
  const { server_url, tenant_key } = config;

  // Validate configuration
  if (!server_url || !tenant_key) {
    console.error('[GiljoAI Plugin] Missing required configuration: server_url and tenant_key');
    return [];
  }

  try {
    // Fetch agent templates from GiljoAI API
    const url = `${server_url}/api/v1/agent-templates/plugin?tenant_key=${encodeURIComponent(tenant_key)}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json'
      },
      // Timeout after 5 seconds
      signal: AbortSignal.timeout(5000)
    });

    if (!response.ok) {
      console.error(`[GiljoAI Plugin] Failed to fetch agents: ${response.status} ${response.statusText}`);
      return [];
    }

    const data = await response.json();

    // Convert GiljoAI template format to Claude Code agent format
    return data.templates.map(template => ({
      name: template.name,
      description: template.description || template.role,
      instructions: template.full_instructions,
      capabilities: template.capabilities || [],
      // Optional metadata
      metadata: {
        template_id: template.template_id,
        is_active: template.is_active,
        tenant_key: template.tenant_key
      }
    }));

  } catch (error) {
    console.error('[GiljoAI Plugin] Error fetching agents:', error.message);
    return [];
  }
}

// Export for Claude Code plugin system
module.exports = { getAgents };
```

**Error Handling Strategy:**
- **Network Failure**: Return empty array (graceful degradation)
- **Invalid Config**: Log error, return empty array
- **Server Error**: Log error, return empty array
- **No Agents**: Return empty array (valid state)

**Why Empty Array vs. Throwing:**
- Plugin should not crash Claude Code if server is down
- User can still use built-in agents or manually-created ones
- Error logged to console for debugging

**TODO:** Verify `getAgents()` signature and return format during research.

### Package Metadata (package.json)

```json
{
  "name": "@giljoai/claude-code-agents",
  "version": "1.0.0",
  "description": "GiljoAI agent templates for Claude Code - dynamically fetched from your GiljoAI MCP server",
  "main": "src/agent-provider.js",
  "scripts": {
    "test": "node tests/agent-provider.test.js"
  },
  "files": [
    "src/",
    ".claude-plugin/",
    "README.md"
  ],
  "keywords": [
    "claude-code",
    "agents",
    "giljoai",
    "mcp",
    "ai-agents",
    "code-generation"
  ],
  "author": "GiljoAI",
  "license": "MIT",
  "repository": {
    "type": "git",
    "url": "https://github.com/yourusername/giljoai-mcp.git",
    "directory": "plugins/giljoai-agents"
  },
  "engines": {
    "node": ">=16.0.0"
  },
  "dependencies": {},
  "devDependencies": {
    "node:test": "latest"
  }
}
```

**Key Decisions:**
- **Scoped Package**: `@giljoai/claude-code-agents` for npm organization namespace
- **No Dependencies**: Pure JavaScript, uses built-in `fetch` (Node 18+)
- **Files Whitelist**: Only ship necessary files (no tests, no .git)

---

## Installation Flow

### User Experience (End-to-End)

```
User goes to GiljoAI Dashboard
  ↓
My Settings → Integrations → Claude Code CLI
  ↓
Sees section: "Claude Code Plugin Setup"
  ↓
Install command displayed with tenant_key pre-filled:
  claude plugins install giljoai-agents --config server_url=http://localhost:7272 --config tenant_key=tk_abc123
  ↓
User clicks [Copy Install Command] button
  ↓
User pastes in Claude Code terminal and runs
  ↓
Plugin installed permanently for that user
  ↓
User can verify with: /plugins list
  ↓
User can see agents with: /agents
```

### Install Command Format

**ASSUMPTION (verify during research):**

```bash
# Local development
claude plugins install /path/to/plugins/giljoai-agents \
  --config server_url=http://localhost:7272 \
  --config tenant_key=tk_abc123def456

# Production (once published to npm)
claude plugins install @giljoai/claude-code-agents \
  --config server_url=https://your-giljoai-server.com \
  --config tenant_key=tk_abc123def456
```

**TODO:** Verify exact syntax during research. May need to:
- Provide config in a separate step
- Use environment variables instead
- Store config in a `.claude-plugins.json` file

### Configuration Persistence

**Question for Research:**
- Where does Claude Code store plugin configuration?
- Is it per-user (~/.claude/plugins/config.json)?
- Is it per-project (.claude/plugins.json)?
- Can users edit config without reinstalling?

**Assumption:** Config is stored globally per user, persists across Claude Code restarts.

---

## README.md Content

```markdown
# GiljoAI Agents Plugin for Claude Code

Dynamic agent templates fetched from your GiljoAI MCP server in real-time.

## What This Plugin Does

Instead of managing agent templates as local `.md` files, this plugin:
- Fetches your custom agent templates from the GiljoAI database
- Updates automatically when you change templates in the UI
- Provides multi-tenant isolation (you only see your agents)
- Makes agents available via `/agents` and `@agent_name` syntax

## Prerequisites

1. **GiljoAI MCP Server** running (local or network)
2. **Tenant Key** from your GiljoAI account (Settings → Integrations)
3. **Claude Code CLI** installed

## Installation

### Step 1: Get Your Tenant Key

1. Open GiljoAI Dashboard
2. Go to **My Settings → Integrations → Claude Code CLI**
3. Copy the install command (includes your tenant_key)

### Step 2: Install the Plugin

Run the copied command in your Claude Code terminal:

```bash
claude plugins install giljoai-agents \
  --config server_url=http://localhost:7272 \
  --config tenant_key=tk_your_key_here
```

**Note:** Replace `http://localhost:7272` with your server URL if different.

### Step 3: Verify Installation

```bash
# Check plugin is installed
/plugins list

# You should see: giljoai-agents (v1.0.0)

# List available agents
/agents

# You should see your agent templates
```

## Usage

### In Claude Code

Invoke agents by name using the `@` syntax:

```
@implementer Build a REST API for user authentication
@tester Write comprehensive tests for the auth module
@orchestrator Coordinate the team to build the feature
```

Or use the Task tool in CLI mode:

```python
Task(subagent_type="implementer", prompt="Build the auth module")
```

## Troubleshooting

### Plugin Shows No Agents

**Problem:** `/agents` returns empty list

**Solutions:**
1. Verify server is running: `curl http://localhost:7272/api/health`
2. Check tenant_key is correct: `claude plugins config giljoai-agents`
3. Verify templates exist: Check GiljoAI → Agent Templates (at least one active)

### "Connection Refused" Error

**Problem:** Plugin cannot reach GiljoAI server

**Solutions:**
1. Verify server_url is correct and accessible
2. If using network URL, check firewall rules
3. Test connection: `curl http://localhost:7272/api/v1/agent-templates/plugin?tenant_key=tk_xxx`

### Local `.md` Files Override Plugin Agents

**Problem:** Changes in GiljoAI UI don't reflect in `/agents`

**Explanation:** Claude Code prioritizes local files over plugin agents:
```
1. .claude/agents/*.md (project-level) ← HIGHEST
2. ~/.claude/agents/*.md (user-level)
3. Plugin agents ← LOWEST
```

**Solution:** Remove or rename local `.md` files:
```bash
# Check for conflicts
ls ~/.claude/agents/*.md
ls .claude/agents/*.md

# Remove local overrides
rm ~/.claude/agents/*.md
```

### Agent Template Changes Don't Appear

**Problem:** Updated template in UI but `/agents` shows old version

**Solution:** Claude Code may cache agent list. Restart Claude Code or wait for cache TTL (5 minutes).

## Configuration

View current configuration:
```bash
claude plugins config giljoai-agents
```

Update configuration:
```bash
claude plugins config giljoai-agents server_url=https://new-server.com
```

## Uninstallation

```bash
claude plugins uninstall giljoai-agents
```

## Support

- **Documentation**: https://github.com/yourusername/giljoai-mcp/docs
- **Issues**: https://github.com/yourusername/giljoai-mcp/issues
- **GiljoAI Dashboard**: http://localhost:7272

## License

MIT License - see LICENSE file for details
```

---

## TDD Test Requirements

### Test File Structure

```
tests/
├── agent-provider.test.js       # Core provider logic
├── fixtures/
│   ├── valid-response.json      # Mock API response
│   └── empty-response.json      # Mock empty response
└── README.md                    # How to run tests
```

### Test Cases

**File:** `tests/agent-provider.test.js`

```javascript
const { test } = require('node:test');
const assert = require('node:assert');

// Mock fetch for testing
global.fetch = async (url, options) => {
  // Test can override this
  if (global.mockFetchResponse) {
    return global.mockFetchResponse;
  }
  throw new Error('No mock fetch response defined');
};

// Import module under test
const { getAgents } = require('../src/agent-provider.js');

test('getAgents: successful API response returns agent list', async () => {
  // Arrange
  global.mockFetchResponse = {
    ok: true,
    status: 200,
    json: async () => ({
      templates: [
        {
          name: 'implementer',
          role: 'Code Implementation Specialist',
          description: 'Implements features following TDD',
          full_instructions: 'You are an implementer agent...',
          capabilities: ['code_generation', 'testing'],
          template_id: 'tpl_123',
          is_active: true,
          tenant_key: 'tk_test'
        }
      ],
      count: 1
    })
  };

  const config = {
    server_url: 'http://localhost:7272',
    tenant_key: 'tk_test'
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 1);
  assert.strictEqual(agents[0].name, 'implementer');
  assert.strictEqual(agents[0].description, 'Implements features following TDD');
  assert.ok(agents[0].instructions.includes('implementer agent'));
  assert.deepStrictEqual(agents[0].capabilities, ['code_generation', 'testing']);
});

test('getAgents: API error returns empty array', async () => {
  // Arrange
  global.mockFetchResponse = {
    ok: false,
    status: 500,
    statusText: 'Internal Server Error'
  };

  const config = {
    server_url: 'http://localhost:7272',
    tenant_key: 'tk_test'
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 0);
});

test('getAgents: missing server_url returns empty array', async () => {
  // Arrange
  const config = {
    tenant_key: 'tk_test'
    // server_url missing
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 0);
});

test('getAgents: missing tenant_key returns empty array', async () => {
  // Arrange
  const config = {
    server_url: 'http://localhost:7272'
    // tenant_key missing
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 0);
});

test('getAgents: network timeout returns empty array', async () => {
  // Arrange
  global.mockFetchResponse = Promise.reject(new Error('Network timeout'));

  const config = {
    server_url: 'http://localhost:7272',
    tenant_key: 'tk_test'
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 0);
});

test('getAgents: empty templates array returns empty array', async () => {
  // Arrange
  global.mockFetchResponse = {
    ok: true,
    status: 200,
    json: async () => ({
      templates: [],
      count: 0
    })
  };

  const config = {
    server_url: 'http://localhost:7272',
    tenant_key: 'tk_test'
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 0);
});

test('getAgents: malformed response returns empty array', async () => {
  // Arrange
  global.mockFetchResponse = {
    ok: true,
    status: 200,
    json: async () => ({
      // Missing 'templates' field
      count: 5
    })
  };

  const config = {
    server_url: 'http://localhost:7272',
    tenant_key: 'tk_test'
  };

  // Act
  const agents = await getAgents(config);

  // Assert
  assert.strictEqual(agents.length, 0);
});
```

### Running Tests

```bash
# Run all tests
npm test

# Run with verbose output
node --test tests/agent-provider.test.js
```

### Test Coverage Goals

- **Unit Tests**: 100% coverage of `agent-provider.js`
- **Error Cases**: All failure modes tested
- **Happy Path**: Successful API response
- **Edge Cases**: Empty response, malformed data

---

## Integration with GiljoAI UI (0334c)

This plugin package is consumed by the UI component created in Handover 0334c.

### UI Requirements

The Settings page must provide:

1. **Install Command Generator:**
   - Renders command with user's actual tenant_key
   - Copy button for one-click clipboard copy
   - Example: `claude plugins install giljoai-agents --config server_url=... --config tenant_key=tk_xxx`

2. **Connection Test:**
   - Button: "Test Plugin Connection"
   - Makes request to `/api/v1/agent-templates/plugin?tenant_key=...`
   - Shows success/failure status

3. **Status Indicator:**
   - Not Verified (gray) - default state
   - Verified (green) - after successful test
   - Error (red) - if test fails

4. **Documentation Link:**
   - Link to plugin README.md
   - Troubleshooting section

### Data Flow

```
User clicks "Test Plugin Connection"
  ↓
Frontend calls: GET /api/v1/agent-templates/plugin?tenant_key=tk_xxx
  ↓
Backend returns agent templates (from 0334a)
  ↓
Frontend shows: "✓ Found 5 active agents"
  ↓
Status: Not Verified → Verified
```

---

## Files Summary

### New Files

```
plugins/giljoai-agents/
├── package.json                    # NPM package metadata
├── .claude-plugin/
│   └── plugin.json                 # Plugin manifest
├── src/
│   └── agent-provider.js           # Dynamic agent fetcher
├── tests/
│   ├── agent-provider.test.js      # Unit tests
│   └── fixtures/
│       ├── valid-response.json     # Test fixture
│       └── empty-response.json     # Test fixture
├── README.md                       # Installation guide
└── .gitignore                      # Ignore node_modules
```

### Modified Files

None (this handover is entirely new files)

---

## Success Criteria Checklist

### Plugin Package
- [ ] Directory structure created: `plugins/giljoai-agents/`
- [ ] `package.json` with correct metadata and dependencies
- [ ] `.claude-plugin/plugin.json` manifest exists
- [ ] `src/agent-provider.js` implements `getAgents()` function
- [ ] Error handling for network failures, invalid config, malformed responses
- [ ] README.md with installation and troubleshooting guide

### Testing
- [ ] Unit tests pass (100% coverage of agent-provider.js)
- [ ] Tests cover success case (valid API response)
- [ ] Tests cover error cases (network failure, missing config, etc.)
- [ ] Manual test: Plugin installs successfully
- [ ] Manual test: `/agents` command shows templates from database

### Integration
- [ ] Plugin consumes endpoint from 0334a
- [ ] Tenant_key isolation verified (user only sees their templates)
- [ ] Template changes in UI reflect in `/agents` list (after cache TTL)

### Documentation
- [ ] README.md includes prerequisites, installation steps, usage examples
- [ ] Troubleshooting section addresses common issues
- [ ] Configuration section explains server_url and tenant_key

---

## Dependencies

### Blockers
- **0334a MUST be complete** - Backend API endpoint required
- Claude Code plugin API research must be completed first

### Related Handovers
- **0334a**: Backend API Endpoint (dependency)
- **0334c**: User Profile Setup UI (consumer)
- **0334d**: Staging Prompt Integration (consumer)

---

## Rollback Plan

If plugin approach fails or Claude Code plugin API is incompatible:

1. **Keep existing export mechanism** - Users can still export templates to `.md` files
2. **Hide plugin UI** - Feature flag in Settings to disable plugin setup section
3. **No database changes** - This handover is purely client-side
4. **Delete plugin directory** - No migration required

**Rollback Trigger:**
- Claude Code plugin API doesn't support dynamic agents
- Security concerns with tenant_key in plugin config
- Performance issues with API calls

---

## Open Questions

| Question | Status | Decision |
|----------|--------|----------|
| What is the exact plugin manifest schema? | **RESEARCH REQUIRED** | TBD |
| Does `agents.source: "dynamic"` exist? | **RESEARCH REQUIRED** | TBD |
| What is `getAgents()` signature? | **RESEARCH REQUIRED** | TBD |
| How is plugin configuration provided? | **RESEARCH REQUIRED** | TBD |
| What agent format does Claude Code expect? | **RESEARCH REQUIRED** | TBD |
| Can plugins control cache TTL? | **RESEARCH REQUIRED** | TBD |
| Where is plugin config stored? | **RESEARCH REQUIRED** | TBD |

**ACTION ITEM:** Implementing agent MUST research these questions and document findings before writing code.

---

## Research Findings

**TODO:** Document Claude Code plugin API research here before implementation.

### Plugin API Documentation
- Link to official docs:
- Version tested:
- Date researched:

### Manifest Schema
```json
{
  // Actual schema from research
}
```

### Agent Provider Interface
```javascript
// Actual signature from research
```

### Configuration Mechanism
- How config is provided:
- Where config is stored:
- How to update config:

### Agent Format
```javascript
{
  // Actual required fields from research
}
```

### Caching Behavior
- Cache duration:
- Cache invalidation:
- User control:

---

## Estimated Effort Breakdown

| Task | Estimated Time |
|------|----------------|
| Research Claude Code plugin API | 2-3 hours |
| Create plugin directory structure | 30 min |
| Write plugin.json manifest | 1 hour |
| Write agent-provider.js | 2 hours |
| Write unit tests | 1-2 hours |
| Write README.md | 1 hour |
| Manual testing and debugging | 1-2 hours |
| **Total** | **8-11 hours** |

**Note:** Estimate assumes Claude Code plugin API is well-documented. Add 2-4 hours if extensive reverse-engineering is required.

---

## Recommended Sub-Agent

**Primary:** `system-architect` - Plugin architecture, API integration
**Secondary:** `tdd-implementor` - Unit test creation, TDD workflow
**Tertiary:** `documentation-manager` - README.md and troubleshooting guide

---

## Notes for Implementing Agent

### DO

1. **Research first** - Do NOT write code before understanding Claude Code plugin API
2. **Document findings** - Update "Research Findings" section with actual API details
3. **Test incrementally** - Create minimal plugin first, verify it loads, then add complexity
4. **Handle errors gracefully** - Return empty array, never crash Claude Code
5. **Use built-in fetch** - No external dependencies if possible (Node 18+)
6. **Follow npm best practices** - Scoped package, semantic versioning, LICENSE file

### DO NOT

1. **Assume the specification** - Everything marked "ASSUMPTION" MUST be verified
2. **Hardcode values** - Use config.server_url and config.tenant_key
3. **Expose secrets** - Tenant_key is a partition ID, not a secret, but still handle carefully
4. **Block Claude Code startup** - If plugin fails to load, fail silently
5. **Cache indefinitely** - Respect server's cache_ttl (if available)

### Testing Checklist

- [ ] Plugin loads without errors
- [ ] `/plugins list` shows giljoai-agents
- [ ] `/agents` shows templates from database
- [ ] Changing templates in UI reflects in `/agents` (after cache expires)
- [ ] Invalid tenant_key returns empty array (not error)
- [ ] Network failure returns empty array (not error)
- [ ] Missing config returns empty array (not error)

---

## Additional Resources

### Backend Endpoint (from 0334a)

**Endpoint:** `GET /api/v1/agent-templates/plugin?tenant_key=tk_xxx`

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

### Existing Agent Template Structure

See `src/giljo_mcp/models.py` - `AgentTemplate` table:
- `template_id` (primary key)
- `name` (agent type, must match exactly)
- `role` (short description)
- `description` (detailed explanation)
- `full_instructions` (complete agent prompt)
- `capabilities` (array of strings)
- `is_active` (boolean)
- `tenant_key` (multi-tenant isolation)

---

## Post-Implementation Validation

After completion, verify:

1. **Installation Flow:**
   - Copy command from GiljoAI UI
   - Run in Claude Code terminal
   - Verify `/plugins list` shows plugin
   - Verify `/agents` shows templates

2. **Multi-Tenant Isolation:**
   - Create two users with different tenants
   - Install plugin for each with their tenant_key
   - Verify each sees only their templates

3. **Template Synchronization:**
   - Create new template in GiljoAI UI
   - Wait for cache TTL
   - Verify `/agents` shows new template

4. **Error Handling:**
   - Stop GiljoAI server
   - Verify Claude Code doesn't crash
   - Verify `/agents` returns empty (with console error)

5. **Local File Conflicts:**
   - Create `~/.claude/agents/test.md`
   - Verify local file overrides plugin (test priority)
   - Delete local file
   - Verify plugin agents appear again
