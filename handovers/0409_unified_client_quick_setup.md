# Handover: Unified Client Quick Setup

**Date:** 2026-01-16
**From Agent:** Documentation Manager
**To Agent:** Installation Flow Agent + TDD Implementor
**Priority:** High
**Estimated Complexity:** 8-12 hours
**Status:** Not Started

---

## Task Summary

Add "Quick Setup" buttons to the ProductIntroTour onboarding flow that generate complete, copy-paste installation prompts for Claude Code, Codex CLI, and Gemini CLI. Each prompt includes API key generation, MCP connection commands, slash command installation, and (for Claude Code only) agent template installation - eliminating the current multi-step, error-prone manual setup process.

**Why it's important:** Reduces setup friction from 6+ manual steps to a single copy-paste action, improving user onboarding success rate.

**Expected outcome:** User completes 8-slide tour → clicks client button → pastes prompt into CLI → everything configured automatically.

---

## Context and Background

### Current Setup Pain Points
Users must currently:
1. Run `install.py`
2. Create user account via `/welcome`
3. Navigate to Settings → Integrations
4. Manually configure MCP connection
5. Separately download and install slash commands
6. Download and install agent templates (Claude only)
7. Restart CLI tool

This is error-prone, varies by client, and requires understanding of file system paths and CLI configuration formats.

### Proposed Solution
Add 3 buttons at the end of ProductIntroTour (slide 8):
- **Setup Claude Code** - Full setup (MCP + Commands + Agents)
- **Setup Codex CLI** - MCP + Commands only (multi-terminal mode)
- **Setup Gemini CLI** - MCP + Commands only (multi-terminal mode, Beta)

Each button generates a complete installation prompt that:
- Generates and embeds API key
- Provides client-specific MCP connection command
- Downloads and installs slash commands in correct format/location
- Downloads and installs agent templates (Claude Code only)
- Includes restart instructions

### Why Client Differences Exist

**Claude Code gets agents because:**
- Supports "Claude Code Mode" with native subagent spawning
- Orchestrator can spawn @tdd-implementor, @frontend-tester from local templates
- Requires agent templates in `~/.claude/agents/`

**Codex/Gemini don't get agents because:**
- Operate in "Multi-Terminal Mode" only
- Each agent runs in separate terminal
- Agents fetch missions from MCP server via `get_agent_mission(job_id)`
- No local templates needed - everything from server

---

## Technical Details

### Client Configuration Comparison

| Aspect | Claude Code | Codex CLI | Gemini CLI |
|--------|-------------|-----------|------------|
| Commands Location | `~/.claude/commands/` | `~/.codex/prompts/` | `~/.gemini/commands/` |
| Agents Location | `~/.claude/agents/` | N/A | N/A |
| File Format | Markdown (.md) | Markdown (.md) | TOML (.toml) |
| Arguments | `$ARGUMENTS` | `$VAR_NAME` | `{{args}}` |
| Invocation | `/gil_activate` | `/prompts:gil_activate` | `/gil_activate` |
| MCP Command | `claude mcp add --transport http giljo-mcp URL --header "X-API-Key: KEY"` | `codex mcp add giljo-mcp --env GILJO_MCP_SERVER_URL="URL" --env GILJO_API_KEY="KEY" -- python -m giljo_mcp.mcp_http_stdin_proxy` | `gemini mcp add -t http -H "X-API-Key: KEY" giljo-mcp URL` |
| Extra Requirements | None | WHL proxy module | None (Beta) |
| Execution Mode | Both modes | Multi-terminal only | Multi-terminal only |

### Files to Create/Modify

**Create:**
1. `api/endpoints/quick_setup.py` - New API endpoints for prompt generation and ZIP serving
2. `src/giljo_mcp/template_converter.py` - Format conversion logic (Claude→Codex, Claude→Gemini)

**Modify:**
1. `src/giljo_mcp/tools/slash_command_templates.py` - Add Codex/Gemini template variants
2. `frontend/src/components/settings/ProductIntroTour.vue` - Add quick setup buttons (slide 8)
3. `frontend/src/services/api.js` - Add `setup.generatePrompt(client)` method
4. `api/app.py` - Register new quick_setup router

### API Endpoints Design

#### POST `/api/setup/generate-prompt?client={claude|codex|gemini}`
**Purpose:** Generate client-specific installation prompt

**Request:**
```json
{
  "client": "claude"  // or "codex", "gemini"
}
```

**Response:**
```json
{
  "prompt": "# GiljoAI MCP Setup for Claude Code\n\nPaste this entire prompt into Claude Code...",
  "download_token": "abc123xyz",
  "api_key": "sk_prod_...",
  "server_url": "http://localhost:7272"
}
```

**Implementation Steps:**
1. Generate API key with name `{client}_quick_setup`
2. Get server URL from config.yaml
3. Stage ZIP bundle via temp token
4. Build client-specific prompt with embedded commands
5. Return prompt + metadata

