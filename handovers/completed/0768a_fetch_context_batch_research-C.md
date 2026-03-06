# Handover 0768a: Research — fetch_context() Single-Category-Per-Call Limitation

**Date:** 2026-03-04
**From Agent:** Orchestrator (master coordinator)
**To Agent:** Research agent (deep-researcher)
**Priority:** P2 (Medium)
**Estimated Complexity:** 1 hour
**Status:** Not Started
**Chain:** 0768a (Research) -> 0768b (Fix)

---

## Task Summary

`fetch_context()` forces agents to make 5 sequential MCP calls (one per category) instead of 1 batch call. The MCP schema already defines `categories` as an array — but agents in practice only send one category at a time. Your job is to determine if this is a backend limitation, a protocol instruction issue, or an intentional design constraint.

---

## The Issue (RT-1 / Enhancement #36)

- **What**: Every orchestrator makes 5 sequential `fetch_context()` calls during startup
- **Pattern observed**: `fetch_context(categories=['vision_documents'])`, then `fetch_context(categories=['tech_stack'])`, then `fetch_context(categories=['architecture'])`, etc.
- **Expected**: `fetch_context(categories=['vision_documents','tech_stack','architecture','memory','project'])` in one call
- **Impact**: 5 MCP round-trips instead of 1. Wastes ~21 tool calls when combined with monitoring loops. Every orchestrator hits this.
- **Question**: Is this a backend limitation (can't process multiple categories), a protocol instruction issue (agents told to call one at a time), or intentional (token budget per category)?

---

## CRITICAL: Trace the Full Runtime Flow

```
Agent calls MCP tool "fetch_context" with categories=['cat1','cat2','cat3']
  -> mcp_http.py receives HTTP POST, validates params
  -> tool_map dispatches to tool_accessor.fetch_context()
  -> tool_accessor calls fetch_context function
  -> function iterates/processes categories
  -> DOES IT ACTUALLY HANDLE MULTIPLE? Or just takes categories[0]?
  -> Response assembled and returned
```

**Key question**: The MCP schema defines categories as `{"type": "array", "items": {"type": "string"}}`. But does the implementation actually iterate over the array, or does it only process one element?

---

## Files to Investigate

### Primary (READ THESE BODIES)

| File | Symbol | Lines | What to Look For |
|------|--------|-------|------------------|
| `src/giljo_mcp/tools/context_tools/fetch_context.py` | `fetch_context` | 73-249 | THE MAIN IMPLEMENTATION. Does it loop over categories? How does it build the response? |
| `src/giljo_mcp/tools/context.py` | `fetch_context` | 173-251 | Is this a DIFFERENT implementation or dead code? Which one gets called? |
| `src/giljo_mcp/tools/tool_accessor.py` | `ToolAccessor.fetch_context` | 594-637 | Pass-through — which fetch_context does it call? |
| `api/endpoints/mcp_http.py` | fetch_context schema | ~669-700 | Schema definition — what does the description say about categories? |

### Secondary (CHECK FOR DESIGN CONSTRAINTS)

| File | What to Look For |
|------|------------------|
| `src/giljo_mcp/thin_prompt_generator.py` | How agents are TOLD to call fetch_context — one category at a time or batch? |
| `src/giljo_mcp/services/protocol_builder.py` | Same — agent startup protocol instructions |
| `src/giljo_mcp/tools/context_tools/` directory | Are there per-category handler files? What's the module structure? |
| Any token budget or size limit logic | Is there a per-call token cap that makes batching impractical? |

---

## Research Tasks (Execute in Order)

### Task 1: Determine Which fetch_context Gets Called
1. Read `ToolAccessor.fetch_context()` (tool_accessor.py:594-637) — which module does it import from?
2. Check: is `context.py:fetch_context` or `context_tools/fetch_context.py:fetch_context` the active implementation?
3. Is the other one dead code?

### Task 2: Read the Active Implementation
1. Read the full body of the active `fetch_context()` function
2. Answer: does it iterate over the `categories` array?
3. If yes — does it combine results into one response?
4. If no — does it only process `categories[0]`?
5. Check for any early returns or single-category assumptions

### Task 3: Check Response Structure
1. What does the response look like for a single category?
2. What would the response look like for multiple categories?
3. Is the response keyed by category name? Flat? Concatenated?
4. Is there a token budget or response size limit per call?

### Task 4: Check Agent Instructions
1. Read `thin_prompt_generator.py` — search for `fetch_context`
2. Read `protocol_builder.py` — search for `fetch_context`
3. Are agents explicitly told to call one category at a time?
4. Or are they told to batch but don't because the LLM breaks it into sequential calls?

### Task 5: Analyze Design Trade-offs
1. If batch already works — this is just a protocol instruction fix (tell agents to batch)
2. If batch doesn't work — is there a technical reason? (token limits, response structure)
3. Would batching 5 categories in one call exceed reasonable response sizes?
4. Are there category dependencies? (e.g., `project` category needs `product_id` from `tech_stack`?)

### Task 6: Propose Fix
If this IS a limitation:
- **Approach A**: Fix the backend to properly handle multiple categories
- **Approach B**: Fix only the agent instructions to batch calls
- **Approach C**: Both (backend + instructions)

If this is BY DESIGN:
- Document WHY and close the chain

---

## Chain Log Instructions

### Step 1: Mark Session Started
Read and update `F:\GiljoAI_MCP\prompts\0768_chain\chain_log.json`:
- Set `0768a.status` to `"in_progress"`
- Set `0768a.started_at` to current ISO timestamp

### Step 2: Execute Research Tasks (above)

### Step 3: Write Findings to Chain Log
Update `0768a` in chain_log.json with:
```json
{
  "findings": {
    "batch_supported": true/false,
    "active_implementation": "file:function that actually gets called",
    "dead_code_path": "file:function that is NOT called (if any)",
    "categories_handling": "description of how categories array is processed",
    "response_structure": "description of response format",
    "agent_instructions_say": "what agents are told about calling fetch_context",
    "is_by_design": true/false,
    "design_reason": "why single-category if by design",
    "token_budget_constraint": true/false,
    "proposed_fixes": [
      {
        "name": "Approach A",
        "type": "backend/protocol/both",
        "description": "...",
        "files_to_change": ["..."],
        "backward_compatible": true/false,
        "estimated_loc": 0,
        "recommended": true/false,
        "rationale": "..."
      }
    ]
  }
}
```

Also update: `tasks_completed`, `files_investigated`, `deviations`, `notes_for_next`, `summary`, `status: "complete"`, `completed_at`

---

## Success Criteria

- [ ] Determined which fetch_context implementation is active (context.py vs context_tools/)
- [ ] Confirmed whether batch categories actually works in the backend
- [ ] Agent instruction audit — what do prompts tell agents to do?
- [ ] Design trade-off analysis (token limits, response size, dependencies)
- [ ] At least 2 fix approaches proposed (or documented as by-design)
- [ ] Findings written to chain_log.json

## DO NOT
- Do NOT implement any fixes — research only
- Do NOT modify any source code files
- Do NOT create commits
- Do NOT spawn the next terminal

## Reference Files
- Chain Log: `F:\GiljoAI_MCP\prompts\0768_chain\chain_log.json`
- Handover Instructions: `F:\GiljoAI_MCP\handovers\handover_instructions.md`
- Feb Report Section 6: `F:\GiljoAI_MCP\handovers\Handover_report_feb.md`
