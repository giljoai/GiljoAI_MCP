# Handover 0069: Native MCP Configuration for Codex & Gemini CLI

**Date**: 2025-10-28
**Status**: Planned
**Priority**: High
**Related**: Handover 0068 (Research Validation), Handover 0060 (MCP Tool Exposure)

---

## Executive Summary

Enable native MCP configuration for Codex CLI and Gemini CLI by marking them as fully supported and removing "Coming Soon" placeholders. Uses existing command-line copy-paste approach (safe, preserves other MCP servers like Serena).

**Current State**: Codex/Gemini marked as `supported=False`, UI shows "Coming Soon"
**Target State**: Full support with one-click copy commands in My Settings → MCP Configuration
**Estimated Time**: 30 minutes - 1 hour

---

## Problem Statement

### Current Issues

1. **Backend Registry**:
```python
# api/endpoints/ai_tools.py
AIToolInfo(
    id="codex",
    supported=False,  # ❌ Incorrect
    config_format="command"
),
AIToolInfo(
    id="gemini",
    supported=False,  # ❌ Incorrect
    config_format="command"
)
```

2. **UI Shows Placeholders**:
   - `McpConfigComponent.vue` lines 307-324: "Coming Soon" messaging
   - Instructions say "check documentation for latest MCP support status"
   - Confuses users - makes them think features don't exist yet

3. **Admin Settings Confusion**:
   - Integrations tab has old "How to configure" text
   - Should redirect users to My Settings → MCP Configuration

### Why This Matters

- **Codex CLI** has native MCP support (2025) via `codex mcp add` command
- **Gemini CLI** has MCP support via extensions
- Users can connect NOW, but UI says it's "coming soon"
- Creates support burden ("when will this be available?")

---

## User Experience Flow

### Current Location: My Settings → MCP Configuration

**URL**: `http://10.1.0.164:7274/settings` (Tab: "MCP Configuration")

#### Section 1: AI Tool Self-Configuration ✅ (Already Works!)
Component: `AiToolConfigWizard.vue`

```
┌────────────────────────────────────────────┐
│ AI Tool Configuration                       │
├────────────────────────────────────────────┤
│ Auto-detected settings:                     │
│   • AI Tool: Claude Code                    │
│   • Server: http://10.1.0.164:7272/mcp    │
│                                             │
│ [Generate Configuration Prompt]            │
│                                             │
│ ┌─────────────────────────────────────┐   │
│ │ claude-code mcp add giljoai ...     │   │
│ │                          [📋 Copy]  │   │
│ └─────────────────────────────────────┘   │
└────────────────────────────────────────────┘
```

**Status**: ✅ This already works for all tools!

#### Section 2: Manual AI Tool Configuration ⚠️ (Needs Update)
Component: `McpConfigComponent.vue`

Opens dialog when user clicks "Need advanced options?"

```
Current (Lines 307-324):
❌ "Codex CLI MCP integration is coming soon"
❌ "The command syntax shown is a placeholder"
❌ "Check Codex CLI documentation for latest status"

Should Be:
✅ Shows real command: codex mcp add --transport http...
✅ Copy button works
✅ Instructions for running command
```

---

## Technical Implementation

### Changes Required

#### 1. Backend (5 minutes)

**File**: `api/endpoints/ai_tools.py`

```python
# BEFORE
AIToolInfo(
    id="codex",
    name="Codex CLI",
    supported=False,  # ❌
    config_format="command"
),
AIToolInfo(
    id="gemini",
    name="Gemini CLI",
    supported=False,  # ❌
    config_format="command"
)

# AFTER
AIToolInfo(
    id="codex",
    name="Codex CLI",
    supported=True,  # ✅
    config_format="command"
),
AIToolInfo(
    id="gemini",
    name="Gemini CLI",
    supported=True,  # ✅
    config_format="command"
)
```

#### 2. Frontend: McpConfigComponent.vue (15 minutes)

**File**: `frontend/src/components/McpConfigComponent.vue`

**Remove lines 307-324** (Codex "Coming Soon" placeholder):
```vue
<!-- DELETE THIS -->
} else if (selectedTool.value === 'codex') {
  configContent = generateCodexConfig(generatedApiKey.value, serverUrl)
  fileLocation = 'Command Line (Terminal/PowerShell) - Coming Soon'  // ❌
  downloadFilename = 'codex-setup.md'
  instructions.push(
    'Codex CLI MCP integration is coming soon',  // ❌
    'The command syntax shown is a placeholder',  // ❌
    ...
  )
}
```

