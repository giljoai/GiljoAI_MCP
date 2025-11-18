# Handover 0315: Refactor to MCP Thin Client Architecture

**Status**: Not Started
**Tool**: Claude Code (CLI) - Requires MCP tool creation and prompt refactoring
**Estimated Time**: 5-6 days
**Created**: 2025-11-17
**Assignee**: TDD Implementor + Backend Tester Agents

## Executive Summary

Refactor from fat prompts (embedded context) to thin prompts (MCP-fetched context). Create 6 MCP tools for on-demand context retrieval. Based on v2.0 architecture from Handover 0312.

## Scope

**Create 6 New MCP Tools**:
1. `src/giljo_mcp/tools/get_vision_document.py`
2. `src/giljo_mcp/tools/get_360_memory.py`
3. `src/giljo_mcp/tools/get_git_history.py`
4. `src/giljo_mcp/tools/get_agent_templates.py`
5. `src/giljo_mcp/tools/get_tech_stack.py`
6. `src/giljo_mcp/tools/get_architecture.py`

**Refactor Existing Code**:
1. Update `thin_prompt_generator.py` to emit MCP instructions (not embedded context)
2. Reuse extraction methods from v1.0 (0301-0311) in MCP tools
3. Update orchestrator prompt template

**Code Reuse from v1.0** (60-80%):
- ✅ `_format_tech_stack()` → used in get_tech_stack()
- ✅ `_extract_config_field()` → used in get_architecture()
- ✅ `_extract_product_learnings()` → used in get_360_memory()
- ✅ `_get_relevant_vision_chunks()` → used in get_vision_document()
- ✅ `_format_agent_templates()` → used in get_agent_templates()
- ✅ `_inject_git_instructions()` → used in get_git_history()

**Files Created** (6 MCP tools):
- All in `src/giljo_mcp/tools/`

**Files Modified**:
- `src/giljo_mcp/thin_prompt_generator.py`
- `src/giljo_mcp/tools/__init__.py`
- `src/giljo_mcp/mission_planner.py` (integrate MCP tools)

**Estimated Time**: 5-6 days

## TDD Implementation Plan

**Phase 1: Create MCP Tools (RED)**
- Test get_vision_document() returns chunked content
- Test get_360_memory() returns N projects
- Test get_git_history() returns N commits
- Test all tools respect tenant_key isolation

**Phase 2: Refactor Thin Prompts (GREEN)**
- Test thin prompts emit MCP instructions
- Test thin prompts are <600 tokens
- Test orchestrator can fetch context via MCP

**Phase 3: Integration Testing (GREEN)**
- Test E2E flow: thin prompt → MCP fetch → orchestrator planning
- Test token counts match estimates
- Test graceful degradation (MCP unavailable)

## Dependencies

**Requires**: Handover 0314 (Depth Controls) complete
**Blocks**: Handover 0310 (Integration Testing)

## Success Criteria

- [ ] 6 MCP tools created and registered
- [ ] Thin prompts are <600 tokens
- [ ] MCP tools reuse 60-80% of v1.0 extraction code
- [ ] E2E workflow tested (thin → MCP → orchestrator)
- [ ] All tests passing (>80% coverage)
- [ ] Context prioritization still achieves 70%+ (via depth controls)
