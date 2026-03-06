# Handover 0802b: Implement — 360 Memory "Unknown" Title Fix (RT-5)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Implementation agent
**Priority:** P2
**Estimated Complexity:** 20 minutes
**Status:** Not Started
**Chain:** 0802a (Research COMPLETE) -> 0802b (Implementation)

---

## MANDATORY: Read Before Coding

1. Read coding protocols: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
2. Read 0802a findings: `F:\GiljoAI_MCP\prompts\0802_chain\chain_log.json`

---

## Task Summary

Frontend bug: `CloseoutModal.vue` reads `entry.type` but the API returns `entry_type`. Result: `formatEntryType(undefined)` returns "Unknown". Also, `project_name` is available in the API response but never displayed in the entry panel title.

This is a pure frontend fix — 3 changes in 1 file.

---

## Root Cause

The `ProductMemoryEntry` model's `to_dict()` returns key `type`, but the API transforms it to `entry_type` via the `MemoryEntryResponse` Pydantic model. The Vue component uses `entry.type` which is `undefined` in the API response.

---

## The Fixes

### File: `frontend/src/components/orchestration/CloseoutModal.vue`

**Fix 1: Panel title (line ~87)**

Find:
```
Entry #{{ entry.sequence }} - {{ formatEntryType(entry.type) }}
```

Replace with:
```
{{ entry.project_name || 'Entry #' + entry.sequence }} - {{ formatEntryType(entry.entry_type) }}
```

**Fix 2: Metadata Type display (line ~165)**

Find:
```
{{ entry.type }}
```

Replace with (the reference to `entry.type` in the metadata section):
```
{{ formatEntryType(entry.entry_type) }}
```

**Fix 3: Any other `entry.type` references**

Search the entire file for `entry.type` and replace all occurrences with `entry.entry_type`. The research found references at lines 87 and 163-170.

---

## Implementation Steps

1. Read `F:\GiljoAI_MCP\handovers\handover_instructions.md` — coding protocols
2. Read `frontend/src/components/orchestration/CloseoutModal.vue` — find all `entry.type` references
3. Apply the fixes (change `entry.type` to `entry.entry_type`, add `project_name` to title)
4. Optionally improve the metadata section layout (consolidate Type + Sequence into cleaner format)
5. Update chain_log.json: `F:\GiljoAI_MCP\prompts\0802_chain\chain_log.json`
6. Commit: `fix(0802b): Fix 360 Memory "Unknown" title — field name mismatch entry.type vs entry_type (RT-5)`

## Testing

No automated tests for this Vue component. Verify by reading the updated template.

## DO NOT
- Do NOT change backend code
- Do NOT change the API response format
- Do NOT change the Pydantic model
- Do NOT create new files

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0802_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