#### GET `/api/download/setup/{token}/{client}.zip`
**Purpose:** Serve client-specific ZIP bundle

**Implementation:**
1. Validate token (15-minute expiry)
2. Get client type from URL
3. Generate ZIP with:
   - Claude: commands/ + agents/ folders
   - Codex: prompts/ folder only
   - Gemini: commands/ folder only
4. Stream ZIP response
5. Clean up temp files

### Template Converter Module

**File:** `src/giljo_mcp/template_converter.py`

**Functions:**

```python
def convert_claude_to_codex(template_md: str) -> str:
    """Convert Claude markdown to Codex markdown format.

    Changes:
    - Arguments: $ARGUMENTS → $VAR_NAME
    - Invocation: /command → /prompts:command
    - Location: ~/.claude/commands → ~/.codex/prompts
    """
    pass

def convert_claude_to_gemini(template_md: str) -> str:
    """Convert Claude markdown to Gemini TOML format.

    Structure:
    [command]
    name = "gil_activate"
    description = "..."
    prompt = '''...'''

    Changes:
    - Arguments: $ARGUMENTS → {{args}}
    - Format: Markdown → TOML
    - Location: ~/.claude/commands → ~/.gemini/commands
    """
    pass

def test_conversion_roundtrip():
    """Test that conversions preserve semantic meaning."""
    pass
```

### Slash Command Templates Update

**File:** `src/giljo_mcp/tools/slash_command_templates.py`

**Current:** Only has Claude templates

**Add:**
1. Codex markdown variants (15 commands)
2. Gemini TOML variants (15 commands)

**Template Structure:**

```python
CLAUDE_COMMANDS = {
    "gil_activate": {
        "filename": "gil_activate.md",
        "content": "# Activate Project\n\n$ARGUMENTS\n..."
    },
    # ... 14 more
}

CODEX_COMMANDS = {
    "gil_activate": {
        "filename": "gil_activate.md",
        "content": "# Activate Project\n\n$VAR_NAME\n..."
    },
    # ... 14 more
}

GEMINI_COMMANDS = {
    "gil_activate": {
        "filename": "gil_activate.toml",
        "content": "[command]\nname = 'gil_activate'\n..."
    },
    # ... 14 more
}
```

### Frontend Changes

**File:** `frontend/src/components/settings/ProductIntroTour.vue`

**Add to slide 8 (or modify existing final slide):**

```vue
<v-card-text>
  <h3>Quick Setup - Choose Your Client</h3>
  <p>Click your CLI tool below to get a complete setup prompt:</p>

  <v-row>
    <v-col cols="4">
      <v-btn
        color="primary"
        block
        large
        @click="generateSetupPrompt('claude')"
      >
        <v-icon left>mdi-robot</v-icon>
        Setup Claude Code
        <v-chip small class="ml-2">Recommended</v-chip>
      </v-btn>
      <p class="text-caption mt-2">
        Full setup: MCP + Commands + Agents
      </p>
    </v-col>

    <v-col cols="4">
      <v-btn
        color="primary"
        block
        large
        outlined
        @click="generateSetupPrompt('codex')"
      >
        <v-icon left>mdi-console</v-icon>
        Setup Codex CLI
        <v-chip small class="ml-2" color="warning">Requires Proxy</v-chip>
      </v-btn>
      <p class="text-caption mt-2">
        Multi-terminal: MCP + Commands
      </p>
    </v-col>

    <v-col cols="4">
      <v-btn
        color="primary"
        block
        large
        outlined
        @click="generateSetupPrompt('gemini')"
      >
        <v-icon left>mdi-google</v-icon>
        Setup Gemini CLI
        <v-chip small class="ml-2" color="info">Beta</v-chip>
      </v-btn>
      <p class="text-caption mt-2">
        Multi-terminal: MCP + Commands
      </p>
    </v-col>
  </v-row>

  <!-- Dialog to show generated prompt -->
  <v-dialog v-model="setupDialog" max-width="800">
    <v-card>
      <v-card-title>
        {{ selectedClient }} Setup Prompt
        <v-spacer />
        <v-btn icon @click="setupDialog = false">
          <v-icon>mdi-close</v-icon>
        </v-btn>
      </v-card-title>
      <v-card-text>
        <v-textarea
          :value="setupPrompt"
          readonly
          rows="20"
          outlined
          class="code-text"
        />
      </v-card-text>
      <v-card-actions>
        <v-btn
          color="primary"
          @click="copyToClipboard(setupPrompt)"
        >
          <v-icon left>mdi-content-copy</v-icon>
          Copy to Clipboard
        </v-btn>
        <v-spacer />
        <v-btn text @click="setupDialog = false">Close</v-btn>
      </v-card-actions>
    </v-card>
  </v-dialog>
</v-card-text>
```

