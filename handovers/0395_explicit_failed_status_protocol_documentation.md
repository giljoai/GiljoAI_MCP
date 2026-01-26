# Handover: Explicit FAILED Status Protocol Documentation

**Date:** 2026-01-25
**From Agent:** Claude Opus 4.5 (Main Session)
**To Agent:** Self
**Priority:** Medium
**Estimated Complexity:** 1 hour (E1)
**Status:** Ready for Implementation

---

## Task Summary

Update agent protocol Phase 5 (ERROR HANDLING) to document how agents can explicitly mark themselves as FAILED using the existing `set_agent_status()` tool.

**Why:** During alpha testing, agents didn't know how to explicitly fail a job. They used `report_error()` which only sets "blocked" status. The capability to set "failed" already exists via `set_agent_status()` but isn't documented in the protocol.

**Solution:** Documentation fix - add FAILED guidance to Phase 5 (same approach as Handover 0393).

---

## Background

### MCP Enhancement List Item #16
**Original Issue:** No Explicit `fail_job()` Tool - agents had to use workaround pattern.

**Research Findings (Deep Researcher Agent):**
- `report_error()` sets status to "blocked", NOT "failed"
- `set_agent_status(status="failed", reason="...")` already exists and works
- Design intent: BLOCKED = agent-initiated recoverable, FAILED = system-enforced
- But `set_agent_status()` provides explicit FAILED capability - just undocumented

**Resolution:** Option B - Document existing capability instead of adding new tool.

---

## Technical Details

### File to Modify

**`src/giljo_mcp/services/orchestration_service.py`**
- Location: `_generate_agent_protocol()` function
- Section: Phase 5: ERROR HANDLING & BLOCKED STATUS

### Protocol Text Changes

Add new section after BLOCKED guidance:

```markdown
**To mark yourself FAILED** (unrecoverable error, intentional failure):
1. Call `mcp__giljo-mcp__set_agent_status(
       agent_id="{executor_id}",
       tenant_key="{tenant_key}",
       status="failed",
       reason="<failure reason>"
   )`
2. This is a TERMINAL state - no further work expected
3. Do NOT call complete_job() after failing

**Use FAILED for**: Unrecoverable errors, intentional test failures, cannot proceed
**Use BLOCKED for**: Waiting for clarification, missing context, recoverable issues
```

---

## Implementation Plan

1. Read current Phase 5 text in `_generate_agent_protocol()`
2. Add FAILED guidance section
3. Update MCP Enhancement List #16 as RESOLVED
4. Test imports work
5. Commit and archive

---

## Success Criteria

- [ ] Phase 5 includes explicit FAILED status guidance
- [ ] `set_agent_status()` call syntax shown with correct parameters
- [ ] Clear distinction between FAILED vs BLOCKED documented
- [ ] MCP Enhancement List #16 marked RESOLVED
- [ ] All imports still work

---

## Implementation Summary

**Status**: COMPLETE (2026-01-25)
**Effort**: E1 (~20 minutes actual)

### Changes Made

1. **Agent Protocol (Phase 5: ERROR HANDLING)**
   - File: `src/giljo_mcp/services/orchestration_service.py`
   - Added: Explicit FAILED status guidance with `set_agent_status()` call syntax
   - Clarified: BLOCKED = recoverable, FAILED = terminal
   - Removed: Misleading "actual errors set blocked status" text

2. **MCP Enhancement List**
   - File: `F:\TinyContacts\MCP_ENHANCEMENT_LIST.md`
   - Marked #16 as RESOLVED with research findings and fix rationale

### Protocol Text Added

```markdown
**To mark yourself FAILED** (unrecoverable error, intentional failure):
1. Call `mcp__giljo-mcp__set_agent_status(
       agent_id="{executor_id}",
       tenant_key="{tenant_key}",
       status="failed",
       reason="<failure reason>"
   )`
2. This is a TERMINAL state - no further work expected
3. Do NOT call complete_job() after failing

**Use FAILED for**: Unrecoverable errors, intentional test failures, cannot proceed (terminal)
```

### Key Decision: Option B (Documentation)
Chose documentation over new tool because:
- `set_agent_status()` already provides the capability
- Adding `fail_job()` would duplicate functionality
- Same pattern as Handover 0393 (framing fix)