**Replace with**:
```vue
} else if (selectedTool.value === 'codex') {
  configContent = generateCodexConfig(generatedApiKey.value, serverUrl)
  fileLocation = 'Command Line (Terminal/PowerShell)'  // ✅
  downloadFilename = 'codex-setup.md'
  instructions.push(
    'Open your terminal or command prompt',
    'Copy the command shown above',
    'Paste and run the command to configure Codex CLI',
    'Verify connection: codex mcp list',
    'Start using GiljoAI tools in Codex sessions'
  )
}
```

**Similarly update lines 315-324** (Gemini placeholder).

#### 3. Command Generation Verification (Already Done!)

**File**: `frontend/src/utils/configTemplates.js`

Verify commands generate correctly:

```javascript
// Codex Command
export function generateCodexConfig(apiKey, serverUrl) {
  return `codex mcp add --transport http giljoai ${serverUrl} --header "X-API-Key: ${apiKey}"`
}

// Gemini Command
export function generateGeminiConfig(apiKey, serverUrl) {
  return `gemini mcp add --transport http giljoai ${serverUrl} --header "X-API-Key: ${apiKey}"`
}
```

**Status**: ✅ Already correct!

#### 4. Admin Settings → Integrations Tab (10 minutes)

**Current Issue**: Shows old configuration instructions
**Solution**: Redirect users to My Settings

**File**: `frontend/src/views/AdminSettingsView.vue` (or wherever Integrations tab lives)

```vue
<!-- Integrations Tab -->
<v-window-item value="integrations">
  <v-alert type="info" prominent class="mb-4">
    <v-alert-title>Configure AI Tools</v-alert-title>
    <div class="mt-2">
      Users configure their AI coding tools (Claude Code, Codex, Gemini) in
      <router-link to="/settings" class="text-primary font-weight-bold">
        My Settings → MCP Configuration
      </router-link>
    </div>
  </v-alert>

  <!-- Keep other integration settings here -->
  <!-- (Serena, GitHub, Postgres MCP servers, etc.) -->
</v-window-item>
```

---

## Safety Design: Why Command-Line Approach

### The Overwrite Problem

**If we used downloadable TOML files**:
```toml
# User downloads this
[mcp_servers.giljoai]
url = "http://server:7272/mcp"
```

**User already has** `~/.codex/config.toml`:
```toml
[mcp_servers.serena]
command = "uvx serena"

[mcp_servers.postgres]
command = "uvx mcp-server-postgres"
```

**If user overwrites → ALL OTHER MCP SERVERS LOST!** 🔥

### Our Safe Approach: Append Commands

```bash
# User runs this command
codex mcp add --transport http giljoai http://server:7272/mcp --header "X-API-Key: abc123"
```

**Result**: Appends to config, doesn't overwrite!

```toml
# ~/.codex/config.toml (AFTER command)
[mcp_servers.serena]
command = "uvx serena"

[mcp_servers.postgres]
command = "uvx mcp-server-postgres"

[mcp_servers.giljoai]  # ✅ ADDED, not replaced
transport = "http"
url = "http://server:7272/mcp"
headers = {"X-API-Key": "abc123"}
```

**Benefits**:
- ✅ Safe (preserves existing configs)
- ✅ Idempotent (can run multiple times)
- ✅ User sees what's happening
- ✅ Consistent with Claude Code pattern

---

## Testing Checklist

### Backend Testing
- [ ] GET `/api/ai-tools/supported` returns Codex/Gemini with `supported=True`
- [ ] Both tools appear in UI dropdowns

### Frontend Testing - AI Tool Self-Configuration
- [ ] Select "Codex CLI" → generates command
- [ ] Click copy button → command copied to clipboard
- [ ] Command includes correct server URL and API key
- [ ] Repeat for "Gemini CLI"

### Frontend Testing - Manual Configuration
- [ ] Open "Manual AI Tool Configuration" dialog
- [ ] Select Codex → shows real command (not "Coming Soon")
- [ ] Instructions are actionable (no placeholder text)
- [ ] Copy button works
- [ ] Download markdown guide button works
- [ ] Repeat for Gemini

### Integration Testing
- [ ] Copy command from UI
- [ ] Run in actual terminal (if Codex/Gemini installed)
- [ ] Verify appears in `codex mcp list` / `gemini mcp list`
- [ ] Verify doesn't overwrite other MCP servers
- [ ] Launch tool and verify GiljoAI MCP tools appear