**Methods:**

```javascript
async generateSetupPrompt(client) {
  try {
    this.selectedClient = client;
    const response = await api.setup.generatePrompt(client);
    this.setupPrompt = response.prompt;
    this.setupDialog = true;
  } catch (error) {
    console.error('Failed to generate setup prompt:', error);
    this.$emit('show-snackbar', {
      message: 'Failed to generate setup prompt',
      color: 'error'
    });
  }
}

copyToClipboard(text) {
  navigator.clipboard.writeText(text);
  this.$emit('show-snackbar', {
    message: 'Prompt copied to clipboard!',
    color: 'success'
  });
}
```

**Frontend Service Update:**

**File:** `frontend/src/services/api.js`

```javascript
setup: {
  async generatePrompt(client) {
    const response = await fetch(`/api/setup/generate-prompt?client=${client}`, {
      method: 'POST',
      headers: getAuthHeaders()
    });
    return response.json();
  }
}
```

---

## Implementation Plan

### Phase 1: Backend Infrastructure (4-5 hours)
**Owner:** TDD Implementor + Database Expert

1. Create `src/giljo_mcp/template_converter.py`
   - Implement `convert_claude_to_codex()`
   - Implement `convert_claude_to_gemini()`
   - Write unit tests (12 tests minimum)
   - Test coverage: >85%

2. Update `src/giljo_mcp/tools/slash_command_templates.py`
   - Add `CODEX_COMMANDS` dictionary (15 commands)
   - Add `GEMINI_COMMANDS` dictionary (15 commands)
   - Add `get_commands_for_client(client: str)` helper
   - Write unit tests

3. Create `api/endpoints/quick_setup.py`
   - Implement POST `/api/setup/generate-prompt`
   - Implement GET `/api/download/setup/{token}/{client}.zip`
   - Token management (15-minute expiry)
   - Write integration tests (8 tests minimum)

4. Register router in `api/app.py`
   - Import quick_setup router
   - Register with `/api/setup` prefix

**Testing Criteria:**
- All unit tests pass
- Integration tests verify:
  - API key generation
  - ZIP bundle creation
  - Token expiry enforcement
  - Client-specific content

### Phase 2: Frontend Integration (2-3 hours)
**Owner:** UX Designer + Frontend Tester

1. Update `ProductIntroTour.vue`
   - Add slide 8 with 3 quick setup buttons
   - Implement setup dialog
   - Add copy-to-clipboard functionality
   - Style with Vuetify components

2. Update `frontend/src/services/api.js`
   - Add `setup.generatePrompt(client)` method
   - Handle errors and loading states

3. Write frontend tests
   - Component unit tests (button clicks, dialog display)
   - Integration tests (API calls, clipboard)

**Testing Criteria:**
- Buttons render correctly
- Dialog shows generated prompt
- Copy-to-clipboard works
- Error states handled gracefully

### Phase 3: Prompt Generation Logic (2-3 hours)
**Owner:** TDD Implementor

1. Build client-specific prompts
   - Claude: MCP + Commands + Agents installation
   - Codex: MCP (with proxy) + Commands installation
   - Gemini: MCP + Commands installation

2. Test prompt execution manually
   - Run each generated prompt in respective CLI
   - Verify all files installed correctly
   - Verify MCP connection works
   - Verify slash commands available

**Testing Criteria:**
- Each prompt executes successfully
- Files land in correct locations
- MCP tools accessible
- Slash commands work

### Phase 4: Documentation & Polish (1-2 hours)
**Owner:** Documentation Manager

1. Update user guides
   - Add "Quick Setup" section to installation docs
   - Update ProductIntroTour documentation

2. Create troubleshooting guide
   - Common issues per client
   - Manual fallback instructions

3. Update CLAUDE.md
   - Document new quick setup feature
   - Link to relevant docs

**Success Criteria:**
- Documentation complete
- User guides updated
- Troubleshooting covered

---

## Testing Requirements

### Unit Tests

**Backend:**
- `test_template_converter.py` (12 tests)
  - Test Claude→Codex conversion
  - Test Claude→Gemini conversion
  - Test argument placeholder replacement
  - Test TOML structure generation
  - Test roundtrip semantic preservation

- `test_slash_command_templates.py` (8 tests)
  - Test `get_commands_for_client('claude')`
  - Test `get_commands_for_client('codex')`
  - Test `get_commands_for_client('gemini')`
  - Test command count (15 each)
  - Test filename extensions (.md, .toml)

**Frontend:**
- `ProductIntroTour.spec.js` (6 tests)
  - Test button rendering
  - Test dialog display
  - Test clipboard copy
  - Test API error handling

### Integration Tests

