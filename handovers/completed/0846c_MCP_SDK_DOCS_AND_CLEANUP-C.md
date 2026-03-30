# Handover 0846c: Documentation, Frontend & Test Updates

**Date:** 2026-03-29
**From Agent:** Codex session (orchestrator)
**To Agent:** Next Session
**Priority:** High
**Estimated Complexity:** 1-1.5 hours
**Status:** Not Started
**Edition Scope:** CE

---

## Pre-Work Reading (MANDATORY)

1. `handovers/HANDOVER_INSTRUCTIONS.md` — golden rules, documentation standards
2. `handovers/0846_MCP_SDK_STANDARDIZATION.md` — series coordinator
3. `CLAUDE.md` — project conventions
4. **Chain log `notes_for_next` from 0846a AND 0846b** — what changed, what was deleted

---

## Task Summary

Update all documentation, frontend config commands, and test files to reflect the SDK-based MCP transport. Remove references to deleted constructs (JSONRPCRequest, handle_tools_list, etc.). Sweep for orphaned imports and zombie references. Update CLAUDE.md if needed.

---

## Documentation Files to Update

### 1. Primary API Guide
**File:** `docs/api/MCP_OVER_HTTP_INTEGRATION.md`
- Replace JSON-RPC 2.0 request/response format examples with SDK-based Streamable HTTP
- Update session management section (SDK handles `Mcp-Session-Id`, our middleware handles auth sessions)
- Remove manual `initialize`/`tools/list`/`tools/call` examples — SDK handles this
- Keep download token system docs (unchanged)

### 2. Protocol Quick Reference
**File:** `docs/guides/mcp_protocol_quick_reference.md`
- Update to reflect Streamable HTTP transport
- Remove custom JSON-RPC specifics
- Add note about SDK compliance

### 3. Architecture Overview
**File:** `docs/SERVER_ARCHITECTURE_TECH_STACK.md`
- Update MCP section to reference FastMCP SDK instead of custom implementation
- Keep network topology (127.0.0.1 local, HTTPS LAN/WAN) unchanged

### 4. Agent Flow Summary
**File:** `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md`
- Line 33 says "MCP JSON-RPC 2.0" — update to "MCP Streamable HTTP (SDK)"
- Architecture diagram stays accurate (agents still communicate via MCP protocol to server)

### 5. CLAUDE.md (if needed)
**File:** `CLAUDE.md`
- Check if any MCP transport specifics are mentioned that need updating
- The tech stack section mentions "Real-time: WebSocket via PostgresNotifyBroker" — MCP transport isn't mentioned there, probably no change needed

---

## Frontend Files to Update

### 6. AI Tool Config Wizard
**File:** `frontend/src/components/AiToolConfigWizard.vue`

Check and update MCP add commands for all three platforms:
- **Claude Code:** `claude mcp add --transport http giljo-mcp ${serverUrl}/mcp --header "Authorization: Bearer ${apiKey}"`
  - May need `--transport streamable-http` if SDK uses different transport identifier
  - **Verify:** Does Claude Code CLI recognize `streamable-http` as a transport type, or is `http` still correct?
- **Codex CLI:** `codex mcp add giljo-mcp --url ${serverUrl}/mcp --bearer-token-env-var GILJO_API_KEY`
  - URL unchanged (`/mcp`), auth unchanged
- **Gemini CLI:** `gemini mcp add -t http -H "Authorization: Bearer ${apiKey}" giljo-mcp ${serverUrl}/mcp`
  - Same question about transport type

**Critical:** Test the actual commands before committing. If transport type keywords haven't changed, don't change them.

### 7. MCP Integration Page
**File:** `frontend/src/views/McpIntegration.vue`
- Check for references to JSON-RPC or custom endpoint details
- Update if any user-facing text describes the transport mechanism

### 8. Quick Start / Integration Cards
- `frontend/src/components/settings/integrations/McpIntegrationCard.vue`
- `frontend/src/components/settings/StartupQuickStart.vue`
- Check for hardcoded endpoint details

---

## Test Files to Update

### 9. Manual Test Scripts
- `tests/manual/test_mcp_http_manual.sh` — rewrite to use Streamable HTTP transport (or delete if SDK transport tests cover it)
- `tests/manual/test_mcp_http_manual.ps1` — same

