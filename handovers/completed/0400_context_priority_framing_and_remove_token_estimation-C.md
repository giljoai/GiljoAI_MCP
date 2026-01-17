# Handover 0400: Context Priority/Framing System & Remove Token Estimation

**Status:** ARCHIVED
**Archived:** 2026-01-17

---

## Completion Summary

**What Was Done:**
1. Documented how the context priority/framing system works (this handover serves as documentation)
2. `estimated_tokens` removed from `context_fetch_instructions` - the `_build_fetch_instructions()` method in `mission_planner.py` builds instructions WITHOUT this field

**Verification:**
- `MissionPlanner._build_fetch_instructions()` (lines 1515-1667) returns instructions with: `field`, `tool`, `params`, `framing`, `supports_pagination`
- NO `estimated_tokens` in fetch instructions

**Remaining `estimated_tokens` Usage (Appropriate):**
- Internal logging/debugging
- `fetch_context()` responses (actual content size)
- Chunking calculations

**Final Status:** Complete. Priority/framing guides agent behavior; token estimates removed from fetch pointers.

---

## Original Summary

This document describes how the context priority and framing system works, based on live testing with Claude Code orchestrator. It also specifies removing the `estimated_tokens` field as unnecessary.

## Tool Used for Context Fetching

The orchestrator fetches context using:

```
mcp__giljo-mcp__get_orchestrator_instructions(job_id, tenant_key)
```

Returns:
- `identity` - job/agent/project IDs
- `project_description_inline` - always-on project description
- `context_fetch_instructions` - prioritized categories with fetch params
- `agent_templates` - available agents for spawning
- `field_priorities` - numeric priority map

## Priority Levels

| UI Label | Priority Number | Framing Text | Agent Behavior |
|----------|-----------------|--------------|----------------|
| CRITICAL | 1 | "REQUIRED: ..." | Fetch first, cannot skip |
| IMPORTANT | 2 | "RECOMMENDED: ..." | Strongly fetch, skip only if token-starved |
| REFERENCE | 3 | "OPTIONAL: ..." | Optional, fetch if budget allows |

## Why Token Estimation Was Removed

1. **Maintenance burden** - Estimates become stale as content changes
2. **Priority/framing already guides agent behavior** - Numeric priority + framing text is sufficient
3. **False precision** - Static estimates don't reflect actual content size
4. **Actual usage tracked elsewhere** - `context_budget` and `context_used` provide real tracking

## References

- Handover 0350b - Framing-based context architecture
- Handover 0351 - fetch_context() one-category-per-call enforcement
