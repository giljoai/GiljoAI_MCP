# Handover 0415: Thin Client + Chapter-Based Orchestrator Protocol

**Status**: ✅ ARCHIVED
**Date**: 2026-01-15
**Branch**: `thin-prompt-trimming`
**Agent**: TDD Implementor
**Archived**: 2026-01-17

---

## Completion Summary

**What Was Built**:
- Chapter-based orchestrator protocol with 5 navigable chapters (CH1-CH5)
- `_build_orchestrator_protocol()` function in `orchestration.py`
- Thin staging prompt (113 tokens vs 725 tokens = 84% reduction)
- YOUR/THE labels for explicit identity in prompts

**Key Files Modified**:
- `src/giljo_mcp/tools/orchestration.py` (+417 lines - protocol builder)
- `src/giljo_mcp/tools/tool_accessor.py` (+12 lines - MCP integration)
- `src/giljo_mcp/thin_prompt_generator.py` (explicit labels)
- `tests/unit/test_orchestrator_protocol_chapters.py` (12 TDD tests)

**Commits**: `fd69ee19`, `46096145`

**Final Status**: Production ready. All 12 tests passing. Protocol verified via live MCP call.

## Objective

Integrate chapter-based orchestrator protocol into `get_orchestrator_instructions()` to enable structured, navigable guidance for orchestrators.

## Problem Solved

Previously, orchestrator instructions were provided as a monolithic block of text that was difficult to navigate during long sessions. The "rotation problem" meant critical information would scroll out of view and get lost in context.

## Solution Implemented

### Phase 1: Unit Tests (RED)
Created 12 comprehensive tests in `tests/unit/test_orchestrator_protocol_chapters.py`:
- Protocol structure tests (5 chapters, visual boxes, navigation hints)
- Mode-specific content tests (CLI vs multi-terminal)
- Token reduction tests (staging prompt < 150 tokens)
- Content quality tests (mission clarity, startup sequence, error handling)

### Phase 2: Protocol Builder (GREEN)
Added `_build_orchestrator_protocol()` function to `src/giljo_mcp/tools/orchestration.py`:
- Builds 5 structured chapters with visual boundaries (╔═══╗ boxes)
- Supports both CLI and multi-terminal execution modes
- Includes parameter substitution for project_id, orchestrator_id, tenant_key
- Optional CH5 inclusion for implementation reference

### Phase 3: MCP Integration (GREEN)
**Critical Fix**: Protocol must be added to `ToolAccessor.get_orchestrator_instructions()` in `tool_accessor.py` - this is the actual HTTP MCP endpoint, not the decorator version in `orchestration.py`.

```python
# src/giljo_mcp/tools/tool_accessor.py (lines 849-860)
from giljo_mcp.tools.orchestration import _build_orchestrator_protocol

cli_mode = execution_mode == "claude_code_cli"
orchestrator_protocol = _build_orchestrator_protocol(
    cli_mode=cli_mode,
    context_budget=execution.context_budget or 150000,
    project_id=str(project.id),
    orchestrator_id=job_id,
    tenant_key=tenant_key,
    include_implementation_reference=True
)
response["orchestrator_protocol"] = orchestrator_protocol
```

### Phase 4: Thin Prompt (GREEN)
Updated `generate_staging_prompt()` in `thin_prompt_generator.py` with explicit labels:

```
You are the ORCHESTRATOR for project "{project_name}"

YOUR IDENTITY (use these in all MCP calls):
  YOUR Agent ID: {agent_id}
  YOUR Job ID: {orchestrator_id}
  THE Project ID: {project_id}
  User's Tenant Key: {tenant_key}

MCP Server: {mcp_url}

START NOW: Call get_orchestrator_instructions(job_id='{orchestrator_id}', tenant_key='{tenant_key}')
Response includes orchestrator_protocol with your complete 5-chapter workflow guide.
```

## Protocol Structure

1. **CH1: Your Mission** (~427 tokens) - Role definition and phase awareness
2. **CH2: Startup Sequence** (~1454 tokens) - 7-step staging workflow
3. **CH3: Agent Spawning Rules** (~897 tokens) - Parameter requirements and mode-specific guidance
4. **CH4: Error Handling** (~884 tokens) - Common errors and recovery protocols
5. **CH5: Reference** (~1202 tokens) - Implementation phase reference (optional)

**Total Protocol Size**: ~4,864 tokens (all chapters included)

## Verification

### Unit Tests
All 12 tests pass:
```
tests/unit/test_orchestrator_protocol_chapters.py::test_build_orchestrator_protocol_returns_5_chapters PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_build_orchestrator_protocol_cli_mode_content PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_build_orchestrator_protocol_multi_terminal_mode_content PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_chapter_structure_has_visual_boxes PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_chapter_navigation_hint_present PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_include_implementation_reference_flag PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_orchestrator_protocol_in_instructions_response PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_staging_prompt_token_count_under_150 PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_staging_prompt_removes_inline_tasks PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_ch1_contains_mission_clarity PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_ch2_contains_startup_sequence PASSED
tests/unit/test_orchestrator_protocol_chapters.py::test_ch4_contains_error_handling PASSED
```

### Live MCP Verification
Confirmed `orchestrator_protocol` field appears in response via direct MCP call:
```
mcp__giljo-mcp__get_orchestrator_instructions(
    job_id='6ea5fdea-7313-4580-91a4-7fca969693dc',
    tenant_key='tk_uYhgYTmdb2AJ2KRVojtjOMFsiBhRv16y'
)
```

Response includes all 5 chapters and `navigation_hint`.

## Files Modified

1. **`src/giljo_mcp/tools/orchestration.py`** (+417 lines)
   - Added `_build_orchestrator_protocol()` function

2. **`src/giljo_mcp/tools/tool_accessor.py`** (+12 lines)
   - Added protocol generation to actual MCP HTTP endpoint

3. **`src/giljo_mcp/thin_prompt_generator.py`** (modified)
   - Updated `generate_staging_prompt()` with explicit YOUR/THE labels

4. **`tests/unit/test_orchestrator_protocol_chapters.py`** (new, 300+ lines)
   - 12 comprehensive TDD tests

## Token Impact

| Component | Before | After |
|-----------|--------|-------|
| Staging Prompt | ~725 tokens (inline) | ~113 tokens (thin) |
| Protocol (MCP) | N/A | ~4,864 tokens |
| **Total** | ~725 tokens | ~4,977 tokens |

**Justification**: Token increase is acceptable because:
- Protocol is **navigable** (chapters can be referenced by name)
- Protocol **prevents rotation problem** (guidance stays accessible)
- Protocol is **structured** (clear visual boundaries between sections)
- CH5 can be excluded to save ~1,202 tokens if needed

## Benefits

1. **Navigability**: Orchestrators can reference specific chapters during execution
2. **Clarity**: Visual boundaries prevent content from getting lost
3. **Scalability**: New guidance can be added to existing chapters
4. **Flexibility**: CH5 can be excluded for staging-only orchestrators
5. **Maintainability**: Protocol is centralized in one function
6. **Explicit Identity**: YOUR/THE labels make credential usage crystal clear

## Commits

1. `fd69ee19` - fix(mcp): Add orchestrator_protocol to ToolAccessor (the actual HTTP endpoint)
2. `46096145` - feat(thin-prompt): Add explicit YOUR/THE labels for orchestrator identity

## References

- **Previous Work**: Handover 0246a-c (Thin Client Architecture, Staging Workflow)
- **Architecture**: `docs/ORCHESTRATOR.md`
- **Testing**: `tests/unit/test_orchestrator_protocol_chapters.py`