### Admin Settings Testing
- [ ] Navigate to Admin Settings → Integrations
- [ ] Verify message redirects to My Settings
- [ ] Click link → navigates to correct tab
- [ ] Other integrations (Serena, etc.) still work

---

## Acceptance Criteria

### Must Have
- [x] Codex marked as `supported=True` in backend
- [x] Gemini marked as `supported=True` in backend
- [x] "Coming Soon" messaging removed from UI
- [x] Real commands generate with user's API key
- [x] Copy button works for all tools
- [x] Commands are safe (append to config, don't overwrite)
- [x] Admin → Integrations redirects to user settings

### Nice to Have
- [ ] Add "Test Connection" button (pings MCP endpoint)
- [ ] Show connection status indicator
- [ ] Add troubleshooting tips in UI

---

## Implementation Notes

### Existing Functionality to Preserve

**DO NOT CHANGE**:
- `AiToolConfigWizard.vue` - Already works perfectly!
- Command generation functions in `configTemplates.js` - Already correct!
- Copy-to-clipboard logic - Already implemented!
- API key generation flow - Already secure!

**ONLY CHANGE**:
- Backend: `supported` flag
- Frontend: Remove "Coming Soon" placeholders
- Frontend: Update instructions to be actionable
- Admin Settings: Add redirect message

### Why This is Low-Risk

1. **No new code** - just enabling existing features
2. **Copy-paste commands already tested** with Claude Code
3. **Backend change is trivial** (boolean flag)
4. **Frontend changes are cosmetic** (text updates)
5. **No database migrations** required
6. **No installation flow changes** required

---

## Documentation Updates Needed

### User Facing
- [ ] Update README.md with Codex/Gemini support notice
- [ ] Add screenshot of MCP Configuration tab
- [ ] Document command syntax for all three tools

### Developer Facing
- [ ] Update `docs/MCP_INTEGRATION.md` (if exists)
- [ ] Note in CLAUDE.md that Codex/Gemini fully supported

---

## Rollback Plan

If issues discovered:

1. **Quick rollback** (5 seconds):
```python
# Set back to False in ai_tools.py
supported=False
```

2. **Revert frontend changes** (git revert)

3. **No database cleanup needed** (no schema changes)

4. **No user data affected** (configuration is client-side)

---

## Future Enhancements (Out of Scope)

### Tier 2: Connection Testing
- Add "Test Connection" button
- Pings `/api/mcp/health` with user's API key
- Shows success/failure toast notification

### Tier 3: Status Dashboard
- Show which tools are currently connected
- Display last connection time
- Show which MCP tools are available

### Tier 4: Automation Helpers
- Generate shell scripts for batch setup
- Create installer helpers for team setups
- Export configuration for CI/CD

**Note**: These are separate projects for later consideration.

---

## Related Work

### Handover 0068: Research Validation
- Validated Codex/Gemini have native MCP support
- Confirmed command-line approach is optimal
- Documented why wrappers/TOML downloads are unnecessary

### Handover 0060: MCP Tool Exposure
- Created HTTP MCP endpoint at `:7272/mcp`
- Implemented tool registration system
- Added multi-tenant isolation

---

## Success Metrics

### Quantitative
- Codex/Gemini show `supported=True` in API response
- Zero "Coming Soon" text in production UI
- Command generation works for 100% of tool selections

### Qualitative
- Users can connect Codex/Gemini without confusion
- Support tickets about "when will this be available?" drop to zero
- Documentation is clear and actionable

---

## Timeline

**Total Estimated Time**: 30 minutes - 1 hour

- Backend changes: 5 minutes
- Frontend updates: 20 minutes
- Testing: 30 minutes
- Documentation: 15 minutes

**Complexity**: Low (enabling existing features, not building new ones)

---

## Conclusion

This handover enables full Codex/Gemini support by simply flipping the `supported` flag and removing placeholder text. The underlying infrastructure (command generation, copy-paste, API keys) already works perfectly.

**Key Insight**: The work was already done in previous projects. This handover just exposes it to users.

**Safety**: Command-line append approach preserves user's existing MCP server configurations (Serena, Postgres, GitHub, etc.) - no risk of data loss.

**User Experience**: One-click copy → paste in terminal → done. Consistent with Claude Code pattern users already know.
