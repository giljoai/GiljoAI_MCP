# Handover 0767b + 0768b: Combined Implementation — Serialization Safety + Schema Fix

**Date:** 2026-03-04
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Implementation agent (tdd-implementor)
**Priority:** High
**Estimated Complexity:** 30 minutes
**Status:** Not Started
**Chains:** 0767b (datetime defense-in-depth) + 0768b (fetch_context schema fix)

---

## Task Summary

Two small, targeted fixes from research chains 0767a and 0768a. Both are in the MCP HTTP handler area. Combined because they're tiny and independent.

### Fix 1: json.dumps Safety Net (0767b — 1 line)

Add `default=str` to the `json.dumps()` call in `handle_tools_call()`. This prevents ANY non-serializable type (datetime, UUID, Decimal) from crashing the MCP response. The specific `get_agent_mission()` datetime bug was already fixed by 0731c typed returns, but the systemic vulnerability remains.

### Fix 2: Misleading fetch_context MCP Schema (0768b — ~15 lines)

The MCP schema advertises `default=['all']` and includes `'all'` in the categories enum, but the backend rejects both with an error. Agents waste a failed call trying the default. Fix the schema to match reality and add a parallelism hint.

### Fix 3: Dead Code Removal (0768b cleanup)

`_flatten_results()` in `fetch_context.py` is dead code — never called because single-category enforcement makes it unreachable. Remove it.

---

## Fix 1: json.dumps Safety Net

### File: `api/endpoints/mcp_http.py`
### Location: Line ~988 (inside `handle_tools_call`)

**Current code:**
```python
result_text = json.dumps(serializable_result, indent=2, ensure_ascii=False)
```

**Change to:**
```python
result_text = json.dumps(serializable_result, indent=2, ensure_ascii=False, default=str)
```

That's it. One parameter added. This converts any non-JSON-native type to string via `str()` instead of crashing.

### Why this is safe:
- Types that `json.dumps` already handles (str, int, float, bool, None, list, dict) are unaffected — `default` is only called for types json can't serialize natively
- `datetime` objects become ISO-formatted strings via `str()` (Python's datetime.__str__ produces ISO format)
- `UUID` objects become their string representation
- This is the standard Python pattern for JSON serialization safety

---

## Fix 2: Misleading fetch_context MCP Schema

### File: `api/endpoints/mcp_http.py`
### Location: Lines ~681-700 (fetch_context inputSchema)

Find the `categories` property in the fetch_context schema. The current schema says:

```python
"categories": {
    "type": "array",
    "items": {
        "type": "string",
        "enum": [... includes "all" ...]
    },
    "default": ["all"],
    "description": "Categories to fetch. [\"all\"] for everything."
}
```

**Change to** (remove 'all' from enum, remove default, update description):

The enum should list only valid categories WITHOUT 'all'. Remove the `default` key entirely. Update the description to say exactly ONE category per call. Add a note that agents can make parallel calls.

### Also update the param whitelist

Check `_TOOL_SCHEMA_PARAMS` dict (~line 265) — the `fetch_context` entry should still include `categories` (it does).

---

## Fix 3: Dead Code Removal

### File: `src/giljo_mcp/tools/context_tools/fetch_context.py`
### Location: Lines 329-353 (approximately)

Remove the `_flatten_results()` function entirely. It was designed for `output_format='flat'` with multi-category responses, but single-category enforcement (Handover 0351) makes it unreachable. No callers exist.

**Verify before deleting:** Use Serena `find_referencing_symbols` or grep to confirm `_flatten_results` has zero callers.

---

## Fix 4 (Optional): Parallelism Hint in Framing Instructions

### File: `src/giljo_mcp/mission_planner.py`
### Symbol: `MissionPlanner._build_fetch_instructions`

If the framing instructions structure per-category fetch calls, consider adding a note like:
"TIP: These fetch_context calls are independent — you can make them in parallel as separate tool calls."

**Only do this if it fits naturally into the existing instruction format. Do not force it.**

---

## Implementation Steps

1. Read `api/endpoints/mcp_http.py` — find the json.dumps line (~988) and the fetch_context schema (~681-700)
2. Apply Fix 1 (add `default=str`) — 1 line change
3. Apply Fix 2 (fix misleading schema) — update enum, remove default, update description
4. Read `src/giljo_mcp/tools/context_tools/fetch_context.py` — find `_flatten_results`
5. Verify `_flatten_results` has zero callers
6. Apply Fix 3 (remove dead code)
7. Optionally apply Fix 4 (parallelism hint in mission_planner.py)
8. Run the test suite: `python -m pytest tests/ -x -q --timeout=30`
9. If tests pass, commit with message: `fix(0767b+0768b): Add json.dumps safety net, fix misleading fetch_context schema, remove dead code`

### Update BOTH chain logs after implementation:
- `F:\GiljoAI_MCP\prompts\0767_chain\chain_log.json` — update 0767b session
- `F:\GiljoAI_MCP\prompts\0768_chain\chain_log.json` — update 0768b session

---

## Testing

### For Fix 1 (json.dumps safety):
No new tests needed — this is a safety net that only activates on serialization failure. Existing tests cover the happy path. The defense-in-depth nature means it should never actually trigger with current code.

### For Fix 2 (schema fix):
No behavioral change — this is schema documentation. Verify by reading the updated schema.

### For Fix 3 (dead code):
Run `python -m pytest tests/ -x -q --timeout=30` to confirm nothing breaks.

---

## Success Criteria

- [ ] `json.dumps` in mcp_http.py has `default=str` parameter
- [ ] fetch_context MCP schema no longer advertises `'all'` or `default=['all']`
- [ ] fetch_context description clearly states one category per call
- [ ] `_flatten_results()` removed from fetch_context.py
- [ ] All tests pass
- [ ] Both chain_log.json files updated
- [ ] Changes committed

## DO NOT
- Do NOT change any backend logic in fetch_context — single-category is by design
- Do NOT add batch/multi-category support — this is intentionally restricted
- Do NOT refactor get_agent_mission — 0731c already fixed the datetime issue
- Do NOT create new files or modules

## Reference Files
- 0767 Chain Log: `F:\GiljoAI_MCP\prompts\0767_chain\chain_log.json`
- 0768 Chain Log: `F:\GiljoAI_MCP\prompts\0768_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
- Coding Protocols: `F:\GiljoAI_MCP\handovers\Reference_docs\QUICK_LAUNCH.txt`
