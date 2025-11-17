# Handover 0313: Implement Priority System Refactor

**Status**: Not Started
**Tool**: Claude Code (CLI) - Requires backend and frontend changes
**Estimated Time**: 3-4 days
**Created**: 2025-11-17
**Assignee**: TDD Implementor Agent

## Executive Summary

Refactor priority system from "token trimming levels" to "importance emphasis signals". Based on v2.0 architecture designed in Handover 0312.

## Scope

**Backend Changes**:
1. Update `User.field_priority_config` to use 4-level priority (1-4 instead of 10/7/4/0)
2. Refactor `mission_planner.py` to pass priority metadata (not trimmed content)
3. Update `thin_prompt_generator.py` to emit priority signals in thin prompts
4. Update `defaults.py` with new priority semantics

**Frontend Changes**:
1. Update UserSettings.vue to show 4 priority levels (Critical/Important/Nice/Exclude)
2. Reduce UI cards from 13 → 6 (consolidate Tech Stack 6 cards → 1 card)
3. Update drag-and-drop zones for 4-level system

**Files Modified**:
- `src/giljo_mcp/mission_planner.py`
- `src/giljo_mcp/thin_prompt_generator.py`
- `src/giljo_mcp/config/defaults.py`
- `frontend/src/views/UserSettings.vue`
- `api/endpoints/users.py` (documentation)

**Estimated Time**: 3-4 days

## TDD Implementation Plan

**Phase 1: Write Failing Tests (RED)**
- Test priority metadata passed to orchestrator
- Test 4-level priority validation (1/2/3/4 only)
- Test UI renders 4 drag-drop zones

**Phase 2: Minimal Implementation (GREEN)**
- Update priority validation
- Refactor mission_planner to emit metadata
- Update UI components

**Phase 3: Refactor & Optimize (REFACTOR)**
- Clean up old priority logic
- Optimize drag-drop performance
- Add logging for priority debugging

## Dependencies

**Requires**: Handover 0312 (Architecture v2.0 Design) complete
**Blocks**: Handover 0314 (Depth Controls)

## Success Criteria

- [ ] Priority system uses 4 levels (1=Critical, 2=Important, 3=Nice, 4=Exclude)
- [ ] UserSettings.vue shows 6 cards (not 13)
- [ ] Thin prompts emit priority metadata
- [ ] All tests passing (>80% coverage)
- [ ] Migration from v1.0 priorities handled gracefully