**Backend:**
- `test_quick_setup_endpoints.py` (8 tests)
  - Test POST `/api/setup/generate-prompt` for each client
  - Test token generation and validation
  - Test ZIP download endpoint
  - Test token expiry (15 minutes)
  - Test invalid client parameter
  - Test missing auth header

**End-to-End:**
- Manual testing in each CLI tool:
  1. Complete ProductIntroTour
  2. Click client button
  3. Copy prompt
  4. Paste into CLI
  5. Verify setup completes successfully

### Manual Testing

**For each client (Claude, Codex, Gemini):**

1. Fresh install test:
   - Clean `~/.claude/`, `~/.codex/`, or `~/.gemini/` directories
   - Run quick setup
   - Verify all files installed
   - Test MCP connection: `claude mcp list` (or equivalent)
   - Test slash command: `/gil_activate product_id=123`

2. Upgrade test:
   - Existing installation with old commands
   - Run quick setup
   - Verify files replaced/updated
   - Test no duplicate commands

3. Error scenarios:
   - Network timeout during ZIP download
   - Invalid API key
   - Server not running
   - Verify error messages helpful

---

## Dependencies and Blockers

### Dependencies
- ✅ ProductIntroTour component exists
- ✅ `slash_command_templates.py` exists (needs extension)
- ✅ API key generation system exists
- ✅ Config.yaml server URL accessible

### Potential Blockers
- **Codex proxy requirement:** Users need WHL proxy module installed
  - **Solution:** Document in prompt, provide download link
- **Token cleanup:** Need scheduled job to clean expired tokens
  - **Solution:** Add cleanup to existing maintenance job
- **File permissions:** CLI tools may have different permission requirements
  - **Solution:** Test on Windows/Mac/Linux before release

---

## Success Criteria

### Feature Works As Specified
1. User completes ProductIntroTour
2. User sees 3 client buttons (Claude, Codex, Gemini)
3. User clicks button → prompt copied to clipboard
4. User pastes prompt into CLI → all setup steps execute automatically
5. User restarts CLI → MCP connected, slash commands available
6. For Claude Code: Agent templates also installed

### All Tests Pass
- Unit tests: >85% coverage
- Integration tests: All 8+ tests pass
- Manual tests: All 3 clients verified

### Code Quality
- Chef's kiss production-grade code
- No commented-out code
- Clean refactoring
- Type hints and docstrings

### Documentation Complete
- User guides updated
- API documentation added
- Troubleshooting guide created
- CLAUDE.md updated

---

## Rollback Plan

### If Things Go Wrong

**Backend Issues:**
1. Remove quick_setup router from `api/app.py`
2. Revert endpoint files
3. Users fall back to manual setup (existing flow)

**Frontend Issues:**
1. Remove quick setup buttons from ProductIntroTour
2. Hide slide 8
3. Users still see tour, just no quick setup

**File Conflicts:**
1. Quick setup checks for existing files before overwriting
2. Backup existing files to `~/.claude/backup/` (etc.)
3. User can restore manually if needed

**Database:**
- No database changes required (API keys use existing system)

---

## Additional Resources

### Related Documentation
- [Installation Flow](F:\GiljoAI_MCP\docs\INSTALLATION_FLOW_PROCESS.md)
- [MCP Tools Manual](F:\GiljoAI_MCP\docs\manuals\MCP_TOOLS_MANUAL.md)
- [Thin Client Architecture](F:\GiljoAI_MCP\docs\guides\thin_client_migration_guide.md)

### External Resources
- [Claude MCP Documentation](https://docs.anthropic.com/claude/docs/mcp)
- [Codex CLI Documentation](https://codex-cli.readthedocs.io/)
- [Gemini CLI Documentation](https://ai.google.dev/gemini-api/docs/cli)

### Similar Implementations
- VS Code extension one-click setup
- JetBrains plugin configuration wizard
- Docker Desktop QuickStart

---

## Out of Scope

The following are explicitly **NOT** part of this handover:

- Automatic terminal injection (CLI tools execute commands automatically)
- Electron app integration (desktop app with native setup)
- SaaS hosted version differences (multi-tenant setup considerations)
- Automated updates for slash commands (future enhancement)
- Command version compatibility checking (future enhancement)

---

## Notes for Implementation Agent

1. **Start with Phase 1** - Backend must be solid before frontend work
2. **Use TDD** - Write tests first, especially for template conversion
3. **Test manually in all 3 CLIs** - Don't assume conversion logic works without verification
4. **Document client differences clearly** - Users will ask "Why doesn't Codex get agents?"
5. **Keep prompts concise** - Aim for <500 lines per client prompt
6. **Handle errors gracefully** - Network issues, permission errors, etc.

---

## Progress Updates

### [Date] - [Agent/Session]
**Status:** Not Started

**Next Steps:**
- Kick off Phase 1 with TDD Implementor
- Review template conversion logic
- Begin unit test development
