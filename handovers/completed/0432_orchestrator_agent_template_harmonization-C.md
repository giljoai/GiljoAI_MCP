# Handover: 0432 Orchestrator & Agent Template Harmonization

**Date:** 2025-01-22
**Status:** Completed
**Priority:** High

---

## Summary

Harmonized orchestrator and agent templates to fix incorrect BLOCKED protocol documentation, remove inappropriate sections from orchestrator, and ensure consistency across all template generation paths.

---

## What Was Built

### BLOCKED Protocol Fix
- Fixed incorrect `report_progress()` → correct `report_error()` for marking BLOCKED
- Added `acknowledge_job()` as the resume mechanism
- Fixed status terminology: `waiting`/`working`/`complete` (not `pending`/`active`/`completed`)

### Orchestrator Template Cleanup
- Removed "REQUESTING BROADER CONTEXT" (orchestrator doesn't ask itself)
- Added "Before Closeout" verification section
- Added "If Requirements Are Unclear" with correct BLOCKED protocol

### Agent Template Additions
- Added "Agent Guidelines" section for regular agents
- Added "If Blocked or Unclear" section with correct protocol
- Regular agents keep "REQUESTING BROADER CONTEXT" (they ask orchestrator)

### Code Path Consistency
- Fixed `template_seeder.py` - both `seed_tenant_templates()` and `refresh_tenant_template_instructions()`
- Fixed `SystemPromptService._build_default_orchestrator_prompt()` - "Restore default" button

---

## Key Files Modified

| File | Changes |
|------|---------|
| `src/giljo_mcp/template_seeder.py` | Orchestrator/agent separation, BLOCKED protocol |
| `src/giljo_mcp/services/orchestration_service.py` | Enhanced Phase 5 in full_protocol |
| `src/giljo_mcp/tools/orchestration.py` | Fixed status transition diagram |
| `src/giljo_mcp/system_prompts/service.py` | Fixed restore default code path |
| `handovers/Agent instructions and where they live.md` | Updated documentation |

---

## Commits

```
ee8c5619 fix: Remove context_request from SystemPromptService default orchestrator
c27cb420 docs: Update agent instructions doc with Handover 0432 changes
5061ec76 feat: Add closeout framing section to orchestrator template
c16c4c1b fix: Remove context_request section from orchestrator template
23fda64e fix: Correct BLOCKED status protocol - use report_error() not report_progress()
```

---

## Status Transitions (Reference)

```
waiting ─[acknowledge_job()]─→ working
working ─[report_progress()]─→ working (no status change)
working ─[complete_job()]─→ complete
working ─[report_error()]─→ blocked
blocked ─[acknowledge_job()]─→ working (resume)
```

---

## Testing

- Verified via UI: Admin Settings → System Prompt → "Restore default"
- Confirmed orchestrator prompt no longer contains "REQUESTING BROADER CONTEXT"
- Backend restart + cache clear applied successfully

---

## Pending (Out of Scope)

- Detailed closeout verification protocol in `full_protocol` (framing added, detail deferred)
- Team/dependency sections in mission text (0353)
- `get_team_agents()` enhancement to return message counts

---

**Status:** ✅ Production ready. All changes committed and verified.
