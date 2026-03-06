# Handover 0802a: Research — 360 Memory "Unknown" Title Bug (RT-5)

**Date:** 2026-03-05
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2
**Estimated Complexity:** 45 minutes
**Status:** Not Started
**Chain:** 0802a (Research) -> 0802b (Fix)

---

## Task Summary

RT-5: 360 Memory entries display "Unknown" as their title in the UI instead of the project name. Entry #27 specifically observed showing as "Unknown". Also the display format "Type: Sequence: #27" is confusing.

Trace the FULL data flow: `write_360_memory()` MCP tool call -> `ProductMemoryEntry` database table -> API endpoint response -> Vue frontend rendering.

---

## Research Tasks

### Task 1: Trace the Write Path
1. Read `src/giljo_mcp/tools/write_360_memory.py` — the `write_360_memory()` function
   - What fields does it save? Is there a `title` or `project_name` field?
   - Does it store the project name, or does it need to be JOINed later?
2. Read the `ProductMemoryEntry` model (likely in `src/giljo_mcp/models/` — search for it)
   - What columns exist? Is there a title/name column?
   - What are the defaults? Is "Unknown" a default anywhere?
3. Read `ProductMemoryRepository` — how are entries stored?

### Task 2: Trace the Read Path
1. Find the API endpoint that returns memory entries for the UI
   - Search for routes like `/api/products/*/memory` or `/api/memory`
   - Check `api/endpoints/` directory for memory-related endpoints
2. Read the endpoint handler — does it JOIN to projects table to get the project name?
3. Check: does the API response include a `title` or `project_name` field?
4. Check: if the project is deleted or the `project_id` is null, what does the API return?

### Task 3: Trace the Frontend Display
1. Search Vue frontend (likely `frontend/src/`) for components displaying memory entries
   - Search for "Unknown", "360 Memory", "product_memory", "memory_entries"
2. Read the component — how does it render the title?
3. Check: is "Unknown" a fallback in the Vue component (e.g., `entry.title || 'Unknown'`)?
4. Check: the "Type: Sequence: #27" display — where does this format come from?

### Task 4: Determine Root Cause
1. Is the project_name not saved at write time?
2. Is the API not JOINing to get the project name?
3. Is the frontend using a wrong field for the title?
4. Is this a data issue (specific entries missing project_id) or a code issue?

---

## Chain Log Instructions

Update `F:\GiljoAI_MCP\prompts\0802_chain\chain_log.json`:
- Set `0802a.status` to `"in_progress"` at start, `"complete"` when done
- Write findings with:
  - `root_cause`: where the "Unknown" comes from (backend/API/frontend)
  - `write_path`: what fields are stored
  - `read_path`: what fields are returned
  - `frontend_display`: how the component renders
  - `proposed_fix`: what to change and where

## Success Criteria
- [ ] Traced write path (write_360_memory -> DB)
- [ ] Traced read path (DB -> API -> response)
- [ ] Traced frontend display (Vue component rendering)
- [ ] Identified root cause of "Unknown" title
- [ ] Identified root cause of "Type: Sequence: #27" display
- [ ] Proposed fix with file locations
- [ ] Findings written to chain_log.json

## DO NOT
- Do NOT implement any fixes — research only
- Do NOT modify any source code files
- Do NOT create commits

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0802_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
