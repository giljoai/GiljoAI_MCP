# Handover 0389: Dynamic Agent Name Examples in cli_mode_rules

**Status:** COMPLETE (2026-01-04)
**Priority:** MEDIUM
**Commits:** c05ed337

## Problem

The `cli_mode_rules` in orchestrator instructions contained hardcoded example `"implementer-frontend"`, but:
1. This agent doesn't exist in default templates
2. Examples should be dynamic based on tenant's active agent templates

Alpha trial feedback: LLM tried to use the non-existent example agent name.

## Solution

Made the example dynamic by using actual agent names from `allowed_agent_names`:

```python
# Before (hardcoded)
"e.g., 'implementer-frontend'"

# After (dynamic)
example_agents = allowed_agent_names[:2]
example_str = ", ".join(f"'{n}'" for n in example_agents)
f"e.g., {example_str}"  # Results in: "e.g., 'orchestrator', 'implementer'"
```

## Files Modified

| File | Change |
|------|--------|
| `src/giljo_mcp/tools/tool_accessor.py` | Build dynamic example from allowed_agent_names |
| `src/giljo_mcp/thin_prompt_generator.py` | Replace hardcoded examples with placeholders |

## Testing

- Verified syntax with py_compile
- Tested dynamic logic with edge cases (empty list, single agent)

## Completion Notes

- Examples now match tenant's actual active agents
- Falls back to `'implementer'` if list empty
- Fills gap in 0384-0401 range