### 10. Test Reports (Historical — Mark as Superseded)
- `tests/TEST_REPORT_MCP_HTTP.md` — add header note: "Superseded by 0846 SDK migration"
- `tests/integration/MCP_HTTP_TOOL_CATALOG_TEST_REPORT.md` — same

### 11. Test Fixtures
- `tests/fixtures/orchestrator_simulator.py` — check if it references mcp_http patterns
- `tests/fixtures/mock_agent_simulator.py` — same

---

## Orphan & Zombie Sweep

After 0846b removed the old code, scan for:

1. **Dead imports:** `grep -r "mcp_http" --include="*.py"` — any remaining imports of deleted module
2. **Dead references:** `grep -r "JSONRPCRequest\|JSONRPCResponse\|JSONRPCError"` — any code referencing deleted models
3. **Dead function refs:** `grep -r "handle_initialize\|handle_tools_list\|handle_tools_call"` — any references to deleted handlers
4. **Dead schema refs:** `grep -r "_build_project_tools\|_build_message_tools\|_TOOL_SCHEMA_PARAMS"` — any references to deleted schema builders
5. **Stale test imports:** Check test files for imports from deleted modules
6. **Dev tools:** `dev_tools/simulator/` — check for stale MCP endpoint references

For each finding: delete the dead reference, fix the import, or update the code.

---

## Files to Modify

| File | Action | Notes |
|------|--------|-------|
| `docs/api/MCP_OVER_HTTP_INTEGRATION.md` | MODIFY | Update transport docs |
| `docs/guides/mcp_protocol_quick_reference.md` | MODIFY | Update protocol reference |
| `docs/SERVER_ARCHITECTURE_TECH_STACK.md` | MODIFY | Update MCP section |
| `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` | MODIFY | Update transport label |
| `frontend/src/components/AiToolConfigWizard.vue` | MODIFY (if needed) | Update CLI config commands |
| `tests/manual/test_mcp_http_manual.sh` | DELETE or REWRITE | Old transport test |
| `tests/manual/test_mcp_http_manual.ps1` | DELETE or REWRITE | Old transport test |
| `tests/TEST_REPORT_MCP_HTTP.md` | MODIFY | Add superseded note |
| Various (orphan sweep) | MODIFY | Fix dead imports/references |

---

## Key Constraints

- Do NOT modify completed handovers in `handovers/completed/` — they are historical records
- Do NOT change tool names, descriptions, or behavior — only transport/protocol documentation
- Keep documentation concise per handover instructions (max 1000 words for any doc update)
- Frontend config commands must be tested against actual CLI tools before committing

---

## Success Criteria

- [ ] `docs/api/MCP_OVER_HTTP_INTEGRATION.md` reflects SDK-based transport
- [ ] `docs/guides/mcp_protocol_quick_reference.md` updated
- [ ] `docs/SERVER_ARCHITECTURE_TECH_STACK.md` MCP section updated
- [ ] `handovers/Reference_docs/AGENT_FLOW_SUMMARY.md` transport label updated
- [ ] Frontend config wizard commands verified and updated if needed
- [ ] Zero grep hits for deleted constructs (JSONRPCRequest, handle_tools_list, etc.)
- [ ] Zero dead imports from deleted `mcp_http` module
- [ ] Manual test scripts updated or deleted
- [ ] `ruff check src/ api/` passes clean
- [ ] All existing tests pass

---

## Chain Execution Instructions

### Step 1: Read Chain Log
Read `prompts/0846_chain/chain_log.json`
- Check `orchestrator_directives` — if STOP, halt immediately
- **Review 0846a AND 0846b `notes_for_next`** — what was deleted, what needs updating
- Verify 0846b status is `complete`

### Step 2: Mark Session Started
Update your session: `"status": "in_progress", "started_at": "<timestamp>"`

### Step 3: Execute Handover Tasks
Follow the plan above. Start with the orphan sweep (it informs which docs need updating).

### Step 4: Update Chain Log
Update your session with:
- `tasks_completed`, `deviations`, `blockers_encountered`
- `notes_for_next`: null (this is the last session)
- `cascading_impacts`: List if any findings need follow-up handovers
- `summary`, `status`: "complete", `completed_at`

### Step 5: STOP
This is the final session in the chain. Mark `final_status: "complete"` in the chain log. Commit and exit.
