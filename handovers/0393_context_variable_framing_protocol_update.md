# Handover: Context Variable Framing Protocol Update

**Date:** 2026-01-25
**From Agent:** Claude Opus 4.5 (Main Session)
**To Agent:** TDD Implementor / Self
**Priority:** Medium
**Estimated Complexity:** 2-3 hours (E1)
**Status:** Ready for Implementation

---

## Task Summary

Update orchestrator and agent protocol instructions to explicitly guide them to use `project_path` and other context variables from `fetch_context()` responses, rather than hardcoding paths observed in their terminal session.

**Why:** During alpha testing, orchestrators wrote missions with hardcoded paths like `F:\TinyContacts\agent_reports\` because the protocol didn't explicitly instruct them to use context-provided values. This is fragile for a commercial hosted product.

**Solution:** Add framing/verbiage to existing protocol templates (B+ approach - industry-standard context injection pattern).

---

## Background

### MCP Enhancement List Item #15
**Original Issue:** Dynamic Path Variables - Hardcoded paths in missions are fragile.

**Root Cause Analysis:**
- `Product.project_path` IS available via `fetch_context(categories=["product_core"])`
- Orchestrators/agents weren't explicitly told to USE it
- They inferred paths from their terminal environment instead

**Resolution Approach:** Protocol documentation fix, not template substitution engine.
- This aligns with industry standards (Claude Code, Cursor, Copilot all use context injection)
- Leverages agent intelligence rather than fighting it
- Minimal code changes, maximum clarity

---

## Technical Details

### Files to Modify

1. **`src/giljo_mcp/tools/orchestration.py`**
   - Location: `_build_orchestrator_protocol()` or protocol chapter builders
   - Change: Add context variable guidance to CH2: STARTUP SEQUENCE

2. **`src/giljo_mcp/services/orchestration_service.py`**
   - Location: `_build_agent_full_protocol()` method
   - Change: Add context variable guidance to Phase 1: INITIALIZATION

### Protocol Text Changes

#### CH2: STARTUP SEQUENCE (Orchestrator)

Add as new guidance section:

```markdown
## CONTEXT VARIABLES
Your `fetch_context()` responses contain authoritative values:
- `project_path`: The project directory (use this, never hardcode terminal paths)
- `product_name`: The product name
- `tenant_key`: Your tenant isolation key

When writing missions or referencing directories, ALWAYS use values from context.
Never infer or hardcode paths from your current terminal session.
```

#### Phase 1: INITIALIZATION (Agent)

Add to Phase 1 guidance:

```markdown
## CONTEXT AWARENESS
Your mission and context contain authoritative values including `project_path`.
When creating files or referencing directories, use context-provided paths.
Do not hardcode paths observed in your terminal environment.
```

---

## Implementation Plan

### Phase 1: Locate Protocol Builders (15 min)
1. Find orchestrator protocol builder in orchestration.py
2. Find agent protocol builder in orchestration_service.py
3. Review current CH2 and Phase 1 text

### Phase 2: Update Orchestrator Protocol (30 min)
1. Add CONTEXT VARIABLES section to CH2
2. Keep text concise (~50 words)

### Phase 3: Update Agent Protocol (30 min)
1. Add CONTEXT AWARENESS note to Phase 1
2. Keep text concise (~30 words)

### Phase 4: Testing (45 min)
1. Run existing protocol tests
2. Verify token count hasn't increased significantly

### Phase 5: Update Enhancement List (15 min)
1. Mark #15 as RESOLVED in MCP_ENHANCEMENT_LIST.md

---

## Success Criteria

- [ ] Orchestrator protocol CH2 includes CONTEXT VARIABLES guidance
- [ ] Agent protocol Phase 1 includes CONTEXT AWARENESS note
- [ ] All existing tests pass
- [ ] Token increase < 100 tokens
- [ ] MCP Enhancement List #15 marked RESOLVED

---

## Implementation Summary

**Status**: COMPLETE (2026-01-25)
**Effort**: E1 (~30 minutes actual)

### Changes Made

1. **Orchestrator Protocol (CH2: STARTUP SEQUENCE)**
   - File: `src/giljo_mcp/tools/orchestration.py`
   - Added: CONTEXT VARIABLES warning after Step 2 (Fetch Context)
   - Instructs orchestrators to use `project_path` from context, never hardcode terminal paths

2. **Agent Protocol (Phase 1: INITIALIZATION)**
   - File: `src/giljo_mcp/services/orchestration_service.py`
   - Added: CONTEXT AWARENESS note after environment detection
   - Instructs agents to use context-provided paths

3. **MCP Enhancement List**
   - File: `F:\TinyContacts\MCP_ENHANCEMENT_LIST.md`
   - Marked #15 as RESOLVED with full rationale

### Verification
- Both files import successfully
- Protocol text appears in correct locations
- Token increase: ~60 tokens (well under 100 token budget)

### Key Decision: B+ Approach (Industry Standard)
Chose protocol framing over template substitution engine because:
- `project_path` already available via `fetch_context()`
- Leverages agent intelligence (how Claude Code, Cursor work)
- Less code, more flexibility
- Works for commercial hosted product

