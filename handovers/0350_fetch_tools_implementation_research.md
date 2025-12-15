# Fetch Tools Implementation Research

## Session Date: 2025-12-15

## Context
User tested `get_orchestrator_instructions` MCP tool and discovered that multiple `fetch_tool` references in the orchestrator instructions point to non-existent MCP tools.

## Credentials Used for Testing
- Orchestrator ID: `6792fae5-c46b-4ed7-86d6-df58aa833df3`
- Tenant Key: `***REMOVED***`

## 9 Context Categories Confirmed
1. **project_context** - Project description (MANDATORY, always critical tier)
2. **product_core** - Product name, description, features
3. **tech_stack** - Programming languages, frameworks, databases
4. **architecture** - Architecture patterns, API style, design patterns
5. **testing** - Quality standards, strategy, frameworks
6. **vision_documents** - Vision document chunks (4-level depth: optional/light/medium/full)
7. **memory_360** - Project closeout summaries (mini-GitHub concept)
8. **git_history** - Aggregated git commits
9. **agent_templates** - Agent template library (2-level depth: type_only/full)

## Phantom Fetch Tools (Referenced but NOT Implemented)
These `fetch_tool` references exist in mission_planner.py but have NO corresponding MCP tools:

| Reference in Instructions | Status |
|--------------------------|--------|
| `fetch_vision_document(product_id, offset, limit)` | NOT IMPLEMENTED |
| `fetch_architecture(product_id)` | NOT IMPLEMENTED |
| `fetch_testing_config(product_id)` | NOT IMPLEMENTED |
| `fetch_360_memory(product_id, limit=N)` | NOT IMPLEMENTED |
| `fetch_git_history(product_id, limit)` | NOT IMPLEMENTED |
| `get_available_agents(tenant_key, active_only=True)` | EXISTS |

## User Decision: Keep Fetch Tool References
User explicitly requested to keep all fetch_tool references in the codebase as placeholders for future implementation.

## Duplicate Fetch Tool Issue (RESOLVED)
**Problem**: Two different signatures for memory_360:
- `fetch_360_memory(product_id, offset, limit)` - pagination style in `_get_memory_summary()`
- `fetch_360_memory(product_id, limit=N)` - simple style in caller

**User Choice**: Option B - Simple signature without pagination

**Fix Applied**: Removed pagination-style signature from `_get_memory_summary()` function in `mission_planner.py`

## Implementation Approach Question
User asked: "Should we implement one unified `fetch_context` tool or individual fetch tools per category?"

### Option A: Single Unified Tool (RECOMMENDED)
```python
fetch_context(
    tenant_key: str,
    product_id: str,
    category: Literal["vision_documents", "memory_360", "git_history",
                      "architecture", "testing", "tech_stack", "agent_templates"],
    offset: Optional[int] = None,  # For vision_documents pagination
    limit: Optional[int] = None    # Override user's depth if needed
)
```

**Benefits**:
- Respects user's depth settings from Settings -> Context UI
- Single point of maintenance
- Matches UI pattern (one panel, multiple categories)
- Multi-tenant safe

### Option B: Individual Tools (6-9 separate tools)
- `fetch_vision_document(product_id, offset, limit)`
- `fetch_360_memory(product_id, limit)`
- `fetch_git_history(product_id, limit)`
- `fetch_architecture(product_id)`
- `fetch_testing_config(product_id)`
- `fetch_tech_stack(product_id)`
- `fetch_agent_templates(tenant_key)`

### Option C: Hybrid Approach
- Keep `get_available_agents()` separate (already exists)
- Unified tool for others

## Key Files Reference

### `src/giljo_mcp/mission_planner.py`
- Contains `_build_context_with_priorities()` - main context builder
- Contains `_get_memory_summary()` - 360 memory helper
- Contains `_generate_fetch_commands()` - vision document fetch command generator
- Fetch tool references added at lines ~1691, ~1714, ~1767, ~1836-1911, ~1940, ~1956

### `api/endpoints/mcp_http.py`
- `handle_tools_list()` - MCP tool schema definitions (lines 123-531)
- `handle_tools_call()` - MCP tool routing (lines 534-663)
- Tool map at lines ~580-629

### `src/giljo_mcp/tools/tool_accessor.py`
- `ToolAccessor` class with all MCP tool implementations
- `get_orchestrator_instructions()` - main context delivery method

### `frontend/src/components/settings/ContextPriorityConfig.vue`
- UI for context settings with depth toggles
- Shows 9 context categories with priority and depth controls

## Next Steps (PENDING USER DECISION)
1. User needs to decide on implementation approach (A, B, or C)
2. If Option A chosen: Implement unified `fetch_context` in mcp_http.py and tool_accessor.py
3. Update mission_planner.py fetch_tool references to match chosen approach
4. Test with real orchestrator credentials

## Architecture Notes
- MCP over HTTP only (Stdio removed in Handover 0334)
- All tools require tenant_key for multi-tenant isolation
- User depth settings stored in User.context_config or ContextConfiguration table
- Vision documents support 4-level depth (optional/light/medium/full) with SUMY summaries
